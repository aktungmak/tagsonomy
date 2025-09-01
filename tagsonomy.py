import argparse
import sys

import rdflib
import queries
import tag_api

UC_CLASSES = """
@prefix uc: <http://databricks.com/ontology/uc/>.
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#>.

uc:Securable a rdfs:Class.
uc:Catalog rdfs:subClassOf uc:Securable;
    rdfs:label "CATALOG".
uc:Schema rdfs:subClassOf uc:Securable;
    rdfs:label "SCHEMA".
uc:Table rdfs:subClassOf uc:Securable;
    rdfs:label "TABLE".
uc:Volume rdfs:subClassOf uc:Securable;
    rdfs:label "VOLUME".
uc:Column rdfs:subClassOf uc:Securable;
    rdfs:label "COLUMN".

uc:name a rdfs:Property.

# uc:in_table rdfs:domain uc:Column;
#     rdfs:range uc:Table.
# uc:in_schema rdfs:domain uc:Table;
#     rdfs:domain uc:Volume;
#     rdfs:range uc:Schema.
# uc:in_catalog rdfs:domain uc:Schema;
#     rdfs:range uc:Catalog.
"""


def main(command: str, workspace_url: str, pat: str, *rdf_files: str):
    ct = tag_api.ClassTagger(workspace_url, pat)
    g = rdflib.Graph()
    g.parse(data=UC_CLASSES)
    for file in rdf_files:
        g.parse(location=file)

    for securable_type, securable_name, tags in queries.securable_to_classes(g):
        if command == 'update':
            ct.apply_tags(securable_type, securable_name, *tags)
        elif command == 'clear':
            ct.clear_tags(securable_type, securable_name)
        else:
            raise Exception(f"unknown command {command}")

if __name__ == '__main__':
    g = rdflib.Graph()
    g.parse("small.ttl")
    g.query("SELECT * WHERE {?s ?p ?o}")

    parser = argparse.ArgumentParser(description='Update tags based on taxonomy.')
    parser.add_argument('command', type=str, help='Command to execute')
    parser.add_argument('workspace_url', type=str, help='Workspace URL')
    parser.add_argument('token_file', type=str, help='File containing the token')
    parser.add_argument('rdf_files', nargs='+', help='RDF files to process')

    args = parser.parse_args()

    with open(args.token_file) as f:
        token = f.read()

    main(args.command, args.workspace_url, token, *args.rdf_files)

if __name__ == '__main__':
    command = sys.argv[1]
    workspace_url = sys.argv[2]
    with open(sys.argv[3]) as f: token = f.read()
    files = sys.argv[4:]
    main(command, workspace_url, token, *files)
