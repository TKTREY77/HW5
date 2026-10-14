import { STATUS_LABEL, TICKET_KIND } from '../format'
import type { Board, Ticket } from '../types'

interface Props {
  tickets: Ticket[]
  selected: number | null
  onSelect: (id: number) => void
  runningTicket: number | null
  board: Board | null
}

export default function TicketTray({ tickets, selected, onSelect, runningTicket, board }: Props) {
  const open = tickets.filter(t => t.is_open)
  const done = tickets.filter(t => !t.is_open)
  const pendingFor = (id: number) => board?.pending_approvals.filter(a => a.ticket_id === id).length ?? 0

  const card = (t: Ticket, i: number) => {
    const kind = TICKET_KIND[t.type] ?? { label: t.type, icon: '📄' }
    const pending = pendingFor(t.id)
    return (
      <button
        key={t.id}
        className={`ticket-card ${selected === t.id ? 'selected' : ''} ${t.is_open ? '' : 'is-resolved'}`}
        style={{ ['--tilt' as string]: `${[-0.6, 0.5, -0.3][i % 3]}deg` }}
        onClick={() => onSelect(t.id)}
      >
        <div className="ticket-top">
          <span className="ticket-no">#{t.id}</span>
          <span className="ticket-kind">{kind.icon} {kind.label}</span>
        </div>
        <div className="ticket-subject">{t.subject}</div>
        <div className="ticket-from">from {t.requester}</div>
        <div className="ticket-foot">
          {runningTicket === t.id ? (
            <span className="pill working"><span className="pulse" /> Team working</span>
          ) : (
            <span className={`pill status-${t.status}`}>{STATUS_LABEL[t.status] ?? t.status}</span>
          )}
          {pending > 0 && <span className="pill sign">✍ {pending} to sign</span>}
        </div>
        {!t.is_open && <div className="stamp" key={`stamp-${t.status}`}>Resolved</div>}
      </button>
    )
  }

  return (
    <aside className="tray">
      <div className="tray-section">
        <h2 className="tray-title">In-tray <span className="count">{open.length}</span></h2>
        {open.length === 0 && <p className="tray-empty">Nothing waiting. Nice work.</p>}
        {open.map(card)}
      </div>
      {done.length > 0 && (
        <div className="tray-section out">
          <h2 className="tray-title">Out-tray <span className="count">{done.length}</span></h2>
          {done.map(card)}
        </div>
      )}
    </aside>
  )
}
