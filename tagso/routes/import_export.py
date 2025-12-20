from flask import Blueprint, request, render_template, current_app, Response
from werkzeug.local import LocalProxy

import_export_bp = Blueprint("import_export", __name__)

gm = LocalProxy(lambda: current_app.gm)


@import_export_bp.get("/import_export")
def import_export_get():
    return render_template("import_export.html")


@import_export_bp.post("/import_export")
def import_post():
    if "file" not in request.files:
        return render_template("import_export.html", message="No file selected")

    file = request.files["file"]

    try:
        before_count = len(gm._graph)
        gm._graph.parse(file)
        triples_added = len(gm._graph) - before_count

        current_app.logger.info(
            f"Imported {triples_added} triples from {file.filename}"
        )
        return render_template(
            "import_export.html",
            message=f"Successfully imported {triples_added} triples from {file.filename}",
        )

    except Exception as e:
        current_app.logger.error(f"Error importing file: {e}")
        return render_template(
            "import_export.html", message=f"Error importing file: {str(e)}"
        )


@import_export_bp.get("/export")
def export_get():
    """Export the graph as a Turtle file download."""
    turtle_data = gm._graph.serialize(format="turtle")

    return Response(
        turtle_data,
        mimetype="text/turtle",
        headers={"Content-Disposition": "attachment; filename=tagsonomy_export.ttl"},
    )
