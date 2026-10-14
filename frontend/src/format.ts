export const money = (n: number | null | undefined) =>
  n == null ? '—' : n.toLocaleString('en-US', { style: 'currency', currency: 'USD' })

export const clock = (iso: string) =>
  new Date(iso).toLocaleTimeString([], { hour: 'numeric', minute: '2-digit', second: '2-digit' })

export function deskDate(iso: string) {
  const d = new Date(`${iso}T12:00:00`)
  return {
    weekday: d.toLocaleDateString('en-US', { weekday: 'long' }),
    month: d.toLocaleDateString('en-US', { month: 'short' }).toUpperCase(),
    day: d.getDate(),
    year: d.getFullYear(),
  }
}

export const TICKET_KIND: Record<string, { label: string; icon: string }> = {
  customer_order: { label: 'Customer order', icon: '🛍' },
  rent_notice: { label: 'Rent notice', icon: '🏠' },
  price_override: { label: 'Discount request', icon: '🏷' },
}

export const STATUS_LABEL: Record<string, string> = {
  open: 'Open',
  in_progress: 'In progress',
  waiting_on_approval: 'Needs your signature',
  blocked: 'Blocked',
  resolved: 'Resolved',
}

export const APPROVAL_KIND: Record<string, { label: string; moneyOut: boolean }> = {
  invoice_payment: { label: 'Pay vendor invoice', moneyOut: true },
  rent_payment: { label: 'Pay rent', moneyOut: true },
  vendor_purchase: { label: 'Approve restock purchase', moneyOut: true },
  price_override: { label: 'Approve discount quote', moneyOut: false },
}
