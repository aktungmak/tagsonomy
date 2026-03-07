from flask import Blueprint, request, render_template, current_app, Response
from werkzeug.local import LocalProxy
from rdflib import Graph, RDF, RDFS, SKOS, URIRef

import_export_bp = Blueprint("import_export", __name__)

gm = LocalProxy(lambda: current_app.gm)


def _get_orphans_in_graph(graph) -> list[str]:
    """Return URIs of Classes, Concepts, Properties that lack skos:inScheme."""
    r = graph.query(
        """
        SELECT DISTINCT ?uri
        WHERE {
            {
                ?uri a rdfs:Class .
                FILTER NOT EXISTS { ?uri skos:inScheme ?s }
            }
            UNION
            {
                ?uri a skos:Concept .
                FILTER NOT EXISTS { ?uri skos:inScheme ?s }
            }
            UNION
            {
                ?uri a rdf:Property .
                FILTER NOT EXISTS { ?uri skos:inScheme ?s }
            }
        }
        """
    )
    return [row.uri.toPython() for row in r.bindings if row.get("uri")]


@import_export_bp.get("/import_export")
def import_export_get():
    concept_schemes = gm.get_concept_schemes()
    return render_template(
        "import_export.html",
        concept_schemes=concept_schemes,
    )


@import_export_bp.post("/import_export")
def import_post():
    if "file" not in request.files:
        return render_template(
            "import_export.html",
            concept_schemes=gm.get_concept_schemes(),
            message="No file selected",
        )

    file = request.files["file"]
    default_scheme = request.form.get("default_scheme", "").strip() or None

    try:
        temp_graph = Graph()
        temp_graph.parse(file)
        orphans = _get_orphans_in_graph(temp_graph)

        if orphans:
            if not default_scheme:
                return render_template(
                    "import_export.html",
                    concept_schemes=gm.get_concept_schemes(),
                    message=f"Import contains {len(orphans)} items without skos:inScheme. "
                    "Please select a Default Concept Scheme or add skos:inScheme to the file.",
                ), 400

            scheme_ref = URIRef(default_scheme)
            for uri in orphans:
                temp_graph.add((URIRef(uri), SKOS.inScheme, scheme_ref))

        before_count = len(gm._graph)
        gm._graph += temp_graph
        triples_added = len(gm._graph) - before_count

        current_app.logger.info(
            f"Imported {triples_added} triples from {file.filename}"
        )
        return render_template(
            "import_export.html",
            concept_schemes=gm.get_concept_schemes(),
            message=f"Successfully imported {triples_added} triples from {file.filename}",
        )

    except Exception as e:
        current_app.logger.error(f"Error importing file: {e}")
        return render_template(
            "import_export.html",
            concept_schemes=gm.get_concept_schemes(),
            message=f"Error importing file: {str(e)}",
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
