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

    def get_tables(self) -> list[dict]:
        r = self._graph.query(
            """
            SELECT ?uri ?name
            WHERE {
                ?uri rdf:type uc:Table .
                OPTIONAL { ?uri uc:name ?name }
            }
        """
        )
        return self._to_dicts(r.bindings)

    def insert_table(self, uri: str, name: str):
        uri = URIRef(uri)
        if uri not in self._graph.subjects(RDF.type, UC.Table):
            self._graph.add((uri, RDF.type, UC.Table))
            self._graph.add((uri, UC.name, Literal(name)))
        logger.info(f"Inserting table {name} iri: {uri}")

    def get_concept_schemes(self) -> list[dict]:
        """Get all skos:ConceptScheme resources with optional rdfs:label."""
        r = self._graph.query(
            """
            SELECT ?uri ?label
            WHERE {
                ?uri a skos:ConceptScheme .
                OPTIONAL { ?uri rdfs:label ?label }
            }
            ORDER BY ?label
            """
        )
        return self._to_dicts(r.bindings)

    def get_members_in_scheme(self, scheme_uri: str) -> list[dict]:
        """Return Classes, Concepts, Properties, and Actions where ?resource skos:inScheme ?scheme.
        Each item has uri, label, and type (rdfs:Class, skos:Concept, rdf:Property, or uc:Action).
        """
        r = self._graph.query(
            """
            SELECT ?uri ?label ?type
            WHERE {
                ?uri skos:inScheme ?scheme .
                ?uri rdf:type ?type .
                FILTER(?type IN (rdfs:Class, skos:Concept, rdf:Property, uc:Action))
                OPTIONAL { ?uri rdfs:label ?label }
            }
            ORDER BY ?label
            """,
            initBindings={"scheme": URIRef(scheme_uri)},
        )
        rows = self._to_dicts(r.bindings)
        for row in rows:
            if row.get("type") is not None:
                try:
                    row["type"] = self._graph.namespace_manager.qname(URIRef(row["type"]))
                except Exception:
                    pass
        return rows

    def insert_concept_scheme(self, uri: str, label: str, comment: Optional[str] = None):
        """Add a skos:ConceptScheme with label and optional comment."""
        uri_ref = URIRef(uri)
        self._graph.add((uri_ref, RDF.type, SKOS.ConceptScheme))
        self._graph.add((uri_ref, RDFS.label, Literal(label)))
        if comment:
            self._graph.add((uri_ref, RDFS.comment, Literal(comment)))
        logger.info(f"Inserted concept scheme {label} iri: {uri_ref}")

    def update_concept_scheme(
        self, uri: str, label: str, comment: Optional[str] = None
    ):
        """Update the label and comment of an existing concept scheme."""
        uri_ref = URIRef(uri)
        for old_label in self._graph.objects(uri_ref, RDFS.label):
            self._graph.remove((uri_ref, RDFS.label, old_label))
        self._graph.add((uri_ref, RDFS.label, Literal(label)))
        for old_comment in self._graph.objects(uri_ref, RDFS.comment):
            self._graph.remove((uri_ref, RDFS.comment, old_comment))
        if comment:
            self._graph.add((uri_ref, RDFS.comment, Literal(comment)))
        logger.info(f"Updated concept scheme {uri} with label: {label}")

    def add_members_to_scheme(self, scheme_uri: str, resource_uris: list[str]):
        """Add skos:inScheme triples for the given Concepts/Properties to the scheme."""
        scheme_ref = URIRef(scheme_uri)
        for res_uri in resource_uris:
            res_ref = URIRef(res_uri)
            self._graph.add((res_ref, SKOS.inScheme, scheme_ref))
        logger.info(f"Added {len(resource_uris)} members to scheme {scheme_uri}")

    def get_concept_scheme_detail(self, uri: str) -> Optional[dict]:
        """Get detailed information about a concept scheme (uri, label, comment)."""
        r = self._graph.query(
            """
            SELECT ?uri ?label ?comment
            WHERE {
                ?uri a skos:ConceptScheme .
                OPTIONAL { ?uri rdfs:label ?label }
                OPTIONAL { ?uri rdfs:comment ?comment }
            }
            LIMIT 1
            """,
            initBindings={"uri": URIRef(uri)},
        )
        rows = self._to_dicts(r.bindings)
        return rows[0] if rows else None

    def get_concepts(self) -> list[dict]:
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
        """
        )
        return self._to_dicts(r.bindings)

    def get_concept_detail(self, uri: str) -> Optional[dict]:
        """Get detailed information about a single concept including label, comment, type, in_scheme, and alt labels."""
        r = self._graph.query(
            """
            SELECT ?uri ?label ?comment ?type ?in_scheme
            WHERE {
                ?uri ?p ?o .
                OPTIONAL { ?uri rdfs:label ?label }
                OPTIONAL { ?uri rdfs:comment ?comment }
                OPTIONAL { ?uri rdf:type ?type }
                OPTIONAL { ?uri skos:inScheme ?in_scheme }
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

    def get_alt_labels(self, uri: str) -> list[str]:
        """Get all skos:altLabel values for a resource."""
        uri_ref = URIRef(uri)
        return [alt.toPython() for alt in self._graph.objects(uri_ref, SKOS.altLabel)]

    def get_concept_detail_full(self, uri: str) -> Optional[dict]:
        """Get all concept detail data in one query: type, in_scheme, labels, comments,
        alt_labels, superclasses, subclasses, assigned_tables.
        """
        uri_ref = URIRef(uri)
        r = self._graph.query(
            """
            SELECT ?row_kind ?type_val ?in_scheme ?label_val ?rel_uri ?rel_label ?table_uri ?table_name
            WHERE {
                {
                    BIND("type" AS ?row_kind) .
                    ?uri rdf:type ?type_val .
                    FILTER(?type_val IN (rdfs:Class, skos:Concept)) .
                    OPTIONAL { ?uri skos:inScheme ?in_scheme }
                }
                UNION
                {
                    BIND("label" AS ?row_kind) .
                    ?uri rdfs:label ?label_val .
                }
                UNION
                {
                    BIND("comment" AS ?row_kind) .
                    ?uri rdfs:comment ?label_val .
                }
                UNION
                {
                    BIND("altLabel" AS ?row_kind) .
                    ?uri skos:altLabel ?label_val .
                }
                UNION
                {
                    BIND("super" AS ?row_kind) .
                    ?uri rdfs:subClassOf ?rel_uri .
                    OPTIONAL { ?rel_uri rdfs:label ?rel_label }
                }
                UNION
                {
                    BIND("sub" AS ?row_kind) .
                    ?rel_uri rdfs:subClassOf ?uri .
                    OPTIONAL { ?rel_uri rdfs:label ?rel_label }
                }
                UNION
                {
                    BIND("broader" AS ?row_kind) .
                    ?uri skos:broader ?rel_uri .
                    OPTIONAL { ?rel_uri rdfs:label ?rel_label }
                }
                UNION
                {
                    BIND("narrower" AS ?row_kind) .
                    ?uri skos:narrower ?rel_uri .
                    OPTIONAL { ?rel_uri rdfs:label ?rel_label }
                }
                UNION
                {
                    BIND("table" AS ?row_kind) .
                    ?table_uri uc:conceptAssignment ?uri .
                    OPTIONAL { ?table_uri uc:name ?table_name }
                }
            }
            """,
            initBindings={"uri": uri_ref},
        )
        rows = self._to_dicts(r.bindings)
        if not rows:
            return None

        result = {
            "uri": uri,
            "type": None,
            "in_scheme": None,
            "labels": [],
            "comments": [],
            "alt_labels": [],
            "superclasses": [],
            "subclasses": [],
            "assigned_tables": [],
        }
        seen_super = set()
        seen_sub = set()
        seen_tables = set()

        def qname(val):
            if val is None:
                return None
            try:
                return self._graph.namespace_manager.qname(URIRef(val))
            except Exception:
                return str(val)

        for row in rows:
            kind = row.get("row_kind")
            if kind == "type":
                if result["type"] is None:
                    result["type"] = qname(row.get("type_val"))
                if result["in_scheme"] is None and row.get("in_scheme"):
                    result["in_scheme"] = qname(row.get("in_scheme"))
            elif kind == "label" and row.get("label_val"):
                result["labels"].append(row["label_val"].toPython() if hasattr(row["label_val"], "toPython") else str(row["label_val"]))
            elif kind == "comment" and row.get("label_val"):
                result["comments"].append(row["label_val"].toPython() if hasattr(row["label_val"], "toPython") else str(row["label_val"]))
            elif kind == "altLabel" and row.get("label_val"):
                result["alt_labels"].append(row["label_val"].toPython() if hasattr(row["label_val"], "toPython") else str(row["label_val"]))
            elif kind == "super" and row.get("rel_uri"):
                rel_uri = row["rel_uri"].toPython() if hasattr(row["rel_uri"], "toPython") else str(row["rel_uri"])
                if rel_uri not in seen_super:
                    seen_super.add(rel_uri)
                    result["superclasses"].append({
                        "uri": rel_uri,
                        "label": row.get("rel_label") and (row["rel_label"].toPython() if hasattr(row["rel_label"], "toPython") else str(row["rel_label"])),
                    })
            elif kind == "sub" and row.get("rel_uri"):
                rel_uri = row["rel_uri"].toPython() if hasattr(row["rel_uri"], "toPython") else str(row["rel_uri"])
                if rel_uri not in seen_sub:
                    seen_sub.add(rel_uri)
                    result["subclasses"].append({
                        "uri": rel_uri,
                        "label": row.get("rel_label") and (row["rel_label"].toPython() if hasattr(row["rel_label"], "toPython") else str(row["rel_label"])),
                    })
            elif kind == "broader" and row.get("rel_uri"):
                rel_uri = row["rel_uri"].toPython() if hasattr(row["rel_uri"], "toPython") else str(row["rel_uri"])
                if rel_uri not in seen_super:
                    seen_super.add(rel_uri)
                    result["superclasses"].append({
                        "uri": rel_uri,
                        "label": row.get("rel_label") and (row["rel_label"].toPython() if hasattr(row["rel_label"], "toPython") else str(row["rel_label"])),
                    })
            elif kind == "narrower" and row.get("rel_uri"):
                rel_uri = row["rel_uri"].toPython() if hasattr(row["rel_uri"], "toPython") else str(row["rel_uri"])
                if rel_uri not in seen_sub:
                    seen_sub.add(rel_uri)
                    result["subclasses"].append({
                        "uri": rel_uri,
                        "label": row.get("rel_label") and (row["rel_label"].toPython() if hasattr(row["rel_label"], "toPython") else str(row["rel_label"])),
                    })
            elif kind == "table" and row.get("table_uri"):
                t_uri = row["table_uri"].toPython() if hasattr(row["table_uri"], "toPython") else str(row["table_uri"])
                if t_uri not in seen_tables:
                    seen_tables.add(t_uri)
                    result["assigned_tables"].append({
                        "table_uri": t_uri,
                        "table_name": row.get("table_name") and (row["table_name"].toPython() if hasattr(row["table_name"], "toPython") else str(row["table_name"])),
                    })

        return result

    def get_property_detail_full(self, uri: str) -> Optional[dict]:
        """Get all property detail data in one query: type, in_scheme, domain, range,
        labels, comments, alt_labels, superproperties, subproperties, assigned_columns.
        """
        uri_ref = URIRef(uri)
        r = self._graph.query(
            """
            SELECT ?row_kind ?type_val ?in_scheme ?label_val ?rel_uri ?rel_label
                   ?domain ?domain_label ?range ?range_label ?column_uri ?column_name
            WHERE {
                {
                    BIND("type" AS ?row_kind) .
                    ?uri a rdf:Property .
                    OPTIONAL { ?uri skos:inScheme ?in_scheme }
                    OPTIONAL {
                        ?uri rdfs:domain ?domain .
                        OPTIONAL { ?domain rdfs:label ?domain_label }
                    }
                    OPTIONAL {
                        ?uri rdfs:range ?range .
                        OPTIONAL { ?range rdfs:label ?range_label }
                    }
                }
                UNION
                {
                    BIND("label" AS ?row_kind) .
                    ?uri rdfs:label ?label_val .
                }
                UNION
                {
                    BIND("comment" AS ?row_kind) .
                    ?uri rdfs:comment ?label_val .
                }
                UNION
                {
                    BIND("altLabel" AS ?row_kind) .
                    ?uri skos:altLabel ?label_val .
                }
                UNION
                {
                    BIND("superprop" AS ?row_kind) .
                    ?uri rdfs:subPropertyOf ?rel_uri .
                    OPTIONAL { ?rel_uri rdfs:label ?rel_label }
                }
                UNION
                {
                    BIND("subprop" AS ?row_kind) .
                    ?rel_uri rdfs:subPropertyOf ?uri .
                    OPTIONAL { ?rel_uri rdfs:label ?rel_label }
                }
                UNION
                {
                    BIND("column" AS ?row_kind) .
                    ?column_uri uc:propertyAssignment ?uri .
                    OPTIONAL { ?column_uri uc:name ?column_name }
                }
            }
            """,
            initBindings={"uri": uri_ref},
        )
        rows = self._to_dicts(r.bindings)
        if not rows:
            return None

        result = {
            "uri": uri,
            "type": "rdf:Property",
            "in_scheme": None,
            "domain": None,
            "domain_label": None,
            "range": None,
            "range_label": None,
            "labels": [],
            "comments": [],
            "alt_labels": [],
            "superproperties": [],
            "subproperties": [],
            "assigned_columns": [],
        }
        seen_super = set()
        seen_sub = set()
        seen_columns = set()

        def qname(val):
            if val is None:
                return None
            try:
                return self._graph.namespace_manager.qname(URIRef(val))
            except Exception:
                return str(val)

        def to_py(obj):
            return obj.toPython() if obj is not None and hasattr(obj, "toPython") else (str(obj) if obj is not None else None)

        for row in rows:
            kind = row.get("row_kind")
            if kind == "type":
                if result["in_scheme"] is None and row.get("in_scheme"):
                    result["in_scheme"] = qname(row.get("in_scheme"))
                if result["domain"] is None and row.get("domain"):
                    result["domain"] = row["domain"].toPython() if hasattr(row["domain"], "toPython") else str(row["domain"])
                if result["domain_label"] is None and row.get("domain_label"):
                    result["domain_label"] = to_py(row["domain_label"])
                if result["range"] is None and row.get("range"):
                    result["range"] = row["range"].toPython() if hasattr(row["range"], "toPython") else str(row["range"])
                if result["range_label"] is None and row.get("range_label"):
                    result["range_label"] = to_py(row["range_label"])
            elif kind == "label" and row.get("label_val"):
                result["labels"].append(to_py(row["label_val"]))
            elif kind == "comment" and row.get("label_val"):
                result["comments"].append(to_py(row["label_val"]))
            elif kind == "altLabel" and row.get("label_val"):
                result["alt_labels"].append(to_py(row["label_val"]))
            elif kind == "superprop" and row.get("rel_uri"):
                rel_uri = to_py(row["rel_uri"])
                if rel_uri not in seen_super:
                    seen_super.add(rel_uri)
                    result["superproperties"].append({
                        "uri": rel_uri,
                        "label": to_py(row.get("rel_label")),
                    })
            elif kind == "subprop" and row.get("rel_uri"):
                rel_uri = to_py(row["rel_uri"])
                if rel_uri not in seen_sub:
                    seen_sub.add(rel_uri)
                    result["subproperties"].append({
                        "uri": rel_uri,
                        "label": to_py(row.get("rel_label")),
                    })
            elif kind == "column" and row.get("column_uri"):
                c_uri = to_py(row["column_uri"])
                if c_uri not in seen_columns:
                    seen_columns.add(c_uri)
                    result["assigned_columns"].append({
                        "column_uri": c_uri,
                        "column_name": to_py(row.get("column_name")),
                    })

        return result

    def update_property(
        self,
        uri: str,
        label: str,
        comments: Optional[list[str]] = None,
        alt_labels: Optional[list[str]] = None,
        domain: Optional[str] = None,
        range_uri: Optional[str] = None,
    ) -> bool:
        """Replace rdfs:label, rdfs:comment, skos:altLabel, rdfs:domain, and rdfs:range for an rdf:Property.

        Each predicate is fully replaced: multiple rdfs:label values become a single label;
        comments and alt labels use the provided lists (empty lists clear them).
        Empty or whitespace-only domain/range clears those triples.

        Returns:
            True if the URI exists and is typed rdf:Property; False otherwise.
        """
        uri_ref = URIRef(uri)
        if RDF.Property not in set(self._graph.objects(uri_ref, RDF.type)):
            return False

        label_clean = label.strip()
        if not label_clean:
            return False

        def _normalize_str_list(values: Optional[list[str]]) -> list[str]:
            if not values:
                return []
            out: list[str] = []
            for item in values:
                if item is None:
                    continue
                s = str(item).strip()
                if s:
                    out.append(s)
            return out

        for old in self._graph.objects(uri_ref, RDFS.label):
            self._graph.remove((uri_ref, RDFS.label, old))
        self._graph.add((uri_ref, RDFS.label, Literal(label_clean)))

        for old in self._graph.objects(uri_ref, RDFS.comment):
            self._graph.remove((uri_ref, RDFS.comment, old))
        for text in _normalize_str_list(comments):
            self._graph.add((uri_ref, RDFS.comment, Literal(text)))

        for old in self._graph.objects(uri_ref, SKOS.altLabel):
            self._graph.remove((uri_ref, SKOS.altLabel, old))
        for alt in _normalize_str_list(alt_labels):
            self._graph.add((uri_ref, SKOS.altLabel, Literal(alt)))

        for old in self._graph.objects(uri_ref, RDFS.domain):
            self._graph.remove((uri_ref, RDFS.domain, old))
        domain_clean = (domain or "").strip()
        if domain_clean:
            self._graph.add((uri_ref, RDFS.domain, URIRef(domain_clean)))

        for old in self._graph.objects(uri_ref, RDFS.range):
            self._graph.remove((uri_ref, RDFS.range, old))
        range_clean = (range_uri or "").strip()
        if range_clean:
            self._graph.add((uri_ref, RDFS.range, URIRef(range_clean)))

        logger.info(f"Updated property {uri}")
        return True

    def update_concept(
        self,
        uri: str,
        label: str,
        comments: Optional[list[str]] = None,
        alt_labels: Optional[list[str]] = None,
    ) -> bool:
        """Replace rdfs:label, rdfs:comment, and skos:altLabel for an rdfs:Class or skos:Concept.

        Comments and alt labels use the provided lists (empty lists clear them).

        Returns:
            True if the URI exists and is typed rdfs:Class or skos:Concept; False otherwise.
        """
        uri_ref = URIRef(uri)
        types = set(self._graph.objects(uri_ref, RDF.type))
        if RDFS.Class not in types and SKOS.Concept not in types:
            return False

        label_clean = label.strip()
        if not label_clean:
            return False

        def _normalize_str_list(values: Optional[list[str]]) -> list[str]:
            if not values:
                return []
            out: list[str] = []
            for item in values:
                if item is None:
                    continue
                s = str(item).strip()
                if s:
                    out.append(s)
            return out

        for old in self._graph.objects(uri_ref, RDFS.label):
            self._graph.remove((uri_ref, RDFS.label, old))
        self._graph.add((uri_ref, RDFS.label, Literal(label_clean)))

        for old in self._graph.objects(uri_ref, RDFS.comment):
            self._graph.remove((uri_ref, RDFS.comment, old))
        for text in _normalize_str_list(comments):
            self._graph.add((uri_ref, RDFS.comment, Literal(text)))

        for old in self._graph.objects(uri_ref, SKOS.altLabel):
            self._graph.remove((uri_ref, SKOS.altLabel, old))
        for alt in _normalize_str_list(alt_labels):
            self._graph.add((uri_ref, SKOS.altLabel, Literal(alt)))

        logger.info(f"Updated concept {uri}")
        return True

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

    def delete_concept_assignment(self, table_uri: str, concept_uri: str):
        """Remove a concept assignment from a table."""
        table_uri = URIRef(table_uri)
        concept_uri = URIRef(concept_uri)
        self._graph.remove((table_uri, UC.conceptAssignment, concept_uri))
        logger.info(f"Removed concept assignment: {table_uri} -> {concept_uri}")

    def delete_column_property_assignment(self, column_uri: str, property_uri: str):
        """Remove a property assignment from a column."""
        column_uri = URIRef(column_uri)
        property_uri = URIRef(property_uri)
        self._graph.remove((column_uri, UC.propertyAssignment, property_uri))
        logger.info(f"Removed property assignment: {column_uri} -> {property_uri}")

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

    def get_columns(self) -> list[dict]:
        r = self._graph.query(
            """
            SELECT ?uri ?name
            WHERE {
                ?uri rdf:type uc:Column .
                OPTIONAL { ?uri uc:name ?name }
            }
        """
        )
        return self._to_dicts(r.bindings)

    def get_table_by_name(self, name: str) -> Optional[dict]:
        """Look up a table by its uc:name (fully qualified catalog.schema.table)."""
        r = self._graph.query(
            """
            SELECT ?uri ?name
            WHERE {
                ?uri rdf:type uc:Table .
                ?uri uc:name ?name .
            }
            """,
            initBindings={"name": Literal(name)},
        )
        rows = self._to_dicts(r.bindings)
        return rows[0] if rows else None

    def get_column_by_name(self, name: str) -> Optional[dict]:
        """Look up a column by its uc:name (fully qualified catalog.schema.table.column)."""
        r = self._graph.query(
            """
            SELECT ?uri ?name
            WHERE {
                ?uri rdf:type uc:Column .
                ?uri uc:name ?name .
            }
            """,
            initBindings={"name": Literal(name)},
        )
        rows = self._to_dicts(r.bindings)
        return rows[0] if rows else None

    def insert_column(self, uri: str, name: str):
        uri = URIRef(uri)
        if uri not in self._graph.subjects(RDF.type, UC.Column):
            self._graph.add((uri, RDF.type, UC.Column))
            self._graph.add((uri, UC.name, Literal(name)))
        logger.info(f"Inserting column {name} iri: {uri}")

    def insert_function(self, uri: str, name: str):
        uri_ref = URIRef(uri)
        if uri_ref not in self._graph.subjects(RDF.type, UC.Function):
            self._graph.add((uri_ref, RDF.type, UC.Function))
            self._graph.add((uri_ref, UC.name, Literal(name)))
        logger.info(f"Inserting function {name} iri: {uri_ref}")

    def get_functions(self) -> list[dict]:
        r = self._graph.query(
            """
            SELECT ?uri ?name
            WHERE {
                ?uri rdf:type uc:Function .
                OPTIONAL { ?uri uc:name ?name }
            }
            """
        )
        return self._to_dicts(r.bindings)

    def get_function_by_name(self, name: str) -> Optional[dict]:
        """Look up a function by its uc:name (fully qualified catalog.schema.function)."""
        r = self._graph.query(
            """
            SELECT ?uri ?name
            WHERE {
                ?uri rdf:type uc:Function .
                ?uri uc:name ?name .
            }
            """,
            initBindings={"name": Literal(name)},
        )
        rows = self._to_dicts(r.bindings)
        return rows[0] if rows else None

    def insert_action_assignment(self, function_uri: str, action_uri: str):
        """Insert an action assignment from a function to an action."""
        function_uri = URIRef(function_uri)
        action_uri = URIRef(action_uri)
        self._graph.add((function_uri, UC.actionAssignment, action_uri))
        logger.info(f"Assigned function {function_uri} to action {action_uri}")

    def delete_action_assignment(self, function_uri: str, action_uri: str):
        """Remove an action assignment from a function."""
        function_uri = URIRef(function_uri)
        action_uri = URIRef(action_uri)
        self._graph.remove((function_uri, UC.actionAssignment, action_uri))
        logger.info(f"Removed action assignment: {function_uri} -> {action_uri}")

    def function_action_assignments(
        self,
        function_uri: Optional[str] = None,
        action_uri: Optional[str] = None,
    ) -> list[dict]:
        """Get function/action assignments.

        Args:
            function_uri: If provided, returns all actions assigned to this function
            action_uri: If provided, returns all functions assigned to this action
        """
        bindings = {}
        if function_uri:
            bindings["function_uri"] = URIRef(function_uri)
        if action_uri:
            bindings["action_uri"] = URIRef(action_uri)

        r = self._graph.query(
            """
            SELECT ?function_uri ?function_name ?action_uri ?action_name
            WHERE {
                ?function_uri uc:actionAssignment ?action_uri .
                OPTIONAL { ?function_uri uc:name ?function_name }
                OPTIONAL { ?action_uri rdfs:label ?action_name }
            }
            """,
            initBindings=bindings if bindings else None,
        )
        return self._to_dicts(r.bindings)

    def get_actions(self) -> list[dict]:
        r = self._graph.query(
            """
            SELECT DISTINCT ?uri ?label
            WHERE {
                ?uri a uc:Action .
                OPTIONAL { ?uri rdfs:label ?label }
            }
            ORDER BY ?label
            """
        )
        return self._to_dicts(r.bindings)

    def insert_action(
        self,
        uri: str,
        label: str,
        comment: Optional[str] = None,
        alt_labels: Optional[list[str]] = None,
        notes: Optional[list[str]] = None,
        action_inputs: Optional[list[str]] = None,
        action_outputs: Optional[list[str]] = None,
        target_concepts: Optional[list[str]] = None,
        scheme_uri: Optional[str] = None,
    ):
        """Create uc:Action with all properties."""
        uri_ref = URIRef(uri)
        self._graph.add((uri_ref, RDF.type, UC.Action))
        self._graph.add((uri_ref, RDFS.label, Literal(label)))
        if comment:
            self._graph.add((uri_ref, RDFS.comment, Literal(comment)))
        for alt in alt_labels or []:
            self._graph.add((uri_ref, SKOS.altLabel, Literal(alt)))
        for note in notes or []:
            self._graph.add((uri_ref, SKOS.note, Literal(note)))
        for prop_uri in action_inputs or []:
            self._graph.add((uri_ref, UC.actionInput, URIRef(prop_uri)))
        for prop_uri in action_outputs or []:
            self._graph.add((uri_ref, UC.actionOutput, URIRef(prop_uri)))
        for concept_uri in target_concepts or []:
            self._graph.add((uri_ref, UC.targetConcept, URIRef(concept_uri)))
        if scheme_uri:
            self._graph.add((uri_ref, SKOS.inScheme, URIRef(scheme_uri)))
        logger.info(f"Inserted action {label} iri: {uri_ref}")

    def get_action_detail_full(self, uri: str) -> Optional[dict]:
        """Get all action detail data: labels, comments, altLabels, notes,
        inputs, outputs, targetConcept, assigned functions.
        """
        uri_ref = URIRef(uri)
        r = self._graph.query(
            """
            SELECT ?row_kind ?label_val ?prop_uri ?prop_label ?concept_uri ?concept_label
                   ?function_uri ?function_name
            WHERE {
                {
                    BIND("label" AS ?row_kind) .
                    ?uri rdfs:label ?label_val .
                }
                UNION
                {
                    BIND("comment" AS ?row_kind) .
                    ?uri rdfs:comment ?label_val .
                }
                UNION
                {
                    BIND("altLabel" AS ?row_kind) .
                    ?uri skos:altLabel ?label_val .
                }
                UNION
                {
                    BIND("note" AS ?row_kind) .
                    ?uri skos:note ?label_val .
                }
                UNION
                {
                    BIND("input" AS ?row_kind) .
                    ?uri uc:actionInput ?prop_uri .
                    OPTIONAL { ?prop_uri rdfs:label ?prop_label }
                }
                UNION
                {
                    BIND("output" AS ?row_kind) .
                    ?uri uc:actionOutput ?prop_uri .
                    OPTIONAL { ?prop_uri rdfs:label ?prop_label }
                }
                UNION
                {
                    BIND("target" AS ?row_kind) .
                    ?uri uc:targetConcept ?concept_uri .
                    OPTIONAL { ?concept_uri rdfs:label ?concept_label }
                }
                UNION
                {
                    BIND("function" AS ?row_kind) .
                    ?function_uri uc:actionAssignment ?uri .
                    OPTIONAL { ?function_uri uc:name ?function_name }
                }
            }
            """,
            initBindings={"uri": uri_ref},
        )
        rows = self._to_dicts(r.bindings)
        if not rows:
            return None

        def to_py(obj):
            return obj.toPython() if obj is not None and hasattr(obj, "toPython") else (str(obj) if obj is not None else None)

        result = {
            "uri": uri,
            "labels": [],
            "comments": [],
            "alt_labels": [],
            "notes": [],
            "action_inputs": [],
            "action_outputs": [],
            "target_concepts": [],
            "assigned_functions": [],
        }
        seen_inputs = set()
        seen_outputs = set()
        seen_targets = set()
        seen_functions = set()

        for row in rows:
            kind = row.get("row_kind")
            if kind == "label" and row.get("label_val"):
                result["labels"].append(to_py(row["label_val"]))
            elif kind == "comment" and row.get("label_val"):
                result["comments"].append(to_py(row["label_val"]))
            elif kind == "altLabel" and row.get("label_val"):
                result["alt_labels"].append(to_py(row["label_val"]))
            elif kind == "note" and row.get("label_val"):
                result["notes"].append(to_py(row["label_val"]))
            elif kind == "input" and row.get("prop_uri"):
                p_uri = to_py(row["prop_uri"])
                if p_uri not in seen_inputs:
                    seen_inputs.add(p_uri)
                    result["action_inputs"].append({
                        "uri": p_uri,
                        "label": to_py(row.get("prop_label")),
                    })
            elif kind == "output" and row.get("prop_uri"):
                p_uri = to_py(row["prop_uri"])
                if p_uri not in seen_outputs:
                    seen_outputs.add(p_uri)
                    result["action_outputs"].append({
                        "uri": p_uri,
                        "label": to_py(row.get("prop_label")),
                    })
            elif kind == "target" and row.get("concept_uri"):
                c_uri = to_py(row["concept_uri"])
                if c_uri not in seen_targets:
                    seen_targets.add(c_uri)
                    result["target_concepts"].append({
                        "uri": c_uri,
                        "label": to_py(row.get("concept_label")),
                    })
            elif kind == "function" and row.get("function_uri"):
                f_uri = to_py(row["function_uri"])
                if f_uri not in seen_functions:
                    seen_functions.add(f_uri)
                    result["assigned_functions"].append({
                        "function_uri": f_uri,
                        "function_name": to_py(row.get("function_name")),
                    })

        return result

    def update_action(
        self,
        uri: str,
        label: str,
        comment: Optional[str] = None,
        alt_labels: Optional[list[str]] = None,
        notes: Optional[list[str]] = None,
        action_inputs: Optional[list[str]] = None,
        action_outputs: Optional[list[str]] = None,
        target_concepts: Optional[list[str]] = None,
    ):
        """Update an existing action's metadata."""
        uri_ref = URIRef(uri)
        for old in self._graph.objects(uri_ref, RDFS.label):
            self._graph.remove((uri_ref, RDFS.label, old))
        self._graph.add((uri_ref, RDFS.label, Literal(label)))
        for old in self._graph.objects(uri_ref, RDFS.comment):
            self._graph.remove((uri_ref, RDFS.comment, old))
        if comment:
            self._graph.add((uri_ref, RDFS.comment, Literal(comment)))
        for old in self._graph.objects(uri_ref, SKOS.altLabel):
            self._graph.remove((uri_ref, SKOS.altLabel, old))
        for alt in alt_labels or []:
            self._graph.add((uri_ref, SKOS.altLabel, Literal(alt)))
        for old in self._graph.objects(uri_ref, SKOS.note):
            self._graph.remove((uri_ref, SKOS.note, old))
        for note in notes or []:
            self._graph.add((uri_ref, SKOS.note, Literal(note)))
        for old in self._graph.objects(uri_ref, UC.actionInput):
            self._graph.remove((uri_ref, UC.actionInput, old))
        for prop_uri in action_inputs or []:
            self._graph.add((uri_ref, UC.actionInput, URIRef(prop_uri)))
        for old in self._graph.objects(uri_ref, UC.actionOutput):
            self._graph.remove((uri_ref, UC.actionOutput, old))
        for prop_uri in action_outputs or []:
            self._graph.add((uri_ref, UC.actionOutput, URIRef(prop_uri)))
        for old in self._graph.objects(uri_ref, UC.targetConcept):
            self._graph.remove((uri_ref, UC.targetConcept, old))
        for concept_uri in target_concepts or []:
            self._graph.add((uri_ref, UC.targetConcept, URIRef(concept_uri)))
        logger.info(f"Updated action {uri}")

    def get_properties(self) -> list[dict]:
        """Get all RDF properties with their domain and range."""
        r = self._graph.query(
            """
            SELECT DISTINCT ?uri ?name ?domain ?domain_label ?range ?range_label
            WHERE {
                ?uri a rdf:Property .
                OPTIONAL { ?uri rdfs:label ?name }
                OPTIONAL {
                    ?uri rdfs:domain ?domain .
                    OPTIONAL { ?domain rdfs:label ?domain_label }
                }
                OPTIONAL {
                    ?uri rdfs:range ?range .
                    OPTIONAL { ?range rdfs:label ?range_label }
                }
            }
        """
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

    def get_property_detail(self, uri: str) -> Optional[dict]:
        """Get detailed information about a single property including label, comment, domain, range, in_scheme, and alt labels."""
        r = self._graph.query(
            """
            SELECT ?uri ?label ?comment ?domain ?domain_label ?range ?range_label ?in_scheme
            WHERE {
                ?uri a rdf:Property .
                OPTIONAL { ?uri rdfs:label ?label }
                OPTIONAL { ?uri rdfs:comment ?comment }
                OPTIONAL { ?uri skos:inScheme ?in_scheme }
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

    def delete_object(self, uri: str):
        uri_ref = URIRef(uri)
        for pred, obj in list(self._graph.predicate_objects(subject=uri_ref)):
            self._graph.remove((uri_ref, pred, obj))
        for subj, pred in list(self._graph.subject_predicates(object=uri_ref)):
            self._graph.remove((subj, pred, uri_ref))
        logger.info(f"Deleted object {uri}")

    def search(self, query: str, kind: Optional[str] = None) -> list[dict]:
        """Search for concepts and properties using trigram similarity search."""
        if self._engine.dialect.name != "postgresql":
            raise ValueError("Unsupported database engine")
        literal_statements = self._graph.store.tables["literal_statements"]

        conditions = [literal_statements.c.object.op("%")(query)]
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
