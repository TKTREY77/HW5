import type { AgentEvent, Board, Run, Ticket, TicketDetail, TicketSummary } from './types'

export const API_BASE: string = import.meta.env.VITE_API_BASE ?? 'http://localhost:8000'

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: { 'Content-Type': 'application/json', ...(init?.headers ?? {}) },
  })
  const body = await res.json().catch(() => ({}))
  if (!res.ok) throw new Error(typeof body.detail === 'string' ? body.detail : `${res.status} ${res.statusText}`)
  return body as T
}

export const api = {
  health: () => request<{ ok: boolean; model: string; run_in_progress: string | null }>('/api/health'),
  tickets: () => request<{ today: string; tickets: Ticket[] }>('/api/tickets'),
  ticket: (id: number) => request<TicketDetail>(`/api/tickets/${id}`),
  summary: (id: number) => request<TicketSummary>(`/api/tickets/${id}/summary`),
  run: (id: number) => request<Run>(`/api/tickets/${id}/run`, { method: 'POST', body: '{}' }),
  runs: () => request<{ runs: Run[] }>('/api/runs'),
  events: (since: number) => request<{ last_seq: number; events: AgentEvent[] }>(`/api/events?since=${since}&limit=500`),
  board: () => request<Board>('/api/board'),
  approve: (id: number, approver: string) =>
    request<{ ok: boolean; checking_balance?: number; ticket_resolved: boolean }>(`/api/approvals/${id}/approve`, {
      method: 'POST', body: JSON.stringify({ approver, note: 'Approved on the desk dashboard' }),
    }),
  reject: (id: number, approver: string) =>
    request<{ ok: boolean; checking_balance?: number; ticket_resolved: boolean }>(`/api/approvals/${id}/reject`, {
      method: 'POST', body: JSON.stringify({ approver, note: 'Rejected on the desk dashboard' }),
    }),
  reset: () => request<{ ok: boolean }>('/api/reset', { method: 'POST' }),
}
