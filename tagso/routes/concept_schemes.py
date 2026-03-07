from flask import Blueprint, request, render_template, current_app, jsonify
from werkzeug.local import LocalProxy

from config import generate_scheme_uri

concept_schemes_bp = Blueprint("concept_schemes", __name__)

gm = LocalProxy(lambda: current_app.gm)


@concept_schemes_bp.get("/concept_schemes")
def concept_schemes_get():
    return render_template("concept_schemes.html")


@concept_schemes_bp.get("/concept_schemes/schemes")
def concept_schemes_list():
    """JSON API: schemes only (for initial load)."""
    schemes = gm.get_concept_schemes()
    return jsonify({"schemes": schemes})


@concept_schemes_bp.get("/concept_schemes/members")
def concept_schemes_members():
    """JSON API: members for a scheme."""
    scheme_uri = request.args.get("scheme_uri")
    if not scheme_uri:
        return jsonify({"error": "scheme_uri required"}), 400
    members = gm.get_members_in_scheme(scheme_uri)
    return jsonify({"members": members})


@concept_schemes_bp.get("/concept_schemes/resource")
def concept_schemes_resource():
    """JSON for selected resource (concept or property) for detail pane."""
    uri = request.args.get("uri")
    if not uri:
        return jsonify({"error": "uri required"}), 400

    concept = gm.get_concept_detail(uri)
    if concept:
        related = gm.get_properties_for_concept(uri)
        return jsonify(
            {"resource": concept, "type": "concept", "related_properties": related}
        )

    prop = gm.get_property_detail(uri)
    if prop:
        return jsonify({"resource": prop, "type": "property"})

    return jsonify({"error": "Resource not found"}), 404


@concept_schemes_bp.get("/concept_schemes/scheme")
def concept_schemes_scheme_detail():
    """JSON for selected concept scheme for detail pane (edit name/description, add members)."""
    uri = request.args.get("uri")
    if not uri:
        return jsonify({"error": "uri required"}), 400

    scheme = gm.get_concept_scheme_detail(uri)
    if not scheme:
        return jsonify({"error": "Concept scheme not found"}), 404

    members = gm.get_members_in_scheme(uri)
    all_concepts = gm.get_concepts()
    all_properties = gm.get_properties_with_alt_labels()
    member_uris = {m["uri"] for m in members}

    return jsonify(
        {
            "scheme": scheme,
            "members": members,
            "all_concepts": all_concepts,
            "all_properties": all_properties,
            "member_uris": list(member_uris),
        }
    )


@concept_schemes_bp.post("/concept_schemes")
def concept_schemes_post():
    """Create new ConceptScheme."""
    label = request.form.get("label", "").strip()
    if not label:
        return jsonify({"error": "Label is required"}), 400

    uri = request.form.get("uri", "").strip()
    if not uri:
        uri = generate_scheme_uri(label)

    comment = request.form.get("comment", "").strip() or None

    gm.insert_concept_scheme(uri, label, comment)
    return jsonify({"uri": uri, "label": label}), 201


@concept_schemes_bp.post("/concept_schemes/update")
def concept_schemes_update():
    """Update concept scheme label and comment."""
    uri = request.form.get("uri")
    if not uri:
        return jsonify({"error": "uri required"}), 400

    label = request.form.get("label", "").strip()
    if not label:
        return jsonify({"error": "label required"}), 400

    comment = request.form.get("comment", "").strip() or None

    gm.update_concept_scheme(uri, label, comment)
    return jsonify({"success": True}), 200


@concept_schemes_bp.post("/concept_schemes/add_members")
def concept_schemes_add_members():
    """Add selected Concepts/Properties to the scheme."""
    data = request.get_json(silent=True) or {}
    uri = request.form.get("uri") or data.get("uri")
    resource_uris = request.form.getlist("resource_uris") or data.get(
        "resource_uris", []
    )

    if not uri:
        return jsonify({"error": "uri (scheme) required"}), 400

    if not resource_uris:
        return jsonify({"error": "resource_uris required"}), 400

    gm.add_members_to_scheme(uri, resource_uris)
    return jsonify({"success": True}), 200
