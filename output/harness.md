# Campus Customs — Agent Harness Notes

Reference for the MCP server, the FastAPI agent team (Boss, Inventory, Accounting, Facilities, Customer Service), and the React dashboard.

**Contents:** [Database tables](#database-tables) · [Open tickets](#open-tickets-how-they-link) · [MCP tools](#mcp-tools-mcp_serverserverpy) · [Agent team](#agent-team-backendteampy-pydanticai) · [Safety](#safety--guardrails) · [API routes](#backend-routes-backendmainpy-fastapi) · [Dashboard](#frontend-dashboard-frontend-react--vite--typescript) · [Problem 9 results](#problem-9-results-real-run)

### Architecture

```
React dashboard (frontend/, :5173)
   │  fetch + polling (CORS: http://localhost:5173)
   ▼
FastAPI backend (backend/main.py, :8000) ──── human-only: approve_request / reject_request
   │  POST /api/tickets/{id}/run
   ▼
Agent team (backend/team.py, PydanticAI) ── Portkey ──► gpt-6-luna (Responses API)
   Boss ⇄ Inventory ⇄ Accounting ⇄ Facilities ⇄ Customer Service   (delegate tool, full connectivity)
   │  every DB read/write is an MCP tool call (stdio)        every step ──► output/audit_trail.json
   ▼
MCP server (mcp_server/server.py, FastMCP, 15 tools) ──► data/campus_customs_new.db (SQLite)
```

### How to run

```bash
pip install -r requirements.txt                                   # once, into .venv (Python 3.12)
cd backend && uvicorn main:app --reload --port 8000               # terminal 1
cd frontend && npm install && npm run dev                         # terminal 2 → http://localhost:5173
python backend/reset_db.py                                        # or the "Reset desk" button
```

### File map

| Path | What it is |
|---|---|
| `data/campus_customs.db` / `campus_customs_new.db` | pristine DB / working DB |
| `mcp_server/server.py`, `mcp_server/README.md` | MCP server (15 tools) and its docs |
| `.mcp.json` | Claude Code connection to the MCP server |
| `backend/team.py`, `models.py`, `audit.py`, `prompts/*.md` | the 5-agent PydanticAI team, data types, audit logger, one prompt per agent |
| `backend/main.py`, `reset_db.py` | FastAPI routes; DB reset |
| `frontend/` | React + Vite + TypeScript dashboard |
| `output/audit_trail.json` | append-only log of every agent step and human decision |
| `output/mcp_smoke.json` | Claude Code smoke tests of every MCP tool (21 tests) |
| `output/desk_tickets.html` | per-ticket plan (Expected) vs. real run (Actual), plus the Cash tab |
| `output/resolved_tickets.json`, `output/resolved_board.html` | Problem 9 results and dashboard screenshots |
| `output/design.md` | dashboard design rationale |

- **Source DB (pristine):** `data/campus_customs.db`. Never modified; copy it over the working DB to reset.
- **Working DB:** `data/campus_customs_new.db`. The MCP server and backend read/write this copy.
- **"Today":** `desk.date_today` = **2026-08-31**. Do not use the system clock.

---

## Database Tables

### `desk`
| Field | Type | Notes |
|---|---|---|
| `date_today` | TEXT | Simulated current date (`2026-08-31`) |
| `notes` | TEXT | Free-form desk notes (empty) |

**Why it matters:** Every agent anchors date math (due dates, overdue checks, vendor ETAs) to `date_today`, not the real clock.

### `tickets`
| Field | Type | Notes |
|---|---|---|
| `id` | INTEGER PK | Ticket number (101–103) |
| `type` | TEXT | `customer_order`, `rent_notice`, `price_override` |
| `requester` | TEXT | Customer, landlord, or org who raised it |
| `subject` | TEXT | Short title |
| `sku` | TEXT | → `inventory.sku` / `pricing.sku` (nullable) |
| `size` | TEXT | → `inventory.size` (nullable) |
| `qty` | INTEGER | Units requested (nullable) |
| `lease_id` | INTEGER FK | → `leases.id` (nullable) |
| `invoice_id` | INTEGER FK | → `invoices.id` (nullable) |
| `status` | TEXT | `open` (all three today) |
| `notes` | TEXT | Request details |
| `created_at` | TEXT | ISO timestamp with ET offset |

**Why it matters:** This is the work queue. The Boss reads open tickets and routes them by `type`, and the FK columns tell each specialist which rows to pull.

### `inventory`
| Field | Type | Notes |
|---|---|---|
| `sku` | TEXT | PK (with `size`) |
| `name` | TEXT | Product name |
| `size` | TEXT | `S/M/L/XL` or `OS` (one size) |
| `qty` | INTEGER | On-hand units |
| `location` | TEXT | Store aisle |

**Why it matters:** The Inventory agent checks stock by `(sku, size)` and spots shortages. Currently out of stock: `CC-TEE-WHITE` S (0) and `CC-MUG-CREST` OS (0).

### `pricing`
| Field | Type | Notes |
|---|---|---|
| `sku` | TEXT PK | → `inventory.sku` |
| `unit_cost` | REAL | Cost to Campus Customs |
| `list_price` | REAL | Retail price |

**Why it matters:** Supports quotes and discount decisions. Margin = `list_price − unit_cost` sets the floor for any price override (e.g., hoodie $58 list / $22 cost).

### `vendors`
| Field | Type | Notes |
|---|---|---|
| `id` | INTEGER PK | Vendor ID |
| `name` | TEXT | Bulldog Print Co / Elm City Gifts / QuickShip CT |
| `specialty` | TEXT | apparel reprint / mugs & small goods / local courier |
| `lead_days` | INTEGER | 5 / 3 / 1 |

**Why it matters:** Inventory picks the right supplier and computes ETA = `date_today + lead_days`. A vendor with an open invoice will not ship.

### `invoices`
| Field | Type | Notes |
|---|---|---|
| `id` | INTEGER PK | Invoice number |
| `vendor_id` | INTEGER FK | → `vendors.id` |
| `amount` | REAL | Amount owed |
| `due_date` | TEXT | Due date |
| `status` | TEXT | `open` / (paid once settled) |
| `description` | TEXT | What it was for |

**Why it matters:** Accounting tracks what's owed. Any `open` invoice blocks that vendor from shipping. Currently: **#501, Bulldog Print Co, $840, due 2026-08-28 (3 days overdue), "Rush reprint CC-TEE-WHITE S".**

### `leases`
| Field | Type | Notes |
|---|---|---|
| `id` | INTEGER PK | Lease ID |
| `space_name` | TEXT | Chapel Street shop |
| `landlord` | TEXT | Elm City Properties |
| `monthly_rent` | REAL | $2,400 |
| `next_due` | TEXT | 2026-09-02 |
| `notes` | TEXT | (empty) |

**Why it matters:** The Facilities agent owns rent. It confirms the amount and due date and asks Accounting to queue a payment for human approval.

### `cash_accounts`
| Field | Type | Notes |
|---|---|---|
| `name` | TEXT PK | `checking` |
| `balance` | REAL | $3,400.00 |
| `date` | TEXT | As-of date |

**Why it matters:** The pay tool must check this first and refuse any payment that would push the balance below $0. Money only goes out; there is no revenue inflow.

### `payments`
| Field | Type | Notes |
|---|---|---|
| `id` | INTEGER PK | Payment ID |
| `kind` | TEXT | e.g., `invoice` / `rent` |
| `ref_id` | INTEGER | → `invoices.id` or `leases.id` depending on `kind` |
| `amount` | REAL | Amount paid |
| `account` | TEXT | → `cash_accounts.name` |
| `paid_at` | TEXT | Timestamp |
| `approved_by` | TEXT | Human approver (required) |

**Why it matters:** Audit log of outgoing money (empty today). A row is written only after human approval, and `approved_by` proves a human signed off.

### Board tables (added by the MCP server on first start)

These three tables don't exist in the original DB. `mcp_server/server.py` creates them (`CREATE TABLE IF NOT EXISTS`) the first time it touches the working DB, and again after every reset.

### `approvals`
| Field | Type | Notes |
|---|---|---|
| `id` | INTEGER PK | Slip number shown on the dashboard |
| `ticket_id` | INTEGER FK | → `tickets.id` |
| `kind` | TEXT | `invoice_payment` / `rent_payment` / `vendor_purchase` / `price_override` |
| `ref_id` | INTEGER | → `invoices.id`, `leases.id` or `drafts.id` (purchase); NULL for price_override |
| `payee` | TEXT | Vendor or landlord (from the DB, not the model) |
| `amount` | REAL | Money out for payments/purchases; quote total for price_override |
| `details` | TEXT | Human-readable description + the agent's reason |
| `requested_by` | TEXT | Agent that queued it (stamped by the backend) |
| `status` | TEXT | `pending` / `approved` / `rejected` |
| `created_at`, `decided_by`, `decided_at`, `decision_note` | TEXT | Who decided and when (`decided_by` must be a human) |
| `payment_id` | INTEGER | → `payments.id` once paid |

**Why it matters:** The human approval queue. Agents can only insert `pending` rows. Only the human-only `approve_request` turns one into a payment.

### `drafts`
| Field | Type | Notes |
|---|---|---|
| `id` | INTEGER PK | Draft number |
| `ticket_id` | INTEGER FK | → `tickets.id` |
| `channel` | TEXT | `email` / `phone_script` / `letter` / `vendor_order` |
| `recipient`, `subject`, `body` | TEXT | The message |
| `author` | TEXT | Agent that wrote it |
| `status` | TEXT | `draft` / `blocked` (vendor has open invoices) / `approved` (purchase signed) |
| `created_at` | TEXT | Timestamp |

**Why it matters:** The outbox. Nothing is ever sent; customers, landlords and vendors are only ever written to here.

### `ticket_notes`
| Field | Type | Notes |
|---|---|---|
| `id` | INTEGER PK | Note number |
| `ticket_id` | INTEGER FK | → `tickets.id` |
| `author` | TEXT | Agent name, or `human:<name>` when the dashboard resolves a ticket |
| `note`, `created_at` | TEXT | What was found or done |

**Why it matters:** The working history on each ticket, so agents see what teammates already did and don't duplicate work.

---

## Open Tickets: How They Link

### Ticket 101: `customer_order`, Tauhid Zaman, "Bulldog tee" (CC-TEE-WHITE, S, qty 1)
- `inventory`: CC-TEE-WHITE S has **0** on hand (M 5, L 3, XL 2), so it can't ship today.
- `invoice_id = 501` → `invoices`: $840 open, **overdue**, owed to vendor 1. It's the rush reprint of this exact item.
- `vendors`: Bulldog Print Co (apparel reprint, **5 lead days**). It **won't ship while #501 is open**.
- **Path:** Accounting requests human approval to pay #501 ($840; cash $3,400 → $2,560). Once it's paid, Inventory reorders from Bulldog with ETA **2026-09-05** (8/31 + 5). Customer Service drafts an update to Tauhid (draft only) and can offer M as an alternative.
- Agents: **Inventory, Accounting, Customer Service**.

### Ticket 102: `rent_notice`, Elm City Properties, "Rent due"
- `lease_id = 1` → `leases`: Chapel Street shop, **$2,400 due 2026-09-02** (2 days out).
- `cash_accounts`: $3,400 covers it on its own.
- **Path:** Facilities verifies the lease and asks Accounting to queue a $2,400 rent payment for human approval (`payments.kind = rent`, `ref_id = 1`).
- Agents: **Facilities, Accounting**.

### Ticket 103: `price_override`, Yale AI Club, "Bulk hoodie discount" (CC-HOOD-NAVY, M, qty 20)
- `inventory`: CC-HOOD-NAVY M has **8** on hand, **12 short** (S 4, L 14, XL 6).
- `pricing`: list $58, cost $22. At list, 20 units = $1,160. Any discount must stay above $22/unit cost.
- `vendors`: restock comes from Bulldog Print Co (5 days), which is **also blocked by invoice #501**.
- **Path:** The Boss or a human decides on a discount. Inventory confirms stock and reorder timing. Customer Service drafts a quote reply (draft only). Since money only goes out, the discount doesn't create any cash inflow in the system.
- Agents: **Boss, Inventory, Customer Service**.

### Cross-ticket constraints
- **Cash:** paying #501 ($840) + rent ($2,400) = **$3,240 ≤ $3,400**, which leaves **$160**. Both can be paid, but only with that thin buffer. Any extra vendor reorder cost has to fit within what's left, or the pay tool refuses.
- **Invoice #501 is the bottleneck.** It blocks both Ticket 101 (tee S reprint) and Ticket 103 (hoodie M restock), since both need Bulldog.
- **Every payment needs human approval** through the dashboard. All customer/vendor messages stay as drafts on the board.

---

## MCP Tools (`mcp_server/server.py`)

The MCP server is the **only** path from the agents to `data/campus_customs_new.db`. There are no local Python tools that touch the database. "Today" always comes from `desk.date_today`. On first start the server adds three board tables to the working DB: `approvals` (human approval queue), `drafts` (unsent messages and vendor orders) and `ticket_notes`.

### Original three tools (Problem 3)

| Tool | Tables read | Unlocks ticket | Why it's the right tool for that ticket |
|---|---|---|---|
| `check_restock_path(sku, size, vendor_id)` | `inventory`, `vendors`, `invoices`, `desk` | **101** (Tauhid's size S tee) | It shows in one call that CC-TEE-WHITE S has 0 on hand, that Bulldog Print Co won't reprint while invoice #501 ($840, 3 days overdue) is open, and that the ETA becomes 2026-09-05 once it's paid, which is exactly what has to be resolved before Tauhid's order can ship. |
| `check_rent_and_cash(lease_id, account)` | `leases`, `cash_accounts`, `invoices`, `desk` | **102** (Elm City Properties rent) | It confirms the $2,400 Chapel Street rent is due in 2 days and that the $3,400 checking balance covers it, leaving $1,000, or just $160 if invoice #501 is also paid. That lets Accounting request a human-approved payment knowing it won't go negative. |
| `quote_bulk_order(sku, size, qty, discount_pct)` | `pricing`, `inventory` | **103** (Yale AI Club, 20 hoodies) | It prices 20 CC-HOOD-NAVY M at the $58 list ($1,160) or any proposed discount, flags the $22 cost floor (max ~62% off), and shows the 12-unit shortfall that would cost $264 to restock, so the Boss can decide on the discount with real margin and stock numbers. |

### All tools (14 in Problem 5, 15 since Problem 7)

| Tool | Type | Tables read | Tables written | Used by | Ticket(s) |
|---|---|---|---|---|---|
| `list_tickets()` | read | `tickets`, `desk` | — | dashboard only (Problem 7) | all |
| `list_open_tickets()` | read | `tickets`, `desk` | — | Boss | all |
| `get_ticket(ticket_id)` | read | `tickets`, `inventory`, `pricing`, `leases`, `invoices`, `vendors`, `ticket_notes`, `approvals`, `drafts`, `desk` | — | all five | all |
| `list_vendors()` | read | `vendors`, `invoices`, `desk` | — | Boss, Inventory, Accounting, Customer Service | 101, 103 |
| `get_board()` | read | `cash_accounts`, `approvals`, `drafts`, `payments`, `desk` | — | Boss, Accounting (+ dashboard) | all |
| `check_restock_path(sku, size, vendor_id)` | read | `inventory`, `vendors`, `invoices`, `desk` | — | Inventory, Customer Service | 101, 103 |
| `check_rent_and_cash(lease_id, account)` | read | `leases`, `cash_accounts`, `invoices`, `desk` | — | Boss, Accounting, Facilities | 102 |
| `quote_bulk_order(sku, size, qty, discount_pct)` | read | `pricing`, `inventory` | — | Boss, Inventory, Accounting, Customer Service | 103 |
| `update_ticket(ticket_id, note, status)` | write | `tickets` | `ticket_notes`, `tickets.status` | all five (only Boss, or a human via the dashboard, may resolve) | all |
| `request_payment_approval(kind, ref_id, ticket_id, reason)` | write (no money moves) | `invoices`, `vendors`, `leases`, `cash_accounts`, `approvals` | `approvals` | Accounting only | 101 (invoice #501), 102 (rent) |
| `request_price_override(ticket_id, sku, size, qty, discount_pct, reason)` | write (no money moves) | `pricing`, `inventory` | `approvals` | Boss only | 103 |
| `draft_message(ticket_id, channel, recipient, subject, body)` | write (never sent) | `tickets` | `drafts` | Facilities, Customer Service | 101, 102, 103 |
| `draft_vendor_order(ticket_id, vendor_id, sku, size, qty)` | write (never sent, no money moves) | `inventory`, `vendors`, `invoices`, `pricing`, `cash_accounts`, `approvals`, `desk` | `drafts`, `approvals` (`vendor_purchase`) | Inventory only | 101, 103 |
| `approve_request(approval_id, approver, note)` | **human only**, the pay tool (payments + purchases) | `approvals`, `cash_accounts`, `invoices`, `leases`, `drafts`, `desk` | `payments`, `cash_accounts`, `invoices.status`, `leases.next_due`, `drafts.status`, `approvals` | dashboard (no agent) | 101, 102, 103 |
| `reject_request(approval_id, approver, note)` | **human only** | `approvals` | `approvals` | dashboard (no agent) | 101, 102, 103 |

**What each new tool is for:**
- `list_open_tickets` / `get_ticket`: the Boss's triage queue. `get_ticket` follows every FK (`sku`, `lease_id`, `invoice_id`) so an agent gets the linked inventory, pricing, lease, invoice and vendor rows in one call, plus what the team already did.
- `list_vendors`: lets Inventory match a product to a vendor `specialty` and see which vendors are blocked by open invoices. The DB has no SKU→vendor table, so this avoids guessing.
- `get_board`: the cash picture across **all** pending payment requests (projected balance), so no agent queues payments in isolation.
- `request_payment_approval`: pulls amount and payee from the DB (agents can't type an amount), refuses duplicates and amounts above the balance, and returns the projected balance.
- `request_price_override`: refuses discounts below `unit_cost`; queues the rest for a human.
- `draft_message` / `draft_vendor_order`: outbound communication exists only as board drafts. Vendor orders are auto-marked `blocked` when the vendor has open invoices and report whether cost exceeds projected cash. Since Problem 7, each vendor order also queues a `vendor_purchase` approval (amount = qty × unit_cost); the human can't approve it until the vendor's invoices are paid.
- `list_tickets`: every ticket including resolved ones, for the dashboard's ticket list (not given to agents).
- `approve_request` / `reject_request`: the only tools that can move money or finalize a discount. Hidden from all agents.

---

## Agent Team (`backend/team.py`, PydanticAI)

All five agents run on **`gpt-6-luna` via Portkey** (`https://api.portkey.ai/v1`, OpenAI Responses API, `PORTKEY_API_KEY` from `.env`). The model name is a constant in code, not an env override, so no agent can run on a different model. Instructions live in `backend/prompts/<agent>.md`; output is a structured `AgentReport` (`backend/models.py`).

| Agent | Prompt | Owns | MCP tools (DB tables via those tools) | Delegates to |
|---|---|---|---|---|
| **Boss** | `prompts/boss.md` | Triage, routing, discount recommendation, ticket status, final report to human | `list_open_tickets`, `get_ticket`, `get_board`, `list_vendors`, `check_rent_and_cash`, `quote_bulk_order`, `request_price_override`, `update_ticket` (tickets, ticket_notes, approvals, drafts, cash_accounts, payments, vendors, invoices, leases, pricing, inventory) | any of the 4 |
| **Inventory** | `prompts/inventory.md` | Stock by SKU/size, vendor choice, ETA, restock drafts | `get_ticket`, `list_vendors`, `check_restock_path`, `quote_bulk_order`, `draft_vendor_order`, `update_ticket` (inventory, vendors, invoices, pricing, drafts, desk) | any of the other 4 |
| **Accounting** | `prompts/accounting.md` | Cash, invoices, queuing payments, margin checks | `get_ticket`, `get_board`, `list_vendors`, `check_rent_and_cash`, `quote_bulk_order`, `request_payment_approval`, `update_ticket` (cash_accounts, invoices, leases, approvals, payments, pricing) | any of the other 4 |
| **Facilities** | `prompts/facilities.md` | Lease, rent notices, landlord drafts | `get_ticket`, `check_rent_and_cash`, `draft_message`, `update_ticket` (leases, cash_accounts, drafts) | any of the other 4 |
| **Customer Service** | `prompts/customer_service.md` | Customer/student-group reply drafts | `get_ticket`, `check_restock_path`, `quote_bulk_order`, `list_vendors`, `draft_message`, `update_ticket` (inventory, pricing, vendors, drafts) | any of the other 4 |

**Delegation (full connectivity):** every agent has a `delegate(to, task)` tool that can reach any other agent. The sub-agent runs with its own prompt and tool set and returns its `AgentReport` as the tool result. Guardrails: an agent can't delegate to itself or to anyone already in the chain (no ping-pong loops), and depth is capped at 3 (`boss → a → b → c`).

**Typical routing:** 101 Boss → Inventory → Accounting (queue invoice #501) → Customer Service (draft). 102 Boss → Facilities (verify + landlord draft) → Accounting (queue rent). 103 Boss → Inventory (stock/restock) → Boss `request_price_override` → Customer Service (quote draft).

**Audit trail (`output/audit_trail.json`):** `backend/audit.py` appends one entry per step **as it happens**: `run_start`, `agent_start`, every `model_step` (text, requested tool calls, tokens), every MCP `tool_call` (args + trimmed result), `delegation`/`delegation_refused`, `tool_blocked`, `agent_end` (report + usage), `run_end`/`run_error`. The file is a JSON list that is never cleared; each append is an atomic rewrite (temp file + rename), and an unreadable file is set aside rather than deleted.

**Run it:** `python backend/team.py --ticket 101` or `--all`. Reset the working DB with `python backend/reset_db.py`.

---

## Safety & Guardrails

### Real money
- **Human approval for every payment, enforced in code.** Agents can only *queue* (`request_payment_approval`). The pay tool `approve_request` is in no agent's tool list, and `backend/team.py` blocks it again at call time (`tool_blocked` in the audit) even if a model tried to call it. The server also rejects agent names (`boss`, `accounting`, …) as the approver.
- **No negative balances.** `approve_request` refuses any payment larger than the current checking balance. `request_payment_approval` refuses requests above the balance and reports the projected balance after *all* pending payments, warning when the queue would overdraw.
- **Money only goes out.** No tool increases `cash_accounts.balance`; quotes and discounts never count as cash.
- **Amounts come from the DB, not the model.** Payment amounts and payees are read from `invoices`/`leases`; the model can't type a dollar figure into a payment.
- **No duplicates.** A second pending request for the same invoice or lease is refused (seen live: Accounting reused approval #1 instead of re-queuing).
- **Discount floor.** `request_price_override` refuses any price below `pricing.unit_cost`, and discounts still need human approval.
- **Identity can't be spoofed.** The backend overwrites `author`/`requested_by` with the agent that actually made the call.
- **Vendor block.** `draft_vendor_order` marks orders `blocked` while the vendor has open invoices.

### Real customers, vendors and landlords
- **Nothing is ever sent.** There is no email, SMS or phone tool anywhere. `draft_message` and `draft_vendor_order` only write to the `drafts` table, which the human reviews on the dashboard.
- Prompts forbid claiming a message was sent, promising dates not returned by a tool, presenting unapproved discounts as final, or exposing internal details (unpaid invoices, cash) to customers.
- Customer data stays minimal: only the requester name from the ticket; no invented contact details.

### Token and cost limits
- **Shared budget per ticket run** (all delegated agents draw from the same `RunUsage`): max **40 model requests**, **60 tool calls**, **250,000 total tokens**. Hitting a limit stops the run cleanly and logs `run_error` to the audit trail.
- **Per response:** `max_tokens = 4,000`, reasoning effort `medium`.
- **Delegation depth ≤ 3** and no cycles, so agents can't bounce work back and forth indefinitely.
- **Trimmed audit entries:** long tool results are cut to 600 characters so the log stays small.
- **Observed cost (Problem 9 real runs):** 101 = 44,978 tokens / 18 requests; 102 = 42,448 / 17; 103 = 42,175 / 15. All three tickets took **129,601 tokens** total, every run well under the 250k / 40-request caps.

### Human on the dashboard
- **A signature on every decision.** The dashboard sends the "Signing as" name with each approve/reject; it is stored as `approvals.decided_by` and `payments.approved_by`. Agent names are refused.
- **No decisions mid-run.** Approve, reject and reset return 409 while the team is working, so cash never changes under an agent's feet. Only one team run at a time.
- **Resolving requires the human.** A ticket resolves only when the Boss resolves it, or when the human has decided every slip on it (`author = human:<name>`). Agents can't fake the `human:` prefix because the backend overwrites their identity.
- **Visible impact before signing.** Each slip shows "Checking after signing". Slips that would overdraw are disabled, and vendor purchases warn when the vendor is still blocked.
- **Reset is confirmed.** "Reset desk" asks first and says exactly what is cleared; the audit trail is never cleared.

### Data safety
- The pristine `data/campus_customs.db` is never opened by the server; `backend/reset_db.py` restores the working copy from it.
- Read tools open SQLite in read-only mode; only the write tools open a writable connection.
- `PORTKEY_API_KEY` is read from `.env` only and never logged or written.

---

## Backend Routes (`backend/main.py`, FastAPI)

Start from `backend/` with `uvicorn main:app --reload --port 8000` → http://localhost:8000 (interactive docs at `/docs`). Every DB read/write goes through the MCP server via one stdio client held for the app's lifetime; CORS allows any `localhost` port for the React dev server.

- `GET /api/health`: liveness check, the model in use (`gpt-6-luna`), and the id of any run in progress.
- `GET /api/tickets`: all tickets (101–103) with `status`, an `is_open` flag (open vs. resolved) and each ticket's latest run.
- `GET /api/tickets/{ticket_id}`: one ticket with its linked rows, notes, approvals and drafts (MCP `get_ticket`).
- `GET /api/tickets/{ticket_id}/summary`: per-agent recap of the ticket's latest run (each agent's report, tools used with counts, hand-offs, token usage) for the dashboard's Team recap.
- `POST /api/tickets/{ticket_id}/run`: starts the agent team (Boss first) on that ticket in the background and returns a `run_id` (202); 409 if a run is already going.
- `GET /api/runs`: every run started in this server session with its status (`queued`/`running`/`done`/`error`).
- `GET /api/runs/{run_id}`: one run's status and, when done, the Boss's final `AgentReport` plus token usage.
- `GET /api/events?since=&limit=&run_id=&ticket_id=`: recent audit-trail events (agent statements, delegations, tool calls) with a `seq` cursor, so the dashboard polls only what's new.
- `GET /api/board`: the approval board: pending and decided approvals, drafts, payments, balance and projected balance.
- `POST /api/approvals/{approval_id}/approve`: **human click**: body `{approver, note}`; runs the human-only `approve_request`, the only place cash changes (invoice/rent payment or vendor purchase). Refuses agent names, negative balances and blocked vendors; logged as `human_decision`. If it was the ticket's last pending request, the ticket is marked **resolved** (`author = human:<name>`).
- `POST /api/approvals/{approval_id}/reject`: human click to reject a pending request; nothing is paid; logged as `human_decision`; also resolves the ticket if nothing else is pending.
- `GET /api/cash`: current `cash_accounts` (checking balance), pending payment total, projected balance, and the payments made.
- `POST /api/reset`: copies the pristine `data/campus_customs.db` over `data/campus_customs_new.db` for a fresh run (refused while a run is active); the audit trail is kept and gets a `db_reset` entry.

**Notes:**
- **One run at a time:** a single team run at a time keeps cash decisions and the token budget unambiguous. Approvals and reset are also refused while the agents are mid-run.
- **No uvloop:** `uvicorn[standard]` is deliberately not used. Its uvloop event loop hung the MCP stdio subprocess at startup, so `requirements.txt` installs plain `uvicorn` + `watchfiles` (for `--reload`).

---

## Frontend Dashboard (`frontend/`, React + Vite + TypeScript)

`cd frontend && npm install && npm run dev` → http://localhost:5173, calling the backend at http://localhost:8000 (backend CORS allows `http://localhost:5173`). Design rationale: `output/design.md`.

- **Layout:** In-tray/Out-tray of tickets (left) → case file with facts, a 5-desk team floor, live "Desk radio" feed, team recap and outbox (center) → cash drawer with signature slips and a receipt tape (right).
- **Live updates:** a single polling loop (`src/useDesk.ts`) refreshes tickets, board, cash, runs and incremental events (`/api/events?since=`) every 1.5 s during a run and every 5 s when idle.
- **Approvals:** the human enters their name once ("Signing as"); each slip shows the cash impact before signing; the till display counts down after a payment.
- **Resolved:** when the human decides a ticket's last request, the backend resolves it and the card gets a RESOLVED stamp and moves to the Out-tray.
- **Verified live (scratch DB):** ticket 101 run → Boss → Inventory, Accounting, Customer Service (Facilities not needed, as planned); signed slip #1 → checking $3,400 → $2,560; ticket 101 → resolved; 51k tokens.

### Dashboard layout in detail

| Zone | Component | Shows | Backed by |
|---|---|---|---|
| Top bar | `TopBar.tsx` | brand, **desk calendar** (desk.date_today), **checking till** (animated), "Signing as" signature field, online light, Reset desk | `/api/board`, `/api/health`, `/api/reset` |
| Left | `TicketTray.tsx` | **In-tray** (open) and **Out-tray** (resolved, with RESOLVED stamp) paper cards; status pill, "✍ N to sign", "Team working" pulse | `/api/tickets`, `/api/board` |
| Center top | `CaseFile.tsx` | ticket header, notes, **Hand to the Boss →**, run cost; fact cards: shelf sizes (requested outlined, zeros red), pricing + cost floor, linked invoice/lease | `/api/tickets/{id}`, `POST /api/tickets/{id}/run` |
| Center | team floor (`CaseFile.tsx`) | 5 agent desks: *on it* / *waiting on hand-off* / *✓ reported back* / *standing by* / *not needed* | `/api/events` |
| Center left | `ActivityFeed.tsx` | **Desk radio**: hand-offs (from → to + task), plain-English tool lines (click for args/result), agent reports, human signatures, run dividers; LIVE + follow | `/api/events?since=` |
| Center right | `Recap` (in `CaseFile.tsx`), `Outbox.tsx` | per-agent recap cards (summary, hand-offs, tool chips with counts); "sign here" callout; drafts as envelopes stamped *Draft · not sent* / *Blocked* | `/api/tickets/{id}/summary`, `/api/tickets/{id}` |
| Right | `CashDrawer.tsx` | balance, pending meter, "If you sign everything", **Sign here** slips (Reject / Sign & pay), **receipt tape**, signed/rejected history | `/api/board`, `POST /api/approvals/{id}/approve\|reject` |

Agent colors and glyphs: Boss ★ navy · Inventory ▦ teal · Accounting $ amber · Facilities ⌂ violet · Customer Service ✉ rose · Human ✍ gold. Full rationale is in `output/design.md`.

---

## Problem 9 Results (real run)

Reset `data/campus_customs_new.db` → starting checking **$3,400.00**. Ran 101 → 102 → 103 from the dashboard (all appended live to `output/audit_trail.json`: 133 entries), then the human (Teddy) signed all three slips.

| Ticket | Agents (delegations) | Human approval | Cash change | Final status |
|---|---|---|---|---|
| 101 tee | Boss → Inventory, Accounting, Customer Service | #1 invoice #501 → payment #1 | **−$840.00** | resolved |
| 102 rent | Boss → Facilities → Accounting; Boss → Accounting (no duplicate) | #2 rent lease 1 → payment #2 | **−$2,400.00** | resolved |
| 103 hoodies | Boss → Inventory, Customer Service; Boss queued the 10% discount | #3 price override (quote, $1,044) | **$0.00** | resolved |

Ending checking **$160.00** = `cash_accounts.checking`. The 12-hoodie restock ($264) was not bought: it would overdraw by $104, and the Boss flagged it as a follow-up. Details: `output/resolved_tickets.json`, `output/desk_tickets.html` (Actual + Cash tabs), `output/resolved_board.html` (screenshots).

