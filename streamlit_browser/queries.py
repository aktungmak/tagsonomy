"""
SPARQL query functions for the RDFS Ontology Browser.

This module contains all the SPARQL queries used to retrieve information
from the RDF graph. These queries are designed to be reusable across
different parts of the application.
"""

from rdflib import Graph, URIRef, Literal


def rdfs_classes(graph: Graph):
    """Get all RDFS classes from the graph."""
    query = """
    SELECT DISTINCT ?class_iri ?label
    WHERE {
        {
            ?class_iri a rdfs:Class .
        }
        UNION
        {
            ?class_iri rdfs:subClassOf ?other .
        }
        OPTIONAL { ?class_iri rdfs:label ?label }
    }
    """
    return [r.asdict() for r in graph.query(query)]


def subclasses(graph: Graph, class_uri: URIRef):
    """Get direct subclasses of a given class."""
    query = """
    SELECT DISTINCT ?class_iri ?label
    WHERE {
        ?class_iri rdfs:subClassOf ?class .
        OPTIONAL { ?class_iri rdfs:label ?label }
    }
    """
    return [r.asdict() for r in graph.query(query, initBindings={'class': class_uri})]


def superclasses(graph: Graph, class_uri: URIRef):
    """Get direct superclasses of a given class."""
    query = """
    SELECT DISTINCT ?class_iri ?label
    WHERE {
        ?class rdfs:subClassOf ?class_iri .
        OPTIONAL { ?class_iri rdfs:label ?label }
    }
    """
    return [r.asdict() for r in graph.query(query, initBindings={'class': class_uri})]


def rdfs_properties(graph: Graph):
    """Get all RDFS properties from the graph."""
    query = """
    SELECT DISTINCT ?property_iri ?label
    WHERE {
        {
            ?property_iri a rdfs:Property .
        }
        UNION
        {
            ?property_iri rdfs:subPropertyOf ?other .
        }
        OPTIONAL { ?property_iri rdfs:label ?label }
    }
    """
    return [r.asdict() for r in graph.query(query)]


def class_attributes(graph: Graph, class_uri: URIRef):
    """Get all attributes where this class is the subject."""
    query = """
    SELECT DISTINCT ?predicate ?object
    WHERE {
        ?class ?predicate ?object .
        FILTER(?predicate != rdf:type && ?predicate != rdfs:subClassOf)
    }
    ORDER BY ?predicate ?object
    """
    return list(graph.query(query, initBindings={'class': class_uri}))


def semantic_assignments(graph: Graph, class_uri: URIRef):
    """Get catalog objects that have semantic assignments to this class."""
    query = """
    SELECT DISTINCT ?object ?name
    WHERE {
        ?object uc:semanticAssignment ?class .
        OPTIONAL { ?object uc:name ?name }
    }
    ORDER BY ?name ?object
    """
    return list(graph.query(query, initBindings={'class': class_uri}))


def related_properties(graph: Graph, class_uri: URIRef):
    """Get properties that have this class as domain or range."""
    query = """
    SELECT DISTINCT ?property ?predicate ?predicate_label
    WHERE {
        {
            ?property rdfs:domain ?class .
            BIND("rdfs:domain" as ?predicate)
        }
        UNION
        {
            ?property rdfs:range ?class .
            BIND("rdfs:range" as ?predicate)
        }
        OPTIONAL { ?property rdfs:label ?predicate_label }
    }
    ORDER BY ?property ?predicate
    """
    return list(graph.query(query, initBindings={'class': class_uri}))


def subproperties(graph: Graph, property_uri: URIRef):
    """Get direct subproperties of a given property."""
    query = """
    SELECT DISTINCT ?property_iri ?label
    WHERE {
        ?property_iri rdfs:subPropertyOf ?parent_property .
        OPTIONAL { ?property_iri rdfs:label ?label }
    }
    ORDER BY ?label ?property_iri
    """
    return [r.asdict() for r in graph.query(query, initBindings={'parent_property': property_uri})]


def superproperties(graph: Graph, property_uri: URIRef):
    """Get direct superproperties of a given property."""
    query = """
    SELECT DISTINCT ?property_iri ?label
    WHERE {
        ?child_property rdfs:subPropertyOf ?property_iri .
        OPTIONAL { ?property_iri rdfs:label ?label }
    }
    ORDER BY ?label ?property_iri
    """
    return [r.asdict() for r in graph.query(query, initBindings={'child_property': property_uri})]


def property_attributes(graph: Graph, property_uri: URIRef):
    """Get all attributes where this property is the subject."""
    query = """
    SELECT DISTINCT ?predicate ?object
    WHERE {
        ?property ?predicate ?object .
        FILTER(?predicate != rdf:type && ?predicate != rdfs:subPropertyOf && 
               ?predicate != rdfs:domain && ?predicate != rdfs:range)
    }
    ORDER BY ?predicate ?object
    """
    return list(graph.query(query, initBindings={'property': property_uri}))


def related_concepts(graph: Graph, property_uri: URIRef):
    """Get concepts that are related to this property via domain and range."""
    query = """
    SELECT DISTINCT ?concept ?predicate ?label
    WHERE {
        {
            ?property rdfs:domain ?concept .
            BIND("rdfs:domain" as ?predicate)
        }
        UNION
        {
            ?property rdfs:range ?concept .
            BIND("rdfs:range" as ?predicate)
        }
        OPTIONAL { ?concept rdfs:label ?label }
    }
    ORDER BY ?predicate ?label ?concept
    """
    return list(graph.query(query, initBindings={'property': property_uri}))


def catalog_objects(graph: Graph):
    """Get all catalog objects (uc:Table and uc:Column)."""
    query = """
    SELECT DISTINCT ?object ?type ?name
    WHERE {
        ?object a ?type .
        FILTER(?type = uc:Table || ?type = uc:Column)
        OPTIONAL { ?object uc:name ?name }
    }
    """
    return list(graph.query(query))


def catalog_object_attributes(graph: Graph, object_uri: URIRef):
    """Get all attributes where this catalog object is the subject."""
    query = """
    SELECT DISTINCT ?predicate ?object
    WHERE {
        ?catalog_object ?predicate ?object .
        FILTER(?predicate != rdf:type && ?predicate != uc:semanticAssignment)
    }
    """
    return list(graph.query(query, initBindings={'catalog_object': object_uri}))


def catalog_object_semantic_assignments(graph: Graph, object_uri: URIRef):
    """Get classes that this catalog object is semantically assigned to."""
    query = """
    SELECT DISTINCT ?class ?label
    WHERE {
        ?catalog_object uc:semanticAssignment ?class .
        OPTIONAL { ?class rdfs:label ?label }
    }
    """
    return list(graph.query(query, initBindings={'catalog_object': object_uri}))


def search_properties_by_name(graph: Graph, search_term: str):
    """Search for properties by name/label."""
    if not search_term:
        return rdfs_properties(graph)

    search_term = search_term.lower()
    properties = rdfs_properties(graph)

    # Filter properties that match the search term
    filtered = []
    for prop_uri, label, domain, range_uri in properties:
        prop_name = str(prop_uri).split('/')[-1].split('#')[-1].lower()
        label_text = str(label).lower() if label else ""

        if search_term in prop_name or search_term in label_text:
            filtered.append((prop_uri, label, domain, range_uri))

    return filtered


def search_classes_by_name(graph: Graph, search_term: str):
    """Search for classes by name/label."""
    if not search_term:
        return rdfs_classes(graph)

    search_term = search_term.lower()
    classes = rdfs_classes(graph)

    # Filter classes that match the search term
    filtered = []
    for class_uri, label in classes:
        class_name = str(class_uri).split('/')[-1].split('#')[-1].lower()
        label_text = str(label).lower() if label else ""

        if search_term in class_name or search_term in label_text:
            filtered.append((class_uri, label))

    return filtered


def search_catalog_objects_by_name(graph: Graph, search_term: str):
    """Search for catalog objects by name."""
    if not search_term:
        return catalog_objects(graph)

    search_term = search_term.lower()
    catalog_objects_list = catalog_objects(graph)

    # Filter catalog objects that match the search term
    filtered = []
    for obj_uri, obj_type, name in catalog_objects_list:
        obj_name = str(obj_uri).split('/')[-1].split('#')[-1].lower()
        name_text = str(name).lower() if name else ""

        if search_term in obj_name or search_term in name_text:
            filtered.append((obj_uri, obj_type, name))

    return filtered
