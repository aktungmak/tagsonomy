"""
Catalog Objects page for the RDFS Ontology Browser multipage app.

This module contains the implementation of the Catalog Objects page which allows
users to browse catalog objects and add new ones from Databricks Unity Catalog.
"""

import streamlit as st
from rdflib import Graph, Literal
from databricks.sdk import WorkspaceClient
import sys
import os

# Add parent directory to path to import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from graph_manager import get_graph_manager, format_uri_display
from queries import (
    catalog_objects,
    catalog_object_attributes,
    catalog_object_semantic_assignments,
)

# Set page config
st.set_page_config(
    page_title="Catalog Objects - RDFS Ontology Browser",
    page_icon="📊",
    layout="wide"
)

st.title("📊 Catalog Objects")

w = WorkspaceClient()

# Get the graph manager
graph_manager = get_graph_manager()
graph = graph_manager.get_graph()


@st.dialog("Add Catalog Object", on_dismiss="rerun")
def add_catalog_object_dialog():
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


if st.button("Add Catalog Object", type="primary"):
    add_catalog_object_dialog()

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
    st.stop()

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
