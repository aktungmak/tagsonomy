from flask import Blueprint, request, render_template, url_for, current_app
from werkzeug.local import LocalProxy
from werkzeug.utils import redirect
from rdflib import SKOS, RDFS

from config import USER_NS, generate_uri_from_name

classes_bp = Blueprint('classes', __name__)

gm = LocalProxy(lambda: current_app.gm)


@classes_bp.get('/classes')
def classes_get():
    class_uri = request.args.get('class_uri', '')
    # TODO collect assigned_tables in a single query
    classes = gm.get_classes()
    for cls in classes:
        cls['assigned_tables'] = gm.get_assignments(class_uri=cls['uri'])
    return render_template("classes.html", classes=classes, class_uri=class_uri, user_ns=str(USER_NS))


@classes_bp.post('/classes')
def classes_post():
    label = request.form['label']

    uri = request.form['uri']
    if not uri:
        uri = generate_uri_from_name(label)

    class_type_str = request.form['type']
    if class_type_str == 'rdfs_class':
        class_type = RDFS.Class
    elif class_type_str == 'skos_concept':
        class_type = SKOS.Concept
    else:
        return {'error': f'Invalid class type: {class_type_str}'}, 400

    comment = request.form['comment']

    gm.insert_class(uri, label, class_type, comment)
    return redirect(url_for('classes.classes_get', class_uri=uri))


@classes_bp.delete('/class')
def class_delete():
    data = request.get_json()
    class_uri = data.get('uri')
    if not class_uri:
        return {'error': 'URI is required'}, 400
    gm.delete_object(class_uri)
    return {'success': True}, 200
