import logging
import urllib.parse
import os
from typing import Optional

from rdflib import Graph, RDF, RDFS, Namespace, URIRef, Literal
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

# Register SQLAlchemy store plugin
# TODO do we need to do this?
# registerplugins()


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
        except psycopg2.errors.DuplicateTable:
            self._graph.open(db_url)
        
        self._graph.bind("uc", UC)
        self._graph.bind("user", USER_NS)
        self._graph.bind("rdf", RDF)
        self._graph.bind("rdfs", RDFS)

    def get_tables(self, uri: Optional[URIRef] = None):
        r = self._graph.query("""
            SELECT ?uri ?name
            WHERE {
                ?uri rdf:type uc:Table .
                OPTIONAL { ?uri uc:name ?name }
            }
        """, initBindings={'uri': uri} if uri else None)
        return r.bindings

    def insert_table(self, uri: str, name: str):
        uri = URIRef(uri)
        if uri not in self._graph.subjects(RDF.type, UC.Table):
            self._graph.add((uri, RDF.type, UC.Table))
            self._graph.add((uri, UC.name, Literal(name)))
        app.logger.info(f"Inserting table {name} iri: {uri}")


    def get_classes(self, uri: Optional[URIRef] = None):
        r = self._graph.query("""
            SELECT DISTINCT ?uri ?name
            WHERE {
                { ?uri a rdfs:Class . }
                UNION
                { ?uri rdfs:subClassOf ?other . }
                OPTIONAL { ?uri rdfs:label ?name }
            }
        """, initBindings={'uri': uri} if uri else None)
        return r.bindings

    def insert_class(self, uri: str, name: str, superclass: Optional[URIRef] = None):
        uri = URIRef(uri)
        if uri not in self._graph.subjects(RDF.type, RDFS.Class):
            self._graph.add((uri, RDF.type, RDFS.Class))
            self._graph.add((uri, RDFS.label, Literal(name)))
            if superclass:
                self._graph.add((uri, RDFS.subClassOf, superclass))
        app.logger.info(f"Inserting class {name} iri: {uri}")



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
    return render_template("tables.html", tables=gm.get_tables(), table_uri=table_uri)


@app.post('/tables')
def tables_post():
    uri = request.form['uri']
    name = request.form['name']
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


# Class routes ####################
@app.get('/classes')
def classes_get():
    class_uri = request.args.get('class_uri', '')
    return render_template("classes.html", classes=gm.get_classes(), class_uri=class_uri)


@app.post('/classes')
def classes_post():
    uri = request.form['uri']
    name = request.form['name']
    if not uri:
        uri = _generate_uri_from_name(name)
    gm.insert_class(uri, name)
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
@app.route('/assignments', methods=['POST', 'DELETE'])
def assignments():
    if request.method == 'POST':
        raise NotImplementedError("POST method not implemented")
    elif request.method == 'DELETE':
        raise NotImplementedError("DELETE method not implemented")


# Sync to UC ######################
@app.route('/sync', methods=['GET', 'POST'])
def sync():
    if request.method == 'GET':
        return render_template("sync.html")
    elif request.method == 'POST':
        raise NotImplementedError("POST method not implemented")


if __name__ == '__main__':
    app.run(debug=True, port=5501)
