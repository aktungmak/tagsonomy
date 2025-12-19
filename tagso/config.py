import os
import urllib.parse

from rdflib import Namespace
from databricks.sdk import WorkspaceClient


# Namespaces
UC = Namespace("http://databricks.com/ontology/uc/")
USER_NS = Namespace("http://example.com/ontology/")


def get_database_url():
    """Get database URL from environment, using Lakebase PG* variables.
    
    For Databricks Apps with Lakebase, standard PG* environment variables are injected.
    """
    workspace_client = WorkspaceClient()
    pg_host = os.environ.get('PGHOST')
    pg_database = os.environ.get('PGDATABASE')
    pg_user = os.environ.get('DATABRICKS_CLIENT_ID')
    pg_port = os.environ.get('PGPORT', '5432')
    # TODO: handle password expiry and renewal properly
    pg_pass = workspace_client.config.oauth_token().access_token

    if pg_host and pg_database and pg_user:
        return f'postgresql://{pg_user}:{pg_pass}@{pg_host}:{pg_port}/{pg_database}'

    # Default to SQLite for local development
    return 'sqlite:///tagso.db'


def generate_uri_from_name(name: str) -> str:
    """Generate an IRI from a catalog object name."""
    return str(USER_NS[urllib.parse.quote(name)])
