# Campus Customs Desk: Design & UI/UX Choices

The dashboard (`frontend/`, React + Vite + TypeScript, `npm run dev` → http://localhost:5173) is designed as **the shop owner's back-office desk**: tickets sit in an in-tray, the selected ticket opens as a case file, the five agents have their own desks on a "team floor", and money lives in a cash drawer where nothing leaves without your signature. The metaphor isn't decoration. Each physical object maps to a real rule of the system, so the interface teaches the rules without a manual.

---

## 1. Layout: three zones, left to right = intake → work → money

```
┌──────────────────────────── top bar ───────────────────────────────────────┐
│ CC Campus Customs   [AUG 31 Monday]  [CHECKING $3,400.00]  Signing as ____  │
├──────────────┬───────────────────────────────────────────┬─────────────────┤
│  IN-TRAY     │  CASE FILE · Ticket #101                   │  CASH DRAWER    │
│  #101 tee    │  title · requester · "notes" · [Hand to   │  $3,400.00      │
│  #102 rent   │                                Boss →]     │  meter, pending │
│  #103 hoodie │  facts: shelf sizes · pricing · invoice    │  projected      │
│              │  TEAM FLOOR: 5 agent desks (live state)    │  SIGN HERE      │
│  OUT-TRAY    │  ┌ Desk radio (live feed) ┐ ┌ Team recap ┐ │  slips…         │
│  #102 ▣ RESOLVED │                      │ │ Outbox      │ │  RECEIPT TAPE   │
└──────────────┴───────────────────────────────────────────┴─────────────────┘
```

- **Left: In-tray / Out-tray.** All three tickets as paper cards, each with number, type icon, subject, requester and a status pill. Cards are slightly tilted like papers on a desk and straighten on hover or selection. Open tickets stay in the **In-tray**; resolved ones move to the **Out-tray** with a stamp. A "✍ 2 to sign" pill tells you which tickets are waiting on *you*, not the agents.
- **Center: Case file.** The selected ticket opens as a manila folder (with a folder tab). The top holds the facts the agents will use, pulled from the DB: shelf stock by size (with the requested size outlined and zeros in red), pricing and cost floor, the linked invoice or lease. Then the primary action, **"Hand to the Boss →"**. Below that:
  - **Team floor:** five desks showing who is working right now.
  - **Desk radio:** the live activity feed.
  - **Team recap:** one card per agent summarizing what it did.
  - **Outbox:** the drafts the team wrote.
- **Right: Cash drawer.** The checking balance, a meter of how much of it is spoken for, the projected balance if you sign everything, the **Sign here** approval slips, and a **receipt tape** of payments.

The reading order matches the work order: a ticket comes in (left), the team works it (center), you sign off on money (right). On narrower screens the cash drawer moves under the workspace, and on mobile everything stacks.

## 2. Telling the five agents apart

Each agent has a fixed **ink color, tint, glyph and role line**, used consistently on its desk, its feed bubbles, its recap card, its slips and drafts:

| Agent | Glyph | Ink | Why |
|---|---|---|---|
| Boss | ★ | navy | the manager; matches the app chrome, reads as "in charge" |
| Inventory | ▦ | teal | shelves/boxes; calm, operational |
| Accounting | $ | amber | money, but not "green = good"; a cautious color for the people who guard cash |
| Facilities | ⌂ | violet | the building/lease, clearly separate from the store floor |
| Customer Service | ✉ | rose | warm, people-facing; the envelope matches the drafts it writes |
| You (human) | ✍ | gold on navy | the signature pen; you're visually different from every agent |

Color is never the only signal: every badge also has a glyph and (where space allows) a name, so the roster works for color-blind users and in grayscale.

**Team floor states** make delegation visible at a glance:
- **On it:** lifted card, colored outline, pulsing dot. This is the agent currently holding the work, i.e. the deepest one that has started and not yet reported back.
- **Waiting on hand-off:** tinted. It delegated and is waiting for an answer.
- **✓ Reported back:** done this run.
- **Standing by / not needed:** faded. This is deliberate: on ticket 102, Inventory and Customer Service stay faded, which shows the Boss *didn't* blanket-call everyone (the Problem 6 plan).

## 3. The live feed ("Desk radio")

The feed polls `/api/events?since=<cursor>` every 1.5 s while the team works (5 s when idle), so it only ever downloads new lines. It translates audit events into a conversation:
- **Hand-offs:** `Boss → Inventory` with both badges and a dashed bubble holding the actual task text. Delegation reads like passing a note across the desk.
- **Tool calls:** one quiet line in plain English ("Checked stock & restock path") plus the real tool name in mono, e.g. `check_restock_path`. Click it to expand the exact arguments and the MCP result. Plain English is for the owner; the raw detail is there for auditing.
- **Reports:** when an agent finishes, a solid-bordered bubble shows its summary, status and a "✍ needs you" list.
- **Your decisions:** your signature appears in the feed in handwriting, so the human's actions are part of the same timeline.
- **Run dividers:** for start and finish (with token count), plus blocked/refused actions in amber.

A "● LIVE" tag and a typing indicator show the team is still thinking, and **follow** auto-scrolls (untick it to read back without being yanked down).

## 4. Summaries of each agent's actions

**Team recap** (`GET /api/tickets/{id}/summary`) shows one card per agent that took part in the latest run. Each card has a colored left edge, the agent's own 2–4 sentence report, who it handed off to, and chips for every MCP tool it used with counts (e.g. `check_rent_and_cash ×2`). It refreshes live during the run, so it doubles as a scoreboard. After the run the case header also shows the run's cost: model calls, tool calls and total tokens.

## 5. Representing cash

Cash is treated as the most important, most protected number on the screen:
- **Always visible:** the checking balance sits in a "till" display in the top bar on every view, and again large in the cash drawer.
- **It moves when money moves:** after you sign a payment the balance **counts down** to the new value and flashes coral, like a till. You *see* $840 leave rather than noticing a number changed.
- **Pending vs. projected:** the drawer shows what's waiting for your signature (−$X) and **"If you sign everything"**. That line turns gold when it gets tight (< $300) and red if it would go negative. The meter bar shows how much of today's cash is already spoken for. This is where the case's central tension (rent + invoice #501 leave only $160, less than the $264 hoodie restock) becomes obvious.
- **Slips show their impact before you sign:** each payment slip states "Checking after signing: $X". If that would be negative, the Sign button is disabled and the slip says the till will refuse. The backend refuses it anyway.
- **Receipt tape:** payments print as a monospace receipt (opening balance → each payment with the approver's signature → balance), with a torn edge.
- A small note reminds you that money only goes out; sales never top up the drawer.

## 6. Human approval as "signing a slip"

- **Who signs:** you type your name once in **Signing as** (top bar, saved locally). It renders in handwriting on every slip's signature line. Every approve call sends that name, the backend rejects agent names, and the name is written to `payments.approved_by`.
- **What a slip shows:** slip number, ticket, the agent that prepared it (badge), what it is ("Pay vendor invoice", "Pay rent", "Approve restock purchase", "Approve discount quote"), the amount in red for money out or navy for quotes, payee, details and impact.
- **Guardrails you can see:**
  - A vendor-purchase slip warns "Pay slip #N first: Bulldog won't ship while that invoice is open".
  - Buttons are disabled while the team is mid-run or when no signer name is set, with tooltips explaining why.
  - Slips for the selected ticket float to the top and are outlined.
- **Feedback:** every decision gives a toast ("Signed slip #1. Checking is now $2,560.00") and a feed entry. Decided slips move to a signed/rejected history under the tape.

## 7. Resolved tickets

A ticket resolves when the team has worked it and **you have decided every request on it**. The backend marks it resolved after your last signature or rejection, or the Boss can resolve it directly if nothing needs a human. When that happens:
- the card gets a red **RESOLVED rubber stamp** that thumps down with a short scale-in animation, and moves to the **Out-tray**;
- its accent edge turns green and the text fades back, like a filed paper;
- the status pill turns green, a toast confirms it, and "Hand to the Boss" is disabled.

Statuses on the way there read like a desk too: *Open → Team working (pulsing) → Needs your signature → Resolved*.

## 8. Drafts: the outbox

Every message the agents write appears as an **airmail-striped envelope** with a stamp label: **Draft · not sent**, **Blocked** (a vendor order held up by an open invoice) or **Purchase signed**. Click the subject to read the body; **Copy text** puts it on the clipboard for a human to send. Nothing in the UI can send an email or place a call, which matches the rule that drafts stay on the board.

## 9. Creative touches that make it pleasant

- **Desk calendar** showing the *desk date* (Mon, Aug 31 2026), not today's real date, a quiet reminder that the agents live in `desk.date_today`.
- **Paper physics:** slightly tilted tickets, a manila folder tab, perforated slip tops, torn receipt tape, linen desk texture.
- **Rubber stamps** for resolved tickets and drafts; **handwritten signatures**; a **counting till** for cash.
- **Team floor** with "on it" pulses, so a multi-agent run feels like watching a small office work.
- **Plain-English tool lines** with one-click raw detail, friendly for the owner and complete for an auditor.
- **Toasts** for run start/finish, payments and resolutions; empty states that say what will appear ("Quiet desk…").
- **Offline banner** with the exact command to start the backend if it isn't running; a green/red status light in the top bar.
- **Reset desk** with a confirmation that says exactly what will be cleared (and that the audit trail is kept).

## 10. Practical choices

- **No UI framework, no external fonts or CDNs:** plain React + one CSS file with design tokens (`styles.css`). It loads instantly, works offline against localhost, and the look is fully custom. The handwriting uses system script fonts (Bradley Hand / Segoe Script) with a cursive fallback.
- **API:** `src/api.ts` calls `http://localhost:8000` directly (override with `VITE_API_BASE`); backend CORS allows `http://localhost:5173`.
- **One polling loop** (`useDesk.ts`) refreshes tickets, board, cash, runs and incremental events together, fast during runs and slow when idle, so every panel stays consistent with the others.
- **Accessibility:** color + glyph + text for every agent and status, real buttons for all actions, an `aria-live` toast region, and visible focus via the browser defaults.
