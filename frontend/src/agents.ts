import type { AgentName } from './types'

export interface AgentMeta {
  name: AgentName
  label: string
  role: string
  glyph: string
  color: string // ink color
  tint: string // soft background
}

export const AGENT_META: Record<AgentName, AgentMeta> = {
  boss: { name: 'boss', label: 'Boss', role: 'Triage & decisions', glyph: '★', color: '#1d3a8a', tint: '#e6ecfb' },
  inventory: { name: 'inventory', label: 'Inventory', role: 'Stock, vendors, ETAs', glyph: '▦', color: '#0f6e66', tint: '#e0f2ef' },
  accounting: { name: 'accounting', label: 'Accounting', role: 'Cash & payments', glyph: '$', color: '#9a5b00', tint: '#fbefd9' },
  facilities: { name: 'facilities', label: 'Facilities', role: 'Lease & landlord', glyph: '⌂', color: '#6b3fc7', tint: '#efe8fc' },
  customer_service: { name: 'customer_service', label: 'Customer Service', role: 'Customer replies', glyph: '✉', color: '#b0275e', tint: '#fbe6ee' },
}

export const AGENT_ORDER: AgentName[] = ['boss', 'inventory', 'accounting', 'facilities', 'customer_service']

export const TOOL_LABELS: Record<string, string> = {
  list_open_tickets: 'Checked the ticket queue',
  get_ticket: 'Read the ticket file',
  list_vendors: 'Looked up vendors',
  get_board: 'Checked the approval board',
  check_restock_path: 'Checked stock & restock path',
  check_rent_and_cash: 'Checked rent vs. cash',
  quote_bulk_order: 'Priced the order',
  update_ticket: 'Updated the ticket',
  request_payment_approval: 'Queued a payment for you',
  request_price_override: 'Queued a discount for you',
  draft_message: 'Wrote a draft message',
  draft_vendor_order: 'Drafted a vendor order',
  delegate: 'Handed off work',
}
