"""
Concepts page for the RDFS Ontology Browser multipage app.

This module contains the implementation of the Concepts page which allows
users to browse and explore concepts (RDFS classes) in the ontology.
"""

import streamlit as st
from rdflib import Graph, Literal
import sys
import os

# Add parent directory to path to import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from graph_manager import get_graph_manager, format_uri_display
from queries import (
    rdfs_classes,
    class_attributes,
    subclasses,
    superclasses,
    related_properties,
    semantic_assignments,
)


def concepts_page():
    """Main concepts page content."""
    st.title("🏷️ Concepts")

    # Get the graph
    graph = get_graph_manager().get_graph()

    if st.button("New Concept", type="primary"):
        # TODO show a popup that lets the user create the new concept and write it to the graph
        st.info("New concept creation will be implemented later.")

    # Searchable class selection
    st.selectbox(
        "Search and select a concept:",
        options=rdfs_classes(graph),
        format_func=lambda c: f"{c.get('label') or format_uri_display(c['class_iri'])} - {c['class_iri']}",
        index=None,
        key="selected_concept",
        placeholder="Type to search by name, label, or IRI...",
    )

    # Only show details if a class is actually selected
    if st.session_state.selected_concept is None:
        st.stop()

    selected_concept = st.session_state.selected_concept
    st.markdown(f"**IRI:** `{selected_concept['class_iri']}`")

    # Show general class attributes
    attributes = class_attributes(graph, selected_concept["class_iri"])
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

        # Retrieve subclasses and superclasses
        subs = subclasses(graph, selected_concept["class_iri"])
        supers = superclasses(graph, selected_concept["class_iri"])

        if supers:
            st.write("**Parent Classes:**")
            for superclass in supers:
                st.button(str(superclass.get("label") or format_uri_display(superclass["class_iri"])),
                          on_click=lambda concept=superclass: setattr(st.session_state, 'selected_concept', concept))

        if subs:
            st.write("**Subclasses:**")
            for subclass in subs:
                st.button(str(subclass.get("label") or format_uri_display(subclass["class_iri"])),
                          on_click=lambda concept=subclass: setattr(st.session_state, 'selected_concept', concept))

        if not subs and not supers:
            st.info("No related classes found.")

    with col2:
        st.subheader("Related Properties")

        # Show related properties
        related_props = related_properties(graph, selected_concept["class_iri"])
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
        assignments = semantic_assignments(graph, selected_concept["class_iri"])
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


# Define the page
page = st.Page(concepts_page, title="Concepts", icon="🏷️")