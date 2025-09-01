"""
Properties tab functionality for the RDFS Ontology Browser.

This module contains the implementation of the Properties tab which allows
users to browse and explore properties in the ontology.
"""

import streamlit as st
from rdflib import Graph, Literal
from queries import (
    rdfs_properties,
    property_attributes,
    subproperties,
    superproperties,
    related_concepts,
)
from graph_manager import format_uri_display


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
