"""Data types shared by the Campus Customs agent team (team.py) and the audit trail (audit.py)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from pydantic import BaseModel, Field

AgentName = Literal["boss", "inventory", "accounting", "facilities", "customer_service"]
AGENTS: tuple[AgentName, ...] = ("boss", "inventory", "accounting", "facilities", "customer_service")

TicketStatus = Literal["open", "in_progress", "waiting_on_approval", "blocked", "resolved"]


class AgentReport(BaseModel):
    """What every agent hands back, to the agent that delegated to it or (for the Boss) to the human."""

    summary: str = Field(description="2-4 sentences: what you found and did, with the real numbers from the tools.")
    status: TicketStatus = Field(description="Where the work stands after your turn.")
    actions_taken: list[str] = Field(default_factory=list, description="Each tool action you took, e.g. 'Queued approval #2: $2,400 rent'.")
    approval_ids: list[int] = Field(default_factory=list, description="Approval requests you (or agents you delegated to) queued.")
    draft_ids: list[int] = Field(default_factory=list, description="Drafts you (or agents you delegated to) saved on the board.")
    needs_human: list[str] = Field(default_factory=list, description="Decisions only the human can make (payments, discounts, trade-offs).")
    next_steps: list[str] = Field(default_factory=list, description="What should happen after the human acts.")


@dataclass
class TeamDeps:
    """Per-agent-run context. A new one is made for every delegation."""

    run_id: str
    agent: AgentName
    ticket_id: int | None = None
    depth: int = 0
    chain: list[AgentName] = field(default_factory=list)  # who delegated to whom, e.g. ["boss", "accounting"]


class AuditStep(BaseModel):
    """One line in output/audit_trail.json."""

    time: str
    run_id: str
    event: Literal[
        "run_start", "run_end", "run_error",
        "agent_start", "agent_end", "model_step",
        "tool_call", "tool_blocked", "delegation", "delegation_refused",
        "human_decision", "db_reset",
    ]
    agent: AgentName | None = None
    ticket_id: int | None = None
    depth: int | None = None
    data: dict[str, Any] = Field(default_factory=dict)
