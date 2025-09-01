import streamlit as st
import rdflib
from rdflib import Graph, Namespace, URIRef, Literal
from rdflib.namespace import RDF, RDFS
import os
from pathlib import Path
import re

# Define namespaces
UC = Namespace("http://databricks.com/ontology/uc/")
EXAMPLE = Namespace("http://example.com/animals/")


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
            self.graph.add((obj_uri, RDF.type, UC.table))
        elif object_type == 'column':
            self.graph.add((obj_uri, RDF.type, UC.column))
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
    """Get all catalog objects (uc:table and uc:column)."""
    query = """
    SELECT DISTINCT ?object ?type ?name
    WHERE {
        ?object a ?type .
        FILTER(?type = uc:table || ?type = uc:column)
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


@st.dialog("Create New Catalog Object")
def create_new_catalog_object_dialog(graph_manager):
    """Display a dialog for creating a new catalog object."""
    
    # Form for creating new catalog object
    with st.form("new_catalog_object_form"):
        st.write("Enter details for the new catalog object:")
        
        # Object name input
        object_name = st.text_input(
            "Object Name *",
            placeholder="e.g., users.my_schema.my_table",
            help="The name of the catalog object (required)"
        )
        
        # Object type selection
        object_type = st.selectbox(
            "Object Type *",
            options=["table", "column"],
            help="Select whether this is a table or column"
        )
        
        # IRI input with auto-generation
        auto_generate_iri = st.checkbox(
            "Auto-generate IRI",
            value=True,
            help="Automatically generate an IRI based on the object name"
        )
        
        if auto_generate_iri:
            if object_name:
                # Preview the auto-generated IRI
                preview_iri = graph_manager._generate_iri_from_name(object_name)
                st.text_input(
                    "Generated IRI (preview)",
                    value=preview_iri,
                    disabled=True,
                    help="This IRI will be auto-generated from the object name"
                )
                custom_iri = None
            else:
                st.info("Enter an object name to see the auto-generated IRI preview")
                custom_iri = None
        else:
            custom_iri = st.text_input(
                "Custom IRI *",
                placeholder="e.g., http://example.com/animals/my_custom_object",
                help="Enter a custom IRI for this object"
            )
        
        # Form submission
        col1, col2 = st.columns(2)
        
        with col1:
            submitted = st.form_submit_button("Create Object", type="primary")
        
        with col2:
            if st.form_submit_button("Cancel", type="secondary"):
                st.rerun()
        
        # Handle form submission
        if submitted:
            # Validation
            if not object_name:
                st.error("Object name is required")
                return
            
            if not auto_generate_iri and not custom_iri:
                st.error("Custom IRI is required when auto-generation is disabled")
                return
            
            try:
                # Create the catalog object
                iri_to_use = custom_iri if not auto_generate_iri else None
                new_object_uri = graph_manager.add_catalog_object(
                    name=object_name,
                    object_type=object_type,
                    iri=iri_to_use
                )
                
                st.success(f"Successfully created {object_type}: {object_name}")
                st.success(f"IRI: {new_object_uri}")
                
                # Wait a moment then refresh the page to show the new object
                st.balloons()
                st.rerun()
                
            except Exception as e:
                st.error(f"Error creating catalog object: {str(e)}")


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

    if st.button("New Catalog Object", type="primary"):
        create_new_catalog_object_dialog(graph_manager)

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
