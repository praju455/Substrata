"""Typed local demo API; SSE connects directly to FastAPI."""

import asyncio
import json
import os
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.exc import SQLAlchemyError

from substrata.audit import verify_chain
from substrata.database import build_engine
from substrata.graph import GraphSnapshot
from substrata.llm import configured_client
from substrata.runtime import Runtime

ROOT = Path(__file__).resolve().parents[2]
router = APIRouter()


class WorkspaceState(BaseModel):
    generation: str
    synthetic: Literal[True]
    replay: dict
    graph: GraphSnapshot
    tier1_ids: list[str]
    shared_dependencies: list[dict]
    scenarios: list[dict]
    events: list[dict]
    actions: list[dict]
    confirmations: list[dict]
    audit: dict
    audit_events: list[dict]
    evaluation: list[dict]


class ReplayStart(BaseModel):
    event_limit: int = Field(default=1, ge=1, le=6)


class ReplyOptions(BaseModel):
    noise: float = Field(default=0, ge=0, le=1, allow_inf_nan=False)


class Decision(BaseModel):
    actor: str = Field(min_length=1, max_length=96)
    role: Literal["procurement_approver", "planning_approver"]
    decision: Literal["approved", "rejected"]
    reason: str = Field(min_length=1, max_length=2000)


class Resolution(BaseModel):
    node_id: str = Field(min_length=1, max_length=96)
    actor: str = Field(min_length=1, max_length=96)
    reason: str = Field(min_length=1, max_length=2000)


def runtime_for(request: Request) -> Runtime:
    with request.app.state.runtime_lock:
        return initialize_runtime(request)


def initialize_runtime(request: Request) -> Runtime:
    runtime = request.app.state.runtime
    if runtime is None:
        engine = build_engine(ROOT / "data/substrata.sqlite3")
        try:
            runtime = Runtime(
                engine,
                ROOT / "data",
                configured_client(),
                float(os.environ.get("SUBSTRATA_INFERENCE_THRESHOLD", "0.75")),
                float(os.environ.get("SUBSTRATA_SPEND_LIMIT", "10000")),
            )
        except (ValueError, SQLAlchemyError, KeyError, OSError) as exc:
            engine.dispose()
            raise HTTPException(
                503, "Demo is not ready. Run python scripts/dev.py seed; check local configuration."
            ) from exc
        request.app.state.runtime = runtime
    return runtime


@router.get("/state", response_model=WorkspaceState)
def state(request: Request):
    return runtime_for(request).state()


@router.get("/graph", response_model=GraphSnapshot)
def graph(request: Request):
    return runtime_for(request).state()["graph"]


@router.post("/mapper/run")
def mapper_run(request: Request):
    return runtime_for(request).map()


@router.post("/confirmations/simulate")
def confirmations(request: Request, options: ReplyOptions):
    return {"replies": runtime_for(request).confirm(options.noise)}


async def replay_worker(runtime: Runtime, event_limit: int):
    try:
        for _ in range(event_limit):
            if not runtime.active:
                break
            result = await asyncio.to_thread(runtime.process_next)
            if result is None:
                break
            await asyncio.sleep(0.4)
    except Exception as exc:
        await asyncio.to_thread(
            runtime.publish,
            "failed",
            {
                "error_type": type(exc).__name__,
                "message": "Replay stopped. Check input data and audit verification.",
            },
            False,
        )
    finally:
        runtime.active = False


@router.post("/replay/start")
async def replay_start(request: Request, options: ReplayStart):
    runtime = runtime_for(request)
    if runtime.task is not None and not runtime.task.done():
        raise HTTPException(409, "Replay is already active.")
    runtime.ensure_chain()
    runtime.active = True
    runtime.task = asyncio.create_task(replay_worker(runtime, options.event_limit))
    return {"active": True, "event_limit": options.event_limit}


@router.post("/replay/pause")
async def replay_pause(request: Request):
    runtime = runtime_for(request)
    runtime.active = False
    if runtime.task is not None:
        await runtime.task
    return {"active": False}


@router.post("/replay/reset")
async def replay_reset(request: Request):
    runtime = runtime_for(request)
    runtime.active = False
    if runtime.task is not None:
        await runtime.task
    return await asyncio.to_thread(runtime.reset)


@router.post("/events/{event_id}/resolve")
def resolve(request: Request, event_id: str, resolution: Resolution):
    return runtime_for(request).resolve(event_id, **resolution.model_dump())


@router.post("/scenarios/{scenario_id}/refresh")
def refresh(request: Request, scenario_id: str):
    return runtime_for(request).refresh(scenario_id)


@router.post("/approvals/{action_id}/decision")
def approval(request: Request, action_id: str, decision: Decision):
    return runtime_for(request).decide(action_id, decision.model_dump())


@router.get("/audit/verify")
def audit_verify(request: Request, expected_head: str | None = None):
    workspace = runtime_for(request).state()
    return verify_chain(workspace["audit_events"], expected_head)


@router.get("/stream")
async def stream(request: Request, once: bool = False, after: int = 0):
    runtime = runtime_for(request)
    if after < 0:
        raise HTTPException(422, "Stream cursor must be nonnegative.")
    last = request.headers.get("last-event-id", "")
    generation, cursor = "", after
    if ":" in last:
        generation, value = last.rsplit(":", 1)
        if value.isdigit():
            cursor = int(value)

    async def messages():
        nonlocal generation, cursor
        while not await request.is_disconnected():
            current, rows = runtime.stream_batch(cursor)
            if generation and current != generation:
                cursor = 0
                current, rows = runtime.stream_batch(0)
                yield 'event: reset\ndata: {"type":"reset"}\n\n'
            generation = current
            for row in rows:
                cursor = row["id"]
                yield f"id: {generation}:{cursor}\ndata: {json.dumps(row)}\n\n"
            if not rows:
                yield ": heartbeat\n\n"
            if once:
                return
            await asyncio.sleep(0.5)

    return StreamingResponse(
        messages(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
