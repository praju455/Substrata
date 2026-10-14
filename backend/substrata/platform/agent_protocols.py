"""Stateless, tenant-authenticated MCP and A2A facades over deterministic tools."""

import json
from typing import Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field

from substrata.platform.cascade import assess
from substrata.platform.domain import Identifier


class SnapshotArguments(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version: int | None = Field(default=None, ge=1)
    as_of: AwareDatetime | None = None


class EvidenceArguments(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query: str = Field(min_length=1, max_length=2000)


class ApprovalArguments(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: Identifier
    decision: Literal["approved", "rejected"]
    reason: str = Field(min_length=1, max_length=2000)


class AuditArguments(BaseModel):
    model_config = ConfigDict(extra="forbid")

    expected_head: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}$")


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


def _tool_definitions():
    from substrata.platform.events import EventSubmission
    from substrata.platform.governance import ProposalInput

    return {
        "cascade.assess": (
            AssessmentArguments,
            "Calculate supplier exposure using the deterministic graph engine.",
            "analyst",
        ),
        "graph.snapshot": (
            SnapshotArguments,
            "Read the caller tenant's current or historical versioned graph.",
            "viewer",
        ),
        "audit.verify": (
            AuditArguments,
            "Verify the caller tenant's append-only audit chain.",
            "viewer",
        ),
        "event.submit": (
            EventSubmission,
            "Submit a sourced event for tenant-scoped classification and entity review.",
            "analyst",
        ),
        "evidence.discover": (
            EvidenceArguments,
            "Retrieve cited evidence and propose links using the configured mapper.",
            "analyst",
        ),
        "mitigation.propose": (
            ProposalInput,
            "Create a sourced mitigation draft for the tenant approval policy.",
            "analyst",
        ),
        "approval.decide": (
            ApprovalArguments,
            "Record a policy-checked approval or rejection with a reason.",
            "approver",
        ),
    }


def execute_tool(store, actor, name, arguments):
    definitions = _tool_definitions()
    if name not in definitions:
        raise ValueError("Unknown tool.")
    model, _description, role = definitions[name]
    actor.require(role)
    request = model.model_validate(arguments)
    values = request.model_dump()
    if name == "cascade.assess":
        return run_tool(store, actor, values)
    if name == "graph.snapshot":
        return store.snapshot(actor.tenant_id, **values).model_dump(mode="json")
    if name == "audit.verify":
        return store.audit(actor.tenant_id, values["expected_head"])["verification"]
    if name == "event.submit":
        from substrata.platform.events import submit

        return submit(store, actor, request)
    if name == "evidence.discover":
        from substrata.platform.evidence import discover

        return discover(store, actor, values["query"])
    if name == "mitigation.propose":
        from substrata.platform.governance import propose

        return propose(store, actor, request)
    if name == "approval.decide":
        from substrata.platform.governance import decide

        return decide(store, actor, values["id"], values["decision"], values["reason"])
    raise ValueError("Tool handler is not registered.")


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
                        "name": name,
                        "description": description,
                        "inputSchema": model.model_json_schema(),
                    }
                    for name, (model, description, _role) in _tool_definitions().items()
                ]
            },
        )
    if method == "tools/call":
        name = params.get("name")
        try:
            result = execute_tool(store, actor, name, params.get("arguments", {}))
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
        "description": (
            "Tenant-scoped mapping, sensing, assessment, audit and governed response tools."
        ),
        "url": f"{base_url.rstrip('/')}/platform/a2a",
        "version": "0.1.0",
        "protocolVersion": "0.3.0",
        "capabilities": {"streaming": False, "pushNotifications": False},
        "defaultInputModes": ["application/json"],
        "defaultOutputModes": ["application/json"],
        "skills": [
            {
                "id": skill_id,
                "name": name,
                "description": description,
                "tags": tags,
                "examples": examples,
                "inputModes": ["application/json"],
                "outputModes": ["application/json"],
            }
            for skill_id, name, description, tags, examples in A2A_SKILLS
        ],
    }


A2A_SKILLS = [
    (
        "cascade-assessment",
        "Deterministic cascade assessment",
        "Assess supplier exposure across a versioned tenant graph.",
        ["supply-chain", "risk", "assessment"],
        ["Assess exposure from supplier upstream."],
    ),
    (
        "graph-snapshot",
        "Versioned graph snapshot",
        "Read a tenant graph snapshot or historical revision.",
        ["graph", "supply-chain"],
        ["Read graph version 3."],
    ),
    (
        "evidence-discovery",
        "Evidence-backed dependency discovery",
        "Search tenant documents and propose cited supplier links.",
        ["evidence", "supplier-mapping"],
        ["Find cited evidence for this supplier relationship."],
    ),
    (
        "event-submission",
        "Sourced event submission",
        "Submit a source-attributed event for mapping and alert rules.",
        ["events", "risk"],
        ["Submit a sourced supply interruption event."],
    ),
    (
        "mitigation-draft",
        "Governed mitigation draft",
        "Create a policy-checked mitigation proposal for human review.",
        ["mitigation", "governance"],
        ["Prepare a sourced mitigation option for assessment abc."],
    ),
    (
        "approval-decision",
        "Human approval decision",
        "Record a policy-authorized approval or rejection with a reason.",
        ["approval", "governance"],
        ["Reject action abc with a documented reason."],
    ),
    (
        "audit-verification",
        "Audit chain verification",
        "Verify the tenant append-only audit chain and optional anchored head.",
        ["audit", "compliance"],
        ["Verify this tenant's audit chain."],
    ),
]


SKILL_TO_TOOL = {
    "cascade-assessment": "cascade.assess",
    "graph-snapshot": "graph.snapshot",
    "evidence-discovery": "evidence.discover",
    "event-submission": "event.submit",
    "mitigation-draft": "mitigation.propose",
    "approval-decision": "approval.decide",
    "audit-verification": "audit.verify",
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
        skill_id = params.get("skillId", "cascade-assessment")
        tool_name = SKILL_TO_TOOL.get(skill_id)
        if tool_name is None:
            raise ValueError("A2A skill is not registered.")
        result = execute_tool(store, actor, tool_name, part["data"])
    except (ValueError, TypeError) as error:
        return mcp_response(request_id, error={"code": -32602, "message": str(error)})
    return mcp_response(
        request_id,
        {
            "id": params["id"],
            "status": {"state": "completed"},
            "artifacts": [
                {
                    "name": skill_id,
                    "parts": [{"type": "data", "data": result}],
                }
            ],
        },
    )
