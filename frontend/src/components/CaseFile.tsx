import { useEffect, useMemo, useState } from 'react'
import { api } from '../api'
import { AGENT_META, AGENT_ORDER, TOOL_LABELS } from '../agents'
import { STATUS_LABEL, TICKET_KIND, money } from '../format'
import type { AgentEvent, AgentName, Board, Ticket, TicketDetail, TicketSummary } from '../types'
import ActivityFeed from './ActivityFeed'
import AgentBadge from './AgentBadge'
import Outbox from './Outbox'

interface Props {
  ticket: Ticket
  events: AgentEvent[]
  board: Board | null
  activeRun: string | null
  runningTicket: number | null
  version: number
  onRun: () => void
}

const SIZE_ORDER = ['XS', 'S', 'M', 'L', 'XL', 'XXL', 'OS']

type DeskState = 'working' | 'waiting' | 'done' | 'idle'

export default function CaseFile({ ticket, events, board, activeRun, runningTicket, version, onRun }: Props) {
  const [detail, setDetail] = useState<TicketDetail | null>(null)
  const [summary, setSummary] = useState<TicketSummary | null>(null)
  const runningHere = runningTicket === ticket.id
  const kind = TICKET_KIND[ticket.type] ?? { label: ticket.type, icon: '📄' }

  // Ticket file + recap: reload when the ticket changes, a run finishes, a slip is signed, or the board changes.
  const boardKey = board ? `${board.pending_approvals.length}-${board.drafts.length}-${board.payments.length}` : ''
  useEffect(() => {
    api.ticket(ticket.id).then(setDetail).catch(() => {})
    api.summary(ticket.id).then(setSummary).catch(() => {})
  }, [ticket.id, ticket.status, version, boardKey])

  // While the team is working this ticket, refresh the recap as new events arrive.
  const evCount = events.filter(e => e.ticket_id === ticket.id).length
  useEffect(() => {
    if (runningHere) api.summary(ticket.id).then(setSummary).catch(() => {})
  }, [evCount, runningHere, ticket.id])

  // Events for this ticket: agent events + your decisions on its slips.
  const ticketEvents = useMemo(() => events.filter(e => e.ticket_id === ticket.id || (e.event === 'db_reset')), [events, ticket.id])
  const latestRunId = useMemo(() => [...ticketEvents].reverse().find(e => e.event === 'run_start')?.run_id ?? null, [ticketEvents])

  // Who is at their desk right now (deepest agent that started and hasn't reported back).
  const deskStates = useMemo(() => {
    const states: Record<AgentName, DeskState> = { boss: 'idle', inventory: 'idle', accounting: 'idle', facilities: 'idle', customer_service: 'idle' }
    if (!latestRunId) return { states, current: null as AgentName | null }
    const stack: AgentName[] = []
    for (const e of ticketEvents) {
      if (e.run_id !== latestRunId || !e.agent) continue
      if (e.event === 'agent_start') { stack.push(e.agent); states[e.agent] = 'working' }
      if (e.event === 'agent_end') { stack.pop(); states[e.agent] = 'done' }
    }
    const current = runningHere ? stack[stack.length - 1] ?? null : null
    for (const a of stack) if (a !== current) states[a] = 'waiting'
    return { states, current }
  }, [ticketEvents, latestRunId, runningHere])

  const pendingHere = board?.pending_approvals.filter(a => a.ticket_id === ticket.id) ?? []
  const drafts = detail?.drafts ?? []
  const otherRunBusy = !!activeRun && !runningHere

  return (
    <section className="casefile">
      <div className="folder-tab">Case file · Ticket #{ticket.id}</div>
      <header className="case-head">
        <div>
          <div className="case-kind">{kind.icon} {kind.label} · from <b>{ticket.requester}</b></div>
          <h1 className="case-title">{ticket.subject}</h1>
          {ticket.notes && <p className="case-note">“{ticket.notes}”</p>}
        </div>
        <div className="case-actions">
          <span className={`pill big status-${ticket.status}`}>{runningHere ? 'Team working…' : STATUS_LABEL[ticket.status] ?? ticket.status}</span>
          <button className="btn primary run-btn" onClick={onRun} disabled={!!activeRun || !ticket.is_open}
            title={!ticket.is_open ? 'Ticket is resolved' : otherRunBusy ? 'The team is busy with another ticket' : 'The Boss reads the ticket and delegates'}>
            {runningHere ? <><span className="pulse light" /> Team is on it</> : summary?.run_id ? 'Run the team again' : 'Hand to the Boss →'}
          </button>
          {summary?.usage && !runningHere && (
            <span className="usage">{summary.usage.requests} model calls · {summary.usage.tool_calls} tool calls · {summary.usage.total_tokens.toLocaleString()} tokens</span>
          )}
        </div>
      </header>

      <Facts detail={detail} />

      <div className="floor">
        {AGENT_ORDER.map(a => {
          const st = deskStates.states[a]
          const m = AGENT_META[a]
          const isCurrent = deskStates.current === a
          return (
            <div key={a} className={`desk-seat ${st} ${isCurrent ? 'current' : ''}`} style={{ ['--ink' as string]: m.color, ['--tint' as string]: m.tint }}>
              <AgentBadge agent={a} size="lg" />
              <div className="seat-name">{m.label}</div>
              <div className="seat-state">
                {isCurrent ? <><span className="pulse" style={{ background: m.color }} /> on it</> :
                  st === 'waiting' ? 'waiting on hand-off' : st === 'done' ? '✓ reported back' : runningHere ? 'standing by' : latestRunId ? 'not needed' : m.role}
              </div>
            </div>
          )
        })}
      </div>

      <div className="case-grid">
        <ActivityFeed events={ticketEvents} running={runningHere} />
        <div className="case-side">
          <Recap summary={summary} running={runningHere} />
          {pendingHere.length > 0 && (
            <div className="sign-callout">✍ {pendingHere.length} slip{pendingHere.length > 1 ? 's' : ''} for this ticket in the cash drawer: {pendingHere.map(p => `#${p.id}`).join(', ')}</div>
          )}
          <Outbox drafts={drafts} />
        </div>
      </div>
    </section>
  )
}

function Facts({ detail }: { detail: TicketDetail | null }) {
  if (!detail) return <div className="facts muted">Opening the file…</div>
  const t = detail.ticket
  return (
    <div className="facts">
      {detail.inventory_all_sizes && (
        <div className="fact">
          <div className="fact-label">Shelf · {t.sku}</div>
          <div className="sizes">
            {[...detail.inventory_all_sizes].sort((a, b) => SIZE_ORDER.indexOf(a.size) - SIZE_ORDER.indexOf(b.size)).map(s => (
              <span key={s.size} className={`size ${s.size === t.size ? 'wanted' : ''} ${s.qty === 0 ? 'zero' : ''}`}>
                <b>{s.size}</b>{s.qty}
              </span>
            ))}
          </div>
          {t.qty != null && t.size && <div className="fact-sub">Wants {t.qty} × {t.size}</div>}
        </div>
      )}
      {detail.pricing && (
        <div className="fact">
          <div className="fact-label">Pricing</div>
          <div className="fact-value">{money(detail.pricing.list_price)} <small>list</small></div>
          <div className="fact-sub">cost {money(detail.pricing.unit_cost)} · floor for any discount</div>
        </div>
      )}
      {detail.invoice && (
        <div className={`fact ${detail.invoice.status === 'open' ? 'alert' : 'ok'}`}>
          <div className="fact-label">Invoice #{detail.invoice.id} · {detail.invoice_vendor?.name}</div>
          <div className="fact-value">{money(detail.invoice.amount)} <small>{detail.invoice.status}</small></div>
          <div className="fact-sub">due {detail.invoice.due_date} · {detail.invoice.description}</div>
        </div>
      )}
      {detail.lease && (
        <div className="fact">
          <div className="fact-label">Lease #{detail.lease.id} · {detail.lease.space_name}</div>
          <div className="fact-value">{money(detail.lease.monthly_rent)} <small>/ month</small></div>
          <div className="fact-sub">next due {detail.lease.next_due} · {detail.lease.landlord}</div>
        </div>
      )}
    </div>
  )
}

function Recap({ summary, running }: { summary: TicketSummary | null; running: boolean }) {
  if (!summary?.run_id) {
    return <div className="recap empty">No run yet. Hand the ticket to the Boss and each agent's recap lands here.</div>
  }
  const order = AGENT_ORDER.filter(a => summary.agents.some(x => x.agent === a))
  return (
    <div className="recap">
      <h3 className="side-title">Team recap {running && <span className="muted">(updating live)</span>}</h3>
      {order.map(name => {
        const r = summary.agents.find(x => x.agent === name)!
        const m = AGENT_META[name]
        return (
          <div key={name} className="recap-card" style={{ ['--ink' as string]: m.color, ['--tint' as string]: m.tint }}>
            <div className="recap-head">
              <AgentBadge agent={name} size="sm" withLabel />
              {r.delegated_to.length > 0 && <span className="handoffs">→ {r.delegated_to.map(d => AGENT_META[d]?.label ?? d).join(', ')}</span>}
            </div>
            <p className="recap-text">{r.summary ?? (running ? 'Working…' : 'No report.')}</p>
            {Object.keys(r.tools).length > 0 && (
              <div className="tool-chips">
                {Object.entries(r.tools).map(([tool, n]) => (
                  <span key={tool} className="tool-chip" title={TOOL_LABELS[tool] ?? tool}>{tool}{n > 1 ? ` ×${n}` : ''}</span>
                ))}
              </div>
            )}
          </div>
        )
      })}
    </div>
  )
}
