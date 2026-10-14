import { useEffect, useRef, useState } from 'react'
import { AGENT_META, TOOL_LABELS } from '../agents'
import { clock } from '../format'
import type { AgentEvent, AgentName } from '../types'
import AgentBadge from './AgentBadge'

export default function ActivityFeed({ events, running }: { events: AgentEvent[]; running: boolean }) {
  const box = useRef<HTMLDivElement>(null)
  const [follow, setFollow] = useState(true)

  useEffect(() => {
    if (follow && box.current) box.current.scrollTop = box.current.scrollHeight
  }, [events.length, follow])

  const visible = events.filter(e => e.event !== 'model_step' || e.data.text)

  return (
    <div className="feed-wrap">
      <div className="feed-head">
        <h3 className="side-title">Desk radio {running && <span className="live">● LIVE</span>}</h3>
        <label className="follow"><input type="checkbox" checked={follow} onChange={e => setFollow(e.target.checked)} /> follow</label>
      </div>
      <div className="feed" ref={box}>
        {visible.length === 0 && <div className="feed-empty">Quiet desk. When the team works this ticket you'll hear every hand-off, tool and report here.</div>}
        {visible.map(e => <Line key={e.seq} e={e} />)}
        {running && <div className="typing"><span /><span /><span /></div>}
      </div>
    </div>
  )
}

function Line({ e }: { e: AgentEvent }) {
  const [open, setOpen] = useState(false)
  const agent = e.agent as AgentName | null
  const m = agent ? AGENT_META[agent] : null
  const style = m ? { ['--ink' as string]: m.color, ['--tint' as string]: m.tint } : undefined
  const time = <span className="t">{clock(e.time)}</span>

  switch (e.event) {
    case 'run_start':
      return <div className="divider">{time} Run started · the Boss picks up ticket #{e.ticket_id}</div>
    case 'run_end':
      return <div className="divider ok">{time} Run finished · {e.data.usage?.total_tokens?.toLocaleString() ?? '?'} tokens · status {e.data.status}</div>
    case 'run_error':
      return <div className="divider bad">{time} Run stopped: {e.data.error}</div>
    case 'db_reset':
      return <div className="divider">{time} Desk reset to the original database</div>
    case 'agent_start':
      if (!e.depth) return null
      return <div className="line arrive" style={style}>{time}<AgentBadge agent={agent!} size="sm" /> <b>{m?.label}</b> picks up the hand-off</div>
    case 'delegation': {
      const to = AGENT_META[e.data.to as AgentName]
      return (
        <div className="line handoff" style={style}>
          {time}
          <AgentBadge agent={agent!} size="sm" /><span className="arrow">→</span><AgentBadge agent={e.data.to} size="sm" />
          <div className="bubble"><span className="who">{m?.label} → {to?.label}</span>{e.data.task}</div>
        </div>
      )
    }
    case 'delegation_refused':
      return <div className="line warn" style={style}>{time}<AgentBadge agent={agent!} size="sm" /> Hand-off to {e.data.to} refused ({e.data.reason}); keeps working itself</div>
    case 'tool_blocked':
      return <div className="line warn" style={style}>{time}<AgentBadge agent={agent!} size="sm" /> Blocked from using <code>{e.data.tool}</code>, a human-only tool</div>
    case 'model_step':
      return (
        <div className="line say" style={style}>{time}<AgentBadge agent={agent!} size="sm" />
          <div className="bubble"><span className="who">{m?.label}</span>{e.data.text}</div>
        </div>
      )
    case 'tool_call': {
      const tool = e.data.tool as string
      return (
        <div className={`line tool ${e.data.error ? 'warn' : ''}`} style={style}>
          {time}<AgentBadge agent={agent!} size="sm" />
          <button className="tool-line" onClick={() => setOpen(o => !o)}>
            <span>{TOOL_LABELS[tool] ?? tool}</span> <code>{tool}</code> <span className="chev">{open ? '▾' : '▸'}</span>
          </button>
          {open && <pre className="tool-detail">{JSON.stringify(e.data.args, null, 1)}{'\n→ '}{e.data.error ?? e.data.result}</pre>}
        </div>
      )
    }
    case 'agent_end': {
      const r = e.data.report ?? {}
      return (
        <div className="line report" style={style}>{time}<AgentBadge agent={agent!} size="sm" />
          <div className="bubble report-bubble">
            <span className="who">{m?.label} reports back · {r.status}</span>
            {r.summary}
            {r.needs_human?.length > 0 && <ul className="needs">{r.needs_human.map((n: string, i: number) => <li key={i}>✍ {n}</li>)}</ul>}
          </div>
        </div>
      )
    }
    case 'human_decision':
      return (
        <div className="line human">{time}<AgentBadge agent="human" size="sm" />
          <div className="bubble human-bubble"><span className="who">{e.data.approver}</span>
            {e.data.decision === 'approve' ? 'signed' : 'rejected'} slip #{e.data.approval_id}{e.data.ticket_resolved ? ' · ticket resolved' : ''}
          </div>
        </div>
      )
    default:
      return null
  }
}
