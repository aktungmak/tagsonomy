import logging
from typing import Optional

from rdflib import Graph, RDF, RDFS, URIRef, Literal
from psycopg2.errors import DuplicateTable

from config import UC, USER_NS


logger = logging.getLogger(__name__)


class GraphManager:
    def __init__(self, db_url: str, identifier: str = 'tagsonomy'):
        """
        Initialize GraphManager with SQLAlchemy store
        
        Args:
            db_url: connection string
            identifier: Identifier for the graph store
        """
        self._graph = Graph(store='SQLAlchemy', identifier=identifier)

        try:
            self._graph.open(db_url, create=True)
        except DuplicateTable:
            self._graph.open(db_url)

        self._graph.bind("uc", UC)
        self._graph.bind("user", USER_NS)
        self._graph.bind("rdf", RDF)
        self._graph.bind("rdfs", RDFS)

    def _to_dicts(self, bindings) -> list[dict]:
        """Convert SPARQL bindings to list of dicts with string keys and native Python values."""
        return [{str(k): v.toPython() if v is not None else None for k, v in row.items()} for row in bindings]

    def get_tables(self, uri: Optional[URIRef] = None) -> list[dict]:
        r = self._graph.query("""
            SELECT ?uri ?name
            WHERE {
                ?uri rdf:type uc:Table .
                OPTIONAL { ?uri uc:name ?name }
            }
        """, initBindings={'uri': uri} if uri else None)
        return self._to_dicts(r.bindings)

    def insert_table(self, uri: str, name: str):
        uri = URIRef(uri)
        if uri not in self._graph.subjects(RDF.type, UC.Table):
            self._graph.add((uri, RDF.type, UC.Table))
            self._graph.add((uri, UC.name, Literal(name)))
        logger.info(f"Inserting table {name} iri: {uri}")

    def get_classes(self, uri: Optional[URIRef] = None) -> list[dict]:
        r = self._graph.query("""
            SELECT DISTINCT ?uri ?name
            WHERE {
                { ?uri a rdfs:Class . }
                UNION
                { ?uri rdfs:subClassOf ?other . }
                OPTIONAL { ?uri rdfs:label ?name }
            }
        """, initBindings={'uri': uri} if uri else None)
        return self._to_dicts(r.bindings)

    def insert_class(self, uri: str, label: str, class_type: URIRef, comment: Optional[str] = None,
                     superclass: Optional[URIRef] = None):
        uri = URIRef(uri)
        if uri not in self._graph.subjects(RDF.type, class_type):
            self._graph.add((uri, RDF.type, class_type))
            self._graph.add((uri, RDFS.label, Literal(label)))
            if comment:
                self._graph.add((uri, RDFS.comment, Literal(comment)))
            if superclass:
                self._graph.add((uri, RDFS.subClassOf, superclass))
        logger.info(f"Inserting class {label} iri: {uri}")

    def insert_assignment(self, table_uri: str, class_uri: str):
        """Insert a semantic assignment from a table to a class."""
        table_uri = URIRef(table_uri)
        class_uri = URIRef(class_uri)
        self._graph.add((table_uri, UC.semanticAssignment, class_uri))
        logger.info(f"Assigned table {table_uri} to class {class_uri}")

    def get_assignments(self, table_uri: Optional[str] = None, class_uri: Optional[str] = None) -> list[dict]:
        """Get semantic assignments, filtered by table or class.
        
        Args:
            table_uri: If provided, returns all classes assigned to this table
            class_uri: If provided, returns all tables assigned to this class
        """
        bindings = {}
        if table_uri:
            bindings['table_uri'] = URIRef(table_uri)
        if class_uri:
            bindings['class_uri'] = URIRef(class_uri)

        r = self._graph.query("""
            SELECT ?table_uri ?table_name ?class_uri ?class_name
            WHERE {
                ?table_uri uc:semanticAssignment ?class_uri .
                OPTIONAL { ?table_uri uc:name ?table_name }
                OPTIONAL { ?class_uri rdfs:label ?class_name }
            }
        """, initBindings=bindings if bindings else None)
        return self._to_dicts(r.bindings)

    def delete_object(self, uri: str):
        uri = URIRef(uri)
        for pred, obj in self._graph.predicate_objects(subject=uri):
            self._graph.remove((uri, pred, obj))
        logger.info(f"Deleted object {uri}")

    def close(self):
        self._graph.close()
