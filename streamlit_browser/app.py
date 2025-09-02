"""
RDFS Ontology Browser - Main Application Entry Point

This is the main Streamlit application home page for the RDFS Ontology Browser.
Navigate to different pages using the sidebar.
"""

import streamlit as st
from graph_manager import get_graph_manager

# Set page config
st.set_page_config(
    page_title="Ontology Browser",
    page_icon="🔍",
    layout="wide"
)

st.title("🔍 Ontology Browser")

st.markdown("""
Welcome to the Ontology Browser! This tool allows you to explore and manage ontologies and their relationships with catalog objects.

## Navigation

Use the sidebar to navigate to different sections:

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
        st.switch_page("pages/1_Concepts.py")

with col2:
    if st.button("🔗 Browse Properties", type="primary", use_container_width=True):
        st.switch_page("pages/2_Properties.py")

with col3:
    if st.button("📊 Manage Catalog Objects", type="primary", use_container_width=True):
        st.switch_page("pages/3_Catalog_Objects.py")