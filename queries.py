import rdflib



def securable_to_classes(g: rdflib.Graph):
    "use the uc:semanticAssignment predicate to simplify"
    result = g.query("""
    SELECT ?securable_type ?securable_name (GROUP_CONCAT(?tag; SEPARATOR=",") AS ?tags)
    WHERE {
        ?Securable a [rdfs:subClassOf* uc:Securable;
                      rdfs:label ?securable_type];
            uc:name ?securable_name;
            uc:semanticAssignment/rdfs:subClassOf* ?super.
        ?super rdfs:label ?tag.
    }
    GROUP BY ?securable_type ?securable_name""")
    return ((stype.toPython(), sname.toPython(), tags.split(",")) for stype, sname, tags in result)

def semantic_inconsistency(g: rdflib.Graph):
    result = g.query("""
    SELECT ?upstream_securable_name ?downstream_securable_name
    WHERE {
        ?upstream_securable a [rdfs:subClassOf* uc:Securable;
                               rdfs:label ?securable_type];
            uc:name ?upstream_securable_name;
            uc:semanticAssignment ?upstream_class.
        ?downstream_securable a [rdfs:subClassOf* uc:Securable;
                                 rdfs:label ?securable_type];
            uc:name ?downstream_securable_name;
            uc:semanticAssignment ?downstream_class.
    }
    """)