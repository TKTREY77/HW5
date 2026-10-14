import { AGENT_META } from '../agents'
import type { AgentName } from '../types'

export default function AgentBadge({ agent, size = 'md', withLabel = false }: { agent: AgentName | 'human'; size?: 'sm' | 'md' | 'lg'; withLabel?: boolean }) {
  if (agent === 'human') {
    return (
      <span className={`badge badge-${size} badge-human`} title="You">
        <span className="badge-dot">✍</span>{withLabel && <span className="badge-label">You</span>}
      </span>
    )
  }
  const m = AGENT_META[agent] ?? { label: agent, role: '', glyph: '•', color: '#555', tint: '#eee' }
  return (
    <span className={`badge badge-${size}`} style={{ ['--ink' as string]: m.color, ['--tint' as string]: m.tint }} title={`${m.label}: ${m.role}`}>
      <span className="badge-dot">{m.glyph}</span>
      {withLabel && <span className="badge-label">{m.label}</span>}
    </span>
  )
}
