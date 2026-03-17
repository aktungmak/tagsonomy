"""End-to-end lifecycle tests for property-to-column assignment.

Flow: create scheme, import property, register table and column, assign, verify,
unassign, cleanup.
"""

import io

import pytest


def test_property_assignment_create_and_delete(client):
    """Assign property to column, verify it exists, unassign, verify it is gone."""
    # 1. Create scheme
    scheme_resp = client.post(
        "/concept_schemes",
        json={"label": "TestScheme"},
        headers={"Content-Type": "application/json"},
    )
    assert scheme_resp.status_code == 201
    scheme_uri = scheme_resp.get_json()["uri"]

    # 2. Import property (TTL with property in scheme)
    property_uri = "http://example.com/ontology/TestProperty"
    ttl_content = f"""@prefix user: <http://example.com/ontology/> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix skos: <http://www.w3.org/2004/02/skos/core#> .
@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .

user:TestProperty a rdf:Property ;
    rdfs:label "Test Property" ;
    skos:inScheme <{scheme_uri}> .
"""
    import_resp = client.post(
        "/import_export",
        data={
            "file": (io.BytesIO(ttl_content.encode()), "test.ttl"),
            "default_scheme": scheme_uri,
        },
    )
    assert import_resp.status_code == 200

    # 3. Register table and column
    table_name = "main.default.test_table"
    column_name = "main.default.test_table.test_column"
    table_resp = client.post(
        "/catalog/register",
        json={"type": "table", "name": table_name},
        headers={"Content-Type": "application/json"},
    )
    assert table_resp.status_code == 201
    table_uri = table_resp.get_json()["uri"]

    column_resp = client.post(
        "/catalog/register",
        json={"type": "column", "name": column_name},
        headers={"Content-Type": "application/json"},
    )
    assert column_resp.status_code == 201
    column_uri = column_resp.get_json()["uri"]

    # 4. Assign property to column (same as UI)
    assign_resp = client.post(
        "/catalog/assign_property",
        json={"column_uri": column_uri, "property_uri": property_uri},
        headers={"Content-Type": "application/json"},
    )
    assert assign_resp.status_code == 201

    # 5. Verify assignment exists (direct endpoint)
    list_resp = client.get("/catalog/property_assignments")
    assert list_resp.status_code == 200
    assignments = list_resp.get_json()["assignments"]
    matching = [
        a
        for a in assignments
        if a["column_uri"] == column_uri and a["property_uri"] == property_uri
    ]
    assert len(matching) == 1

    # 6. Unassign (same as UI)
    unassign_resp = client.delete(
        "/catalog/assign_property",
        json={"column_uri": column_uri, "property_uri": property_uri},
        headers={"Content-Type": "application/json"},
    )
    assert unassign_resp.status_code == 200

    # 7. Verify assignment is gone
    list_resp_after = client.get("/catalog/property_assignments")
    assert list_resp_after.status_code == 200
    assignments_after = list_resp_after.get_json()["assignments"]
    matching_after = [
        a
        for a in assignments_after
        if a["column_uri"] == column_uri and a["property_uri"] == property_uri
    ]
    assert len(matching_after) == 0

    # 8. Cleanup: deregister column, table, delete property, delete scheme
    client.delete(
        "/catalog/resource",
        json={"uri": column_uri},
        headers={"Content-Type": "application/json"},
    )
    client.delete(
        "/catalog/resource",
        json={"uri": table_uri},
        headers={"Content-Type": "application/json"},
    )
    client.delete(
        "/catalog/resource",
        json={"uri": property_uri},
        headers={"Content-Type": "application/json"},
    )
    client.delete(
        "/concept_schemes",
        json={"uri": scheme_uri},
        headers={"Content-Type": "application/json"},
    )
