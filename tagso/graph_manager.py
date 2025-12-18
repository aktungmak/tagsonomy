import logging
from typing import Optional

from rdflib import Graph, RDF, RDFS, SKOS, URIRef, Literal
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
        self._graph.bind("skos", SKOS)

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

    def get_concepts(self, uri: Optional[URIRef] = None) -> list[dict]:
        r = self._graph.query("""
            SELECT DISTINCT ?uri ?label
            WHERE {
                { ?uri a rdfs:Class . }
                UNION
                { ?uri rdfs:subClassOf ?other . }
                UNION
                { ?uri a skos:Concept . }
                OPTIONAL { ?uri rdfs:label ?label }
            }
        """, initBindings={'uri': URIRef(uri)} if uri else None)
        return self._to_dicts(r.bindings)

    def insert_concept(self, uri: str, label: str, concept_type: URIRef, comment: Optional[str] = None):
        uri = URIRef(uri)
        self._graph.add((uri, RDF.type, concept_type))
        self._graph.add((uri, RDFS.label, Literal(label)))
        if comment:
            self._graph.add((uri, RDFS.comment, Literal(comment)))
        logger.info(f"Inserting concept {label} iri: {uri}")

    def get_concept_detail(self, uri: str) -> Optional[dict]:
        """Get detailed information about a single concept including label, comment, and type."""
        r = self._graph.query("""
            SELECT ?uri ?label ?comment ?type
            WHERE {
                ?uri ?p ?o .
                OPTIONAL { ?uri rdfs:label ?label }
                OPTIONAL { ?uri rdfs:comment ?comment }
                OPTIONAL { ?uri rdf:type ?type }
            }
        """, initBindings={'uri': URIRef(uri)})
        
        bindings = list(r.bindings)
        if not bindings:
            return None

        result = {str(k): v.toPython() if v is not None else None for k, v in bindings[0].items()}
        return result

    def get_concept_relationships(self, uri: str) -> list[dict]:
        """Get all relationships (rdfs:subClassOf, skos:broader, skos:narrower) for a concept.
        
        Returns a list of dicts with predicate, predicate_type (prefixed name), object, and object_label.
        """
        # TODO: also find subclasses (where uri is object)
        r = self._graph.query("""
            SELECT ?predicate ?object ?object_label
            WHERE {
                ?uri ?predicate ?object .
                FILTER(?predicate IN (rdfs:subClassOf, skos:broader, skos:narrower))
                OPTIONAL { ?object rdfs:label ?object_label }
            }
        """, initBindings={'uri': URIRef(uri)})
        
        results = self._to_dicts(r.bindings)
        for row in results:
            row['predicate_type'] = self._graph.namespace_manager.qname(URIRef(row['predicate']))
        return results

    def update_concept(self, uri: str, label: str, comment: Optional[str] = None):
        """Update the label and comment of an existing concept."""
        uri_ref = URIRef(uri)
        
        # Remove existing label and comment
        for old_label in self._graph.objects(uri_ref, RDFS.label):
            self._graph.remove((uri_ref, RDFS.label, old_label))
        self._graph.add((uri_ref, RDFS.label, Literal(label)))

        if comment:
            for old_comment in self._graph.objects(uri_ref, RDFS.comment):
                self._graph.remove((uri_ref, RDFS.comment, old_comment))
            self._graph.add((uri_ref, RDFS.comment, Literal(comment)))

        logger.info(f"Updated concept {uri} with label: {label}")

    def add_concept_relationship(self, subject_uri: str, predicate_type: str, object_uri: str):
        """Add a relationship between concepts.
        
        Args:
            subject_uri: The source concept URI
            predicate_type: One of 'rdfs:subClassOf', 'skos:broader', 'skos:narrower'
            object_uri: The target concept URI
        """
        subject = URIRef(subject_uri)
        obj = URIRef(object_uri)
        predicate = self._graph.namespace_manager.expand_curie(predicate_type)
        
        self._graph.add((subject, predicate, obj))
        logger.info(f"Added relationship: {subject_uri} {predicate_type} {object_uri}")

    def delete_concept_relationship(self, subject_uri: str, predicate_type: str, object_uri: str):
        """Delete a relationship between concepts."""
        subject = URIRef(subject_uri)
        obj = URIRef(object_uri)
        predicate = self._graph.namespace_manager.expand_curie(predicate_type)
        
        self._graph.remove((subject, predicate, obj))
        logger.info(f"Deleted relationship: {subject_uri} {predicate_type} {object_uri}")

    def insert_assignment(self, table_uri: str, concept_uri: str):
        """Insert a semantic assignment from a table to a concept."""
        table_uri = URIRef(table_uri)
        concept_uri = URIRef(concept_uri)
        self._graph.add((table_uri, UC.semanticAssignment, concept_uri))
        logger.info(f"Assigned table {table_uri} to concept {concept_uri}")

    def get_assignments(self, table_uri: Optional[str] = None, concept_uri: Optional[str] = None) -> list[dict]:
        """Get semantic assignments, filtered by table or concept.
        
        Args:
            table_uri: If provided, returns all concepts assigned to this table
            concept_uri: If provided, returns all tables assigned to this concept
        """
        bindings = {}
        if table_uri:
            bindings['table_uri'] = URIRef(table_uri)
        if concept_uri:
            bindings['concept_uri'] = URIRef(concept_uri)

        r = self._graph.query("""
            SELECT ?table_uri ?table_name ?concept_uri ?concept_name
            WHERE {
                ?table_uri uc:semanticAssignment ?concept_uri .
                OPTIONAL { ?table_uri uc:name ?table_name }
                OPTIONAL { ?concept_uri rdfs:label ?concept_name }
            }
        """, initBindings=bindings if bindings else None)
        return self._to_dicts(r.bindings)

    def get_columns(self, uri: Optional[URIRef] = None) -> list[dict]:
        r = self._graph.query("""
            SELECT ?uri ?name
            WHERE {
                ?uri rdf:type uc:Column .
                OPTIONAL { ?uri uc:name ?name }
            }
        """, initBindings={'uri': uri} if uri else None)
        return self._to_dicts(r.bindings)

    def insert_column(self, uri: str, name: str):
        uri = URIRef(uri)
        if uri not in self._graph.subjects(RDF.type, UC.Column):
            self._graph.add((uri, RDF.type, UC.Column))
            self._graph.add((uri, UC.name, Literal(name)))
        logger.info(f"Inserting column {name} iri: {uri}")

    def get_properties(self, uri: Optional[str] = None) -> list[dict]:
        """Get all RDF properties with their domain and range."""
        r = self._graph.query("""
            SELECT DISTINCT ?uri ?name ?domain ?domain_label ?range ?range_label
            WHERE {
                ?uri a rdf:Property .
                OPTIONAL { ?uri rdfs:label ?name }
                OPTIONAL { 
                    ?uri rdfs:domain ?domain .
                    ?domain rdfs:label ?domain_label
                }
                OPTIONAL { 
                    ?uri rdfs:range ?range .
                    ?range rdfs:label ?range_label
                }
            }
        """, initBindings={'uri': URIRef(uri)} if uri else None)
        return self._to_dicts(r.bindings)

    def insert_property(self, uri: str, name: str, domain: Optional[str] = None, range_: Optional[str] = None):
        """Insert a new RDF property with optional domain and range."""
        uri = URIRef(uri)
        self._graph.add((uri, RDF.type, RDF.Property))
        self._graph.add((uri, RDFS.label, Literal(name)))
        if domain:
            self._graph.add((uri, RDFS.domain, URIRef(domain)))
        if range_:
            self._graph.add((uri, RDFS.range, URIRef(range_)))
        logger.info(f"Inserting property {name} iri: {uri}")

    def delete_object(self, uri: str):
        uri = URIRef(uri)
        for pred, obj in self._graph.predicate_objects(subject=uri):
            self._graph.remove((uri, pred, obj))
        logger.info(f"Deleted object {uri}")

    def close(self):
        self._graph.close()
