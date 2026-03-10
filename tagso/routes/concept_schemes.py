from flask import Blueprint, render_template, current_app
from werkzeug.local import LocalProxy

from config import generate_scheme_uri
from validation import require_params

concept_schemes_bp = Blueprint("concept_schemes", __name__)

gm = LocalProxy(lambda: current_app.gm)


@concept_schemes_bp.get("/concept_schemes")
def concept_schemes_get():
    return render_template("concept_schemes.html")


@concept_schemes_bp.get("/concept_schemes/schemes")
def concept_schemes_list():
    """JSON API: schemes only (for initial load)."""
    schemes = gm.get_concept_schemes()
    return {"schemes": schemes}


@concept_schemes_bp.get("/concept_schemes/members")
@require_params("scheme_uri", source="args")
def concept_schemes_members(params):
    """JSON API: members for a scheme."""
    members = gm.get_members_in_scheme(params["scheme_uri"])
    return {"members": members}


@concept_schemes_bp.get("/concept_schemes/resource")
@require_params("uri", source="args")
def concept_schemes_resource(params):
    """JSON for selected resource (concept or property) for detail pane."""
    uri = params["uri"]
    concept = gm.get_concept_detail(uri)
    if concept:
        related = gm.get_properties_for_concept(uri)
        return {"resource": concept, "type": "concept", "related_properties": related}

    prop = gm.get_property_detail(uri)
    if prop:
        return {"resource": prop, "type": "property"}

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
    member_uris = {m["uri"] for m in members}

    return {
        "scheme": scheme,
        "members": members,
        "all_concepts": all_concepts,
        "all_properties": all_properties,
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


@concept_schemes_bp.delete("/concept_schemes")
@require_params("uri", source="json")
def concept_schemes_delete(params):
    """Delete a concept scheme and all its triples."""
    gm.delete_object(params["uri"])
    return {"success": True}, 200
