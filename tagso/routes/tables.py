from flask import Blueprint, request, render_template, url_for, current_app
from werkzeug.local import LocalProxy
from werkzeug.utils import redirect

from config import USER_NS, generate_uri_from_name

tables_bp = Blueprint("tables", __name__)

gm = LocalProxy(lambda: current_app.gm)
workspace_client = LocalProxy(lambda: current_app.workspace_client)


@tables_bp.get("/tables")
def tables_get():
    table_uri = request.args.get("table_uri", "")
    catalogs = [c.name for c in workspace_client.catalogs.list()]
    tables = gm.get_tables()
    return render_template(
        "tables.html",
        tables=tables,
        table_uri=table_uri,
        catalogs=catalogs,
        user_ns=str(USER_NS),
    )


@tables_bp.post("/tables")
def tables_post():
    uri = request.form.get("uri", "")
    catalog = request.form["catalog"]
    schema = request.form["schema"]
    table = request.form["table"]
    name = f"{catalog}.{schema}.{table}"
    if not uri:
        uri = generate_uri_from_name(name)
    gm.insert_table(uri, name)
    return redirect(url_for("tables.tables_get", table_uri=uri))


@tables_bp.delete("/table")
def table_delete():
    data = request.get_json()
    table_uri = data.get("uri")
    if not table_uri:
        return {"error": "URI is required"}, 400
    gm.delete_object(table_uri)
    return {"success": True}, 200


@tables_bp.get("/table/edit")
def table_edit_get():
    table_uri = request.args.get("uri")
    if not table_uri:
        return redirect(url_for("tables.tables_get"))

    tables = gm.get_tables(uri=table_uri)
    if not tables:
        return {"error": "Table not found"}, 404

    table = tables[0]
    assigned_concepts = gm.concept_table_assignments(table_uri=table_uri)

    return render_template(
        "edit_table.html",
        table=table,
        assigned_concepts=assigned_concepts,
    )


# Unity Catalog API endpoints for cascading dropdowns
@tables_bp.get("/api/catalogs")
def api_catalogs():
    catalogs = workspace_client.catalogs.list()
    return [c.name for c in catalogs]


@tables_bp.get("/api/schemas/<catalog>")
def api_schemas(catalog):
    schemas = workspace_client.schemas.list(catalog_name=catalog)
    return [s.name for s in schemas]


@tables_bp.get("/api/tables/<catalog>/<schema>")
def api_tables(catalog, schema):
    tables = workspace_client.tables.list(catalog_name=catalog, schema_name=schema)
    return [t.name for t in tables]
