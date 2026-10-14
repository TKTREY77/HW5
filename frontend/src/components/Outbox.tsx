import { useState } from 'react'
import type { Draft } from '../types'
import AgentBadge from './AgentBadge'

const CHANNEL: Record<string, string> = { email: '✉ Email', letter: '✎ Letter', phone_script: '☎ Call script', vendor_order: '📦 Vendor order' }

export default function Outbox({ drafts }: { drafts: Draft[] }) {
  if (drafts.length === 0) return null
  return (
    <div className="outbox">
      <h3 className="side-title">Outbox <span className="muted">(drafts, never sent)</span></h3>
      {drafts.map(d => <Envelope key={d.id} d={d} />)}
    </div>
  )
}

function Envelope({ d }: { d: Draft }) {
  const [open, setOpen] = useState(false)
  const [copied, setCopied] = useState(false)
  const stamp = d.status === 'blocked' ? 'Blocked' : d.status === 'approved' ? 'Purchase signed' : 'Draft · not sent'
  return (
    <article className={`envelope ${d.status}`}>
      <div className="env-top">
        <span>{CHANNEL[d.channel] ?? d.channel} · to <b>{d.recipient}</b></span>
        <span className={`env-stamp ${d.status}`}>{stamp}</span>
      </div>
      <div className="env-subject" onClick={() => setOpen(o => !o)}>{d.subject} <span className="chev">{open ? '▾' : '▸'}</span></div>
      {open && <p className="env-body">{d.body}</p>}
      <div className="env-foot">
        <AgentBadge agent={d.author as never} size="sm" withLabel />
        <button className="btn ghost tiny" onClick={() => { navigator.clipboard?.writeText(d.body); setCopied(true); setTimeout(() => setCopied(false), 1500) }}>
          {copied ? 'Copied' : 'Copy text'}
        </button>
      </div>
    </article>
  )
}
