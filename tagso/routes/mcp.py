from flask import Blueprint, request, current_app
from werkzeug.local import LocalProxy


mcp_bp = Blueprint("mcp", __name__)

gm = LocalProxy(lambda: current_app.gm)

SEARCH_TOOL = "semantic_search"
ASSIGNED_DATA_OBJECTS_TOOL = "assigned_data_objects"


@mcp_bp.route("/mcp", methods=["OPTIONS"])
def mcp_options():
    return "", 204


@mcp_bp.post("/mcp")
def mcp_handler():
    data = request.get_json()
    print(data)
    method = data.get("method")
    if method == "initialize":
        return initialize(data)
    elif method == "notifications/initialized":
        return notifications_initialized(data)
    elif method == "ping":
        return ping(data)
    elif method == "tools/list":
        return tools_list(data)
    elif method == "tools/call":
        return tools_call(data)
    else:
        return {"error": "Method not found"}, 404


def initialize(data):
    params = data.get("params", {})
    return {
        "jsonrpc": "2.0",
        "id": data.get("id"),
        "result": {
            "protocolVersion": params.get("protocolVersion"),
            "capabilities": {"tools": {}},
            "serverInfo": {
                "name": "Tagsonomy",
                "version": "1.0.0",
                "description": "A tool for working with ontologies and semantic assignments in Unity Catalog.",
            },
            "instructions": "Search for concepts and properties along with semantically assigned tables and columns in Unity Catalog.",
        },
    }, 200


def notifications_initialized(data):
    return "", 202


def ping(data):
    return {"jsonrpc": "2.0", "id": data.get("id"), "result": {}}, 200


def tools_list(data):
    return {
        "jsonrpc": "2.0",
        "id": data.get("id"),
        "result": {
            "tools": [
                {
                    "name": SEARCH_TOOL,
                    "description": "Search for concepts and properties and their synonyms.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "The text to search for.",
                            },
                            "kind": {
                                "type": "string",
                                "enum": ["concept", "property", "all"],
                                "description": "What kind of objects to include in the search.",
                            },
                        },
                        "required": ["query", "kind"],
                    },
                },
                {
                    "name": ASSIGNED_DATA_OBJECTS_TOOL,
                    "description": "Get the data objects assigned to a concept or property.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "uri": {
                                "type": "string",
                                "description": "The URI of the concept or property to get the assigned data objects for.",
                            },
                        },
                        "required": ["uri"],
                    },
                },
            ],
        },
    }, 200


def tools_call(data):
    params = data.get("params", {})
    tool_name = params.get("name")
    if tool_name == SEARCH_TOOL:
        return call_search(data)
    elif tool_name == ASSIGNED_DATA_OBJECTS_TOOL:
        return call_assigned_data_objects(data)
    return {"error": "Tool not found"}, 404


def call_search(data):
    params = data.get("params", {})
    arguments = params.get("arguments", {})
    query = arguments.get("query")
    kind = arguments.get("kind")

    results = gm.search(query, kind)
    return {
        "jsonrpc": "2.0",
        "id": data.get("id"),
        "result": {
            "structuredContent": results,
            "content": [{"type": "text", "text": str(results)}],
            "isError": False,
        },
    }, 200


def call_assigned_data_objects(data):
    params = data.get("params", {})
    arguments = params.get("arguments", {})
    uri = arguments.get("uri")
    # results = gm.get_assigned_data_objects(uri)
    results = ["table1", "table2"]
    return {
        "jsonrpc": "2.0",
        "id": data.get("id"),
        "result": {
            "content": [{"type": "text", "text": str(results)}],
            "isError": False,
        },
    }, 200
