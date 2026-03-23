import logging

from flask import Flask, render_template
from databricks.sdk import WorkspaceClient

from config import get_database_url
from graph_manager import GraphManager
from routes import (
    catalog_bp,
    concept_schemes_bp,
    assign_bp,
    import_export_bp,
    sync_bp,
    mcp_bp,
    actions_bp,
)


def create_app(config_overrides=None):
    """Application factory for creating the Flask app.

    Args:
        config_overrides: Optional dict with database_url and/or workspace_client
            for testing. When database_url is set, it overrides get_database_url().
            When workspace_client is set, it is used instead of WorkspaceClient().
    """
    config_overrides = config_overrides or {}
    app = Flask(__name__)
    app.logger.setLevel(logging.INFO)

    db_url = config_overrides.get("database_url") or get_database_url()
    app.gm = GraphManager(db_url)
    app.workspace_client = config_overrides.get(
        "workspace_client", WorkspaceClient()
    )

    # Register blueprints
    app.register_blueprint(catalog_bp)
    app.register_blueprint(concept_schemes_bp)
    app.register_blueprint(assign_bp)
    app.register_blueprint(import_export_bp)
    app.register_blueprint(sync_bp)
    app.register_blueprint(mcp_bp)
    app.register_blueprint(actions_bp)

    # Index route
    @app.route("/")
    def index():
        return render_template("index.html")

    @app.route("/visualisation")
    def visualisation():
        """Return graph data for visualisation."""
        gm = app.gm

        concepts = gm.get_concepts()
        concept_relationships = {
            c["uri"]: gm.get_concept_relationships(c["uri"]) for c in concepts
        }
        properties = gm.get_properties()
        tables = gm.get_tables()
        columns = gm.get_columns()
        functions = gm.get_functions()
        actions = gm.get_actions()
        table_assignments = gm.concept_table_assignments()
        column_assignments = [
            a
            for col in columns
            for a in gm.column_property_assignments(column_uri=col["uri"])
        ]
        function_assignments = gm.function_action_assignments()

        return {
            "concepts": concepts,
            "concept_relationships": concept_relationships,
            "properties": properties,
            "tables": tables,
            "columns": columns,
            "functions": functions,
            "actions": actions,
            "table_assignments": table_assignments,
            "column_assignments": column_assignments,
            "function_assignments": function_assignments,
        }

    return app


# Create the app instance for gunicorn/flask run
app = create_app()


if __name__ == "__main__":
    app.run(debug=True, port=5501)
