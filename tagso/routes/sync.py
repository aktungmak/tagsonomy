from os import environ

from config import get_database_url
from databricks.sdk import WorkspaceClient
from flask import Blueprint, current_app, render_template, request, url_for
from werkzeug.local import LocalProxy

from graph_manager import GraphManager

sync_bp = Blueprint("sync", __name__)

workspace_client: WorkspaceClient = LocalProxy(lambda: current_app.workspace_client)
gm: GraphManager = LocalProxy(lambda: current_app.gm)


def _get_job_url(job_id):
    return f"{workspace_client.config.host}/jobs/{job_id}"


@sync_bp.get("/sync")
def sync_get():
    job_id = environ.get("SYNC_JOB_ID")
    error = None if job_id else "SYNC_JOB_ID environment variable is not set"
    job_url = _get_job_url(job_id) if job_id else None
    return render_template(
        "sync.html", job_id=job_id, job_url=job_url, error=error, run_page_url=None
    )


@sync_bp.post("/sync")
def sync_post():
    prefix = request.args.get("prefix", "TYPE_")
    job_id = environ.get("SYNC_JOB_ID")
    error = None
    run_page_url = None

    try:
        r = workspace_client.jobs.run_now(
            job_id,
            job_parameters={
                "prefix": prefix,
                "mappings_url": request.url_root.rstrip("/")
                + url_for("sync.sync_mappings_get"),
            },
        )
        run_page_url = workspace_client.jobs.get_run(run_id=r.run_id).run_page_url
    except Exception as e:
        error = str(e)

    job_url = _get_job_url(job_id) if job_id else None
    return render_template(
        "sync.html",
        job_id=job_id,
        job_url=job_url,
        error=error,
        run_page_url=run_page_url,
    )


@sync_bp.get("/sync/mappings")
def sync_mappings_get():
    "Retrieve table/column name to concept/property label mappings from graph"
    from collections import defaultdict

    table_tags = defaultdict(list)
    for assignment in gm.concept_table_assignments():
        table_name = assignment.get("table_name")
        concept_label = assignment.get("concept_name")
        if table_name and concept_label:
            table_tags[table_name].append(concept_label)

    column_tags = defaultdict(list)
    for assignment in gm.column_property_assignments():
        column_name = assignment.get("column_name")
        property_label = assignment.get("property_name")
        if column_name and property_label:
            column_tags[column_name].append(property_label)

    result = []
    for name, tags in table_tags.items():
        result.append({"name": name, "type": "table", "tags": tags})
    for name, tags in column_tags.items():
        result.append({"name": name, "type": "column", "tags": tags})

    return result
