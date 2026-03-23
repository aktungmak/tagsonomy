"""End-to-end lifecycle tests for action-to-function assignment.

Flow: create scheme, create action, register function, assign, verify,
unassign, cleanup.
"""

import pytest


def test_action_assignment_create_and_delete(client):
    """Assign action to function, verify it exists, unassign, verify it is gone."""
    # 1. Create scheme
    scheme_resp = client.post(
        "/concept_schemes",
        json={"label": "ActionAssignScheme"},
        headers={"Content-Type": "application/json"},
    )
    assert scheme_resp.status_code == 201
    scheme_uri = scheme_resp.get_json()["uri"]

    # 2. Create action (via POST /actions)
    action_resp = client.post(
        "/actions",
        json={
            "label": "Test Action",
            "scheme_uri": scheme_uri,
        },
        headers={"Content-Type": "application/json"},
    )
    assert action_resp.status_code == 201
    action_uri = action_resp.get_json()["uri"]

    # 3. Register function
    function_name = "main.default.test_function"
    register_resp = client.post(
        "/catalog/register",
        json={"type": "function", "name": function_name},
        headers={"Content-Type": "application/json"},
    )
    assert register_resp.status_code == 201
    function_uri = register_resp.get_json()["uri"]

    # 4. Assign action to function (same as UI)
    assign_resp = client.post(
        "/catalog/assign_action",
        json={"function_uri": function_uri, "action_uri": action_uri},
        headers={"Content-Type": "application/json"},
    )
    assert assign_resp.status_code == 201

    # 5. Verify assignment exists (direct endpoint)
    list_resp = client.get("/catalog/action_assignments")
    assert list_resp.status_code == 200
    assignments = list_resp.get_json()["assignments"]
    matching = [
        a
        for a in assignments
        if a["function_uri"] == function_uri and a["action_uri"] == action_uri
    ]
    assert len(matching) == 1

    # 6. Unassign (same as UI)
    unassign_resp = client.delete(
        "/catalog/assign_action",
        json={"function_uri": function_uri, "action_uri": action_uri},
        headers={"Content-Type": "application/json"},
    )
    assert unassign_resp.status_code == 200

    # 7. Verify assignment is gone
    list_resp_after = client.get("/catalog/action_assignments")
    assert list_resp_after.status_code == 200
    assignments_after = list_resp_after.get_json()["assignments"]
    matching_after = [
        a
        for a in assignments_after
        if a["function_uri"] == function_uri and a["action_uri"] == action_uri
    ]
    assert len(matching_after) == 0

    # 8. Cleanup: deregister function, delete action, delete scheme
    client.delete(
        "/catalog/resource",
        json={"uri": function_uri},
        headers={"Content-Type": "application/json"},
    )
    client.delete(
        "/actions",
        json={"uri": action_uri},
        headers={"Content-Type": "application/json"},
    )
    client.delete(
        "/concept_schemes",
        json={"uri": scheme_uri},
        headers={"Content-Type": "application/json"},
    )
