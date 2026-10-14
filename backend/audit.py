"""Append-only audit trail: output/audit_trail.json.

Every execution step of every agent (start, each model response, each MCP tool call, each
delegation, end) is appended as soon as it happens. The file is a JSON list that is never
cleared between runs; each append rewrites it atomically (temp file + rename) so a crash can't
truncate it, and an unreadable file is set aside rather than deleted.
"""

from __future__ import annotations

import json
import os
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from models import AuditStep, TeamDeps

# AUDIT_TRAIL_PATH overrides the path for tests.
AUDIT_PATH = Path(os.getenv("AUDIT_TRAIL_PATH") or Path(__file__).resolve().parent.parent / "output" / "audit_trail.json")
MAX_CHARS = 600  # long tool results are trimmed so the log stays readable
_lock = threading.Lock()


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def short(value: Any, limit: int = MAX_CHARS) -> Any:
    text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, default=str)
    return text if len(text) <= limit else text[: limit - 1] + "…"


def _load() -> list[dict]:
    if not AUDIT_PATH.exists():
        return []
    try:
        data = json.loads(AUDIT_PATH.read_text(encoding="utf-8") or "[]")
        if isinstance(data, list):
            return data
    except json.JSONDecodeError:
        pass
    AUDIT_PATH.rename(AUDIT_PATH.with_suffix(f".corrupt-{int(datetime.now().timestamp())}.json"))
    return []


def log(event: str, deps: TeamDeps | None = None, *, run_id: str | None = None, **data: Any) -> None:
    step = AuditStep(
        time=now_iso(),
        run_id=run_id or (deps.run_id if deps else "-"),
        event=event,
        agent=deps.agent if deps else None,
        ticket_id=deps.ticket_id if deps else data.pop("ticket_id", None),
        depth=deps.depth if deps else None,
        data=data,
    )
    with _lock:
        AUDIT_PATH.parent.mkdir(parents=True, exist_ok=True)
        entries = _load()
        entries.append(step.model_dump())
        tmp = AUDIT_PATH.with_suffix(".tmp")
        tmp.write_text(json.dumps(entries, indent=2, ensure_ascii=False), encoding="utf-8")
        os.replace(tmp, AUDIT_PATH)
