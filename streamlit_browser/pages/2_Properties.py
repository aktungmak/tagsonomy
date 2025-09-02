"""
Properties page for the RDFS Ontology Browser multipage app.

This module contains the implementation of the Properties page which allows
users to browse and explore properties in the ontology.
"""

import streamlit as st
from rdflib import Graph, Literal
import sys
import os

# Add parent directory to path to import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from graph_manager import get_graph_manager, format_uri_display
from queries import (
    rdfs_properties,
    property_attributes,
    subproperties,
    superproperties,
    related_concepts, 
    semantic_assignments,
)

# Set page config
st.set_page_config(
    page_title="Properties - RDFS Ontology Browser",
    page_icon="🔗",
    layout="wide"
)

st.title("🔗 Properties")

# Get the graph manager
graph_manager = get_graph_manager()
graph = graph_manager.get_graph()

if st.button("New Property", type="primary"):
    # TODO show a popup that lets the user create the new property and write it to the graph
    st.info("New property creation will be implemented later.")

# Searchable property selection
st.selectbox(
    "Search and select a property:",
    options=rdfs_properties(graph),
    format_func=lambda c: f"{c['label']} - {c['property_iri']}",
    index=None,
    key="selected_property",
    placeholder="Type to search by name, label, or IRI...",
)

# Only show details if a property is actually selected
if st.session_state.selected_property is None:
    st.stop()

selected_property = st.session_state.selected_property
st.markdown(f"**IRI:** `{selected_property['property_iri']}`")

# Show general property attributes
attributes = property_attributes(graph, selected_property['property_iri'])
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
    subs = subproperties(graph, selected_property['property_iri'])
    supers = superproperties(graph, selected_property['property_iri'])

    if supers:
        st.write("**Parent Properties:**")
        for super_prop in supers:
            st.button(str(super_prop["label"] or super_prop["property"]),
                      on_click=lambda prop=super_prop: setattr(st.session_state, 'selected_property', prop))

    if subs:
        st.write("**Subproperties:**")
        for sub_prop in subs:
            st.button(str(sub_prop["label"] or sub_prop["property"]),
                      on_click=lambda prop=sub_prop: setattr(st.session_state, 'selected_property', prop))

    if not subs and not supers:
        st.info("No related properties found.")

with col2:
    st.subheader("Related Concepts")

    # Show related concepts via domain and range
    rel_concepts = related_concepts(graph, selected_property['property_iri'])
    if rel_concepts:
        for concept_uri, predicate, label in rel_concepts:
            concept_name = str(label) if label else format_uri_display(concept_uri)
            relation_type = "Domain" if "domain" in str(predicate) else "Range"
            st.write(f"**{relation_type}:** {concept_name}")
    else:
        st.info("No related concepts found.")

with col3:
    st.subheader("Linked Catalog Objects")

    # Show linked catalog objects
    assignments = semantic_assignments(graph, selected_property['property_iri'])
    if assignments:
        for obj_uri, name in assignments:
            obj_name = str(name) if name else format_uri_display(obj_uri)
            st.write(f"- {obj_name}")
    else:
        st.info("No catalog objects assigned.")

st.divider()
# Assign to Catalog Object button
if st.button("Assign to Catalog Object", type="secondary"):
    st.info("Assign to Catalog Object functionality will be implemented later.")
