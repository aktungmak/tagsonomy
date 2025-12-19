import logging

from flask import Flask, render_template
from databricks.sdk import WorkspaceClient

from config import get_database_url
from graph_manager import GraphManager
from routes import (
    tables_bp,
    columns_bp,
    concepts_bp,
    properties_bp,
    assign_bp,
    imports_bp,
    search_bp,
)


def create_app():
    """Application factory for creating the Flask app."""
    app = Flask(__name__)
    app.logger.setLevel(logging.INFO)

    # Initialize shared resources
    app.gm = GraphManager(get_database_url())
    app.workspace_client = WorkspaceClient()

    # Register blueprints
    app.register_blueprint(tables_bp)
    app.register_blueprint(columns_bp)
    app.register_blueprint(concepts_bp)
    app.register_blueprint(properties_bp)
    app.register_blueprint(assign_bp)
    app.register_blueprint(imports_bp)
    app.register_blueprint(search_bp)

    # Index route
    @app.route('/')
    def index():
        return render_template("index.html")

    @app.route('/visualisation')
    def visualisation():
        """Return graph data for visualisation."""
        gm = app.gm
        
        concepts = gm.get_concepts()
        concept_relationships = {c['uri']: gm.get_concept_relationships(c['uri']) for c in concepts}
        properties = gm.get_properties()
        tables = gm.get_tables()
        columns = gm.get_columns()
        table_assignments = gm.get_assignments()
        column_assignments = [a for col in columns for a in gm.get_assignments(column_uri=col['uri'])]

        return {
            'concepts': concepts,
            'concept_relationships': concept_relationships,
            'properties': properties,
            'tables': tables,
            'columns': columns,
            'table_assignments': table_assignments,
            'column_assignments': column_assignments
        }

    return app


# Create the app instance for gunicorn/flask run
app = create_app()


if __name__ == '__main__':
    app.run(debug=True, port=5501)
