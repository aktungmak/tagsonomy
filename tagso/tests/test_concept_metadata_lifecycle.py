"""Tests for updating rdfs:Class / skos:Concept metadata via POST /concept_schemes/concept/update."""

import io
from urllib.parse import urlencode


def test_concept_update_metadata(client):
    scheme_resp = client.post(
        "/concept_schemes",
        json={"label": "ConceptMetaScheme"},
        headers={"Content-Type": "application/json"},
    )
    assert scheme_resp.status_code == 201
    scheme_uri = scheme_resp.get_json()["uri"]

    concept_uri = "http://example.com/ontology/TestConcept"

    ttl_content = f"""@prefix user: <http://example.com/ontology/> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix skos: <http://www.w3.org/2004/02/skos/core#> .

user:TestConcept a rdfs:Class ;
    rdfs:label "Original" ;
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

    update_resp = client.post(
        "/concept_schemes/concept/update",
        json={
            "uri": concept_uri,
            "label": "Updated label",
            "comments": ["First comment", "Second comment"],
            "alt_labels": ["Synonym A", "Synonym B"],
        },
        headers={"Content-Type": "application/json"},
    )
    assert update_resp.status_code == 200

    detail_resp = client.get(
        f"/concept_schemes/resource/concept?{urlencode({'uri': concept_uri})}"
    )
    assert detail_resp.status_code == 200
    res = detail_resp.get_json()["resource"]
    assert res["labels"] == ["Updated label"]
    assert res["comments"] == ["First comment", "Second comment"]
    assert res["alt_labels"] == ["Synonym A", "Synonym B"]


def test_concept_update_not_found(client):
    r = client.post(
        "/concept_schemes/concept/update",
        json={
            "uri": "http://example.com/missing#concept",
            "label": "X",
            "comments": [],
            "alt_labels": [],
        },
        headers={"Content-Type": "application/json"},
    )
    assert r.status_code == 404
