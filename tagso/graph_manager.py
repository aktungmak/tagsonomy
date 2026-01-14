import logging
from typing import Optional

from rdflib import Graph, RDF, RDFS, SKOS, URIRef, Literal
from psycopg2.errors import DuplicateTable
from sqlalchemy import select

from config import UC, USER_NS


logger = logging.getLogger(__name__)


class GraphManager:
    def __init__(self, db_url: str, identifier: str = "tagsonomy"):
        """
        Initialize GraphManager with SQLAlchemy store

        Args:
            db_url: connection string
            identifier: Identifier for the graph store
        """
        self._graph = Graph(store="SQLAlchemy", identifier=identifier)

        try:
            self._graph.open(db_url, create=True)
        except DuplicateTable:
            self._graph.open(db_url)

        # Reuse the engine created by rdflib_sqlalchemy
        self._engine = self._graph.store.engine

        self._graph.bind("uc", UC)
        self._graph.bind("user", USER_NS)
        self._graph.bind("rdf", RDF)
        self._graph.bind("rdfs", RDFS)
        self._graph.bind("skos", SKOS)

    def _to_dicts(self, bindings) -> list[dict]:
        """Convert SPARQL bindings to list of dicts with string keys and native Python values."""
        return [
            {str(k): v.toPython() if v is not None else None for k, v in row.items()}
            for row in bindings
        ]

    def get_tables(self, uri: Optional[str] = None) -> list[dict]:
        r = self._graph.query(
            """
            SELECT ?uri ?name
            WHERE {
                ?uri rdf:type uc:Table .
                OPTIONAL { ?uri uc:name ?name }
            }
        """,
            initBindings={"uri": URIRef(uri)} if uri else None,
        )
        return self._to_dicts(r.bindings)

    def insert_table(self, uri: str, name: str):
        uri = URIRef(uri)
        if uri not in self._graph.subjects(RDF.type, UC.Table):
            self._graph.add((uri, RDF.type, UC.Table))
            self._graph.add((uri, UC.name, Literal(name)))
        logger.info(f"Inserting table {name} iri: {uri}")

    def get_concepts(self, uri: Optional[str] = None) -> list[dict]:
        r = self._graph.query(
            """
            SELECT DISTINCT ?uri ?label
            WHERE {
                { ?uri a rdfs:Class . }
                UNION
                { ?uri rdfs:subClassOf ?other . }
                UNION
                { ?uri a skos:Concept . }
                OPTIONAL { ?uri rdfs:label ?label }
            }
        """,
            initBindings={"uri": URIRef(uri)} if uri else None,
        )
        return self._to_dicts(r.bindings)

    def get_concepts_with_alt_labels(self) -> list[dict]:
        """Get all concepts with their alt labels in a single query.

        Returns list of dicts with uri, label, and alt_labels (as a list).
        """
        r = self._graph.query(
            """
            SELECT DISTINCT ?uri ?label (GROUP_CONCAT(?alt; separator="||") AS ?alt_labels_concat)
            WHERE {
                { ?uri a rdfs:Class . }
                UNION
                { ?uri rdfs:subClassOf ?other . }
                UNION
                { ?uri a skos:Concept . }
                OPTIONAL { ?uri rdfs:label ?label }
                OPTIONAL { ?uri skos:altLabel ?alt }
            }
            GROUP BY ?uri ?label
        """
        )
        results = []
        for row in r.bindings:
            concept = {
                "uri": row["uri"].toPython() if row.get("uri") else None,
                "label": row["label"].toPython() if row.get("label") else None,
            }
            alt_concat = row.get("alt_labels_concat")
            if alt_concat and str(alt_concat):
                concept["alt_labels"] = str(alt_concat).split("||")
            else:
                concept["alt_labels"] = []
            results.append(concept)
        return results

    def insert_concept(
        self,
        uri: str,
        label: str,
        concept_type: URIRef,
        comment: Optional[str] = None,
        alt_labels: Optional[list[str]] = None,
    ):
        uri = URIRef(uri)
        self._graph.add((uri, RDF.type, concept_type))
        self._graph.add((uri, RDFS.label, Literal(label)))
        if comment:
            self._graph.add((uri, RDFS.comment, Literal(comment)))
        if alt_labels:
            for alt_label in alt_labels:
                self._graph.add((uri, SKOS.altLabel, Literal(alt_label)))
        logger.info(f"Inserting concept {label} iri: {uri}")

    def get_concept_detail(self, uri: str) -> Optional[dict]:
        """Get detailed information about a single concept including label, comment, type, and alt labels."""
        r = self._graph.query(
            """
            SELECT ?uri ?label ?comment ?type
            WHERE {
                ?uri ?p ?o .
                OPTIONAL { ?uri rdfs:label ?label }
                OPTIONAL { ?uri rdfs:comment ?comment }
                OPTIONAL { ?uri rdf:type ?type }
            }
        """,
            initBindings={"uri": URIRef(uri)},
        )

        bindings = list(r.bindings)
        if not bindings:
            return None

        result = {
            str(k): v.toPython() if v is not None else None
            for k, v in bindings[0].items()
        }

        # Get alt labels separately (there can be multiple)
        result["alt_labels"] = self.get_alt_labels(uri)
        return result

    def get_concept_relationships(self, uri: str) -> list[dict]:
        """Get all relationships (rdfs:subClassOf, skos:broader, skos:narrower) for a concept.

        Returns a list of dicts with predicate, predicate_type (prefixed name), object, and object_label.
        """
        # TODO: also find subclasses (where uri is object)
        r = self._graph.query(
            """
            SELECT ?predicate ?object ?object_label
            WHERE {
                ?uri ?predicate ?object .
                FILTER(?predicate IN (rdfs:subClassOf, skos:broader, skos:narrower))
                OPTIONAL { ?object rdfs:label ?object_label }
            }
        """,
            initBindings={"uri": URIRef(uri)},
        )

        results = self._to_dicts(r.bindings)
        for row in results:
            row["predicate_type"] = self._graph.namespace_manager.qname(
                URIRef(row["predicate"])
            )
        return results

    def update_concept(
        self,
        uri: str,
        label: str,
        comment: Optional[str] = None,
        alt_labels: Optional[list[str]] = None,
    ):
        """Update the label, comment, and alt labels of an existing concept."""
        uri_ref = URIRef(uri)

        # Remove existing label and comment
        for old_label in self._graph.objects(uri_ref, RDFS.label):
            self._graph.remove((uri_ref, RDFS.label, old_label))
        self._graph.add((uri_ref, RDFS.label, Literal(label)))

        if comment:
            for old_comment in self._graph.objects(uri_ref, RDFS.comment):
                self._graph.remove((uri_ref, RDFS.comment, old_comment))
            self._graph.add((uri_ref, RDFS.comment, Literal(comment)))

        # Update alt labels if provided (replace all existing ones)
        # TODO I think we should only add new alt labels, not replace existing ones - a different endpoint is for deleting
        if alt_labels is not None:
            for old_alt in self._graph.objects(uri_ref, SKOS.altLabel):
                self._graph.remove((uri_ref, SKOS.altLabel, old_alt))
            for alt_label in alt_labels:
                self._graph.add((uri_ref, SKOS.altLabel, Literal(alt_label)))

        logger.info(f"Updated concept {uri} with label: {label}")

    def get_alt_labels(self, uri: str) -> list[str]:
        """Get all skos:altLabel values for a resource."""
        uri_ref = URIRef(uri)
        return [alt.toPython() for alt in self._graph.objects(uri_ref, SKOS.altLabel)]

    def add_concept_relationship(
        self, subject_uri: str, predicate_type: str, object_uri: str
    ):
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

    def delete_concept_relationship(
        self, subject_uri: str, predicate_type: str, object_uri: str
    ):
        """Delete a relationship between concepts."""
        subject = URIRef(subject_uri)
        obj = URIRef(object_uri)
        predicate = self._graph.namespace_manager.expand_curie(predicate_type)

        self._graph.remove((subject, predicate, obj))
        logger.info(
            f"Deleted relationship: {subject_uri} {predicate_type} {object_uri}"
        )

    def insert_concept_assignment(self, table_uri: str, concept_uri: str):
        """Insert a concept assignment from a table to a concept."""
        table_uri = URIRef(table_uri)
        concept_uri = URIRef(concept_uri)
        self._graph.add((table_uri, UC.conceptAssignment, concept_uri))
        logger.info(f"Assigned table {table_uri} to concept {concept_uri}")

    def insert_column_property_assignment(self, column_uri: str, property_uri: str):
        """Insert a property assignment from a column to a property."""
        column_uri = URIRef(column_uri)
        property_uri = URIRef(property_uri)
        self._graph.add((column_uri, UC.propertyAssignment, property_uri))
        logger.info(f"Assigned column {column_uri} to property {property_uri}")

    def concept_table_assignments(
        self,
        table_uri: Optional[str] = None,
        concept_uri: Optional[str] = None,
    ) -> list[dict]:
        """Get table/concept assignments.

        Args:
            table_uri: If provided, returns all concepts assigned to this table
            concept_uri: If provided, returns all tables assigned to this concept
        """
        bindings = {}
        if table_uri:
            bindings["table_uri"] = URIRef(table_uri)
        if concept_uri:
            bindings["concept_uri"] = URIRef(concept_uri)

        r = self._graph.query(
            """
            SELECT ?table_uri ?table_name ?concept_uri ?concept_name
            WHERE {
                ?table_uri uc:conceptAssignment ?concept_uri .
                OPTIONAL { ?table_uri uc:name ?table_name }
                OPTIONAL { ?concept_uri rdfs:label ?concept_name }
            }
        """,
            initBindings=bindings if bindings else None,
        )
        return self._to_dicts(r.bindings)

    def column_property_assignments(
        self,
        column_uri: Optional[str] = None,
        property_uri: Optional[str] = None,
    ) -> list[dict]:
        """Get column/property assignments.

        Args:
            column_uri: If provided, returns all properties assigned to this column
            property_uri: If provided, returns all columns assigned to this property
        """
        bindings = {}
        if column_uri:
            bindings["column_uri"] = URIRef(column_uri)
        if property_uri:
            bindings["property_uri"] = URIRef(property_uri)

        r = self._graph.query(
            """
            SELECT ?column_uri ?column_name ?property_uri ?property_name
            WHERE {
                ?column_uri uc:propertyAssignment ?property_uri .
                OPTIONAL { ?column_uri uc:name ?column_name }
                OPTIONAL { ?property_uri rdfs:label ?property_name }
            }
        """,
            initBindings=bindings if bindings else None,
        )
        return self._to_dicts(r.bindings)

    def get_columns(self, uri: Optional[str] = None) -> list[dict]:
        r = self._graph.query(
            """
            SELECT ?uri ?name
            WHERE {
                ?uri rdf:type uc:Column .
                OPTIONAL { ?uri uc:name ?name }
            }
        """,
            initBindings={"uri": URIRef(uri)} if uri else None,
        )
        return self._to_dicts(r.bindings)

    def insert_column(self, uri: str, name: str):
        uri = URIRef(uri)
        if uri not in self._graph.subjects(RDF.type, UC.Column):
            self._graph.add((uri, RDF.type, UC.Column))
            self._graph.add((uri, UC.name, Literal(name)))
        logger.info(f"Inserting column {name} iri: {uri}")

    def get_properties(self, uri: Optional[str] = None) -> list[dict]:
        """Get all RDF properties with their domain and range."""
        r = self._graph.query(
            """
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
        """,
            initBindings={"uri": URIRef(uri)} if uri else None,
        )
        return self._to_dicts(r.bindings)

    def get_properties_with_alt_labels(self) -> list[dict]:
        """Get all properties with their alt labels in a single query.

        Returns list of dicts with uri, name, and alt_labels (as a list).
        """
        r = self._graph.query(
            """
            SELECT DISTINCT ?uri ?name (GROUP_CONCAT(?alt; separator="||") AS ?alt_labels_concat)
            WHERE {
                ?uri a rdf:Property .
                OPTIONAL { ?uri rdfs:label ?name }
                OPTIONAL { ?uri skos:altLabel ?alt }
            }
            GROUP BY ?uri ?name
        """
        )
        results = []
        for row in r.bindings:
            prop = {
                "uri": row["uri"].toPython() if row.get("uri") else None,
                "name": row["name"].toPython() if row.get("name") else None,
            }
            alt_concat = row.get("alt_labels_concat")
            if alt_concat and str(alt_concat):
                prop["alt_labels"] = str(alt_concat).split("||")
            else:
                prop["alt_labels"] = []
            results.append(prop)
        return results

    def get_properties_for_concept(self, concept_uri: str) -> list[dict]:
        """Get properties where the concept is used as domain or range.

        Returns a list of property dicts, each with a 'role' key ('domain' or 'range').
        """
        concept_ref = URIRef(concept_uri)

        result = self._graph.query(
            """
            SELECT ?uri ?name ?role
            WHERE {
                {
                    ?uri a rdf:Property .
                    ?uri rdfs:domain ?concept .
                    OPTIONAL { ?uri rdfs:label ?name }
                    BIND("domain" AS ?role)
                }
                UNION
                {
                    ?uri a rdf:Property .
                    ?uri rdfs:range ?concept .
                    OPTIONAL { ?uri rdfs:label ?name }
                    BIND("range" AS ?role)
                }
            }
        """,
            initBindings={"concept": concept_ref},
        )

        return self._to_dicts(result.bindings)

    def insert_property(
        self,
        uri: str,
        name: str,
        domain: Optional[str] = None,
        range_: Optional[str] = None,
        alt_labels: Optional[list[str]] = None,
    ):
        """Insert a new RDF property with optional domain, range, and alt labels."""
        uri = URIRef(uri)
        self._graph.add((uri, RDF.type, RDF.Property))
        self._graph.add((uri, RDFS.label, Literal(name)))
        if domain:
            self._graph.add((uri, RDFS.domain, URIRef(domain)))
        if range_:
            self._graph.add((uri, RDFS.range, URIRef(range_)))
        if alt_labels:
            for alt_label in alt_labels:
                self._graph.add((uri, SKOS.altLabel, Literal(alt_label)))
        logger.info(f"Inserting property {name} iri: {uri}")

    def get_property_detail(self, uri: str) -> Optional[dict]:
        """Get detailed information about a single property including label, comment, domain, range, and alt labels."""
        r = self._graph.query(
            """
            SELECT ?uri ?label ?comment ?domain ?domain_label ?range ?range_label
            WHERE {
                ?uri a rdf:Property .
                OPTIONAL { ?uri rdfs:label ?label }
                OPTIONAL { ?uri rdfs:comment ?comment }
                OPTIONAL { 
                    ?uri rdfs:domain ?domain .
                    OPTIONAL { ?domain rdfs:label ?domain_label }
                }
                OPTIONAL { 
                    ?uri rdfs:range ?range .
                    OPTIONAL { ?range rdfs:label ?range_label }
                }
            }
        """,
            initBindings={"uri": URIRef(uri)},
        )

        bindings = list(r.bindings)
        if not bindings:
            return None

        result = {
            str(k): v.toPython() if v is not None else None
            for k, v in bindings[0].items()
        }

        # Get alt labels separately (there can be multiple)
        result["alt_labels"] = self.get_alt_labels(uri)
        return result

    def update_property(
        self,
        uri: str,
        label: str,
        comment: Optional[str] = None,
        domain: Optional[str] = None,
        range_: Optional[str] = None,
        alt_labels: Optional[list[str]] = None,
    ):
        """Update the label, comment, domain, range, and alt labels of an existing property."""
        # TODO split this into a delete and an insert rather than replacing all the existing items
        uri_ref = URIRef(uri)

        # Update label
        for old_label in self._graph.objects(uri_ref, RDFS.label):
            self._graph.remove((uri_ref, RDFS.label, old_label))
        self._graph.add((uri_ref, RDFS.label, Literal(label)))

        # Update comment
        for old_comment in self._graph.objects(uri_ref, RDFS.comment):
            self._graph.remove((uri_ref, RDFS.comment, old_comment))
        if comment:
            self._graph.add((uri_ref, RDFS.comment, Literal(comment)))

        # Update domain
        for old_domain in self._graph.objects(uri_ref, RDFS.domain):
            self._graph.remove((uri_ref, RDFS.domain, old_domain))
        if domain:
            self._graph.add((uri_ref, RDFS.domain, URIRef(domain)))

        # Update range
        for old_range in self._graph.objects(uri_ref, RDFS.range):
            self._graph.remove((uri_ref, RDFS.range, old_range))
        if range_:
            self._graph.add((uri_ref, RDFS.range, URIRef(range_)))

        # Update alt labels if provided (replace all existing ones)
        if alt_labels is not None:
            for old_alt in self._graph.objects(uri_ref, SKOS.altLabel):
                self._graph.remove((uri_ref, SKOS.altLabel, old_alt))
            for alt_label in alt_labels:
                self._graph.add((uri_ref, SKOS.altLabel, Literal(alt_label)))

        logger.info(f"Updated property {uri} with label: {label}")

    def delete_object(self, uri: str):
        uri = URIRef(uri)
        for pred, obj in self._graph.predicate_objects(subject=uri):
            self._graph.remove((uri, pred, obj))
        logger.info(f"Deleted object {uri}")

    def search(self, query: str, kind: Optional[str] = None) -> list[dict]:
        """Search for concepts and properties using trigram similarity search."""
        if self._engine.dialect.name != "postgresql":
            raise ValueError("Unsupported database engine")
        literal_statements = self._graph.store.tables["literal_statements"]

        conditions = [literal_statements.c.object.op("%")(query)]
        # TODO implement this
        # if kind is not None:
        #     conditions.append(literal_statements.c.type == kind)

        stmt = (
            select(
                literal_statements.c.subject.label("uri"),
                literal_statements.c.object.label("text"),
            )
            .where(*conditions)
            .distinct()
        )
        with self._engine.connect() as conn:
            return [row._asdict() for row in conn.execute(stmt).fetchall()]

    def close(self):
        self._graph.close()
