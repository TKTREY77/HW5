import { useCallback, useEffect, useRef, useState } from 'react'
import { api } from './api'
import type { AgentEvent, Board, Run, Ticket } from './types'

const FAST_MS = 1500 // while the team is working
const SLOW_MS = 5000 // idle
const MAX_EVENTS = 1500

export interface Toast {
  id: number
  tone: 'ok' | 'warn' | 'error' | 'info'
  text: string
}

/** All shared desk state + polling. Events are fetched incrementally with a seq cursor. */
export function useDesk() {
  const [tickets, setTickets] = useState<Ticket[]>([])
  const [today, setToday] = useState<string | null>(null)
  const [board, setBoard] = useState<Board | null>(null)
  const [events, setEvents] = useState<AgentEvent[]>([])
  const [runs, setRuns] = useState<Run[]>([])
  const [activeRun, setActiveRun] = useState<string | null>(null)
  const [online, setOnline] = useState<boolean | null>(null)
  const [toasts, setToasts] = useState<Toast[]>([])
  const [version, setVersion] = useState(0) // bumps when something important changed (run finished, decision)
  const lastSeq = useRef(0)
  const prevActive = useRef<string | null>(null)

  const toast = useCallback((tone: Toast['tone'], text: string) => {
    const id = Date.now() + Math.random()
    setToasts(t => [...t, { id, tone, text }])
    setTimeout(() => setToasts(t => t.filter(x => x.id !== id)), 6000)
  }, [])

  const refresh = useCallback(async () => {
    try {
      const [h, t, b, r, ev] = await Promise.all([
        api.health(), api.tickets(), api.board(), api.runs(), api.events(lastSeq.current),
      ])
      setOnline(true)
      setActiveRun(h.run_in_progress)
      setTickets(t.tickets)
      setToday(t.today)
      setBoard(b)
      setRuns(r.runs)
      if (ev.last_seq < lastSeq.current) {
        // audit file was replaced; start over
        lastSeq.current = 0
        setEvents([])
      } else if (ev.events.length) {
        lastSeq.current = ev.events[ev.events.length - 1].seq
        setEvents(old => [...old, ...ev.events].slice(-MAX_EVENTS))
      }
      if (prevActive.current && !h.run_in_progress) {
        const done = r.runs.find(x => x.run_id === prevActive.current)
        if (done?.status === 'done') toast('ok', `The team finished ticket ${done.ticket_id}. Check the slips that need your signature.`)
        else if (done?.status === 'error') toast('error', `Run on ticket ${done.ticket_id} stopped: ${done.result?.error ?? 'unknown error'}`)
        setVersion(v => v + 1)
      }
      prevActive.current = h.run_in_progress
    } catch {
      setOnline(false)
    }
  }, [toast])

  useEffect(() => {
    let alive = true
    let timer: ReturnType<typeof setTimeout>
    const loop = async () => {
      await refresh()
      if (alive) timer = setTimeout(loop, prevActive.current ? FAST_MS : SLOW_MS)
    }
    loop()
    return () => { alive = false; clearTimeout(timer) }
  }, [refresh])

  const runTicket = useCallback(async (id: number) => {
    try {
      const run = await api.run(id)
      prevActive.current = run.run_id
      setActiveRun(run.run_id)
      toast('info', `Ticket ${id} handed to the Boss.`)
      refresh()
    } catch (e) {
      toast('error', (e as Error).message)
    }
  }, [refresh, toast])

  const decide = useCallback(async (approvalId: number, approve: boolean, signer: string) => {
    try {
      const res = approve ? await api.approve(approvalId, signer) : await api.reject(approvalId, signer)
      toast('ok', approve
        ? `Signed slip #${approvalId}${res.checking_balance != null ? `. Checking is now $${res.checking_balance.toLocaleString('en-US', { minimumFractionDigits: 2 })}` : ''}.`
        : `Rejected slip #${approvalId}. Nothing was paid.`)
      if (res.ticket_resolved) toast('ok', 'That was the last open item, so the ticket is now resolved.')
      setVersion(v => v + 1)
      await refresh()
      return true
    } catch (e) {
      toast('error', (e as Error).message)
      return false
    }
  }, [refresh, toast])

  const reset = useCallback(async () => {
    try {
      await api.reset()
      toast('info', 'Desk reset to the original database. The audit trail was kept.')
      setVersion(v => v + 1)
      refresh()
    } catch (e) {
      toast('error', (e as Error).message)
    }
  }, [refresh, toast])

  return { tickets, today, board, events, runs, activeRun, online, toasts, version, runTicket, decide, reset }
}
