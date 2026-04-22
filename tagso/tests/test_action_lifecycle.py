"""End-to-end lifecycle tests for actions.

Uses the same HTTP requests as the UI: POST to create, GET to list/verify,
DELETE to remove.
"""

import io
from urllib.parse import urlencode

import pytest


def test_action_create_and_delete(client):
    """Create an action, verify it exists, delete it, verify it is gone."""
    label = "Test Action E2E"
    create_payload = {"label": label}

    # Create (same as UI: POST with JSON body)
    create_resp = client.post(
        "/actions",
        json=create_payload,
        headers={"Content-Type": "application/json"},
    )
    assert create_resp.status_code == 201
    data = create_resp.get_json()
    uri = data["uri"]
    assert data["label"] == label
    assert uri

    # Verify it exists (same as UI: GET actions list)
    list_resp = client.get("/actions")
    assert list_resp.status_code == 200
    actions = list_resp.get_json()["actions"]
    matching = [a for a in actions if a["uri"] == uri]
    assert len(matching) == 1
    assert matching[0]["label"] == label

    # Delete (same as UI: DELETE with JSON body containing uri)
    delete_resp = client.delete(
        "/actions",
        json={"uri": uri},
        headers={"Content-Type": "application/json"},
    )
    assert delete_resp.status_code == 200

    # Verify it is gone
    list_resp_after = client.get("/actions")
    assert list_resp_after.status_code == 200
    actions_after = list_resp_after.get_json()["actions"]
    matching_after = [a for a in actions_after if a["uri"] == uri]
    assert len(matching_after) == 0


def test_action_create_with_properties_and_scheme(client):
    """Create an action with inputs, outputs, target concept, and scheme."""
    # 1. Create scheme
    scheme_resp = client.post(
        "/concept_schemes",
        json={"label": "ActionTestScheme"},
        headers={"Content-Type": "application/json"},
    )
    assert scheme_resp.status_code == 201
    scheme_uri = scheme_resp.get_json()["uri"]

    # 2. Import concept and property for action
    concept_uri = "http://example.com/ontology/TestConcept"
    property_uri = "http://example.com/ontology/TestProperty"
    ttl_content = f"""@prefix user: <http://example.com/ontology/> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix skos: <http://www.w3.org/2004/02/skos/core#> .
@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .

user:TestConcept a skos:Concept ;
    rdfs:label "Test Concept" ;
    skos:inScheme <{scheme_uri}> .

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

    # 3. Create action with full properties
    create_payload = {
        "label": "Calculate Premium",
        "comment": "Computes insurance premium",
        "alt_labels": ["Premium Calc"],
        "notes": ["Uses actuarial tables"],
        "action_inputs": [property_uri],
        "action_outputs": [property_uri],
        "target_concepts": [concept_uri],
        "scheme_uri": scheme_uri,
    }
    create_resp = client.post(
        "/actions",
        json=create_payload,
        headers={"Content-Type": "application/json"},
    )
    assert create_resp.status_code == 201
    data = create_resp.get_json()
    action_uri = data["uri"]
    assert action_uri

    # 4. Verify via concept_schemes resource (action detail)
    resource_resp = client.get(
        f"/concept_schemes/resource/action?{urlencode({'uri': action_uri})}"
    )
    assert resource_resp.status_code == 200
    resource_data = resource_resp.get_json()
    assert resource_data["type"] == "action"
    resource = resource_data["resource"]
    assert resource["uri"] == action_uri
    assert len(resource["labels"]) >= 1
    assert "Calculate Premium" in resource["labels"]
    assert len(resource["action_inputs"]) == 1
    assert resource["action_inputs"][0]["uri"] == property_uri
    assert len(resource["action_outputs"]) == 1
    assert len(resource["target_concepts"]) == 1
    assert resource["target_concepts"][0]["uri"] == concept_uri

    # 5. Verify action is in scheme members
    scheme_resp = client.get(f"/concept_schemes/scheme?uri={scheme_uri}")
    assert scheme_resp.status_code == 200
    scheme_data = scheme_resp.get_json()
    member_uris = scheme_data["member_uris"]
    assert action_uri in member_uris

    # 6. Cleanup
    client.delete(
        "/actions",
        json={"uri": action_uri},
        headers={"Content-Type": "application/json"},
    )
    client.delete(
        "/concept_schemes",
        json={"uri": scheme_uri},
        headers={"Content-Type": "application/json"},
    )
