import logging
import urllib.parse
import os
from typing import Optional

from rdflib import SKOS, Graph, RDF, RDFS, Namespace, URIRef, Literal
from rdflib.store import Store
from flask import request, Flask, render_template, url_for
from werkzeug.utils import redirect
from databricks.sdk import WorkspaceClient
from psycopg2.errors import DuplicateTable


# Database configuration
# For Databricks Apps with Lakebase, standard PG* environment variables are injected
def get_database_url():
    """Get database URL from environment, using Lakebase PG* variables."""
    workspace_client = WorkspaceClient()
    pg_host = os.environ.get('PGHOST')
    pg_database = os.environ.get('PGDATABASE')
    pg_user = os.environ.get('DATABRICKS_CLIENT_ID')
    pg_port = os.environ.get('PGPORT', '5432')
    # TODO: handle password expiry and renewal
    pg_pass = workspace_client.config.oauth_token().access_token

    if pg_host and pg_database and pg_user:
        return f'postgresql://{pg_user}:{pg_pass}@{pg_host}:{pg_port}/{pg_database}'

    # Default to SQLite for local development
    return 'sqlite:///tagso.db'


DATABASE_URL = get_database_url()

UC = Namespace("http://databricks.com/ontology/uc/")
USER_NS = Namespace("http://example.com/ontology/")


class GraphManager:
    def __init__(self, db_url: str, identifier: str = 'tagsonomy'):
        """
        Initialize GraphManager with SQLAlchemy store
        
        Args:
            db_url: connection string
            identifier: Identifier for the graph store
        """
        self._graph = Graph(store='SQLAlchemy', identifier=identifier)

        try:
            self._graph.open(db_url, create=True)
        except DuplicateTable:
            self._graph.open(db_url)

        self._graph.bind("uc", UC)
        self._graph.bind("user", USER_NS)
        self._graph.bind("rdf", RDF)
        self._graph.bind("rdfs", RDFS)

    def _to_dicts(self, bindings) -> list[dict]:
        """Convert SPARQL bindings to list of dicts with string keys and native Python values."""
        return [{str(k): v.toPython() if v is not None else None for k, v in row.items()} for row in bindings]

    def get_tables(self, uri: Optional[URIRef] = None) -> list[dict]:
        r = self._graph.query("""
            SELECT ?uri ?name
            WHERE {
                ?uri rdf:type uc:Table .
                OPTIONAL { ?uri uc:name ?name }
            }
        """, initBindings={'uri': uri} if uri else None)
        return self._to_dicts(r.bindings)

    def insert_table(self, uri: str, name: str):
        uri = URIRef(uri)
        if uri not in self._graph.subjects(RDF.type, UC.Table):
            self._graph.add((uri, RDF.type, UC.Table))
            self._graph.add((uri, UC.name, Literal(name)))
        app.logger.info(f"Inserting table {name} iri: {uri}")

    def get_classes(self, uri: Optional[URIRef] = None) -> list[dict]:
        r = self._graph.query("""
            SELECT DISTINCT ?uri ?name
            WHERE {
                { ?uri a rdfs:Class . }
                UNION
                { ?uri rdfs:subClassOf ?other . }
                OPTIONAL { ?uri rdfs:label ?name }
            }
        """, initBindings={'uri': uri} if uri else None)
        return self._to_dicts(r.bindings)

    def insert_class(self, uri: str, label: str, class_type: URIRef, comment: Optional[str] = None,
                     superclass: Optional[URIRef] = None):
        uri = URIRef(uri)
        if uri not in self._graph.subjects(RDF.type, class_type):
            self._graph.add((uri, RDF.type, class_type))
            self._graph.add((uri, RDFS.label, Literal(label)))
            if comment:
                self._graph.add((uri, RDFS.comment, Literal(comment)))
            if superclass:
                self._graph.add((uri, RDFS.subClassOf, superclass))
        app.logger.info(f"Inserting class {label} iri: {uri}")

    def insert_assignment(self, table_uri: str, class_uri: str):
        """Insert a semantic assignment from a table to a class."""
        table_uri = URIRef(table_uri)
        class_uri = URIRef(class_uri)
        self._graph.add((table_uri, UC.semanticAssignment, class_uri))
        app.logger.info(f"Assigned table {table_uri} to class {class_uri}")

    def get_assignments(self, table_uri: Optional[str] = None, class_uri: Optional[str] = None) -> list[dict]:
        """Get semantic assignments, filtered by table or class.
        
        Args:
            table_uri: If provided, returns all classes assigned to this table
            class_uri: If provided, returns all tables assigned to this class
        """
        bindings = {}
        if table_uri:
            bindings['table_uri'] = URIRef(table_uri)
        if class_uri:
            bindings['class_uri'] = URIRef(class_uri)
        
        r = self._graph.query("""
            SELECT ?table_uri ?table_name ?class_uri ?class_name
            WHERE {
                ?table_uri uc:semanticAssignment ?class_uri .
                OPTIONAL { ?table_uri uc:name ?table_name }
                OPTIONAL { ?class_uri rdfs:label ?class_name }
            }
        """, initBindings=bindings if bindings else None)
        return self._to_dicts(r.bindings)

    def delete_object(self, uri: str):
        uri = URIRef(uri)
        for pred, obj in self._graph.predicate_objects(subject=uri):
            self._graph.remove((uri, pred, obj))
        app.logger.info(f"Deleted object {uri}")

    def close(self):
        self._graph.close()


app = Flask(__name__)
app.logger.setLevel(logging.INFO)

gm = GraphManager(DATABASE_URL)
workspace_client = WorkspaceClient()


def _generate_uri_from_name(name: str) -> str:
    """Generate an IRI from a catalog object name."""
    app.logger.info(f"generating {name}")
    return str(USER_NS[urllib.parse.quote(name)])


@app.route('/')
def index():
    return render_template("index.html")


# Table routes ####################
@app.get('/tables')
def tables_get():
    table_uri = request.args.get('table_uri', '')
    catalogs = [c.name for c in workspace_client.catalogs.list()]
    # TODO collect assigned_classes in a single query
    tables = gm.get_tables()
    for table in tables:
        table['assigned_classes'] = gm.get_assignments(table_uri=table['uri'])
    return render_template("tables.html", tables=tables, table_uri=table_uri, catalogs=catalogs,
                           user_ns=str(USER_NS))


@app.post('/tables')
def tables_post():
    uri = request.form.get('uri', '')
    catalog = request.form['catalog']
    schema = request.form['schema']
    table_name = request.form['table_name']
    name = f"{catalog}.{schema}.{table_name}"
    if not uri:
        uri = _generate_uri_from_name(name)
    gm.insert_table(uri, name)
    return redirect(url_for('tables_get', table_uri=uri))


@app.delete('/table')
def table_delete():
    data = request.get_json()
    table_uri = data.get('uri')
    if not table_uri:
        return {'error': 'URI is required'}, 400
    gm.delete_object(table_uri)
    return {'success': True}, 200


# Unity Catalog API endpoints for cascading dropdowns
@app.get('/api/catalogs')
def api_catalogs():
    catalogs = workspace_client.catalogs.list()
    return [c.name for c in catalogs]


@app.get('/api/schemas/<catalog>')
def api_schemas(catalog):
    schemas = workspace_client.schemas.list(catalog_name=catalog)
    return [s.name for s in schemas]


@app.get('/api/tables/<catalog>/<schema>')
def api_tables(catalog, schema):
    tables = workspace_client.tables.list(catalog_name=catalog, schema_name=schema)
    return [t.name for t in tables]


# Class routes ####################
@app.get('/classes')
def classes_get():
    class_uri = request.args.get('class_uri', '')
    # TODO collect assigned_tables in a single query
    classes = gm.get_classes()
    for cls in classes:
        cls['assigned_tables'] = gm.get_assignments(class_uri=cls['uri'])
    return render_template("classes.html", classes=classes, class_uri=class_uri, user_ns=str(USER_NS))


@app.post('/classes')
def classes_post():
    label = request.form['label']

    uri = request.form['uri']
    if not uri:
        uri = _generate_uri_from_name(label)

    class_type_str = request.form['type']
    if class_type_str == 'rdfs_class':
        class_type = RDFS.Class
    elif class_type_str == 'skos_concept':
        class_type = SKOS.Concept
    else:
        return {'error': f'Invalid class type: {class_type_str}'}, 400

    comment = request.form['comment']

    gm.insert_class(uri, label, class_type, comment)
    return redirect(url_for('classes_get', class_uri=uri))


@app.delete('/class')
def class_delete():
    data = request.get_json()
    class_uri = data.get('uri')
    if not class_uri:
        return {'error': 'URI is required'}, 400
    gm.delete_object(class_uri)
    return {'success': True}, 200


# Property routes #################
@app.get('/properties')
def properties_get():
    return render_template("properties.html")


@app.post('/properties')
def properties_post():
    raise NotImplementedError("POST method not implemented")


@app.route('/property/<property_uri>')
def property(property_uri):
    return render_template("property.html", property_uri=property_uri)


# Semantic Assignment route #######
@app.get('/assign')
def assign_get():
    selected_class_uri = request.args.get('selected_class_uri', '')
    selected_table_uri = request.args.get('selected_table_uri', '')
    return render_template("assign.html", classes=gm.get_classes(), tables=gm.get_tables(),
                           selected_class_uri=selected_class_uri, selected_table_uri=selected_table_uri)


@app.post('/assign')
def assign_post():
    class_uri = request.form.get('class_uri')
    table_uri = request.form.get('table_uri')
    gm.insert_assignment(table_uri, class_uri)
    return redirect(url_for('assign_get'))


# Sync to UC ######################
@app.route('/sync', methods=['GET', 'POST'])
def sync():
    if request.method == 'GET':
        return render_template("sync.html")
    elif request.method == 'POST':
        raise NotImplementedError("POST method not implemented")


# Import ontology #################
@app.get('/import')
def import_get():
    return render_template("import.html")


@app.post('/import')
def import_post():
    if 'file' not in request.files:
        return render_template("import.html", message="No file selected")
    
    file = request.files['file']
    
    try:
        before_count = len(gm._graph)
        gm._graph.parse(file)
        triples_added = len(gm._graph) - before_count
        
        app.logger.info(f"Imported {triples_added} triples from {file.filename}")
        return render_template("import.html", message=f"Successfully imported {triples_added} triples from {file.filename}")
    
    except Exception as e:
        app.logger.error(f"Error importing file: {e}")
        return render_template("import.html", message=f"Error importing file: {str(e)}")


if __name__ == '__main__':
    app.run(debug=True, port=5501)
