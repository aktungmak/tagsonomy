from flask import Blueprint, request, render_template, current_app, Response
from werkzeug.local import LocalProxy

imports_bp = Blueprint('imports', __name__)

gm = LocalProxy(lambda: current_app.gm)


@imports_bp.get('/import')
def import_get():
    return render_template("import.html")


@imports_bp.post('/import')
def import_post():
    if 'file' not in request.files:
        return render_template("import.html", message="No file selected")

    file = request.files['file']

    try:
        before_count = len(gm._graph)
        gm._graph.parse(file)
        triples_added = len(gm._graph) - before_count

        current_app.logger.info(f"Imported {triples_added} triples from {file.filename}")
        return render_template("import.html",
                               message=f"Successfully imported {triples_added} triples from {file.filename}")

    except Exception as e:
        current_app.logger.error(f"Error importing file: {e}")
        return render_template("import.html", message=f"Error importing file: {str(e)}")


@imports_bp.get('/export')
def export_get():
    """Export the graph as a Turtle file download."""
    turtle_data = gm._graph.serialize(format='turtle')
    
    return Response(
        turtle_data,
        mimetype='text/turtle',
        headers={'Content-Disposition': 'attachment; filename=tagsonomy_export.ttl'}
    )


@imports_bp.route('/sync', methods=['GET', 'POST'])
def sync():
    if request.method == 'GET':
        return render_template("sync.html")
    elif request.method == 'POST':
        raise NotImplementedError("POST method not implemented")
