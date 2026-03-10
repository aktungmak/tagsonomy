from flask import Blueprint, request, render_template, current_app
from werkzeug.local import LocalProxy

from config import generate_uri_from_name
from validation import require_params

catalog_bp = Blueprint("catalog", __name__)

gm = LocalProxy(lambda: current_app.gm)
workspace_client = LocalProxy(lambda: current_app.workspace_client)


@catalog_bp.get("/catalog")
def catalog_get():
    return render_template("catalog.html")


@catalog_bp.get("/catalog/catalogs")
def catalog_catalogs():
    """JSON list of catalog names from SDK."""
    return [c.name for c in workspace_client.catalogs.list()]


@catalog_bp.get("/catalog/schemas/<catalog>")
def catalog_schemas(catalog):
    """JSON list of schema names for a catalog."""
    return [s.name for s in workspace_client.schemas.list(catalog_name=catalog)]


@catalog_bp.get("/catalog/tables/<catalog>/<schema>")
def catalog_tables(catalog, schema):
    """JSON list of table names for a schema."""
    return [
        t.name
        for t in workspace_client.tables.list(catalog_name=catalog, schema_name=schema)
    ]


@catalog_bp.get("/catalog/columns/<catalog>/<schema>/<table>")
def catalog_columns(catalog, schema, table):
    """JSON list of column names for a table."""
    full_name = f"{catalog}.{schema}.{table}"
    table_info = workspace_client.tables.get(full_name=full_name)
    return [c.name for c in (table_info.columns or [])]


@catalog_bp.get("/catalog/registered_tables")
def catalog_registered_tables():
    """JSON API: tables registered in the graph (for verification, tests)."""
    return {"tables": gm.get_tables()}


@catalog_bp.get("/catalog/registered_columns")
def catalog_registered_columns():
    """JSON API: columns registered in the graph (for verification, tests)."""
    return {"columns": gm.get_columns()}


@catalog_bp.get("/catalog/concept_assignments")
def catalog_concept_assignments():
    """JSON API: table-to-concept assignments (for verification, tests)."""
    return {"assignments": gm.concept_table_assignments()}


@catalog_bp.get("/catalog/property_assignments")
def catalog_property_assignments():
    """JSON API: column-to-property assignments (for verification, tests)."""
    assignments = [
        a
        for col in gm.get_columns()
        for a in gm.column_property_assignments(column_uri=col["uri"])
    ]
    return {"assignments": assignments}


@catalog_bp.get("/catalog/resource")
@require_params("type", "name", source="args")
def catalog_resource(params):
    """JSON detail for selected catalog object (catalog, schema, table, or column)."""
    obj_type = params["type"]
    name = params["name"]
    if obj_type not in ("catalog", "schema", "table", "column"):
        return {"error": "Invalid type"}, 400
    if obj_type == "column" and len(name.split(".")) < 4:
        return {"error": "Column name must be catalog.schema.table.column"}, 400

    try:
        if obj_type == "catalog":
            catalog_info = workspace_client.catalogs.get(name=name)
            return {
                "type": "catalog",
                "name": catalog_info.name,
                "comment": getattr(catalog_info, "comment", None) or "",
            }

        if obj_type == "schema":
            schema_info = workspace_client.schemas.get(full_name=name)
            return {
                "type": "schema",
                "name": schema_info.full_name or name,
                "comment": getattr(schema_info, "comment", None) or "",
            }

        if obj_type == "table":
            table_info = workspace_client.tables.get(full_name=name)
            result = {
                "type": "table",
                "name": table_info.full_name or name,
                "comment": getattr(table_info, "comment", None) or "",
                "columns": [
                    {
                        "name": c.name,
                        "type_text": getattr(c, "type_text", ""),
                        "comment": getattr(c, "comment", None) or "",
                    }
                    for c in (table_info.columns or [])
                ],
            }
            table_in_graph = gm.get_table_by_name(name)
            if table_in_graph:
                result["uri"] = table_in_graph["uri"]
                result["assigned_concepts"] = gm.concept_table_assignments(
                    table_uri=table_in_graph["uri"]
                )
            else:
                result["assigned_concepts"] = []
            result["all_concepts"] = gm.get_concepts()
            return result

        # obj_type == "column"
        parts = name.split(".")
        catalog_name, schema_name, table_name, column_name = (
            parts[0],
            parts[1],
            parts[2],
            ".".join(parts[3:]),
        )
        table_full_name = f"{catalog_name}.{schema_name}.{table_name}"
        table_info = workspace_client.tables.get(full_name=table_full_name)
        column_info = next(
            (c for c in (table_info.columns or []) if c.name == column_name),
            None,
        )
        if not column_info:
            return {"error": "Column not found"}, 404
        result = {
            "type": "column",
            "name": name,
            "comment": getattr(column_info, "comment", None) or "",
            "type_text": getattr(column_info, "type_text", ""),
        }
        column_in_graph = gm.get_column_by_name(name)
        if column_in_graph:
            result["uri"] = column_in_graph["uri"]
            result["assigned_properties"] = gm.column_property_assignments(
                column_uri=column_in_graph["uri"]
            )
        else:
            result["assigned_properties"] = []
        result["all_properties"] = gm.get_properties_with_alt_labels()
        return result

    except Exception as e:
        return {"error": str(e)}, 404


@catalog_bp.post("/catalog/register")
@require_params("type", "name", source="json")
def catalog_register(params):
    """Register a table or column in the graph."""
    obj_type = params["type"]
    name = params["name"]
    if obj_type not in ("table", "column"):
        return {"error": "type must be table or column"}, 400

    uri = generate_uri_from_name(name)
    if obj_type == "table":
        if len(name.split(".")) < 3:
            return {"error": "Table name must be catalog.schema.table"}, 400
        gm.insert_table(uri, name)
    else:
        if len(name.split(".")) < 4:
            return {"error": "Column name must be catalog.schema.table.column"}, 400
        gm.insert_column(uri, name)

    return {"uri": uri}, 201


@catalog_bp.delete("/catalog/resource")
@require_params("uri", source="json")
def catalog_deregister(params):
    """Deregister a table or column from the graph (removes object and assignments)."""
    gm.delete_object(params["uri"])
    return {"success": True}, 200


@catalog_bp.post("/catalog/assign_concept")
@require_params("table_uri", "concept_uri", source="json")
def catalog_assign_concept(params):
    """Add a concept assignment to a table (for inline editing)."""
    gm.insert_concept_assignment(params["table_uri"], params["concept_uri"])
    return {"success": True}, 201


@catalog_bp.post("/catalog/assign_property")
@require_params("column_uri", "property_uri", source="json")
def catalog_assign_property(params):
    """Add a property assignment to a column (for inline editing)."""
    gm.insert_column_property_assignment(params["column_uri"], params["property_uri"])
    return {"success": True}, 201


@catalog_bp.delete("/catalog/assign_concept")
@require_params("table_uri", "concept_uri", source="json")
def catalog_unassign_concept(params):
    """Remove a concept assignment from a table."""
    gm.delete_concept_assignment(params["table_uri"], params["concept_uri"])
    return {"success": True}, 200


@catalog_bp.delete("/catalog/assign_property")
@require_params("column_uri", "property_uri", source="json")
def catalog_unassign_property(params):
    """Remove a property assignment from a column."""
    gm.delete_column_property_assignment(params["column_uri"], params["property_uri"])
    return {"success": True}, 200
