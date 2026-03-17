"""End-to-end lifecycle tests for concept schemes.

Uses the same HTTP requests as the UI: POST to create, GET to list/verify,
DELETE to remove.
"""

import pytest


def test_concept_scheme_create_and_delete(client):
    """Create a concept scheme, verify it exists, delete it, verify it is gone."""
    label = "Test Scheme E2E"
    create_payload = {"label": label}

    # Create (same as UI: POST with JSON body)
    create_resp = client.post(
        "/concept_schemes",
        json=create_payload,
        headers={"Content-Type": "application/json"},
    )
    assert create_resp.status_code == 201
    data = create_resp.get_json()
    uri = data["uri"]
    assert data["label"] == label
    assert uri

    # Verify it exists (same as UI: GET schemes list)
    list_resp = client.get("/concept_schemes/schemes")
    assert list_resp.status_code == 200
    schemes = list_resp.get_json()["schemes"]
    matching = [s for s in schemes if s["uri"] == uri]
    assert len(matching) == 1
    assert matching[0]["label"] == label

    # Delete (same as UI would: DELETE with JSON body containing uri)
    delete_resp = client.delete(
        "/concept_schemes",
        json={"uri": uri},
        headers={"Content-Type": "application/json"},
    )
    assert delete_resp.status_code == 200

    # Verify it is gone
    list_resp_after = client.get("/concept_schemes/schemes")
    assert list_resp_after.status_code == 200
    schemes_after = list_resp_after.get_json()["schemes"]
    matching_after = [s for s in schemes_after if s["uri"] == uri]
    assert len(matching_after) == 0
