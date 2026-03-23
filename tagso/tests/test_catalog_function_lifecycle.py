"""End-to-end lifecycle tests for catalog function registration.

Uses the same HTTP requests as the UI: POST to register, GET to verify,
DELETE to deregister.
"""

import pytest


def test_catalog_function_register_and_deregister(client):
    """Register a function, verify it exists, deregister it, verify it is gone."""
    function_name = "main.default.test_function"
    register_payload = {"type": "function", "name": function_name}

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

    # Verify it exists (direct endpoint for registered functions)
    list_resp = client.get("/catalog/registered_functions")
    assert list_resp.status_code == 200
    functions = list_resp.get_json()["functions"]
    matching = [f for f in functions if f["uri"] == uri]
    assert len(matching) == 1
    assert matching[0]["name"] == function_name

    # Deregister (same as UI: DELETE with JSON body containing uri)
    delete_resp = client.delete(
        "/catalog/resource",
        json={"uri": uri},
        headers={"Content-Type": "application/json"},
    )
    assert delete_resp.status_code == 200

    # Verify it is gone
    list_resp_after = client.get("/catalog/registered_functions")
    assert list_resp_after.status_code == 200
    functions_after = list_resp_after.get_json()["functions"]
    matching_after = [f for f in functions_after if f["uri"] == uri]
    assert len(matching_after) == 0
