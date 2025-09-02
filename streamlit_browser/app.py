"""
Ontology Browser - Main Application Entry Point

This is the main Streamlit application that defines the navigation structure
and routing for the Ontology Browser multipage app.
"""

import streamlit as st

# Set page config
st.set_page_config(
    page_title="Ontology Browser",
    page_icon="🔍",
    layout="wide"
)

# Define pages with custom titles and icons
def start_page():
    """Home/Start page content."""
    from graph_manager import get_graph_manager
    
    st.title("🔍 Ontology Browser")

    st.markdown("""
    Welcome to the Ontology Browser! This tool allows you to explore and manage ontologies and their relationships with catalog objects.

    ## Navigation

    Use the sidebar to navigate to different sections:

    - **🏷️ Start** - This welcome page with overview and statistics
    - **🏷️ Concepts** - Browse and explore concepts (RDFS classes) in the ontology
    - **🔗 Properties** - Browse and explore properties in the ontology
    - **📊 Catalog Objects** - Browse catalog objects and add new ones from Databricks Unity Catalog
    - **⚙️ Apply** - Apply configurations and transformations (coming soon)
    """)

    # Display ontology statistics
    st.subheader("📈 Ontology Statistics")

    try:
        # Get the graph manager
        graph_manager = get_graph_manager()
        graph = graph_manager.get_graph()
        
        # Get basic statistics
        total_triples = len(graph)
        
        # Count different types of entities
        from queries import rdfs_classes, rdfs_properties, catalog_objects
        
        classes = rdfs_classes(graph)
        properties = rdfs_properties(graph)
        catalog_objs = catalog_objects(graph)
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total Triples", total_triples)
        
        with col2:
            st.metric("Concepts", len(classes))
        
        with col3:
            st.metric("Properties", len(properties))
        
        with col4:
            st.metric("Catalog Objects", len(catalog_objs))

    except Exception as e:
        st.error(f"Error loading ontology statistics: {str(e)}")
        st.info("Make sure an ontology is properly loaded.")

    st.divider()

    st.markdown("""
    ## Quick Links

    Ready to get started? Choose one of the options below:
    """)

    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("🏷️ Browse Concepts", type="primary", use_container_width=True):
            st.switch_page("pages/concepts.py")

    with col2:
        if st.button("🔗 Browse Properties", type="primary", use_container_width=True):
            st.switch_page("pages/properties.py")

    with col3:
        if st.button("📊 Manage Catalog Objects", type="primary", use_container_width=True):
            st.switch_page("pages/catalog_objects.py")

# Import pages from modules
from pages.concepts import page as concepts_page
from pages.properties import page as properties_page
from pages.catalog_objects import page as catalog_objects_page
from pages.apply import page as apply_page

# Define start page
start = st.Page(start_page, title="Start", icon="🏠")

# Create navigation
pg = st.navigation([start, concepts_page, properties_page, catalog_objects_page, apply_page])

# Run the selected page
pg.run()