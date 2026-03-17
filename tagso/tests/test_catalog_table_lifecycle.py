"""End-to-end lifecycle tests for catalog table registration.

Uses the same HTTP requests as the UI: POST to register, GET /visualisation to verify,
DELETE to deregister.
"""

import pytest


def test_catalog_table_register_and_deregister(client):
    """Register a table, verify it exists, deregister it, verify it is gone."""
    table_name = "main.default.test_table"
    register_payload = {"type": "table", "name": table_name}

    # Register (same as UI: POST with JSON body)
    register_resp = client.post(
        "/catalog/register",
        json=register_payload,
        headers={"Content-Type": "application/json"},
    )
    assert register_resp.status_code == 201
    data = register_resp.get_json()
    uri = data["uri"]
    assert uri

    # Verify it exists (direct endpoint for registered tables)
    list_resp = client.get("/catalog/registered_tables")
    assert list_resp.status_code == 200
    tables = list_resp.get_json()["tables"]
    matching = [t for t in tables if t["uri"] == uri]
    assert len(matching) == 1
    assert matching[0]["name"] == table_name

    # Deregister (same as UI: DELETE with JSON body containing uri)
    delete_resp = client.delete(
        "/catalog/resource",
        json={"uri": uri},
        headers={"Content-Type": "application/json"},
    )
    assert delete_resp.status_code == 200

    # Verify it is gone
    list_resp_after = client.get("/catalog/registered_tables")
    assert list_resp_after.status_code == 200
    tables_after = list_resp_after.get_json()["tables"]
    matching_after = [t for t in tables_after if t["uri"] == uri]
    assert len(matching_after) == 0
