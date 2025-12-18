from flask import Blueprint, request, render_template, url_for, current_app
from werkzeug.local import LocalProxy
from werkzeug.utils import redirect

assign_bp = Blueprint('assign', __name__)

gm = LocalProxy(lambda: current_app.gm)


@assign_bp.get('/assign')
def assign_get():
    selected_concept_uri = request.args.get('selected_concept_uri', '')
    selected_table_uri = request.args.get('selected_table_uri', '')
    selected_property_uri = request.args.get('selected_property_uri', '')
    selected_column_uri = request.args.get('selected_column_uri', '')
    return render_template("assign.html",
                           concepts=gm.get_concepts(),
                           tables=gm.get_tables(),
                           properties=gm.get_properties(),
                           columns=gm.get_columns(),
                           selected_concept_uri=selected_concept_uri,
                           selected_table_uri=selected_table_uri,
                           selected_property_uri=selected_property_uri,
                           selected_column_uri=selected_column_uri)


@assign_bp.post('/assign')
def assign_post():
    concept_uri = request.form.get('concept_uri')
    table_uri = request.form.get('table_uri')
    gm.insert_concept_assignment(table_uri, concept_uri)
    return redirect(url_for('assign.assign_get'))


@assign_bp.post('/assign_column')
def assign_column_post():
    property_uri = request.form.get('property_uri')
    column_uri = request.form.get('column_uri')
    gm.insert_column_property_assignment(column_uri, property_uri)
    return redirect(url_for('assign.assign_get'))
