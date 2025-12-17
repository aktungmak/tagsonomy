from flask import Blueprint, request, render_template, url_for, current_app
from werkzeug.utils import redirect

from config import USER_NS, generate_uri_from_name

tables_bp = Blueprint('tables', __name__)


@tables_bp.get('/tables')
def tables_get():
    gm = current_app.gm
    workspace_client = current_app.workspace_client
    
    table_uri = request.args.get('table_uri', '')
    catalogs = [c.name for c in workspace_client.catalogs.list()]
    # TODO collect assigned_classes in a single query
    tables = gm.get_tables()
    for table in tables:
        table['assigned_classes'] = gm.get_assignments(table_uri=table['uri'])
    return render_template("tables.html", tables=tables, table_uri=table_uri, catalogs=catalogs,
                           user_ns=str(USER_NS))


@tables_bp.post('/tables')
def tables_post():
    gm = current_app.gm
    
    uri = request.form.get('uri', '')
    catalog = request.form['catalog']
    schema = request.form['schema']
    table_name = request.form['table_name']
    name = f"{catalog}.{schema}.{table_name}"
    if not uri:
        uri = generate_uri_from_name(name)
    gm.insert_table(uri, name)
    return redirect(url_for('tables.tables_get', table_uri=uri))


@tables_bp.delete('/table')
def table_delete():
    gm = current_app.gm
    
    data = request.get_json()
    table_uri = data.get('uri')
    if not table_uri:
        return {'error': 'URI is required'}, 400
    gm.delete_object(table_uri)
    return {'success': True}, 200


# Unity Catalog API endpoints for cascading dropdowns
@tables_bp.get('/api/catalogs')
def api_catalogs():
    workspace_client = current_app.workspace_client
    catalogs = workspace_client.catalogs.list()
    return [c.name for c in catalogs]


@tables_bp.get('/api/schemas/<catalog>')
def api_schemas(catalog):
    workspace_client = current_app.workspace_client
    schemas = workspace_client.schemas.list(catalog_name=catalog)
    return [s.name for s in schemas]


@tables_bp.get('/api/tables/<catalog>/<schema>')
def api_tables(catalog, schema):
    workspace_client = current_app.workspace_client
    tables = workspace_client.tables.list(catalog_name=catalog, schema_name=schema)
    return [t.name for t in tables]
