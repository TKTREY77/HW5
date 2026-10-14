# Campus Customs: Multi-Agent Back Office (HW5)

A five-agent team (**Boss, Inventory, Accounting, Facilities, Customer Service**) that works the open tickets of Campus Customs, a small Yale apparel shop. Agents read and write the shop's SQLite database **only through an MCP server**. They prepare payments and draft messages, and a **human approves every payment** on a React dashboard.

```
React board (frontend/, :5173) ──► FastAPI (backend/main.py, :8000) ──► PydanticAI agent team (backend/team.py)
                                         │ human-only approve/reject           │  gpt-6-luna via Portkey
                                         ▼                                      ▼
                              MCP server (mcp_server/server.py, FastMCP, 15 tools) ──► data/campus_customs_new.db
```

**Rules the system enforces:** "today" is `desk.date_today` (2026-08-31); vendor lead times come from `vendors`; vendors with open invoices won't ship; every payment needs human approval and the pay tool refuses to go below $0; money only goes out; customer, landlord and vendor messages are drafts only (nothing is ever sent); every agent uses `gpt-6-luna` through Portkey.

---

## Project layout

```
AI_prompts.md        every prompt used to build this, by problem
requirements.txt     Python dependencies
.env.example         copy to .env and add PORTKEY_API_KEY (the real .env is gitignored)
.gitignore
.mcp.json            lets Claude Code call the MCP tools
README.md
data/
  campus_customs.db        original database (never modified)
  campus_customs_new.db    working copy the app uses (committed in its final, all-resolved state)
mcp_server/          FastMCP server (server.py) + README
backend/             FastAPI routes (main.py), agent team (team.py), prompts/, models.py, audit.py, reset_db.py
frontend/            React + Vite + TypeScript dashboard
output/
  harness.md           full reference: tables, MCP tools, agents, routes, dashboard, safety
  mcp_smoke.json       Claude Code smoke tests of all 15 MCP tools
  desk_tickets.html    per-ticket plan vs. actual run, Cash tab, Reflection tab (double-click to open)
  design.md            dashboard design and UX choices
  resolved_tickets.json  final status, outcome, agent contributions and approvals per ticket
  resolved_board.html  screenshots of the board for each resolved ticket (+ screenshots/)
  audit_trail.json     append-only log of every agent step and human decision
  github_url.txt       this repo's URL
```

---

## Setup (once)

Requirements: **Python 3.10+** (built on 3.12), **Node.js 20+** (built on 24) and a **Portkey API key** with access to `gpt-6-luna`.

```bash
git clone <this repo> && cd HW5

# Python environment (the .mcp.json file expects it at .venv/)
python3 -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# API key
cp .env.example .env                 # then edit .env and set PORTKEY_API_KEY=...

# Frontend dependencies
cd frontend && npm install && cd ..
```

> Notes: `requirements.txt` installs plain `uvicorn` on purpose. `uvicorn[standard]` pulls in uvloop, which hangs the MCP stdio subprocess at startup. `cryptography<49` is pinned because newer releases have no prebuilt wheels for Intel Macs.

---

## Run it

### 1. Copy the original DB to the working copy (clean run)

The committed `data/campus_customs_new.db` holds the **final state of our graded run** (all three tickets resolved, checking $160). For a fresh run, overwrite it with the original:

```bash
cp data/campus_customs.db data/campus_customs_new.db     # or: python backend/reset_db.py
```

Starting state: checking **$3,400.00**, tickets 101/102/103 **open**, invoice #501 **open**. The MCP server adds its board tables (`approvals`, `drafts`, `ticket_notes`) automatically on first use.

### 2. Start the MCP server

The backend **starts the MCP server for you** over stdio, so there's no separate step for a normal run. To run it on its own (it waits for an MCP client on stdin/stdout):

```bash
python mcp_server/server.py
```

To call the tools from **Claude Code**, open Claude Code in this folder. It reads `.mcp.json` and asks you to approve the `campus-customs` server. Then ask, e.g., "use the campus-customs tool check_rent_and_cash for lease 1". See `mcp_server/README.md` for all 15 tools.

### 3. Launch the FastAPI backend (terminal 1)

```bash
cd backend
uvicorn main:app --reload --port 8000        # with .venv activated
```

The API runs at http://localhost:8000, with interactive docs at http://localhost:8000/docs. Routes are listed in `output/harness.md`.

### 4. Start the React board (terminal 2)

```bash
cd frontend
npm run dev
```

Open **http://localhost:5173**, then:

1. Type your name in **Signing as** (top right). Every approval is signed with it.
2. Pick a ticket in the In-tray and click **Hand to the Boss →**. The Desk radio shows each hand-off, tool call and report live.
3. When the run finishes, review the slips in the **cash drawer** and click **Sign & pay** (or Reject). Checking updates immediately.
4. When a ticket's last slip is decided, it's stamped **RESOLVED** and moves to the Out-tray.

Run tickets one at a time: **101 → 102 → 103**.

### 5. Reset the DB before a full run

Do any of these before starting a full 101 → 102 → 103 run:

- click **Reset desk** in the board's top bar (asks for confirmation), or
- `curl -X POST http://localhost:8000/api/reset`, or
- `python backend/reset_db.py` (with the backend stopped, or it's fine while idle).

Reset copies `campus_customs.db` over `campus_customs_new.db`. **`output/audit_trail.json` is never cleared**: new runs are appended to it.

### Optional: run the team without the UI

```bash
cd backend
python team.py --ticket 101      # or --all
```

---

## What happened in our run

| Ticket | Team | Human approval | Cash |
|---|---|---|---|
| 101 tee (size S out of stock) | Boss → Inventory, Accounting, Customer Service | paid overdue invoice #501 to unblock the vendor | −$840.00 |
| 102 rent notice | Boss → Facilities → Accounting | paid $2,400 rent | −$2,400.00 |
| 103 bulk hoodie discount | Boss → Inventory, Customer Service | approved 10% discount quote | $0.00 |

Checking went from **$3,400.00 to $160.00**. The 12-hoodie restock ($264) was flagged as unaffordable rather than bought. Details are in `output/desk_tickets.html`, `output/resolved_tickets.json` and `output/resolved_board.html`.

## Safety, in short

- Agents can only **queue** payments; `approve_request` (the pay tool) is human-only, hidden from every agent, blocked again at call time, and refuses agent names and negative balances.
- Payment amounts come from the database, never from the model.
- There are no email, SMS or phone tools; all outbound messages are drafts.
- Each ticket run has a shared budget of 40 model calls, 60 tool calls and 250k tokens, with delegation depth ≤ 3 and no cycles.

Full details are in `output/harness.md`.
