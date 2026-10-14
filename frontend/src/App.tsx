import { useEffect, useMemo, useState } from 'react'
import { useDesk } from './useDesk'
import TopBar from './components/TopBar'
import TicketTray from './components/TicketTray'
import CaseFile from './components/CaseFile'
import CashDrawer from './components/CashDrawer'
import Toasts from './components/Toasts'

export default function App() {
  const desk = useDesk()
  const [selected, setSelected] = useState<number | null>(null)
  const [signer, setSigner] = useState(() => localStorage.getItem('cc-signer') ?? '')

  useEffect(() => { localStorage.setItem('cc-signer', signer) }, [signer])
  useEffect(() => {
    if (selected == null && desk.tickets.length) setSelected(desk.tickets[0].id)
  }, [desk.tickets, selected])

  const ticket = useMemo(() => desk.tickets.find(t => t.id === selected) ?? null, [desk.tickets, selected])
  const runningTicket = desk.runs.find(r => r.run_id === desk.activeRun)?.ticket_id ?? null

  return (
    <div className="desk">
      <TopBar
        today={desk.today}
        balance={desk.board?.cash_accounts.find(a => a.name === 'checking')?.balance ?? null}
        online={desk.online}
        signer={signer}
        onSigner={setSigner}
        busy={!!desk.activeRun}
        onReset={() => {
          if (window.confirm('Reset the desk to the original database?\n\nApprovals, drafts, notes and payments are cleared and cash goes back to $3,400. The audit trail is kept.')) desk.reset()
        }}
      />
      {desk.online === false && (
        <div className="offline">The desk can't reach the back office at <code>http://localhost:8000</code>. Start it from <code>backend/</code> with <code>uvicorn main:app --reload --port 8000</code>.</div>
      )}
      <main className="workspace">
        <TicketTray tickets={desk.tickets} selected={selected} onSelect={setSelected} runningTicket={runningTicket} board={desk.board} />
        {ticket ? (
          <CaseFile
            key={ticket.id}
            ticket={ticket}
            events={desk.events}
            board={desk.board}
            activeRun={desk.activeRun}
            runningTicket={runningTicket}
            version={desk.version}
            onRun={() => desk.runTicket(ticket.id)}
          />
        ) : (
          <section className="casefile empty-state">Loading tickets…</section>
        )}
        <CashDrawer board={desk.board} selected={selected} signer={signer} busy={!!desk.activeRun} onDecide={desk.decide} />
      </main>
      <Toasts toasts={desk.toasts} />
    </div>
  )
}
