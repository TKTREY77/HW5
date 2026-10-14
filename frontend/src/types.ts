export type AgentName = 'boss' | 'inventory' | 'accounting' | 'facilities' | 'customer_service'

export interface Ticket {
  id: number
  type: 'customer_order' | 'rent_notice' | 'price_override' | string
  requester: string
  subject: string
  sku: string | null
  size: string | null
  qty: number | null
  lease_id: number | null
  invoice_id: number | null
  status: 'open' | 'in_progress' | 'waiting_on_approval' | 'blocked' | 'resolved' | string
  notes: string | null
  created_at: string
  is_open: boolean
  last_run: Run | null
}

export interface Approval {
  id: number
  ticket_id: number | null
  kind: 'invoice_payment' | 'rent_payment' | 'vendor_purchase' | 'price_override' | string
  ref_id: number | null
  payee: string | null
  amount: number
  details: string | null
  requested_by: string
  status: 'pending' | 'approved' | 'rejected'
  created_at: string
  decided_by: string | null
  decided_at: string | null
  decision_note: string | null
  payment_id: number | null
}

export interface Draft {
  id: number
  ticket_id: number | null
  channel: 'email' | 'phone_script' | 'letter' | 'vendor_order' | string
  recipient: string
  subject: string
  body: string
  author: string
  status: 'draft' | 'blocked' | 'approved' | string
  created_at: string
}

export interface Payment {
  id: number
  kind: 'invoice' | 'rent' | 'purchase' | string
  ref_id: number | null
  amount: number
  account: string
  paid_at: string
  approved_by: string
}

export interface Board {
  today: string
  cash_accounts: { name: string; balance: number; date: string }[]
  pending_payments_total: number
  projected_balance: number
  pending_approvals: Approval[]
  decided_approvals: Approval[]
  drafts: Draft[]
  payments: Payment[]
}

export interface TicketDetail {
  today: string
  ticket: Ticket
  inventory_all_sizes?: { size: string; qty: number; location: string }[]
  pricing?: { sku: string; unit_cost: number; list_price: number }
  lease?: { id: number; space_name: string; landlord: string; monthly_rent: number; next_due: string }
  invoice?: { id: number; vendor_id: number; amount: number; due_date: string; status: string; description: string }
  invoice_vendor?: { id: number; name: string; specialty: string; lead_days: number }
  notes: { author: string; note: string; created_at: string }[]
  approvals: Approval[]
  drafts: Draft[]
}

export interface Run {
  run_id: string
  ticket_id: number
  status: 'queued' | 'running' | 'done' | 'error'
  started_at: string
  finished_at?: string
  result: { report?: AgentReport; usage?: Usage; error?: string } | null
}

export interface AgentReport {
  summary: string
  status: string
  actions_taken: string[]
  approval_ids: number[]
  draft_ids: number[]
  needs_human: string[]
  next_steps: string[]
}

export interface Usage {
  requests: number
  tool_calls: number
  input_tokens: number
  output_tokens: number
  total_tokens: number
}

export interface AgentEvent {
  seq: number
  time: string
  run_id: string
  event: string
  agent: AgentName | null
  ticket_id: number | null
  depth: number | null
  data: Record<string, any>
  summary: string
}

export interface AgentRecap {
  agent: AgentName
  tools: Record<string, number>
  delegated_to: AgentName[]
  summary: string | null
  status: string | null
  approval_ids: number[]
  draft_ids: number[]
}

export interface TicketSummary {
  ticket_id: number
  run_id: string | null
  agents: AgentRecap[]
  usage: Usage | null
  finished?: boolean
}
