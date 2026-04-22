from flask import Blueprint, render_template, current_app
from rdflib.namespace import XSD
from werkzeug.local import LocalProxy

from config import generate_scheme_uri
from validation import require_params

concept_schemes_bp = Blueprint("concept_schemes", __name__)

gm = LocalProxy(lambda: current_app.gm)

XSD_DATATYPE_OPTIONS = [
    {"uri": str(t), "label": f"xsd:{t.rsplit('#', 1)[-1]}"}
    for t in (XSD.string, XSD.integer, XSD.float, XSD.dateTime, XSD.boolean)
]


@concept_schemes_bp.get("/concept_schemes")
def concept_schemes_get():
    return render_template("concept_schemes.html")


@concept_schemes_bp.get("/concept_schemes/concept")
@concept_schemes_bp.get("/concept_schemes/property")
@concept_schemes_bp.get("/concept_schemes/action")
def concept_schemes_resource_page():
    """Page with kind in path for deep links (e.g. /concept_schemes/concept?uri=...)."""
    return render_template("concept_schemes.html")


@concept_schemes_bp.get("/concept_schemes/schemes")
def concept_schemes_list():
    """JSON API: schemes only (for initial load)."""
    schemes = gm.get_concept_schemes()
    return {"schemes": schemes}


@concept_schemes_bp.get("/concept_schemes/concepts")
def concept_schemes_concepts():
    """JSON API: all class/concept URIs for domain and range dropdowns."""
    concepts = gm.get_concepts()
    concepts_sorted = sorted(
        concepts,
        key=lambda c: (
            (c.get("label") or c.get("uri") or "").lower(),
            c.get("uri") or "",
        ),
    )
    return {"concepts": concepts_sorted, "datatypes": XSD_DATATYPE_OPTIONS}


@concept_schemes_bp.get("/concept_schemes/members")
@require_params("scheme_uri", source="args")
def concept_schemes_members(params):
    """JSON API: members for a scheme."""
    members = gm.get_members_in_scheme(params["scheme_uri"])
    return {"members": members}


@concept_schemes_bp.get("/concept_schemes/resource/<kind>")
@require_params("uri", source="args")
def concept_schemes_resource(params, kind):
    """JSON for selected resource (concept, property, or action) for detail pane."""
    if kind not in ("concept", "property", "action"):
        return {"error": "Invalid kind"}, 404

    uri = params["uri"]
    if kind == "concept":
        result = gm.get_concept_detail_full(uri)
        if result:
            return {"resource": result, "type": "concept"}
    elif kind == "property":
        result = gm.get_property_detail_full(uri)
        if result:
            return {"resource": result, "type": "property"}
    elif kind == "action":
        result = gm.get_action_detail_full(uri)
        if result:
            return {"resource": result, "type": "action"}

    return {"error": "Resource not found"}, 404


@concept_schemes_bp.get("/concept_schemes/scheme")
@require_params("uri", source="args")
def concept_schemes_scheme_detail(params):
    """JSON for selected concept scheme for detail pane (edit name/description, add members)."""
    uri = params["uri"]
    scheme = gm.get_concept_scheme_detail(uri)
    if not scheme:
        return {"error": "Concept scheme not found"}, 404

    members = gm.get_members_in_scheme(uri)
    all_concepts = gm.get_concepts()
    all_properties = gm.get_properties_with_alt_labels()
    all_actions = gm.get_actions()
    member_uris = {m["uri"] for m in members}

    return {
        "scheme": scheme,
        "members": members,
        "all_concepts": all_concepts,
        "all_properties": all_properties,
        "all_actions": all_actions,
        "member_uris": list(member_uris),
    }


@concept_schemes_bp.post("/concept_schemes")
@require_params("label", source="json")
def concept_schemes_post(params):
    """Create new ConceptScheme."""
    label = params["label"].strip()
    uri = (params.get("uri") or "").strip() or generate_scheme_uri(label)
    comment = (params.get("comment") or "").strip() or None

    gm.insert_concept_scheme(uri, label, comment)
    return {"uri": uri, "label": label}, 201


@concept_schemes_bp.post("/concept_schemes/update")
@require_params("uri", "label", source="json")
def concept_schemes_update(params):
    """Update concept scheme label and comment."""
    uri = params["uri"]
    label = params["label"].strip()
    comment = (params.get("comment") or "").strip() or None

    gm.update_concept_scheme(uri, label, comment)
    return {"success": True}, 200


@concept_schemes_bp.post("/concept_schemes/add_members")
@require_params("uri", "resource_uris", source="json")
def concept_schemes_add_members(params):
    """Add selected Concepts/Properties to the scheme."""
    gm.add_members_to_scheme(params["uri"], params["resource_uris"])
    return {"success": True}, 200


@concept_schemes_bp.post("/concept_schemes/property/update")
@require_params("uri", "label", source="json")
def concept_schemes_property_update(params):
    """Update property metadata: label, comments, alt labels, domain, and range."""
    comments = params.get("comments")
    alt_labels = params.get("alt_labels")
    if comments is not None and not isinstance(comments, list):
        return {"error": "comments must be a JSON array of strings"}, 400
    if alt_labels is not None and not isinstance(alt_labels, list):
        return {"error": "alt_labels must be a JSON array of strings"}, 400

    domain = params.get("domain")
    range_val = params.get("range")
    if domain is not None and not isinstance(domain, str):
        return {"error": "domain must be a string"}, 400
    if range_val is not None and not isinstance(range_val, str):
        return {"error": "range must be a string"}, 400

    ok = gm.update_property(
        uri=params["uri"],
        label=params["label"],
        comments=comments if comments is not None else [],
        alt_labels=alt_labels if alt_labels is not None else [],
        domain=domain,
        range_uri=range_val,
    )
    if not ok:
        return {"error": "Property not found"}, 404
    return {"success": True}, 200


@concept_schemes_bp.post("/concept_schemes/concept/update")
@require_params("uri", "label", source="json")
def concept_schemes_concept_update(params):
    """Update concept/class metadata: label, comments, and alternative labels."""
    comments = params.get("comments")
    alt_labels = params.get("alt_labels")
    if comments is not None and not isinstance(comments, list):
        return {"error": "comments must be a JSON array of strings"}, 400
    if alt_labels is not None and not isinstance(alt_labels, list):
        return {"error": "alt_labels must be a JSON array of strings"}, 400

    ok = gm.update_concept(
        uri=params["uri"],
        label=params["label"],
        comments=comments if comments is not None else [],
        alt_labels=alt_labels if alt_labels is not None else [],
    )
    if not ok:
        return {"error": "Concept not found"}, 404
    return {"success": True}, 200


@concept_schemes_bp.delete("/concept_schemes")
@require_params("uri", source="json")
def concept_schemes_delete(params):
    """Delete a concept scheme and all its triples."""
    gm.delete_object(params["uri"])
    return {"success": True}, 200
