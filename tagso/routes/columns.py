from flask import Blueprint, request, render_template, url_for, current_app
from werkzeug.local import LocalProxy
from werkzeug.utils import redirect

from config import USER_NS, generate_uri_from_name

columns_bp = Blueprint("columns", __name__)

gm = LocalProxy(lambda: current_app.gm)
workspace_client = LocalProxy(lambda: current_app.workspace_client)


@columns_bp.get("/columns")
def columns_get():
    column_uri = request.args.get("column_uri", "")
    catalogs = [c.name for c in workspace_client.catalogs.list()]
    columns = gm.get_columns()
    return render_template(
        "columns.html",
        columns=columns,
        column_uri=column_uri,
        catalogs=catalogs,
        user_ns=str(USER_NS),
    )


@columns_bp.post("/columns")
def columns_post():
    uri = request.form.get("uri", "")
    catalog = request.form["catalog"]
    schema = request.form["schema"]
    table = request.form["table"]
    column = request.form["column"]
    name = f"{catalog}.{schema}.{table}.{column}"
    if not uri:
        uri = generate_uri_from_name(name)
    gm.insert_column(uri, name)
    return redirect(url_for("columns.columns_get", column_uri=uri))


@columns_bp.delete("/column")
def column_delete():
    data = request.get_json()
    column_uri = data.get("uri")
    if not column_uri:
        return {"error": "URI is required"}, 400
    gm.delete_object(column_uri)
    return {"success": True}, 200


@columns_bp.get("/column/edit")
def column_edit_get():
    column_uri = request.args.get("uri")
    if not column_uri:
        return redirect(url_for("columns.columns_get"))

    columns = gm.get_columns(uri=column_uri)
    if not columns:
        return {"error": "Column not found"}, 404

    column = columns[0]
    assigned_properties = gm.column_property_assignments(column_uri=column_uri)

    return render_template(
        "edit_column.html",
        column=column,
        assigned_properties=assigned_properties,
    )


# TODO put this in a file with the other api passthrough endpoints
@columns_bp.get("/api/columns/<catalog>/<schema>/<table>")
def api_columns(catalog, schema, table):
    table = workspace_client.tables.get(full_name=f"{catalog}.{schema}.{table}")
    return [c.name for c in table.columns]
