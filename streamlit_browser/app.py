"""
RDFS Ontology Browser - Main Application Entry Point

This is the main Streamlit application that brings together all the different
components of the RDFS Ontology Browser.
"""

import streamlit as st
from graph_manager import get_graph_manager
from concepts_tab import concepts_tab
from properties_tab import properties_tab
from catalog_objects_tab import catalog_objects_tab
from apply_tab import apply_tab


def main():
    """Main application entry point."""
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
        apply_tab()


if __name__ == "__main__":
    main()