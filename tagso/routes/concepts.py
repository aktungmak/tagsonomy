from flask import Blueprint, request, render_template, url_for, current_app
from werkzeug.local import LocalProxy
from werkzeug.utils import redirect
from rdflib import SKOS, RDFS

from config import USER_NS, generate_uri_from_name

concepts_bp = Blueprint('concepts', __name__)

gm = LocalProxy(lambda: current_app.gm)


@concepts_bp.get('/concepts')
def concepts_get():
    concept_uri = request.args.get('concept_uri', '')
    # TODO collect assigned_tables in a single query
    concepts = gm.get_concepts()
    for concept in concepts:
        concept['assigned_tables'] = gm.get_assignments(concept_uri=concept['uri'])
    return render_template("concepts.html", concepts=concepts, concept_uri=concept_uri, user_ns=str(USER_NS))


@concepts_bp.post('/concepts')
def concepts_post():
    label = request.form['label']

    uri = request.form['uri']
    if not uri:
        uri = generate_uri_from_name(label)

    concept_type_str = request.form['type']
    if concept_type_str == 'rdfs_class':
        concept_type = RDFS.Class
    elif concept_type_str == 'skos_concept':
        concept_type = SKOS.Concept
    else:
        return {'error': f'Invalid concept type: {concept_type_str}'}, 400

    comment = request.form['comment']

    gm.insert_concept(uri, label, concept_type, comment)
    return redirect(url_for('concepts.concepts_get', concept_uri=uri))


@concepts_bp.delete('/concept')
def concept_delete():
    data = request.get_json()
    concept_uri = data.get('uri')
    if not concept_uri:
        return {'error': 'URI is required'}, 400
    gm.delete_object(concept_uri)
    return {'success': True}, 200

