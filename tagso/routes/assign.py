from flask import Blueprint, request, render_template, url_for, current_app
from werkzeug.local import LocalProxy

from validation import require_params

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
@require_params('concept_uri', 'table_uri', source='json')
def assign_post(params):
    gm.insert_concept_assignment(params['table_uri'], params['concept_uri'])
    return {"redirect": url_for("assign.assign_get")}, 201


@assign_bp.post('/assign_column')
@require_params('property_uri', 'column_uri', source='json')
def assign_column_post(params):
    gm.insert_column_property_assignment(params['column_uri'], params['property_uri'])
    return {"redirect": url_for("assign.assign_get")}, 201
