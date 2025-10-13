import rdflib
from databricks.sdk import WorkspaceClient
from databricks.sdk.service.catalog import EntityTagAssignment

import queries

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

DEFAULT_PREFIX = "tgsn"

def apply_tags(wc: WorkspaceClient, prefix: str, securable_type: str, securable_name: str, *tags: str):
    # TODO check the tag string is not too long
    new_tags = set(prefix + tag for tag in tags)
    current_tags = list(wc.entity_tag_assignments.list(securable_type, securable_name))
    old_tags = set(t.tag_key for t in current_tags if t.tag_key.startswith(prefix))

    to_add = new_tags - old_tags
    to_del = old_tags - new_tags

    if len(current_tags) + len(to_add) - len(to_del) >= MAX_TAGS:
        raise Exception(f"too many tags on {securable_type} {securable_name}!")

    print(f"removing tags {to_del} from {securable_type} {securable_name}")
    for tag in to_del:
        wc.entity_tag_assignments.delete(securable_type, securable_name, tag)

    print(f"adding tags {to_add} to {securable_type} {securable_name}")
    for tag in to_add:
        wc.entity_tag_assignments.create(EntityTagAssignment(securable_name, tag, securable_type))

def clear_tags(wc: WorkspaceClient, prefix: str, securable_type: str, securable_name: str):
    current_tags = wc.entity_tag_assignments.list(securable_type, securable_name)
    to_del = set(t.tag_key for t in current_tags if t.tag_key.startswith(prefix))

    print(f"removing tags {to_del} from {securable_type} {securable_name}")
    for tag in to_del:
        wc.entity_tag_assignments.delete(securable_type, securable_name, tag)

def main(command: str, g: rdflib.Graph, prefix: str = DEFAULT_PREFIX):
    g.parse(data=UC_CLASSES)
    wc = WorkspaceClient()

    for securable_type, securable_name, tags in queries.securable_to_classes(g):
        if command == 'update':
            apply_tags(wc, prefix, securable_type, securable_name, *tags)
        elif command == 'clear':
            clear_tags(wc, prefix, securable_type, securable_name)
        else:
            raise ValueError(f"unknown command {command}")
