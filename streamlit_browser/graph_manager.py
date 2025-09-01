"""
Graph management utilities for the RDFS Ontology Browser.

This module contains the GraphManager class for handling RDF graph operations
and related utility functions.
"""

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
            self.graph.add((obj_uri, RDF.type, UC.Table))
        elif object_type == 'column':
            self.graph.add((obj_uri, RDF.type, UC.Column))
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


def format_uri_display(uri):
    """Format URI for display - show the local name."""
    if hasattr(uri, 'split'):
        return str(uri).split('/')[-1].split('#')[-1]
    return str(uri)
