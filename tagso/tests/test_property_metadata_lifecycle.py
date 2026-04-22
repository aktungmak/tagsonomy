"""Tests for updating rdf:Property metadata via POST /concept_schemes/property/update."""

import io
from urllib.parse import urlencode


def test_property_update_metadata(client):
    scheme_resp = client.post(
        "/concept_schemes",
        json={"label": "PropMetaScheme"},
        headers={"Content-Type": "application/json"},
    )
    assert scheme_resp.status_code == 201
    scheme_uri = scheme_resp.get_json()["uri"]

    domain_uri = "http://example.com/ontology/DomainClass"
    range_uri = "http://example.com/ontology/RangeClass"
    property_uri = "http://example.com/ontology/TestProp"

    ttl_content = f"""@prefix user: <http://example.com/ontology/> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix skos: <http://www.w3.org/2004/02/skos/core#> .
@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .

user:DomainClass a rdfs:Class ;
    rdfs:label "Domain" ;
    skos:inScheme <{scheme_uri}> .

user:RangeClass a rdfs:Class ;
    rdfs:label "Range" ;
    skos:inScheme <{scheme_uri}> .

user:TestProp a rdf:Property ;
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
        "/concept_schemes/property/update",
        json={
            "uri": property_uri,
            "label": "Updated label",
            "comments": ["First comment", "Second comment"],
            "alt_labels": ["Synonym A", "Synonym B"],
            "domain": domain_uri,
            "range": range_uri,
        },
        headers={"Content-Type": "application/json"},
    )
    assert update_resp.status_code == 200

    detail_resp = client.get(
        f"/concept_schemes/resource/property?{urlencode({'uri': property_uri})}"
    )
    assert detail_resp.status_code == 200
    res = detail_resp.get_json()["resource"]
    assert res["labels"] == ["Updated label"]
    assert res["comments"] == ["First comment", "Second comment"]
    assert res["alt_labels"] == ["Synonym A", "Synonym B"]
    assert res["domain"] == domain_uri
    assert res["range"] == range_uri


def test_property_update_not_found(client):
    r = client.post(
        "/concept_schemes/property/update",
        json={
            "uri": "http://example.com/missing#prop",
            "label": "X",
            "comments": [],
            "alt_labels": [],
            "domain": "",
            "range": "",
        },
        headers={"Content-Type": "application/json"},
    )
    assert r.status_code == 404
