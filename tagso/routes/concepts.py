from flask import Blueprint, request, render_template, url_for, current_app
from werkzeug.local import LocalProxy
from werkzeug.utils import redirect
from rdflib import SKOS, RDFS

from config import USER_NS, generate_uri_from_name

concepts_bp = Blueprint("concepts", __name__)

gm = LocalProxy(lambda: current_app.gm)


@concepts_bp.get("/concepts")
def concepts_get():
    concept_uri = request.args.get("concept_uri")
    # TODO collect assigned_tables in a single query
    concepts = gm.get_concepts()
    for concept in concepts:
        concept["assigned_tables"] = gm.concept_table_assignments(
            concept_uri=concept["uri"]
        )
        concept["related_properties"] = gm.get_properties_for_concept(concept["uri"])
        concept["alt_labels"] = gm.get_alt_labels(concept["uri"])
    return render_template(
        "concepts.html",
        concepts=concepts,
        concept_uri=concept_uri or "",
        user_ns=str(USER_NS),
    )


@concepts_bp.post("/concepts")
def concepts_post():
    label = request.form["label"]

    uri = request.form["uri"]
    if not uri:
        uri = generate_uri_from_name(label)

    concept_type_str = request.form["type"]
    if concept_type_str == "rdfs_class":
        concept_type = RDFS.Class
    elif concept_type_str == "skos_concept":
        concept_type = SKOS.Concept
    else:
        return {"error": f"Invalid concept type: {concept_type_str}"}, 400

    comment = request.form["comment"]

    alt_labels = request.form.getlist("alt_labels")

    gm.insert_concept(uri, label, concept_type, comment, alt_labels=alt_labels)
    return redirect(url_for("concepts.concepts_get", concept_uri=uri))


@concepts_bp.delete("/concept")
def concept_delete():
    data = request.get_json()
    concept_uri = data.get("uri")
    if not concept_uri:
        return {"error": "URI is required"}, 400
    gm.delete_object(concept_uri)
    return {"success": True}, 200


@concepts_bp.get("/concept/edit")
def concept_edit_get():
    concept_uri = request.args.get("uri")
    if not concept_uri:
        return redirect(url_for("concepts.concepts_get"))

    concept = gm.get_concept_detail(concept_uri)
    if not concept:
        return {"error": "Concept not found"}, 404

    relationships = gm.get_concept_relationships(concept_uri)
    all_concepts = gm.get_concepts()

    return render_template(
        "edit_concept.html",
        concept=concept,
        relationships=relationships,
        all_concepts=all_concepts,
        rdfs_class=str(RDFS.Class),
        skos_concept=str(SKOS.Concept),
    )


@concepts_bp.post("/concept/edit")
def concept_edit_post():
    concept_uri = request.form["uri"]
    label = request.form["label"]
    comment = request.form.get("comment", "")

    alt_labels = request.form.getlist("alt_labels")

    gm.update_concept(concept_uri, label, comment, alt_labels=alt_labels)
    return redirect(url_for("concepts.concept_edit_get", uri=concept_uri))


@concepts_bp.post("/concept/relationship")
def concept_add_relationship():
    subject_uri = request.form["subject_uri"]
    predicate_type = request.form["predicate_type"]
    object_uri = request.form["object_uri"]

    if not all([subject_uri, predicate_type, object_uri]):
        return {"error": "All fields are required"}, 400

    gm.add_concept_relationship(subject_uri, predicate_type, object_uri)
    return redirect(url_for("concepts.concept_edit_get", uri=subject_uri))


@concepts_bp.delete("/concept/relationship")
def concept_delete_relationship():
    data = request.get_json()
    subject_uri = data.get("subject_uri")
    predicate_type = data.get("predicate_type")
    object_uri = data.get("object_uri")

    if not all([subject_uri, predicate_type, object_uri]):
        return {"error": "All fields are required"}, 400

    gm.delete_concept_relationship(subject_uri, predicate_type, object_uri)
    return {"success": True}, 200
