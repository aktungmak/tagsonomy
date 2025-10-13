"""
Apply page for the RDFS Ontology Browser multipage app.

This module contains the implementation of the Apply page which allows users
to apply the current ontology state to Unity Catalog by creating and managing tags.
"""

import streamlit as st
import rdflib
import tagsonomy
import queries

from graph_manager import get_graph_manager


def preview_changes(graph: rdflib.Graph):
    """Preview what changes will be applied to Unity Catalog."""
    st.subheader("🔍 Preview Changes")

    try:
        # Get all securable to classes mappings
        securables = list(queries.securable_to_classes(graph))

        if not securables:
            st.info("No catalog objects with semantic assignments found in the ontology.")
            return []

        st.write(f"Found **{len(securables)}** catalog objects with semantic assignments:")

        # Display the changes in a nice table format
        changes_data = []
        for securable_type, securable_name, tags in securables:
            changes_data.append({
                "Type": securable_type,
                "Name": securable_name,
                "Tags to Apply": ", ".join(tags) if tags else "None"
            })

        st.dataframe(changes_data, use_container_width=True)

        return securables

    except Exception as e:
        st.error(f"Error previewing changes: {str(e)}")
        return []


def apply_changes(graph: rdflib.Graph, command: str):
    """Apply the changes to Unity Catalog using environment credentials."""
    try:
        tagsonomy.main(command, graph)
        return True, "Changes applied successfully!"
    except Exception as e:
        return False, f"Error applying changes: {str(e)}"


def apply_page():
    """Main apply page content."""
    st.title("⚙️ Apply Ontology to Unity Catalog")

    st.markdown("""
    This page allows you to apply the current state of your ontology to Unity Catalog
    by creating and managing tags on catalog objects (tables and columns).
    
    **How it works:**
    1. The system looks for catalog objects with semantic assignments in your ontology
    2. It generates tags based on the class hierarchy for each object
    3. You can preview the changes before applying them
    4. Tags are applied to Unity Catalog using the app's built-in authentication
    """)

    # Get the current graph
    try:
        graph = get_graph_manager().get_graph()

        # Add UC_CLASSES to the graph for processing
        graph.parse(data=tagsonomy.UC_CLASSES)

    except Exception as e:
        st.error(f"Error loading ontology: {str(e)}")
        return

    st.divider()

    st.subheader("🎯 Operation")

    operation = st.radio(
        "Choose operation:",
        ["update", "clear"],
        help="""
        - **Update**: Apply tags based on semantic assignments (adds new tags, removes outdated ones)
        - **Clear**: Remove all taxonomy-related tags from catalog objects
        """
    )

    st.divider()

    # Preview section
    if st.button("🔍 Preview Changes", type="secondary", use_container_width=True):
        if operation == "clear":
            st.info("Clear operation will remove all taxonomy-related tags from catalog objects.")
        else:
            securables = preview_changes(graph)
            if securables:
                st.session_state['preview_data'] = securables

    # Show cached preview if available
    if 'preview_data' in st.session_state and operation == "update":
        st.subheader("📋 Cached Preview")
        st.info("Preview from last run - click 'Preview Changes' to refresh")

        changes_data = []
        for securable_type, securable_name, tags in st.session_state['preview_data']:
            changes_data.append({
                "Type": securable_type,
                "Name": securable_name,
                "Tags to Apply": ", ".join(tags) if tags else "None"
            })
        st.dataframe(changes_data, use_container_width=True)

    st.divider()

    # Apply section
    st.subheader("🚀 Apply Changes")

    # Apply button
    if st.button(
            f"🚀 {operation.title()} Tags in Unity Catalog",
            type="primary",
            use_container_width=True
    ):

        # Show confirmation for destructive operations
        if operation == "clear":
            st.warning("⚠️ This will remove ALL taxonomy-related tags from your catalog objects!")

        # Apply the changes
        with st.spinner(f"Applying {operation} operation to Unity Catalog..."):
            success, message = apply_changes(graph, operation)

        if success:
            st.success(message)
            # Clear cached preview after successful apply
            if 'preview_data' in st.session_state:
                del st.session_state['preview_data']
        else:
            st.error(message)


# Define the page
page = st.Page(apply_page, title="Apply", icon="⚙️")
