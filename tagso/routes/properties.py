from flask import Blueprint, render_template, request, current_app, url_for
from werkzeug.local import LocalProxy
from werkzeug.utils import redirect

from config import generate_uri_from_name

properties_bp = Blueprint('properties', __name__)

gm = LocalProxy(lambda: current_app.gm)


@properties_bp.get('/properties')
def properties_get():
    property_uri = request.args.get('property_uri')
    properties = gm.get_properties(property_uri)
    concepts = gm.get_concepts()
    return render_template("properties.html", properties=properties, property_uri=property_uri, concepts=concepts)


@properties_bp.post('/properties')
def properties_post():
    name = request.form['name']

    uri = request.form.get('uri', '')
    if not uri:
        uri = generate_uri_from_name(name)

    domain = request.form.get('domain')
    range_ = request.form.get('range')

    gm.insert_property(uri, name, domain=domain, range_=range_)
    return redirect(url_for('properties.properties_get', property_uri=uri))


@properties_bp.delete('/property')
def property_delete():
    data = request.get_json()
    property_uri = data.get('uri')
    if not property_uri:
        return {'error': 'URI is required'}, 400
    gm.delete_object(property_uri)
    return {'success': True}, 200


@properties_bp.route('/property/<property_uri>')
def property(property_uri):
    return render_template("property.html", property_uri=property_uri)
