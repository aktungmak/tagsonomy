"""End-to-end lifecycle tests for catalog column registration.

Uses the same HTTP requests as the UI: POST to register, GET /visualisation to verify,
DELETE to deregister.
"""

import pytest


def test_catalog_column_register_and_deregister(client):
    """Register a column, verify it exists, deregister it, verify it is gone."""
    column_name = "main.default.test_table.test_column"
    register_payload = {"type": "column", "name": column_name}

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

    # Verify it exists (direct endpoint for registered columns)
    list_resp = client.get("/catalog/registered_columns")
    assert list_resp.status_code == 200
    columns = list_resp.get_json()["columns"]
    matching = [c for c in columns if c["uri"] == uri]
    assert len(matching) == 1
    assert matching[0]["name"] == column_name

    # Deregister (same as UI: DELETE with JSON body containing uri)
    delete_resp = client.delete(
        "/catalog/resource",
        json={"uri": uri},
        headers={"Content-Type": "application/json"},
    )
    assert delete_resp.status_code == 200

    # Verify it is gone
    list_resp_after = client.get("/catalog/registered_columns")
    assert list_resp_after.status_code == 200
    columns_after = list_resp_after.get_json()["columns"]
    matching_after = [c for c in columns_after if c["uri"] == uri]
    assert len(matching_after) == 0
