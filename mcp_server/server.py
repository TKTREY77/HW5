"""Campus Customs MCP server.

The only gateway between the agent team and data/campus_customs_new.db: every read and
write the agents make goes through a tool here. Every value returned comes straight from
the database; "today" is desk.date_today.

Guardrails enforced in code (not just in prompts):
- Payments only happen in approve_request, which is human-only (never exposed to agents),
  rejects agent names as the approver, and refuses if cash would go below $0.
- Money only goes out: no tool ever increases a cash balance.
- Customer/vendor/landlord messages are stored as drafts on the board; nothing is sent.
- Vendor orders are drafted, and flagged as blocked while the vendor has open invoices.
"""

import os
import sqlite3
from contextlib import contextmanager
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Literal

from fastmcp import FastMCP

# CAMPUS_CUSTOMS_DB overrides the path for tests against a scratch copy.
DB_PATH = Path(os.getenv("CAMPUS_CUSTOMS_DB") or Path(__file__).resolve().parent.parent / "data" / "campus_customs_new.db")

AGENT_NAMES = {"boss", "inventory", "accounting", "facilities", "customer_service"}
TICKET_STATUSES = ("open", "in_progress", "waiting_on_approval", "blocked", "resolved")

mcp = FastMCP("campus-customs")

# Board tables added on top of the original schema (created on first start, safe to re-run).
SCHEMA = """
CREATE TABLE IF NOT EXISTS approvals (
    id INTEGER PRIMARY KEY,
    ticket_id INTEGER,
    kind TEXT NOT NULL,              -- invoice_payment | rent_payment | vendor_purchase | price_override
    ref_id INTEGER,                  -- invoices.id / leases.id / drafts.id (vendor_purchase); NULL for price_override
    payee TEXT,
    amount REAL NOT NULL,            -- money out for payments; quote total for price_override
    details TEXT,
    requested_by TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',   -- pending | approved | rejected
    created_at TEXT NOT NULL,
    decided_by TEXT,
    decided_at TEXT,
    decision_note TEXT,
    payment_id INTEGER,
    FOREIGN KEY (ticket_id) REFERENCES tickets(id)
);
CREATE TABLE IF NOT EXISTS drafts (
    id INTEGER PRIMARY KEY,
    ticket_id INTEGER,
    channel TEXT NOT NULL,           -- email | phone_script | letter | vendor_order
    recipient TEXT NOT NULL,
    subject TEXT NOT NULL,
    body TEXT NOT NULL,
    author TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'draft',     -- draft | blocked (vendor has open invoices) | approved (purchase paid)
    created_at TEXT NOT NULL,
    FOREIGN KEY (ticket_id) REFERENCES tickets(id)
);
CREATE TABLE IF NOT EXISTS ticket_notes (
    id INTEGER PRIMARY KEY,
    ticket_id INTEGER NOT NULL,
    author TEXT NOT NULL,
    note TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY (ticket_id) REFERENCES tickets(id)
);
"""


@contextmanager
def _db(write: bool = False):
    _ensure_schema()  # cheap; recreates the board tables if the DB was just reset
    conn = sqlite3.connect(DB_PATH if write else f"file:{DB_PATH}?mode=ro", uri=not write)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        if write:
            conn.commit()
    finally:
        conn.close()


def _ensure_schema() -> None:
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.executescript(SCHEMA)
    finally:
        conn.close()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _today(conn: sqlite3.Connection) -> str:
    return conn.execute("SELECT date_today FROM desk LIMIT 1").fetchone()["date_today"]


def _days_between(start: str, end: str) -> int:
    return (date.fromisoformat(end[:10]) - date.fromisoformat(start[:10])).days


def _rows(conn: sqlite3.Connection, sql: str, *args) -> list[dict]:
    return [dict(r) for r in conn.execute(sql, args)]


def _row(conn: sqlite3.Connection, sql: str, *args) -> dict | None:
    r = conn.execute(sql, args).fetchone()
    return dict(r) if r else None


def _pending_payments_total(conn: sqlite3.Connection) -> float:
    return conn.execute(
        "SELECT COALESCE(SUM(amount), 0) FROM approvals "
        "WHERE status = 'pending' AND kind IN ('invoice_payment', 'rent_payment', 'vendor_purchase')"
    ).fetchone()[0]


def _add_months(iso: str, months: int) -> str:
    d = date.fromisoformat(iso[:10])
    y, m = divmod(d.month - 1 + months, 12)
    day = min(d.day, 28)  # stay valid in every month
    return date(d.year + y, m + 1, day).isoformat()


# ---------------------------------------------------------------- read tools (tickets & board)

def list_tickets() -> dict:
    """List all tickets (open and resolved) with their status, for the dashboard."""
    with _db() as conn:
        return {"today": _today(conn), "tickets": _rows(conn, "SELECT * FROM tickets ORDER BY id")}


def list_open_tickets() -> dict:
    """List every ticket that is not resolved yet, oldest first, with "today" from desk.date_today.

    The Boss's starting point: shows each ticket's type, requester, subject, linked
    sku/size/qty/lease_id/invoice_id, and current status.
    """
    with _db() as conn:
        return {
            "today": _today(conn),
            "tickets": _rows(conn, "SELECT * FROM tickets WHERE status != 'resolved' ORDER BY created_at"),
        }


def get_ticket(ticket_id: int) -> dict:
    """Get one ticket plus every row it links to, and what the team has already done on it.

    Includes the linked inventory rows and pricing (for sku), lease (lease_id), invoice and
    its vendor (invoice_id), plus this ticket's notes, approval requests and drafts.
    """
    with _db() as conn:
        t = _row(conn, "SELECT * FROM tickets WHERE id = ?", ticket_id)
        if t is None:
            return {"error": f"No ticket with id={ticket_id}."}
        out = {"today": _today(conn), "ticket": t}
        if t["sku"]:
            out["inventory_all_sizes"] = _rows(
                conn, "SELECT size, qty, location FROM inventory WHERE sku = ?", t["sku"])
            out["pricing"] = _row(conn, "SELECT * FROM pricing WHERE sku = ?", t["sku"])
        if t["lease_id"]:
            out["lease"] = _row(conn, "SELECT * FROM leases WHERE id = ?", t["lease_id"])
        if t["invoice_id"]:
            inv = _row(conn, "SELECT * FROM invoices WHERE id = ?", t["invoice_id"])
            out["invoice"] = inv
            if inv:
                out["invoice_vendor"] = _row(conn, "SELECT * FROM vendors WHERE id = ?", inv["vendor_id"])
        out["notes"] = _rows(conn, "SELECT author, note, created_at FROM ticket_notes WHERE ticket_id = ? ORDER BY id", ticket_id)
        out["approvals"] = _rows(conn, "SELECT * FROM approvals WHERE ticket_id = ? ORDER BY id", ticket_id)
        out["drafts"] = _rows(conn, "SELECT * FROM drafts WHERE ticket_id = ? ORDER BY id", ticket_id)
        return out


def list_vendors() -> dict:
    """List every vendor with its specialty, lead_days, open invoices, and whether it will ship now.

    Use this to pick the right supplier for a SKU (match specialty) before checking a restock.
    """
    with _db() as conn:
        today = _today(conn)
        vendors = []
        for v in _rows(conn, "SELECT * FROM vendors ORDER BY id"):
            inv = _rows(conn, "SELECT id, amount, due_date, description FROM invoices "
                              "WHERE vendor_id = ? AND status = 'open'", v["id"])
            vendors.append({**v, "open_invoices": inv, "will_ship": not inv})
        return {"today": today, "vendors": vendors}


def get_board() -> dict:
    """The human approval board: pending approvals, drafts, cash on hand, and projected cash.

    projected_balance = balance minus every pending payment request, i.e. what's left if the
    human approves everything currently queued.
    """
    with _db() as conn:
        cash = _rows(conn, "SELECT * FROM cash_accounts")
        balance = sum(c["balance"] for c in cash)
        pending_total = _pending_payments_total(conn)
        return {
            "today": _today(conn),
            "cash_accounts": cash,
            "pending_payments_total": pending_total,
            "projected_balance": round(balance - pending_total, 2),
            "pending_approvals": _rows(conn, "SELECT * FROM approvals WHERE status = 'pending' ORDER BY id"),
            "decided_approvals": _rows(conn, "SELECT * FROM approvals WHERE status != 'pending' ORDER BY id"),
            "drafts": _rows(conn, "SELECT * FROM drafts ORDER BY id"),
            "payments": _rows(conn, "SELECT * FROM payments ORDER BY id"),
        }


# ---------------------------------------------------------------- read tools (per-ticket checks)

def check_restock_path(sku: str, size: str, vendor_id: int) -> dict:
    """Check whether a SKU/size is in stock and, if not, whether a vendor can restock it.

    Returns on-hand quantity, the vendor's lead time and ETA (desk.date_today + lead_days),
    and any open invoices with that vendor. A vendor with an open invoice will not ship.
    """
    with _db() as conn:
        today = _today(conn)
        item = conn.execute(
            "SELECT sku, name, size, qty, location FROM inventory WHERE sku = ? AND size = ?",
            (sku, size),
        ).fetchone()
        if item is None:
            return {"error": f"No inventory row for sku={sku!r}, size={size!r}."}

        vendor = conn.execute(
            "SELECT id, name, specialty, lead_days FROM vendors WHERE id = ?", (vendor_id,)
        ).fetchone()
        if vendor is None:
            return {"error": f"No vendor with id={vendor_id}."}

        open_invoices = [
            {**dict(r), "days_overdue": max(0, _days_between(r["due_date"], today))}
            for r in conn.execute(
                "SELECT id, amount, due_date, status, description FROM invoices "
                "WHERE vendor_id = ? AND status = 'open'",
                (vendor_id,),
            )
        ]

    eta = date.fromordinal(date.fromisoformat(today).toordinal() + vendor["lead_days"])
    blocked = bool(open_invoices)
    return {
        "today": today,
        "item": dict(item),
        "in_stock": item["qty"] > 0,
        "vendor": dict(vendor),
        "open_invoices": open_invoices,
        "vendor_will_ship": not blocked,
        "eta_if_ordered_today": None if blocked else eta.isoformat(),
        "eta_once_invoices_cleared": eta.isoformat(),
        "note": (
            f"{vendor['name']} will not ship until {len(open_invoices)} open invoice(s) are paid."
            if blocked
            else f"{vendor['name']} can ship; ETA {eta.isoformat()}."
        ),
    }


def check_rent_and_cash(lease_id: int, account: str = "checking") -> dict:
    """Look up a lease's rent and due date and compare it to the cash balance.

    Reports days until rent is due (from desk.date_today), the current balance,
    total open vendor invoices, and whether paying the rent would go negative.
    Read-only: it never pays anything (payments require human approval).
    """
    with _db() as conn:
        today = _today(conn)
        lease = conn.execute(
            "SELECT id, space_name, landlord, monthly_rent, next_due, notes FROM leases WHERE id = ?",
            (lease_id,),
        ).fetchone()
        if lease is None:
            return {"error": f"No lease with id={lease_id}."}

        cash = conn.execute(
            "SELECT name, balance, date FROM cash_accounts WHERE name = ?", (account,)
        ).fetchone()
        if cash is None:
            return {"error": f"No cash account named {account!r}."}

        open_total = conn.execute(
            "SELECT COALESCE(SUM(amount), 0) AS total FROM invoices WHERE status = 'open'"
        ).fetchone()["total"]

    rent = lease["monthly_rent"]
    balance = cash["balance"]
    return {
        "today": today,
        "lease": dict(lease),
        "days_until_due": _days_between(today, lease["next_due"]),
        "cash_account": dict(cash),
        "can_cover_rent": balance >= rent,
        "balance_after_rent": round(balance - rent, 2),
        "open_invoices_total": open_total,
        "can_cover_rent_and_open_invoices": balance >= rent + open_total,
        "balance_after_rent_and_open_invoices": round(balance - rent - open_total, 2),
    }


def quote_bulk_order(sku: str, size: str, qty: int, discount_pct: float = 0.0) -> dict:
    """Price a bulk order from the pricing table and check stock for the requested size.

    Shows list-price total, the discounted total for an optional discount_pct, the
    unit-cost floor (never quote below unit_cost), and the on-hand shortfall.
    """
    if qty <= 0:
        return {"error": "qty must be positive."}
    if not 0 <= discount_pct < 100:
        return {"error": "discount_pct must be between 0 and 100."}

    with _db() as conn:
        price = conn.execute(
            "SELECT sku, unit_cost, list_price FROM pricing WHERE sku = ?", (sku,)
        ).fetchone()
        if price is None:
            return {"error": f"No pricing row for sku={sku!r}."}
        item = conn.execute(
            "SELECT name, size, qty, location FROM inventory WHERE sku = ? AND size = ?",
            (sku, size),
        ).fetchone()
        if item is None:
            return {"error": f"No inventory row for sku={sku!r}, size={size!r}."}

    unit_cost, list_price = price["unit_cost"], price["list_price"]
    unit_quote = round(list_price * (1 - discount_pct / 100), 2)
    max_discount_pct = round((1 - unit_cost / list_price) * 100, 2)
    shortfall = max(0, qty - item["qty"])
    return {
        "sku": sku,
        "name": item["name"],
        "size": size,
        "qty_requested": qty,
        "qty_on_hand": item["qty"],
        "shortfall": shortfall,
        "unit_cost": unit_cost,
        "list_price": list_price,
        "list_total": round(list_price * qty, 2),
        "discount_pct": discount_pct,
        "unit_quote": unit_quote,
        "quote_total": round(unit_quote * qty, 2),
        "margin_per_unit": round(unit_quote - unit_cost, 2),
        "below_cost": unit_quote < unit_cost,
        "max_discount_pct_at_cost": max_discount_pct,
        "restock_cost_for_shortfall": round(unit_cost * shortfall, 2),
    }


# ---------------------------------------------------------------- write tools (agents)

def update_ticket(ticket_id: int, author: str, note: str, status: str | None = None) -> dict:
    """Add a note to a ticket and optionally change its status.

    status: open | in_progress | waiting_on_approval | blocked | resolved.
    Only the Boss (or a human on the dashboard, author "human:<name>") may mark a ticket resolved.
    """
    if status is not None and status not in TICKET_STATUSES:
        return {"error": f"status must be one of {TICKET_STATUSES}."}
    if status == "resolved" and author != "boss" and not author.startswith("human:"):
        return {"error": "Only the Boss can mark a ticket resolved."}
    if not note.strip():
        return {"error": "note must not be empty."}
    with _db(write=True) as conn:
        if _row(conn, "SELECT id FROM tickets WHERE id = ?", ticket_id) is None:
            return {"error": f"No ticket with id={ticket_id}."}
        conn.execute("INSERT INTO ticket_notes (ticket_id, author, note, created_at) VALUES (?, ?, ?, ?)",
                     (ticket_id, author, note.strip(), _now()))
        if status:
            conn.execute("UPDATE tickets SET status = ? WHERE id = ?", (status, ticket_id))
        return {"ok": True, "ticket": _row(conn, "SELECT id, status FROM tickets WHERE id = ?", ticket_id)}


def request_payment_approval(
    kind: Literal["invoice", "rent"], ref_id: int, ticket_id: int, requested_by: str, reason: str
) -> dict:
    """Queue a payment for HUMAN approval. This does not move any money.

    kind="invoice": ref_id is invoices.id; amount and payee come from the invoice + vendor.
    kind="rent": ref_id is leases.id; amount is leases.monthly_rent, payee is the landlord.
    Refuses duplicates and amounts larger than the current cash balance; reports projected cash
    after every pending payment so the human sees the full picture.
    """
    with _db(write=True) as conn:
        if kind == "invoice":
            src = _row(conn, "SELECT i.*, v.name AS payee FROM invoices i JOIN vendors v ON v.id = i.vendor_id "
                             "WHERE i.id = ?", ref_id)
            if src is None:
                return {"error": f"No invoice with id={ref_id}."}
            if src["status"] != "open":
                return {"error": f"Invoice {ref_id} is '{src['status']}', not open; nothing to pay."}
            amount, payee, akind = src["amount"], src["payee"], "invoice_payment"
            details = f"Invoice #{ref_id} to {payee}: {src['description']} (due {src['due_date']})"
        elif kind == "rent":
            src = _row(conn, "SELECT * FROM leases WHERE id = ?", ref_id)
            if src is None:
                return {"error": f"No lease with id={ref_id}."}
            amount, payee, akind = src["monthly_rent"], src["landlord"], "rent_payment"
            details = f"Rent for {src['space_name']} to {payee} (due {src['next_due']})"
        else:
            return {"error": "kind must be 'invoice' or 'rent'."}

        dup = _row(conn, "SELECT id FROM approvals WHERE kind = ? AND ref_id = ? AND status = 'pending'", akind, ref_id)
        if dup:
            return {"error": f"Approval #{dup['id']} for this {kind} is already pending.", "approval_id": dup["id"]}

        balance = conn.execute("SELECT balance FROM cash_accounts WHERE name = 'checking'").fetchone()[0]
        if amount > balance:
            return {"error": f"${amount:,.2f} exceeds the ${balance:,.2f} checking balance; the pay tool would refuse."}
        pending_before = _pending_payments_total(conn)

        cur = conn.execute(
            "INSERT INTO approvals (ticket_id, kind, ref_id, payee, amount, details, requested_by, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (ticket_id, akind, ref_id, payee, amount, f"{details}. Reason: {reason}", requested_by, _now()),
        )
        projected = round(balance - pending_before - amount, 2)
        return {
            "ok": True,
            "approval_id": cur.lastrowid,
            "status": "pending human approval",
            "kind": akind,
            "payee": payee,
            "amount": amount,
            "checking_balance": balance,
            "projected_balance_if_all_pending_approved": projected,
            "warning": None if projected >= 0 else "Pending payments exceed cash; the human cannot approve all of them.",
        }


def request_price_override(
    ticket_id: int, sku: str, size: str, qty: int, discount_pct: float, requested_by: str, reason: str
) -> dict:
    """Queue a discounted bulk quote for HUMAN approval (no money moves).

    Refuses any discount that would price a unit below pricing.unit_cost.
    """
    q = quote_bulk_order(sku, size, qty, discount_pct)
    if "error" in q:
        return q
    if q["below_cost"]:
        return {"error": f"{discount_pct}% off prices below the ${q['unit_cost']:.2f} unit cost "
                         f"(max {q['max_discount_pct_at_cost']}%).", "quote": q}
    with _db(write=True) as conn:
        details = (f"{qty} x {sku} {size} at {discount_pct}% off: ${q['unit_quote']:.2f}/unit, "
                   f"${q['quote_total']:.2f} total (list ${q['list_total']:.2f}); "
                   f"{q['qty_on_hand']} on hand, {q['shortfall']} short. Reason: {reason}")
        cur = conn.execute(
            "INSERT INTO approvals (ticket_id, kind, ref_id, payee, amount, details, requested_by, created_at) "
            "VALUES (?, 'price_override', NULL, NULL, ?, ?, ?, ?)",
            (ticket_id, q["quote_total"], details, requested_by, _now()),
        )
        return {"ok": True, "approval_id": cur.lastrowid, "status": "pending human approval", "quote": q}


def draft_message(
    ticket_id: int,
    channel: Literal["email", "phone_script", "letter"],
    recipient: str,
    subject: str,
    body: str,
    author: str,
) -> dict:
    """Save a message to a customer, landlord or vendor as a DRAFT on the board. Never sent.

    A human reviews drafts on the dashboard; no email is sent and no call is placed.
    """
    if not body.strip():
        return {"error": "body must not be empty."}
    with _db(write=True) as conn:
        if _row(conn, "SELECT id FROM tickets WHERE id = ?", ticket_id) is None:
            return {"error": f"No ticket with id={ticket_id}."}
        cur = conn.execute(
            "INSERT INTO drafts (ticket_id, channel, recipient, subject, body, author, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (ticket_id, channel, recipient, subject, body.strip(), author, _now()),
        )
        return {"ok": True, "draft_id": cur.lastrowid, "status": "draft (not sent)"}


def draft_vendor_order(ticket_id: int, vendor_id: int, sku: str, size: str, qty: int, author: str) -> dict:
    """Draft a restock order to a vendor and queue the purchase for HUMAN approval.

    Nothing is sent and no money moves: the vendor is not contacted. Estimated cost =
    qty x pricing.unit_cost; ETA = desk.date_today + vendors.lead_days. The draft is marked
    'blocked' if the vendor has open invoices (vendors won't ship); the purchase approval can't
    be approved until those invoices are paid.
    """
    if qty <= 0:
        return {"error": "qty must be positive."}
    path = check_restock_path(sku, size, vendor_id)
    if "error" in path:
        return path
    with _db(write=True) as conn:
        price = _row(conn, "SELECT unit_cost FROM pricing WHERE sku = ?", sku)
        if price is None:
            return {"error": f"No pricing row for sku={sku!r}."}
        cost = round(price["unit_cost"] * qty, 2)
        balance = conn.execute("SELECT balance FROM cash_accounts WHERE name = 'checking'").fetchone()[0]
        projected = round(balance - _pending_payments_total(conn), 2)
        blocked = not path["vendor_will_ship"]
        v = path["vendor"]
        body = (f"Order {qty} x {path['item']['name']} ({sku}, size {size}) at ${price['unit_cost']:.2f}/unit, "
                f"est. ${cost:.2f}. Lead time {v['lead_days']} days; ETA {path['eta_once_invoices_cleared']} "
                f"if placed today ({path['today']}).")
        if blocked:
            ids = ", ".join(f"#{i['id']}" for i in path["open_invoices"])
            body += f" BLOCKED: {v['name']} will not ship until open invoice(s) {ids} are paid."
        cur = conn.execute(
            "INSERT INTO drafts (ticket_id, channel, recipient, subject, body, author, status, created_at) "
            "VALUES (?, 'vendor_order', ?, ?, ?, ?, ?, ?)",
            (ticket_id, v["name"], f"Restock {sku} {size} x{qty}", body, author,
             "blocked" if blocked else "draft", _now()),
        )
        draft_id = cur.lastrowid
        appr = conn.execute(
            "INSERT INTO approvals (ticket_id, kind, ref_id, payee, amount, details, requested_by, created_at) "
            "VALUES (?, 'vendor_purchase', ?, ?, ?, ?, ?, ?)",
            (ticket_id, draft_id, v["name"], cost, f"Draft #{draft_id}: {body}", author, _now()),
        )
        return {
            "ok": True,
            "draft_id": draft_id,
            "purchase_approval_id": appr.lastrowid,
            "status": "blocked (vendor has open invoices)" if blocked else "draft (not sent)",
            "vendor": v["name"],
            "estimated_cost": cost,
            "eta": path["eta_once_invoices_cleared"],
            "projected_balance_after_pending_payments": projected,
            "projected_balance_if_purchase_approved": round(projected - cost, 2),
            "cost_exceeds_projected_cash": cost > projected,
        }


# ---------------------------------------------------------------- human-only tools (dashboard)

def approve_request(approval_id: int, approver: str, note: str = "") -> dict:
    """HUMAN ONLY. Approve a pending request; for payments and purchases this is the pay tool.

    Payments/purchases: refuses if checking would go below $0; otherwise writes payments, deducts
    cash, and marks the invoice paid, moves the lease's next_due forward one month, or marks the
    vendor-order draft approved. Vendor purchases are refused while the vendor has open invoices.
    Never exposed to agents, and agent names are rejected as approvers.
    """
    if not approver.strip() or approver.strip().lower().replace(" ", "_") in AGENT_NAMES:
        return {"error": "approve_request needs a human approver name, not an agent."}
    with _db(write=True) as conn:
        a = _row(conn, "SELECT * FROM approvals WHERE id = ?", approval_id)
        if a is None:
            return {"error": f"No approval with id={approval_id}."}
        if a["status"] != "pending":
            return {"error": f"Approval #{approval_id} is already {a['status']}."}

        payment_id = None
        if a["kind"] in ("invoice_payment", "rent_payment", "vendor_purchase"):
            balance = conn.execute("SELECT balance FROM cash_accounts WHERE name = 'checking'").fetchone()[0]
            if a["amount"] > balance:
                return {"error": f"Refused: paying ${a['amount']:,.2f} from ${balance:,.2f} checking "
                                 "would make the balance negative.", "approval_id": approval_id}
            if a["kind"] == "invoice_payment":
                inv = _row(conn, "SELECT status FROM invoices WHERE id = ?", a["ref_id"])
                if inv is None or inv["status"] != "open":
                    return {"error": f"Invoice #{a['ref_id']} is no longer open."}
            if a["kind"] == "vendor_purchase":
                draft = _row(conn, "SELECT recipient FROM drafts WHERE id = ?", a["ref_id"])
                blockers = _rows(conn, "SELECT i.id FROM invoices i JOIN vendors v ON v.id = i.vendor_id "
                                       "WHERE v.name = ? AND i.status = 'open'", draft["recipient"] if draft else "")
                if blockers:
                    ids = ", ".join(f"#{b['id']}" for b in blockers)
                    return {"error": f"Refused: {a['payee']} won't ship while invoice(s) {ids} are open. "
                                     "Approve those first.", "approval_id": approval_id}
            today = _today(conn)
            cur = conn.execute(
                "INSERT INTO payments (kind, ref_id, amount, account, paid_at, approved_by) "
                "VALUES (?, ?, ?, 'checking', ?, ?)",
                ({"invoice_payment": "invoice", "rent_payment": "rent", "vendor_purchase": "purchase"}[a["kind"]],
                 a["ref_id"], a["amount"], today, approver.strip()),
            )
            payment_id = cur.lastrowid
            conn.execute("UPDATE cash_accounts SET balance = balance - ?, date = ? WHERE name = 'checking'",
                         (a["amount"], today))
            if a["kind"] == "invoice_payment":
                conn.execute("UPDATE invoices SET status = 'paid' WHERE id = ?", (a["ref_id"],))
            elif a["kind"] == "vendor_purchase":
                conn.execute("UPDATE drafts SET status = 'approved' WHERE id = ?", (a["ref_id"],))
            else:
                lease = _row(conn, "SELECT next_due FROM leases WHERE id = ?", a["ref_id"])
                conn.execute("UPDATE leases SET next_due = ? WHERE id = ?",
                             (_add_months(lease["next_due"], 1), a["ref_id"]))

        conn.execute(
            "UPDATE approvals SET status = 'approved', decided_by = ?, decided_at = ?, decision_note = ?, "
            "payment_id = ? WHERE id = ?",
            (approver.strip(), _now(), note, payment_id, approval_id),
        )
        new_balance = conn.execute("SELECT balance FROM cash_accounts WHERE name = 'checking'").fetchone()[0]
        return {"ok": True, "approval_id": approval_id, "kind": a["kind"], "payment_id": payment_id,
                "checking_balance": new_balance}


def reject_request(approval_id: int, approver: str, note: str = "") -> dict:
    """HUMAN ONLY. Reject a pending request; nothing is paid or changed."""
    if not approver.strip() or approver.strip().lower().replace(" ", "_") in AGENT_NAMES:
        return {"error": "reject_request needs a human approver name, not an agent."}
    with _db(write=True) as conn:
        a = _row(conn, "SELECT status FROM approvals WHERE id = ?", approval_id)
        if a is None:
            return {"error": f"No approval with id={approval_id}."}
        if a["status"] != "pending":
            return {"error": f"Approval #{approval_id} is already {a['status']}."}
        conn.execute("UPDATE approvals SET status = 'rejected', decided_by = ?, decided_at = ?, decision_note = ? "
                     "WHERE id = ?", (approver.strip(), _now(), note, approval_id))
        return {"ok": True, "approval_id": approval_id, "status": "rejected"}


for _fn in (
    list_tickets, list_open_tickets, get_ticket, list_vendors, get_board,
    check_restock_path, check_rent_and_cash, quote_bulk_order,
    update_ticket, request_payment_approval, request_price_override, draft_message, draft_vendor_order,
    approve_request, reject_request,
):
    mcp.tool(_fn)

_ensure_schema()


if __name__ == "__main__":
    mcp.run(show_banner=False, log_level="WARNING")
