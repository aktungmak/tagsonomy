from flask import Blueprint, render_template, request, current_app
from werkzeug.local import LocalProxy

properties_bp = Blueprint('properties', __name__)

gm = LocalProxy(lambda: current_app.gm)


@properties_bp.get('/properties')
def properties_get():
    return render_template("properties.html")


@properties_bp.post('/properties')
def properties_post():
    raise NotImplementedError("POST method not implemented")


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
