from flask import Blueprint, current_app
from werkzeug.local import LocalProxy

from config import generate_action_uri
from validation import require_params

actions_bp = Blueprint("actions", __name__)

gm = LocalProxy(lambda: current_app.gm)


@actions_bp.get("/actions")
def actions_list():
    """JSON API: list all actions (for dropdowns)."""
    return {"actions": gm.get_actions()}


@actions_bp.post("/actions")
@require_params("label", source="json")
def actions_post(params):
    """Create a new Action."""
    label = params["label"].strip()
    uri = (params.get("uri") or "").strip() or generate_action_uri(label)
    comment = (params.get("comment") or "").strip() or None
    alt_labels = params.get("alt_labels") or []
    notes = params.get("notes") or []
    action_inputs = params.get("action_inputs") or []
    action_outputs = params.get("action_outputs") or []
    target_concepts = params.get("target_concepts") or []
    scheme_uri = (params.get("scheme_uri") or "").strip() or None

    gm.insert_action(
        uri=uri,
        label=label,
        comment=comment,
        alt_labels=alt_labels,
        notes=notes,
        action_inputs=action_inputs,
        action_outputs=action_outputs,
        target_concepts=target_concepts,
        scheme_uri=scheme_uri,
    )
    return {"uri": uri, "label": label}, 201


@actions_bp.post("/actions/update")
@require_params("uri", "label", source="json")
def actions_update(params):
    """Update action metadata."""
    uri = params["uri"]
    label = params["label"].strip()
    comment = (params.get("comment") or "").strip() or None
    alt_labels = params.get("alt_labels") or []
    notes = params.get("notes") or []
    action_inputs = params.get("action_inputs") or []
    action_outputs = params.get("action_outputs") or []
    target_concepts = params.get("target_concepts") or []

    gm.update_action(
        uri=uri,
        label=label,
        comment=comment,
        alt_labels=alt_labels,
        notes=notes,
        action_inputs=action_inputs,
        action_outputs=action_outputs,
        target_concepts=target_concepts,
    )
    return {"success": True}, 200


@actions_bp.delete("/actions")
@require_params("uri", source="json")
def actions_delete(params):
    """Delete an action."""
    gm.delete_object(params["uri"])
    return {"success": True}, 200
