"""FastAPI backend for the Campus Customs dashboard.

Start from backend/:  uvicorn main:app --reload --port 8000   ->  http://localhost:8000 (docs at /docs)

Every database read/write goes through the campus-customs MCP server (one stdio client held open
for the app's lifetime). Agents only *prepare* payments and purchases; the approve route is the only
place the human-only approve_request tool is called, so it's the only place cash actually changes.
"""

from __future__ import annotations

import asyncio
import json
import os
import shutil
from pathlib import Path
import sys
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastmcp import Client
from fastmcp.client.transports import PythonStdioTransport
from pydantic import BaseModel, Field

import audit
import team

PRISTINE_DB = team.ROOT / "data" / "campus_customs.db"
WORKING_DB = Path(os.getenv("CAMPUS_CUSTOMS_DB") or team.ROOT / "data" / "campus_customs_new.db")  # same override as the MCP server

mcp: Client | None = None
runs: dict[str, dict[str, Any]] = {}  # run_id -> status/result, in memory
active_run: str | None = None         # one team run at a time (shared cash, shared token budget)


def _busy() -> bool:
    return active_run is not None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global mcp
    mcp = Client(PythonStdioTransport(str(team.MCP_SERVER), python_cmd=sys.executable, env=team._server_env))
    async with mcp:
        yield


app = FastAPI(title="Campus Customs Desk API", lifespan=lifespan)
app.add_middleware(  # the React dashboard (Vite dev server, http://localhost:5173) runs on another origin
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1)(:\d+)?",  # also any other local port (vite preview, etc.)
    allow_methods=["*"],
    allow_headers=["*"],
)


async def call(tool: str, args: dict[str, Any] | None = None) -> dict[str, Any]:
    result = await mcp.call_tool(tool, args or {})
    return result.data if result.data is not None else json.loads(result.content[0].text)


def _check(result: dict[str, Any], status: int = 400) -> dict[str, Any]:
    if "error" in result:
        raise HTTPException(status_code=status, detail=result["error"])
    return result


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


# ---------------------------------------------------------------- tickets

@app.get("/api/health")
async def health() -> dict[str, Any]:
    return {"ok": True, "model": team.MODEL_NAME, "run_in_progress": active_run}


@app.get("/api/tickets")
async def list_tickets() -> dict[str, Any]:
    data = await call("list_tickets")
    tickets = [
        {**t, "is_open": t["status"] != "resolved",
         "last_run": next((r for r in reversed(runs.values()) if r["ticket_id"] == t["id"]), None)}
        for t in data["tickets"]
    ]
    return {"today": data["today"], "tickets": tickets}


@app.get("/api/tickets/{ticket_id}")
async def get_ticket(ticket_id: int) -> dict[str, Any]:
    return _check(await call("get_ticket", {"ticket_id": ticket_id}), 404)


# ---------------------------------------------------------------- agent runs

class RunRequest(BaseModel):
    instruction: str | None = Field(None, description="Optional extra instruction for the Boss.")


async def _do_run(run_id: str, ticket_id: int, instruction: str | None) -> None:
    global active_run
    runs[run_id]["status"] = "running"
    try:
        result = await team.run_ticket(ticket_id, instruction, run_id=run_id)
        runs[run_id].update(status="error" if "error" in result else "done", result=result, finished_at=_now())
    except Exception as e:  # already written to the audit trail by run_ticket
        runs[run_id].update(status="error", result={"error": f"{type(e).__name__}: {e}"}, finished_at=_now())
    finally:
        active_run = None


@app.post("/api/tickets/{ticket_id}/run", status_code=202)
async def run_ticket(ticket_id: int, body: RunRequest | None = None) -> dict[str, Any]:
    """Start the agent team on a ticket in the background; poll /api/runs/{run_id} and /api/events."""
    global active_run
    if _busy():
        raise HTTPException(409, f"The team is already working a ticket (run {active_run}). Wait for it to finish.")
    _check(await call("get_ticket", {"ticket_id": ticket_id}), 404)
    if _busy():  # re-check: another request may have started a run while we awaited
        raise HTTPException(409, f"The team is already working a ticket (run {active_run}). Wait for it to finish.")
    run_id = active_run = team.new_run_id()
    runs[run_id] = {"run_id": run_id, "ticket_id": ticket_id, "status": "queued", "started_at": _now(), "result": None}
    asyncio.create_task(_do_run(run_id, ticket_id, body.instruction if body else None))
    return runs[run_id]


@app.get("/api/runs")
async def list_runs() -> dict[str, Any]:
    return {"runs": list(runs.values())}


@app.get("/api/runs/{run_id}")
async def get_run(run_id: str) -> dict[str, Any]:
    if run_id not in runs:
        raise HTTPException(404, f"No run {run_id} in this server session.")
    return runs[run_id]


@app.get("/api/tickets/{ticket_id}/summary")
async def ticket_summary(ticket_id: int) -> dict[str, Any]:
    """Per-agent recap of the latest run on a ticket: what each agent said, which tools it used, hand-offs."""
    entries = [e for e in audit._load() if e.get("ticket_id") == ticket_id and e["run_id"] != "human"]
    run_ids = [e["run_id"] for e in entries if e["event"] == "run_start"]
    if not run_ids:
        return {"ticket_id": ticket_id, "run_id": None, "agents": [], "usage": None}
    run_id = run_ids[-1]
    agents: dict[str, dict[str, Any]] = {}
    usage = None
    for e in (x for x in entries if x["run_id"] == run_id):
        name = e.get("agent")
        if e["event"] == "run_end":
            usage = e["data"].get("usage")
        if not name:
            continue
        a = agents.setdefault(name, {"agent": name, "tools": {}, "delegated_to": [], "summary": None,
                                     "status": None, "approval_ids": [], "draft_ids": []})
        if e["event"] == "tool_call":
            a["tools"][e["data"]["tool"]] = a["tools"].get(e["data"]["tool"], 0) + 1
        elif e["event"] == "delegation":
            a["delegated_to"].append(e["data"]["to"])
        elif e["event"] == "agent_end":
            r = e["data"].get("report") or {}
            a.update(summary=r.get("summary"), status=r.get("status"),
                     approval_ids=sorted(set(a["approval_ids"]) | set(r.get("approval_ids", []))),
                     draft_ids=sorted(set(a["draft_ids"]) | set(r.get("draft_ids", []))))
    return {"ticket_id": ticket_id, "run_id": run_id, "agents": list(agents.values()), "usage": usage,
            "finished": usage is not None}


# ---------------------------------------------------------------- events (audit trail)

def _summary(e: dict[str, Any]) -> str:
    d, ev = e["data"], e["event"]
    if ev == "model_step":
        calls = ", ".join(c["tool"] for c in d.get("tool_calls", []))
        return (d.get("text") or "") + (f" → calls {calls}" if calls else "")
    if ev == "tool_call":
        return f"{d.get('tool')}({audit.short(d.get('args'), 120)})" + (f" ERROR {d['error']}" if d.get("error") else "")
    if ev in ("delegation", "delegation_refused"):
        return f"→ {d.get('to')}: {d.get('task')}" + (f" (refused: {d.get('reason')})" if ev == "delegation_refused" else "")
    if ev == "agent_end":
        return (d.get("report") or {}).get("summary", "")
    if ev in ("agent_start", "run_start"):
        return d.get("task", "")
    return audit.short({k: v for k, v in d.items()}, 200)


@app.get("/api/events")
async def events(
    since: int = Query(0, ge=0, description="Return events with seq > since (use the last seq you saw)."),
    limit: int = Query(200, ge=1, le=1000),
    run_id: str | None = None,
    ticket_id: int | None = None,
) -> dict[str, Any]:
    """Recent agent events for auto-refresh: agent statements, delegations, tool calls."""
    entries = audit._load()
    out = []
    for seq, e in enumerate(entries, start=1):
        if seq <= since or (run_id and e["run_id"] != run_id) or (ticket_id and e["ticket_id"] != ticket_id):
            continue
        out.append({"seq": seq, **e, "summary": _summary(e)})
    out = out[-limit:]
    return {"last_seq": len(entries), "events": out}


# ---------------------------------------------------------------- human approvals (the only cash change)

class Decision(BaseModel):
    approver: str = Field(..., min_length=1, description="Name of the human approving (agent names are refused).")
    note: str = ""


@app.get("/api/board")
async def board() -> dict[str, Any]:
    """Approvals (pending/decided), drafts, payments and cash: what the human reviews."""
    return await call("get_board")


async def _approval_ticket(approval_id: int) -> int | None:
    b = await call("get_board")
    a = next((x for x in b["pending_approvals"] + b["decided_approvals"] if x["id"] == approval_id), None)
    return a["ticket_id"] if a else None


async def _maybe_resolve(ticket_id: int | None, approver: str) -> bool:
    """A ticket is done once the team has worked it and the human has decided every request on it."""
    if ticket_id is None:
        return False
    t = await call("get_ticket", {"ticket_id": ticket_id})
    if "error" in t or t["ticket"]["status"] == "resolved" or not t["approvals"]:
        return False
    if any(a["status"] == "pending" for a in t["approvals"]):
        return False
    decided = ", ".join(f"#{a['id']} {a['status']}" for a in t["approvals"])
    r = await call("update_ticket", {"ticket_id": ticket_id, "author": f"human:{approver}", "status": "resolved",
                                     "note": f"All requests decided by {approver} ({decided}). Ticket closed."})
    return "error" not in r


async def _decide(tool: str, approval_id: int, body: Decision) -> dict[str, Any]:
    if _busy():
        raise HTTPException(409, "Wait for the current agent run to finish before deciding.")
    ticket_id = await _approval_ticket(approval_id)
    result = await call(tool, {"approval_id": approval_id, "approver": body.approver, "note": body.note})
    resolved = "error" not in result and await _maybe_resolve(ticket_id, body.approver.strip())
    audit.log("human_decision", run_id="human", ticket_id=ticket_id,
              decision="approve" if tool == "approve_request" else "reject", approval_id=approval_id,
              approver=body.approver, result=audit.short(result), ticket_resolved=resolved)
    return {**_check(result, 409), "ticket_id": ticket_id, "ticket_resolved": resolved}


@app.post("/api/approvals/{approval_id}/approve")
async def approve(approval_id: int, body: Decision) -> dict[str, Any]:
    """Human click: execute a prepared payment/purchase (or accept a discount). Refuses if cash would go negative.
    When it's the ticket's last pending request, the ticket is marked resolved."""
    return await _decide("approve_request", approval_id, body)


@app.post("/api/approvals/{approval_id}/reject")
async def reject(approval_id: int, body: Decision) -> dict[str, Any]:
    """Human click: reject a request (nothing is paid). Resolves the ticket if nothing else is pending."""
    return await _decide("reject_request", approval_id, body)


# ---------------------------------------------------------------- cash & reset

@app.get("/api/cash")
async def cash() -> dict[str, Any]:
    b = await call("get_board")
    return {
        "today": b["today"],
        "accounts": b["cash_accounts"],
        "checking_balance": next((a["balance"] for a in b["cash_accounts"] if a["name"] == "checking"), None),
        "pending_payments_total": b["pending_payments_total"],
        "projected_balance": b["projected_balance"],
        "payments": b["payments"],
    }


@app.post("/api/reset")
async def reset() -> dict[str, Any]:
    """Copy the pristine campus_customs.db over the working DB (audit trail is kept)."""
    if _busy():
        raise HTTPException(409, "Can't reset while the team is running.")
    shutil.copyfile(PRISTINE_DB, WORKING_DB)
    runs.clear()
    audit.log("db_reset", run_id="human", source=PRISTINE_DB.name, target=WORKING_DB.name)
    return {"ok": True, "reset_from": PRISTINE_DB.name, "cash": await cash()}
