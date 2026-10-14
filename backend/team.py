"""Campus Customs agent team: five PydanticAI agents on gpt-6-luna (via Portkey) sharing one MCP server.

- Boss, Inventory, Accounting, Facilities and Customer Service each read their instructions from
  prompts/<name>.md and see only the MCP tools listed in AGENT_TOOLS.
- Every agent can delegate to every other agent with the `delegate` tool (full connectivity).
  Cycles are refused (no delegating back to anyone already in the chain) and depth is capped.
- All database access goes through the MCP server (mcp_server/server.py); there are no local
  shortcut tools. Human-only MCP tools (approve/reject) are hidden from every agent and blocked
  again at call time.
- Every step is appended to output/audit_trail.json (audit.py).

CLI:
    python backend/team.py --ticket 101        # work one ticket (Boss starts)
    python backend/team.py --all               # work every open ticket
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import uuid
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from fastmcp.client.transports import PythonStdioTransport
from pydantic_ai import Agent, RunContext
from pydantic_ai.exceptions import UsageLimitExceeded
from pydantic_ai.mcp import MCPToolset
from pydantic_ai.messages import TextPart, ToolCallPart
from pydantic_ai.models.openai import OpenAIResponsesModel
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai.usage import RunUsage, UsageLimits

import audit
from models import AGENTS, AgentName, AgentReport, TeamDeps

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
PROMPTS = HERE / "prompts"
MCP_SERVER = ROOT / "mcp_server" / "server.py"

# The key lives in .env in HW5/ or the AI Foundations folder above it; it is never written anywhere.
for _folder in (ROOT, ROOT.parent):
    load_dotenv(_folder / ".env", override=False)
os.environ.setdefault("PYDANTIC_AI_NO_BANNER", "1")

# Model: gpt-6-luna only, through Portkey. Not overridable on purpose (assignment rule).
MODEL_NAME = "gpt-6-luna"
PORTKEY_BASE_URL = "https://api.portkey.ai/v1"
REASONING_EFFORT = os.getenv("PORTKEY_REASONING_EFFORT", "medium")

# Token / cost guardrails for one ticket run. Usage is shared across every delegated agent,
# so these cap the whole team's work on a ticket, not just one agent.
MAX_OUTPUT_TOKENS = 4_000        # per model response
USAGE_LIMITS = UsageLimits(
    request_limit=40,            # model calls across the whole team
    tool_calls_limit=60,         # MCP + delegate calls across the whole team
    total_tokens_limit=250_000,  # input + output tokens across the whole team
)
MAX_DELEGATION_DEPTH = 3         # boss -> a -> b -> c, no deeper
LIMITS_SUMMARY = {"request_limit": 40, "tool_calls_limit": 60, "total_tokens_limit": 250_000,
                  "max_output_tokens_per_response": MAX_OUTPUT_TOKENS, "max_delegation_depth": MAX_DELEGATION_DEPTH}

# Which MCP tools each agent may see. approve_request / reject_request are human-only and
# appear in no list.
AGENT_TOOLS: dict[AgentName, set[str]] = {
    "boss": {"list_open_tickets", "get_ticket", "get_board", "list_vendors", "update_ticket",
             "request_price_override", "check_rent_and_cash", "quote_bulk_order"},
    "inventory": {"get_ticket", "list_vendors", "check_restock_path", "quote_bulk_order",
                  "draft_vendor_order", "update_ticket"},
    "accounting": {"get_ticket", "get_board", "list_vendors", "check_rent_and_cash", "quote_bulk_order",
                   "request_payment_approval", "update_ticket"},
    "facilities": {"get_ticket", "check_rent_and_cash", "draft_message", "update_ticket"},
    "customer_service": {"get_ticket", "check_restock_path", "quote_bulk_order", "list_vendors",
                         "draft_message", "update_ticket"},
}
HUMAN_ONLY_TOOLS = {"approve_request", "reject_request"}


class AgentNotConfigured(RuntimeError):
    """PORTKEY_API_KEY is missing."""


def portkey_model() -> OpenAIResponsesModel:
    api_key = os.getenv("PORTKEY_API_KEY")
    if not api_key:
        raise AgentNotConfigured("PORTKEY_API_KEY is not set. Add it to .env (HW5/ or the folder above).")
    # Responses API: Portkey's gpt-6-luna rejects tools + reasoning effort on /v1/chat/completions.
    return OpenAIResponsesModel(
        MODEL_NAME,
        provider=OpenAIProvider(api_key=api_key, base_url=PORTKEY_BASE_URL),
        settings={
            "openai_reasoning_effort": REASONING_EFFORT,
            "openai_store": False,
            "max_tokens": MAX_OUTPUT_TOKENS,
        },
    )


# ------------------------------------------------------------------ MCP toolset (shared by all agents)

async def _audited_mcp_call(ctx: RunContext[TeamDeps], call_tool, name: str, args: dict[str, Any]):
    """Every MCP call passes through here: block human-only tools, stamp identity, audit."""
    deps = ctx.deps
    if name in HUMAN_ONLY_TOOLS or name not in AGENT_TOOLS[deps.agent]:
        audit.log("tool_blocked", deps, tool=name, args=audit.short(args))
        return {"error": f"Tool '{name}' is not available to {deps.agent}. Payments are approved by a human on the dashboard."}
    args = dict(args)
    for key in _IDENTITY_TOOLS.get(name, ()):
        args[key] = deps.agent  # the model can't act under another agent's name
    if deps.ticket_id is not None and "ticket_id" in _TICKET_TOOLS.get(name, ()) and "ticket_id" not in args:
        args["ticket_id"] = deps.ticket_id
    try:
        result = await call_tool(name, args)
    except Exception as e:  # tool errors still get logged, then go back to the model to retry
        audit.log("tool_call", deps, tool=name, args=args, error=audit.short(str(e)))
        raise
    audit.log("tool_call", deps, tool=name, args=args, result=audit.short(result))
    return result


# Tools that take an identity / ticket_id argument (so the wrapper can fill them in).
_IDENTITY_TOOLS = {
    "update_ticket": ("author",), "draft_message": ("author",), "draft_vendor_order": ("author",),
    "request_payment_approval": ("requested_by",), "request_price_override": ("requested_by",),
}
_TICKET_TOOLS = {n: ("ticket_id",) for n in (
    "update_ticket", "draft_message", "draft_vendor_order", "request_payment_approval", "request_price_override",
)}

# MCP stdio servers don't inherit our environment, so pass the test DB override through explicitly.
_server_env = {"CAMPUS_CUSTOMS_DB": os.environ["CAMPUS_CUSTOMS_DB"]} if os.getenv("CAMPUS_CUSTOMS_DB") else None
mcp_toolset = MCPToolset(
    PythonStdioTransport(str(MCP_SERVER), python_cmd=sys.executable, env=_server_env),
    process_tool_call=_audited_mcp_call,
    max_retries=2,
)


def _tools_for(agent: AgentName):
    allowed = AGENT_TOOLS[agent]
    return mcp_toolset.filtered(lambda ctx, tool_def: tool_def.name in allowed)


# ------------------------------------------------------------------ agents

_agents: dict[AgentName, Agent[TeamDeps, AgentReport]] = {}


def build_agent(name: AgentName, model) -> Agent[TeamDeps, AgentReport]:
    agent: Agent[TeamDeps, AgentReport] = Agent(
        model,
        name=name,
        output_type=AgentReport,
        deps_type=TeamDeps,
        instructions=(PROMPTS / f"{name}.md").read_text(encoding="utf-8"),
        toolsets=[_tools_for(name)],
        retries=2,
    )

    @agent.instructions
    def run_context(ctx: RunContext[TeamDeps]) -> str:
        d = ctx.deps
        others = [a for a in AGENTS if a != d.agent and a not in d.chain]
        can_delegate = others if d.depth < MAX_DELEGATION_DEPTH else []
        return (
            f"## This run\n"
            f"- You are: {d.agent}. Ticket: {d.ticket_id if d.ticket_id is not None else 'none given'}.\n"
            f"- Delegation chain so far: {' -> '.join(d.chain) or d.agent}.\n"
            f"- You may delegate to: {', '.join(can_delegate) or 'nobody (max depth reached); finish with your own tools'}.\n"
            f"- Your MCP tools: {', '.join(sorted(AGENT_TOOLS[d.agent]))}."
        )

    @agent.tool
    async def delegate(ctx: RunContext[TeamDeps], to: AgentName, task: str) -> str:
        """Hand a specific task to another Campus Customs agent and get their AgentReport back.

        Args:
            to: boss, inventory, accounting, facilities or customer_service.
            task: A self-contained instruction including the ticket number and every fact they need.
        """
        d = ctx.deps
        if to == d.agent or to in d.chain:
            audit.log("delegation_refused", d, to=to, task=audit.short(task), reason="cycle")
            return f"Refused: {to} is already working on this in the chain ({' -> '.join(d.chain)}). Use your own tools."
        if d.depth >= MAX_DELEGATION_DEPTH:
            audit.log("delegation_refused", d, to=to, task=audit.short(task), reason="max depth")
            return "Refused: maximum delegation depth reached. Finish with your own tools."
        audit.log("delegation", d, to=to, task=audit.short(task))
        child = TeamDeps(run_id=d.run_id, agent=to, ticket_id=d.ticket_id, depth=d.depth + 1, chain=[*d.chain, to])
        report = await run_agent(to, task, child, usage=ctx.usage)
        return report.model_dump_json()

    return agent


def get_agent(name: AgentName) -> Agent[TeamDeps, AgentReport]:
    if not _agents:
        model = portkey_model()
        for a in AGENTS:
            _agents[a] = build_agent(a, model)
    return _agents[name]


async def run_agent(name: AgentName, task: str, deps: TeamDeps, usage: RunUsage | None = None) -> AgentReport:
    """Run one agent, appending every model step to the audit trail as it happens."""
    agent = get_agent(name)
    audit.log("agent_start", deps, task=audit.short(task), chain=deps.chain)
    async with agent.iter(task, deps=deps, usage=usage, usage_limits=USAGE_LIMITS) as run:
        async for node in run:
            if Agent.is_call_tools_node(node):
                resp = node.model_response
                audit.log(
                    "model_step", deps,
                    model=resp.model_name,
                    text=audit.short(" ".join(p.content for p in resp.parts if isinstance(p, TextPart)).strip()) or None,
                    tool_calls=[
                        {"tool": p.tool_name, "args": audit.short(p.args_as_dict(), 300)}
                        for p in resp.parts if isinstance(p, ToolCallPart)
                    ],
                    input_tokens=resp.usage.input_tokens,
                    output_tokens=resp.usage.output_tokens,
                )
        report = run.result.output
    audit.log("agent_end", deps, report=report.model_dump(), usage_so_far=_usage_dict(run.usage))
    return report


def _usage_dict(u: RunUsage) -> dict[str, int]:
    return {"requests": u.requests, "tool_calls": u.tool_calls, "input_tokens": u.input_tokens,
            "output_tokens": u.output_tokens, "total_tokens": u.total_tokens}


# ------------------------------------------------------------------ entry points

def new_run_id() -> str:
    return uuid.uuid4().hex[:12]


async def run_ticket(ticket_id: int, instruction: str | None = None, run_id: str | None = None) -> dict[str, Any]:
    """The Boss works one ticket end to end, delegating as needed."""
    run_id = run_id or new_run_id()
    deps = TeamDeps(run_id=run_id, agent="boss", ticket_id=ticket_id, depth=0, chain=["boss"])
    task = instruction or (
        f"Work ticket {ticket_id}. Read it with get_ticket, delegate to the right specialists, make sure "
        f"every payment or discount is queued for human approval and every outside message is a draft, "
        f"update the ticket status, and report back to the human."
    )
    audit.log("run_start", deps, entry_agent="boss", task=task, model=MODEL_NAME, limits=LIMITS_SUMMARY)
    usage = RunUsage()
    try:
        async with mcp_toolset:  # one MCP server process for the whole team
            report = await run_agent("boss", task, deps, usage=usage)
    except UsageLimitExceeded as e:
        audit.log("run_error", deps, error=f"Token/usage limit hit: {e}", usage=_usage_dict(usage))
        return {"run_id": run_id, "ticket_id": ticket_id, "error": f"Usage limit reached: {e}", "usage": _usage_dict(usage)}
    except Exception as e:
        audit.log("run_error", deps, error=audit.short(f"{type(e).__name__}: {e}"), usage=_usage_dict(usage))
        raise
    audit.log("run_end", deps, status=report.status, usage=_usage_dict(usage))
    return {"run_id": run_id, "ticket_id": ticket_id, "report": report.model_dump(), "usage": _usage_dict(usage)}


async def open_ticket_ids() -> list[int]:
    async with mcp_toolset:
        result = await mcp_toolset.direct_call_tool("list_open_tickets", {})
    return [t["id"] for t in result["tickets"]]


async def run_all_open() -> list[dict[str, Any]]:
    return [await run_ticket(tid) for tid in await open_ticket_ids()]


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the Campus Customs agent team.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--ticket", type=int, help="ticket id to work")
    group.add_argument("--all", action="store_true", help="work every open ticket")
    args = parser.parse_args()
    results = asyncio.run(run_all_open() if args.all else run_ticket(args.ticket))
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
