# Campus Customs MCP Server

A [FastMCP](https://gofastmcp.com) server that is the **only** way the Campus Customs agent team (Boss, Inventory, Accounting, Facilities, Customer Service) reads or writes the store's database. Agents can look things up, queue requests for human approval, and save drafts. They can never pay, send a message, or contact a vendor. Payments happen only through the human-only `approve_request` tool on the dashboard.

**Database:** `data/campus_customs_new.db`, the working copy of the pristine `data/campus_customs.db` (reset with `python backend/reset_db.py`). Read tools open it read-only. "Today" always comes from `desk.date_today` (2026-08-31), not the system clock. On first start the server adds three board tables: `approvals`, `drafts`, `ticket_notes`. Set `CAMPUS_CUSTOMS_DB` to point it at a scratch copy for testing.

## Tools (15)

### Read
| Tool | Reads | What it returns |
|---|---|---|
| `list_tickets()` | `tickets`, `desk` | Every ticket with its status (dashboard) |
| `list_open_tickets()` | `tickets`, `desk` | Every unresolved ticket, oldest first |
| `get_ticket(ticket_id)` | `tickets` + linked `inventory`, `pricing`, `leases`, `invoices`, `vendors`; `ticket_notes`, `approvals`, `drafts` | One ticket with every row it links to and the team's work so far |
| `list_vendors()` | `vendors`, `invoices` | Each vendor's specialty, lead_days, open invoices, and whether it will ship |
| `get_board()` | `cash_accounts`, `approvals`, `drafts`, `payments` | The approval board: pending/decided requests, drafts, payments, balance and projected balance |
| `check_restock_path(sku, size, vendor_id)` | `inventory`, `vendors`, `invoices`, `desk` | On-hand qty, ETA (today + lead_days), blocking invoices (ticket 101) |
| `check_rent_and_cash(lease_id, account="checking")` | `leases`, `cash_accounts`, `invoices`, `desk` | Rent, days until due, and whether cash covers rent and open invoices (ticket 102) |
| `quote_bulk_order(sku, size, qty, discount_pct=0)` | `pricing`, `inventory` | List/discounted totals, cost floor, max discount, shortfall, restock cost (ticket 103) |

### Write (agents; no money moves, nothing is sent)
| Tool | Writes | Guardrails |
|---|---|---|
| `update_ticket(ticket_id, author, note, status=None)` | `ticket_notes`, `tickets.status` | Only `boss` may set `resolved` |
| `request_payment_approval(kind, ref_id, ticket_id, requested_by, reason)` | `approvals` | Amount and payee from `invoices`/`leases`; refuses duplicates and amounts above the balance; reports projected cash |
| `request_price_override(ticket_id, sku, size, qty, discount_pct, requested_by, reason)` | `approvals` | Refuses prices below `unit_cost` |
| `draft_message(ticket_id, channel, recipient, subject, body, author)` | `drafts` | Draft only; never sent |
| `draft_vendor_order(ticket_id, vendor_id, sku, size, qty, author)` | `drafts`, `approvals` | Draft only; marked `blocked` if the vendor has open invoices; queues a `vendor_purchase` approval (qty × unit_cost); flags cost above projected cash |

### Human only (dashboard; hidden from and blocked for every agent)
| Tool | Writes | Guardrails |
|---|---|---|
| `approve_request(approval_id, approver, note="")` | `payments`, `cash_accounts`, `invoices.status`, `leases.next_due`, `drafts.status`, `approvals` | **The pay tool** (invoice, rent, vendor purchase). Refuses agent names as approver; refuses if cash would go below $0; refuses purchases from vendors with open invoices; money only goes out |
| `reject_request(approval_id, approver, note="")` | `approvals` | Human approver required |

## Run

```bash
pip install -r requirements.txt
python mcp_server/server.py
```

Claude Code connects through `.mcp.json` at the project root; the agent team (`backend/team.py`) and the FastAPI backend (`backend/main.py`, which alone calls the human-only tools) start it over stdio.
