"""Stateless, tenant-authenticated MCP and A2A facades over deterministic tools."""

import json

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field

from substrata.platform.cascade import assess


class AssessmentArguments(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_id: str = Field(min_length=1, max_length=96)
    severity: float = Field(ge=0, le=1, allow_inf_nan=False)
    as_of: AwareDatetime
    max_depth: int = Field(default=8, ge=1, le=32)
    graph_version: int | None = Field(default=None, ge=1)


def run_tool(store, actor, arguments):
    actor.require("analyst")
    request = AssessmentArguments.model_validate(arguments)
    snapshot = store.snapshot(actor.tenant_id, version=request.graph_version)
    return assess(
        snapshot,
        request.source_id,
        request.severity,
        as_of=request.as_of,
        max_depth=request.max_depth,
    )


def mcp_response(request_id, result=None, error=None):
    response = {"jsonrpc": "2.0", "id": request_id}
    if error is not None:
        response["error"] = error
    else:
        response["result"] = result
    return response


def handle_mcp(store, actor, body):
    if not isinstance(body, dict) or body.get("jsonrpc") != "2.0":
        return mcp_response(None, error={"code": -32600, "message": "Invalid JSON-RPC request."})
    request_id = body.get("id")
    method = body.get("method")
    params = body.get("params") or {}
    if not isinstance(params, dict) or not isinstance(method, str):
        return mcp_response(request_id, error={"code": -32600, "message": "Invalid request."})
    if method == "initialize":
        return mcp_response(
            request_id,
            {
                "protocolVersion": "2025-03-26",
                "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": {"name": "substrata", "version": "0.1.0"},
            },
        )
    if method == "ping":
        return mcp_response(request_id, {})
    if method == "tools/list":
        actor.require("viewer")
        return mcp_response(
            request_id,
            {
                "tools": [
                    {
                        "name": "cascade.assess",
                        "description": (
                            "Calculate supplier exposure using the deterministic graph engine."
                        ),
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "source_id": {"type": "string", "minLength": 1, "maxLength": 96},
                                "severity": {"type": "number", "minimum": 0, "maximum": 1},
                                "as_of": {"type": "string", "format": "date-time"},
                                "max_depth": {"type": "integer", "minimum": 1, "maximum": 32},
                                "graph_version": {"type": ["integer", "null"], "minimum": 1},
                            },
                            "required": ["source_id", "severity", "as_of"],
                            "additionalProperties": False,
                        },
                    }
                ]
            },
        )
    if method == "tools/call":
        name = params.get("name")
        if name != "cascade.assess":
            return mcp_response(request_id, error={"code": -32602, "message": "Unknown tool."})
        try:
            result = run_tool(store, actor, params.get("arguments", {}))
        except (ValueError, TypeError) as error:
            return mcp_response(request_id, error={"code": -32602, "message": str(error)})
        return mcp_response(
            request_id,
            {
                "content": [{"type": "text", "text": json.dumps(result, separators=(",", ":"))}],
                "structuredContent": result,
                "isError": False,
            },
        )
    if method.startswith("notifications/"):
        return None
    return mcp_response(request_id, error={"code": -32601, "message": "Method not found."})


def a2a_card(base_url: str):
    return {
        "name": "Substrata Supply Chain Risk Agent",
        "description": "Tenant-scoped supply-chain assessment using deterministic calculations.",
        "url": f"{base_url.rstrip('/')}/platform/a2a",
        "version": "0.1.0",
        "protocolVersion": "0.3.0",
        "capabilities": {"streaming": False, "pushNotifications": False},
        "defaultInputModes": ["application/json"],
        "defaultOutputModes": ["application/json"],
        "skills": [
            {
                "id": "cascade-assessment",
                "name": "Deterministic cascade assessment",
                "description": "Assess supplier exposure across a versioned tenant graph.",
                "tags": ["supply-chain", "risk", "assessment"],
                "examples": ["Assess exposure from supplier upstream."],
                "inputModes": ["application/json"],
                "outputModes": ["application/json"],
            }
        ],
    }


def handle_a2a(store, actor, body):
    if not isinstance(body, dict) or body.get("jsonrpc") != "2.0":
        return mcp_response(None, error={"code": -32600, "message": "Invalid JSON-RPC request."})
    request_id = body.get("id")
    if body.get("method") != "tasks/send":
        return mcp_response(request_id, error={"code": -32601, "message": "Method not found."})
    params = body.get("params")
    if not isinstance(params, dict) or not isinstance(params.get("id"), str):
        return mcp_response(request_id, error={"code": -32602, "message": "Task id is required."})
    message = params.get("message")
    try:
        if not isinstance(message, dict) or message.get("role") != "user":
            raise ValueError("A user message is required.")
        parts = message.get("parts")
        if not isinstance(parts, list) or len(parts) != 1 or not isinstance(parts[0], dict):
            raise ValueError("Provide one JSON assessment part.")
        part = parts[0]
        if part.get("type") != "data" or not isinstance(part.get("data"), dict):
            raise ValueError("Assessment input must be a typed JSON data part.")
        result = run_tool(store, actor, part["data"])
    except (ValueError, TypeError) as error:
        return mcp_response(request_id, error={"code": -32602, "message": str(error)})
    return mcp_response(
        request_id,
        {
            "id": params["id"],
            "status": {"state": "completed"},
            "artifacts": [
                {
                    "name": "cascade-assessment",
                    "parts": [{"type": "data", "data": result}],
                }
            ],
        },
    )
