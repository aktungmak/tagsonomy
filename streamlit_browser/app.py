import streamlit as st
import rdflib
from rdflib import Graph, Namespace, URIRef, Literal
from rdflib.namespace import RDF, RDFS
import os
from pathlib import Path
import re
from databricks.sdk import WorkspaceClient

# Define namespaces
UC = Namespace("http://databricks.com/ontology/uc/")
EXAMPLE = Namespace("http://example.com/animals/")

w = WorkspaceClient()


class GraphManager:
    """
    Manages the RDF graph with persistence capabilities.
    Handles both reading and writing operations, automatically saving changes to file.
    """

    def __init__(self, file_path: str = None):
        self.graph = Graph()
        self.current_files = []

        if file_path is None:
            # Load default taxonomies
            parent_dir = Path(__file__).parent.parent
            example_files = [
                parent_dir / "example_taxonomies" / "small.ttl",
                parent_dir / "example_taxonomies" / "aerospace.ttl",
            ]

            for file in example_files:
                if file.exists():
                    self.graph.parse(str(file))
                    self.current_files.append(str(file))
        else:
            if os.path.exists(file_path):
                self.graph.parse(file_path)
                self.current_files.append(file_path)

    def add_catalog_object(self, name: str, object_type: str, iri: str = None):
        """
        Add a new catalog object to the graph.
        
        Args:
            name: The name of the catalog object
            object_type: Either 'table' or 'column'  
            iri: Optional IRI, if not provided will be auto-generated
        """
        if iri is None:
            # Auto-generate IRI from name
            iri = self._generate_iri_from_name(name)

        # Convert to URIRef
        obj_uri = URIRef(iri)

        # Add type triple
        if object_type == 'table':
            self.graph.add((obj_uri, RDF.type, UC.Table))
        elif object_type == 'column':
            self.graph.add((obj_uri, RDF.type, UC.Column))
        else:
            raise ValueError(f"Invalid object type: {object_type}. Must be 'table' or 'column'")

        # Add name triple
        self.graph.add((obj_uri, UC.name, Literal(name)))

        # Save changes to file
        self._save_changes()

        return obj_uri

    def _generate_iri_from_name(self, name: str) -> str:
        """Generate an IRI from a catalog object name."""
        # Clean the name to make it IRI-safe
        clean_name = re.sub(r'[^\w\-_.]', '_', name.lower())
        clean_name = re.sub(r'_+', '_', clean_name).strip('_')

        # Use the EXAMPLE namespace for new objects
        return str(EXAMPLE[clean_name])

    def _save_changes(self):
        """Save the current graph state to the primary file."""
        if self.current_files:
            # Save to the first (primary) file
            primary_file = self.current_files[0]
            self.graph.serialize(destination=primary_file, format='turtle')

    def get_graph(self) -> Graph:
        """Get the underlying RDF graph."""
        return self.graph


@st.cache_resource
def get_graph_manager():
    """Get the cached GraphManager instance."""
    return GraphManager()


def save_graph_to_file(graph: Graph, file_path: str):
    """Save the current graph state to a turtle file."""
    graph.serialize(destination=file_path, format='turtle')


def rdfs_classes(graph: Graph):
    """Get all RDFS classes from the graph."""
    query = """
    SELECT DISTINCT ?class ?label
    WHERE {
        {
            ?class a rdfs:Class .
        }
        UNION
        {
            ?class rdfs:subClassOf ?other .
        }
        OPTIONAL { ?class rdfs:label ?label }
    }
    """
    return list(graph.query(query))


def subclasses(graph: Graph, class_uri: URIRef):
    """Get direct subclasses of a given class."""
    query = """
    SELECT DISTINCT ?subclass ?label
    WHERE {
        ?subclass rdfs:subClassOf ?class .
        OPTIONAL { ?subclass rdfs:label ?label }
    }
    """
    return list(graph.query(query, initBindings={'class': class_uri}))


def superclasses(graph: Graph, class_uri: URIRef):
    """Get direct superclasses of a given class."""
    query = """
    SELECT DISTINCT ?superclass ?label
    WHERE {
        ?class rdfs:subClassOf ?superclass .
        OPTIONAL { ?superclass rdfs:label ?label }
    }
    ORDER BY ?label ?superclass
    """
    return list(graph.query(query, initBindings={'class': class_uri}))


def rdfs_properties(graph: Graph):
    """Get all RDFS properties from the graph."""
    query = """
    SELECT DISTINCT ?property ?label ?domain ?range
    WHERE {
        {
            ?property a rdfs:Property .
        }
        UNION
        {
            ?property rdfs:subPropertyOf ?other .
        }
        OPTIONAL { ?property rdfs:label ?label }
        OPTIONAL { ?property rdfs:domain ?domain }
        OPTIONAL { ?property rdfs:range ?range }
    }
    """
    return list(graph.query(query))


def class_attributes(graph: Graph, class_uri: URIRef):
    """Get all attributes where this class is the subject."""
    query = """
    SELECT DISTINCT ?predicate ?object
    WHERE {
        ?class ?predicate ?object .
        FILTER(?predicate != rdf:type && ?predicate != rdfs:subClassOf)
    }
    ORDER BY ?predicate ?object
    """
    return list(graph.query(query, initBindings={'class': class_uri}))


def semantic_assignments(graph: Graph, class_uri: URIRef):
    """Get catalog objects that have semantic assignments to this class."""
    query = """
    SELECT DISTINCT ?object ?name
    WHERE {
        ?object uc:semanticAssignment ?class .
        OPTIONAL { ?object uc:name ?name }
    }
    ORDER BY ?name ?object
    """
    return list(graph.query(query, initBindings={'class': class_uri}))


def related_properties(graph: Graph, class_uri: URIRef):
    """Get properties that have this class as domain or range."""
    query = """
    SELECT DISTINCT ?property ?predicate ?predicate_label
    WHERE {
        {
            ?property rdfs:domain ?class .
            BIND("rdfs:domain" as ?predicate)
        }
        UNION
        {
            ?property rdfs:range ?class .
            BIND("rdfs:range" as ?predicate)
        }
        OPTIONAL { ?property rdfs:label ?predicate_label }
    }
    ORDER BY ?property ?predicate
    """
    return list(graph.query(query, initBindings={'class': class_uri}))


def subproperties(graph: Graph, property_uri: URIRef):
    """Get direct subproperties of a given property."""
    query = """
    SELECT DISTINCT ?subproperty ?label
    WHERE {
        ?subproperty rdfs:subPropertyOf ?property .
        OPTIONAL { ?subproperty rdfs:label ?label }
    }
    ORDER BY ?label ?subproperty
    """
    return list(graph.query(query, initBindings={'property': property_uri}))


def superproperties(graph: Graph, property_uri: URIRef):
    """Get direct superproperties of a given property."""
    query = """
    SELECT DISTINCT ?superproperty ?label
    WHERE {
        ?property rdfs:subPropertyOf ?superproperty .
        OPTIONAL { ?superproperty rdfs:label ?label }
    }
    ORDER BY ?label ?superproperty
    """
    return list(graph.query(query, initBindings={'property': property_uri}))


def property_attributes(graph: Graph, property_uri: URIRef):
    """Get all attributes where this property is the subject."""
    query = """
    SELECT DISTINCT ?predicate ?object
    WHERE {
        ?property ?predicate ?object .
        FILTER(?predicate != rdf:type && ?predicate != rdfs:subPropertyOf && 
               ?predicate != rdfs:domain && ?predicate != rdfs:range)
    }
    ORDER BY ?predicate ?object
    """
    return list(graph.query(query, initBindings={'property': property_uri}))


def related_concepts(graph: Graph, property_uri: URIRef):
    """Get concepts that are related to this property via domain and range."""
    query = """
    SELECT DISTINCT ?concept ?predicate ?label
    WHERE {
        {
            ?property rdfs:domain ?concept .
            BIND("rdfs:domain" as ?predicate)
        }
        UNION
        {
            ?property rdfs:range ?concept .
            BIND("rdfs:range" as ?predicate)
        }
        OPTIONAL { ?concept rdfs:label ?label }
    }
    ORDER BY ?predicate ?label ?concept
    """
    return list(graph.query(query, initBindings={'property': property_uri}))


def search_properties_by_name(graph: Graph, search_term: str):
    """Search for properties by name/label."""
    if not search_term:
        return rdfs_properties(graph)

    search_term = search_term.lower()
    properties = rdfs_properties(graph)

    # Filter properties that match the search term
    filtered = []
    for prop_uri, label, domain, range_uri in properties:
        prop_name = str(prop_uri).split('/')[-1].split('#')[-1].lower()
        label_text = str(label).lower() if label else ""

        if search_term in prop_name or search_term in label_text:
            filtered.append((prop_uri, label, domain, range_uri))

    return filtered


def search_classes_by_name(graph: Graph, search_term: str):
    """Search for classes by name/label."""
    if not search_term:
        return rdfs_classes(graph)

    search_term = search_term.lower()
    classes = rdfs_classes(graph)

    # Filter classes that match the search term
    filtered = []
    for class_uri, label in classes:
        class_name = str(class_uri).split('/')[-1].split('#')[-1].lower()
        label_text = str(label).lower() if label else ""

        if search_term in class_name or search_term in label_text:
            filtered.append((class_uri, label))

    return filtered


def catalog_objects(graph: Graph):
    """Get all catalog objects (uc:Table and uc:Column)."""
    query = """
    SELECT DISTINCT ?object ?type ?name
    WHERE {
        ?object a ?type .
        FILTER(?type = uc:Table || ?type = uc:Column)
        OPTIONAL { ?object uc:name ?name }
    }
    """
    return list(graph.query(query))


def catalog_object_attributes(graph: Graph, object_uri: URIRef):
    """Get all attributes where this catalog object is the subject."""
    query = """
    SELECT DISTINCT ?predicate ?object
    WHERE {
        ?catalog_object ?predicate ?object .
        FILTER(?predicate != rdf:type && ?predicate != uc:semanticAssignment)
    }
    """
    return list(graph.query(query, initBindings={'catalog_object': object_uri}))


def catalog_object_semantic_assignments(graph: Graph, object_uri: URIRef):
    """Get classes that this catalog object is semantically assigned to."""
    query = """
    SELECT DISTINCT ?class ?label
    WHERE {
        ?catalog_object uc:semanticAssignment ?class .
        OPTIONAL { ?class rdfs:label ?label }
    }
    """
    return list(graph.query(query, initBindings={'catalog_object': object_uri}))


# TODO use this approach for all the search functions
def search_catalog_objects_by_name(graph: Graph, search_term: str):
    """Search for catalog objects by name."""
    if not search_term:
        return catalog_objects(graph)

    search_term = search_term.lower()
    catalog_objects = catalog_objects(graph)

    # Filter catalog objects that match the search term
    filtered = []
    for obj_uri, obj_type, name in catalog_objects:
        obj_name = str(obj_uri).split('/')[-1].split('#')[-1].lower()
        name_text = str(name).lower() if name else ""

        if search_term in obj_name or search_term in name_text:
            filtered.append((obj_uri, obj_type, name))

    return filtered


def format_uri_display(uri):
    """Format URI for display - show the local name."""
    if hasattr(uri, 'split'):
        return str(uri).split('/')[-1].split('#')[-1]
    return str(uri)


@st.dialog("Add Catalog Object", on_dismiss="rerun")
def add_catalog_object_dialog(graph_manager):
    """Display a dialog for creating a new catalog object using Databricks Unity Catalog."""

    st.write("Add a catalog object from Unity Catalog:")

    # Object Type Selection
    object_type = st.radio(
        "Object Type",
        options=["Table", "Column"],
        help="Select whether you want to add a Table or Column object",
        horizontal=True
    )

    # Initialize session state for caching API results
    if 'catalogs' not in st.session_state:
        st.session_state.catalogs = None
    if 'schemas' not in st.session_state:
        st.session_state.schemas = {}
    if 'tables' not in st.session_state:
        st.session_state.tables = {}
    if 'columns' not in st.session_state:
        st.session_state.columns = {}

    # Catalog Selection
    if st.session_state.catalogs is None:
        try:
            with st.spinner("Loading catalogs..."):
                catalogs = w.catalogs.list()
                st.session_state.catalogs = [catalog.name for catalog in catalogs]
        except Exception as e:
            st.error(f"Error fetching catalogs: {str(e)}")
            st.error("Make sure you have Databricks authentication configured and Unity Catalog access.")
            return
    
    if not st.session_state.catalogs:
        st.error("No catalogs found. Make sure you have access to Unity Catalog.")
        return
        
    selected_catalog = st.selectbox(
        "Catalog",
        options=[""] + st.session_state.catalogs,
        help="Select the catalog"
    )

    if not selected_catalog:
        st.info("Please select a catalog to continue")
        return

    # Schema Selection
    schema_key = selected_catalog
    if schema_key not in st.session_state.schemas:
        try:
            with st.spinner(f"Loading schemas for {selected_catalog}..."):
                schemas = w.schemas.list(catalog_name=selected_catalog)
                st.session_state.schemas[schema_key] = [schema.name for schema in schemas]
        except Exception as e:
            st.error(f"Error fetching schemas: {str(e)}")
            return
    
    schema_names = st.session_state.schemas[schema_key]
    if not schema_names:
        st.error(f"No schemas found in catalog '{selected_catalog}'")
        return
        
    selected_schema = st.selectbox(
        "Schema",
        options=[""] + schema_names,
        help="Select the schema"
    )

    if not selected_schema:
        st.info("Please select a schema to continue")
        return

    # Table Selection
    table_key = f"{selected_catalog}.{selected_schema}"
    if table_key not in st.session_state.tables:
        try:
            with st.spinner(f"Loading tables for {table_key}..."):
                tables = w.tables.list(catalog_name=selected_catalog, schema_name=selected_schema)
                st.session_state.tables[table_key] = [table.name for table in tables]
        except Exception as e:
            st.error(f"Error fetching tables: {str(e)}")
            return
    
    table_names = st.session_state.tables[table_key]
    if not table_names:
        st.error(f"No tables found in schema '{selected_catalog}.{selected_schema}'")
        return
        
    selected_table = st.selectbox(
        "Table",
        options=[""] + table_names,
        help="Select the table"
    )

    if not selected_table:
        st.info("Please select a table to continue")
        return

    # Column Selection (for Column object type only)
    selected_column = None
    if object_type == "Column":
        column_key = f"{selected_catalog}.{selected_schema}.{selected_table}"
        if column_key not in st.session_state.columns:
            try:
                with st.spinner(f"Loading columns for {column_key}..."):
                    table_info = w.tables.get(column_key)
                    st.session_state.columns[column_key] = [col.name for col in table_info.columns] if table_info.columns else []
            except Exception as e:
                st.error(f"Error fetching columns: {str(e)}")
                return
        
        column_names = st.session_state.columns[column_key]
        if not column_names:
            st.error(f"No columns found in table '{column_key}'")
            return
            
        selected_column = st.selectbox(
            "Column",
            options=[""] + column_names,
            help="Select a column"
        )

        if not selected_column:
            st.info("Please select a column to continue")
            return

    # Add Object button
    if st.button("Add Object", type="primary"):
        # Determine object name and type
        if object_type == "Table":
            object_name = f"{selected_catalog}.{selected_schema}.{selected_table}"
            object_type_lower = "table"
        else:  # Column
            object_name = f"{selected_catalog}.{selected_schema}.{selected_table}.{selected_column}"
            object_type_lower = "column"
        
        try:
            # Add the object to the graph
            new_object_uri = graph_manager.add_catalog_object(
                name=object_name,
                object_type=object_type_lower
            )
            
            st.success(f"Successfully added {object_type}: {object_name}")
            st.balloons()
            st.rerun()
            
        except Exception as e:
            st.error(f"Error adding catalog object: {str(e)}")


def main():
    st.set_page_config(
        page_title="RDFS Ontology Browser",
        page_icon="🔍",
        layout="wide"
    )

    st.title("🔍 RDFS Ontology Browser")

    # Get the graph manager
    graph_manager = get_graph_manager()
    # TODO should use graph_manager.get_graph() instead of graph
    graph = graph_manager.get_graph()

    # Create tabs
    tab1, tab2, tab3, tab4 = st.tabs(["Concepts", "Properties", "Catalog Objects", "Apply"])

    with tab1:
        st.header("Concepts")
        concepts_tab(graph)

    with tab2:
        st.header("Properties")
        properties_tab(graph)

    with tab3:
        st.header("Catalog Objects")
        catalog_objects_tab(graph, graph_manager)

    with tab4:
        st.header("Apply")
        st.info("This tab is a placeholder and will be implemented later.")


def concepts_tab(graph: Graph):
    """Render the Concepts tab."""

    if st.button("New Concept", type="primary"):
        # TODO show a popup that lets the user create the new concept and write it to the graph
        st.info("New concept creation will be implemented later.")

    # Get all classes for the searchable dropdown
    all_classes = rdfs_classes(graph)

    # Create class options and mapping
    class_options = []
    class_mapping = {}

    for class_uri, label in all_classes:
        display_name = str(label) if label else format_uri_display(class_uri)
        full_display = f"{display_name} ({format_uri_display(class_uri)})"
        class_options.append(full_display)
        class_mapping[full_display] = class_uri

    # Searchable class selection
    selected_display = st.selectbox(
        "Search and select a concept:",
        options=class_options,
        index=None,
        placeholder="Type to search by name, label, or IRI...",
    )

    # Only show details if a class is actually selected
    if selected_display is None:
        return

    selected_class = class_mapping[selected_display]
    st.markdown(f"**IRI:** `{selected_class}`")

    # Show general class attributes
    attributes = class_attributes(graph, selected_class)
    if attributes:
        for predicate, obj in attributes:
            pred_name = format_uri_display(predicate)
            obj_name = format_uri_display(obj) if not isinstance(obj, Literal) else str(obj)
            st.write(f"**{pred_name}:** {obj_name}")
    else:
        st.info("No additional attributes found.")

    # Create three columns for the different sections
    col1, col2, col3 = st.columns(3)

    with col1:
        st.subheader("Concept Hierarchy")

        # Show subclasses and superclasses
        subs = subclasses(graph, selected_class)
        supers = superclasses(graph, selected_class)

        if supers:
            st.write("**Parent Classes:**")
            for super_uri, super_label in supers:
                display_name = str(super_label) if super_label else format_uri_display(super_uri)
                st.write(f"- {display_name}")

        if subs:
            st.write("**Subclasses:**")
            for sub_uri, sub_label in subs:
                display_name = str(sub_label) if sub_label else format_uri_display(sub_uri)
                st.write(f"- {display_name}")

        if not subs and not supers:
            st.info("No related classes found.")

    with col2:
        st.subheader("Related Properties")

        # Show related properties
        related_props = related_properties(graph, selected_class)
        if related_props:
            for prop_uri, predicate, predicate_label in related_props:
                prop_name = format_uri_display(prop_uri)
                relation_type = str(predicate)
                st.write(f"**{prop_name}** ({relation_type})")
        else:
            st.info("No related properties found.")

    with col3:
        st.subheader("Linked Catalog Objects")

        # Show linked catalog objects
        assignments = semantic_assignments(graph, selected_class)
        if assignments:
            for obj_uri, name in assignments:
                obj_name = str(name) if name else format_uri_display(obj_uri)
                st.write(f"- {obj_name}")
        else:
            st.info("No catalog objects assigned.")

    st.divider()
    # Assign to Object button
    if st.button("Assign to Object", type="secondary"):
        st.info("Assign to Object functionality will be implemented later.")


def properties_tab(graph: Graph):
    """Render the Properties tab."""

    if st.button("New Property", type="primary"):
        # TODO show a popup that lets the user create the new property and write it to the graph
        st.info("New property creation will be implemented later.")

    # Get all properties for the searchable dropdown
    all_properties = rdfs_properties(graph)

    # Create property options and mapping
    property_options = []
    property_mapping = {}

    for prop_uri, label, domain_uri, range_uri in all_properties:
        display_name = str(label) if label else format_uri_display(prop_uri)
        full_display = f"{display_name} ({format_uri_display(prop_uri)})"
        property_options.append(full_display)
        property_mapping[full_display] = prop_uri

    # Searchable property selection
    selected_display = st.selectbox(
        "Search and select a property:",
        options=property_options,
        index=None,
        placeholder="Type to search by name, label, or IRI...",
    )

    # Only show details if a property is actually selected
    if selected_display is None:
        return

    selected_property = property_mapping[selected_display]
    st.markdown(f"**IRI:** `{selected_property}`")

    # Show general property attributes
    attributes = property_attributes(graph, selected_property)
    if attributes:
        for predicate, obj in attributes:
            # TODO show the full IRI in brackets after the name
            pred_name = format_uri_display(predicate)
            obj_name = format_uri_display(obj) if not isinstance(obj, Literal) else str(obj)
            st.write(f"**{pred_name}:** {obj_name}")
    else:
        st.info("No additional attributes found.")

    # Create three columns for the different sections
    col1, col2, col3 = st.columns(3)

    with col1:
        st.subheader("Property Hierarchy")

        # Show subproperties and superproperties
        subs = subproperties(graph, selected_property)
        supers = superproperties(graph, selected_property)

        if supers:
            st.write("**Parent Properties:**")
            for super_uri, super_label in supers:
                display_name = str(super_label) if super_label else format_uri_display(super_uri)
                st.write(f"- {display_name}")

        if subs:
            st.write("**Subproperties:**")
            for sub_uri, sub_label in subs:
                display_name = str(sub_label) if sub_label else format_uri_display(sub_uri)
                st.write(f"- {display_name}")

        if not subs and not supers:
            st.info("No related properties found.")

    with col2:
        st.subheader("Related Concepts")

        # Show related concepts via domain and range
        rel_concepts = related_concepts(graph, selected_property)
        if rel_concepts:
            for concept_uri, predicate, label in rel_concepts:
                concept_name = str(label) if label else format_uri_display(concept_uri)
                relation_type = "Domain" if "domain" in str(predicate) else "Range"
                st.write(f"**{relation_type}:** {concept_name}")
        else:
            st.info("No related concepts found.")

    with col3:
        st.subheader("Domain & Range Details")

        # Get domain and range information from the original property data
        for prop_uri, label, domain_uri, range_uri in all_properties:
            if prop_uri == selected_property:
                if domain_uri:
                    st.write(f"**Domain:** {domain_uri}")
                if range_uri:
                    st.write(f"**Range:** {range_uri}")
                if not domain_uri and not range_uri:
                    st.info("No domain or range specified.")
                break

    st.divider()
    # Assign to Catalog Object button
    if st.button("Assign to Catalog Object", type="secondary"):
        st.info("Assign to Catalog Object functionality will be implemented later.")


def catalog_objects_tab(graph: Graph, graph_manager):
    """Render the Catalog Objects tab."""

    if st.button("Add Catalog Object", type="primary"):
        add_catalog_object_dialog(graph_manager)

    # Get all catalog objects for the searchable dropdown
    all_catalog_objects = catalog_objects(graph)

    # Create catalog object options and mapping
    catalog_options = []
    catalog_mapping = {}

    for obj_uri, obj_type, name in all_catalog_objects:
        display_name = str(name) if name else format_uri_display(obj_uri)
        type_name = format_uri_display(obj_type)
        full_display = f"{display_name} ({type_name})"
        catalog_options.append(full_display)
        catalog_mapping[full_display] = (obj_uri, obj_type, name)

    # Searchable catalog object selection
    selected_display = st.selectbox(
        "Search and select a catalog object:",
        options=catalog_options,
        index=None,
        placeholder="Type to search by name or type (table/column)...",
    )

    # Only show details if a catalog object is actually selected
    if selected_display is None:
        return

    selected_object, selected_type, selected_name = catalog_mapping[selected_display]
    st.markdown(f"**IRI:** `{selected_object}`")

    # Show general catalog object attributes
    attributes = catalog_object_attributes(graph, selected_object)
    if attributes:
        for predicate, obj in attributes:
            pred_name = format_uri_display(predicate)
            obj_name = format_uri_display(obj) if not isinstance(obj, Literal) else str(obj)
            print(pred_name, obj_name)
            st.write(f"**{pred_name}:** {obj_name}")
    else:
        st.info("No additional attributes found.")

    st.subheader("Semantic Assignments")

    # Show semantic assignments
    assignments = catalog_object_semantic_assignments(graph, selected_object)
    if assignments:
        for class_uri, label in assignments:
            class_name = str(label) if label else format_uri_display(class_uri)
            st.write(f"- {class_name}")
    else:
        st.info("No semantic assignments found.")

    st.divider()

    # Assignment button
    if st.button("Assign...", type="secondary"):
        st.info("Assignment functionality will be implemented later.")


if __name__ == "__main__":
    main()
