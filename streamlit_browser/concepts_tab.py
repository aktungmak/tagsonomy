"""
Concepts tab functionality for the RDFS Ontology Browser.

This module contains the implementation of the Concepts tab which allows
users to browse and explore concepts (RDFS classes) in the ontology.
"""

import streamlit as st
from rdflib import Graph, Literal
from queries import (
    rdfs_classes,
    class_attributes,
    subclasses,
    superclasses,
    related_properties,
    semantic_assignments,
)
from graph_manager import format_uri_display


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
