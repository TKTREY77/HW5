import { deskDate } from '../format'
import AnimatedMoney from './AnimatedMoney'

interface Props {
  today: string | null
  balance: number | null
  online: boolean | null
  signer: string
  onSigner: (s: string) => void
  busy: boolean
  onReset: () => void
}

export default function TopBar({ today, balance, online, signer, onSigner, busy, onReset }: Props) {
  const d = today ? deskDate(today) : null
  return (
    <header className="topbar">
      <div className="brand">
        <div className="brand-mark">CC</div>
        <div>
          <div className="brand-name">Campus Customs</div>
          <div className="brand-sub">Back-office desk · Chapel Street, New Haven</div>
        </div>
      </div>

      <div className="topbar-right">
        {d && (
          <div className="calendar" title="Desk date (desk.date_today). The agents treat this as today.">
            <div className="cal-month">{d.month}</div>
            <div className="cal-day">{d.day}</div>
            <div className="cal-week">{d.weekday}</div>
          </div>
        )}
        <div className="till" title="Checking balance (cash_accounts)">
          <div className="till-label">Checking</div>
          <AnimatedMoney value={balance} className="till-amount" />
        </div>
        <label className="signer" title="Your name goes on every approval. Agents can never sign.">
          <span className="signer-label">Signing as</span>
          <input value={signer} onChange={e => onSigner(e.target.value)} placeholder="Your name" spellCheck={false} />
        </label>
        <div className="topbar-tools">
          <span className={`status-light ${online ? 'on' : online === false ? 'off' : ''}`} title={online ? 'Back office online' : 'Back office offline'} />
          <button className="btn ghost small" onClick={onReset} disabled={busy} title={busy ? 'Wait for the team to finish' : 'Restore the original database'}>Reset desk</button>
        </div>
      </div>
    </header>
  )
}
