import { useState } from 'react'
import { APPROVAL_KIND, money } from '../format'
import type { Approval, Board } from '../types'
import AgentBadge from './AgentBadge'
import AnimatedMoney from './AnimatedMoney'

interface Props {
  board: Board | null
  selected: number | null
  signer: string
  busy: boolean
  onDecide: (id: number, approve: boolean, signer: string) => Promise<boolean>
}

export default function CashDrawer({ board, selected, signer, busy, onDecide }: Props) {
  const balance = board?.cash_accounts.find(a => a.name === 'checking')?.balance ?? 0
  const pendingOut = board?.pending_payments_total ?? 0
  const projected = board?.projected_balance ?? 0
  const spentPct = balance > 0 ? Math.min(100, (pendingOut / balance) * 100) : 0
  const slips = [...(board?.pending_approvals ?? [])].sort(
    (a, b) => Number(b.ticket_id === selected) - Number(a.ticket_id === selected) || a.id - b.id,
  )

  return (
    <aside className="drawer">
      <section className="cash-card">
        <div className="cash-head">
          <span>Cash drawer</span>
          <span className="cash-acct">checking</span>
        </div>
        <AnimatedMoney value={board ? balance : null} className="cash-big" />
        <div className="meter" title="Pending payments as a share of today's balance">
          <div className="meter-fill" style={{ width: `${spentPct}%` }} />
        </div>
        <div className="cash-rows">
          <div><span>Waiting for your signature</span><b className={pendingOut ? 'neg' : ''}>{pendingOut ? `−${money(pendingOut)}` : money(0)}</b></div>
          <div className={projected < 0 ? 'danger' : projected < 300 ? 'tight' : ''}>
            <span>If you sign everything</span><b>{money(projected)}</b>
          </div>
        </div>
        <p className="cash-note">Money only goes out here. Sales never top up the drawer, and the till refuses any payment that would go below $0.</p>
      </section>

      <section className="slips">
        <h2 className="drawer-title">Sign here <span className="count">{slips.length}</span></h2>
        {slips.length === 0 && <p className="tray-empty">No slips waiting. The agents prepare them; only you can sign.</p>}
        {slips.map(a => (
          <Slip key={a.id} a={a} balance={balance} board={board!} highlight={a.ticket_id === selected}
            signer={signer} busy={busy} onDecide={onDecide} />
        ))}
      </section>

      <section className="ledger">
        <h2 className="drawer-title">Receipt tape</h2>
        <div className="tape">
          <div className="tape-row head"><span>{board?.today ?? ''}</span><span>Opening</span><span>{money(balance + (board?.payments ?? []).reduce((s, p) => s + p.amount, 0))}</span></div>
          {(board?.payments ?? []).map(p => (
            <div key={p.id} className="tape-row">
              <span>#{p.id} {p.kind}</span>
              <span className="tape-who">{p.approved_by}</span>
              <span className="neg">−{money(p.amount)}</span>
            </div>
          ))}
          {(board?.payments.length ?? 0) === 0 && <div className="tape-row muted"><span>No payments yet</span></div>}
          <div className="tape-row total"><span>Balance</span><span /><span>{money(balance)}</span></div>
        </div>
        {(board?.decided_approvals.length ?? 0) > 0 && (
          <div className="decided">
            {board!.decided_approvals.map(a => (
              <div key={a.id} className={`decided-row ${a.status}`}>
                <span>#{a.id} {APPROVAL_KIND[a.kind]?.label ?? a.kind}</span>
                <span>{a.status === 'approved' ? '✓ signed' : '✕ rejected'} by {a.decided_by}</span>
              </div>
            ))}
          </div>
        )}
      </section>
    </aside>
  )
}

function Slip({ a, balance, board, highlight, signer, busy, onDecide }: {
  a: Approval; balance: number; board: Board; highlight: boolean; signer: string; busy: boolean
  onDecide: Props['onDecide']
}) {
  const [working, setWorking] = useState(false)
  const kind = APPROVAL_KIND[a.kind] ?? { label: a.kind, moneyOut: false }
  const after = balance - a.amount
  const overdraw = kind.moneyOut && after < 0
  const blockedBy = a.kind === 'vendor_purchase'
    ? board.pending_approvals.find(x => x.kind === 'invoice_payment' && x.payee === a.payee)
    : undefined
  const noSigner = !signer.trim()
  const disabled = working || busy || noSigner

  const act = async (approve: boolean) => {
    setWorking(true)
    await onDecide(a.id, approve, signer.trim())
    setWorking(false)
  }

  return (
    <article className={`slip ${highlight ? 'highlight' : ''} ${kind.moneyOut ? 'out' : 'quote'}`}>
      <div className="slip-top">
        <span className="slip-no">Slip #{a.id} · ticket {a.ticket_id}</span>
        <AgentBadge agent={a.requested_by as never} size="sm" />
      </div>
      <div className="slip-kind">{kind.label}</div>
      <div className="slip-amount">
        {kind.moneyOut ? '−' : ''}{money(a.amount)}
        {a.payee && <span className="slip-payee"> to {a.payee}</span>}
      </div>
      {a.details && <p className="slip-details">{a.details}</p>}
      {kind.moneyOut ? (
        <div className={`slip-impact ${overdraw ? 'danger' : ''}`}>
          Checking after signing: <b>{money(after)}</b>{overdraw && ' (the till will refuse this)'}
        </div>
      ) : (
        <div className="slip-impact">Quote only. No cash moves when you sign.</div>
      )}
      {blockedBy && <div className="slip-warn">Pay slip #{blockedBy.id} first. {a.payee} won't ship while that invoice is open.</div>}
      <div className="slip-sign">
        <div className="sig-line">{signer.trim() ? <span className="sig">{signer}</span> : <span className="sig-empty">sign above ↑</span>}</div>
        <div className="slip-actions">
          <button className="btn ghost small" disabled={disabled} onClick={() => act(false)}>Reject</button>
          <button className="btn primary small" disabled={disabled || overdraw} onClick={() => act(true)}
            title={noSigner ? 'Enter your name in "Signing as" first' : busy ? 'Wait for the team to finish' : ''}>
            {working ? 'Signing…' : kind.moneyOut ? 'Sign & pay' : 'Sign'}
          </button>
        </div>
      </div>
    </article>
  )
}
