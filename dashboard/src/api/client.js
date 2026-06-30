const BASE_URL = import.meta.env.VITE_BACKEND_BASE_URL || (import.meta.env.PROD ? '' : 'http://localhost:8000')

async function request(path, options = {}) {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })
  if (!res.ok) {
    const text = await res.text().catch(() => '')
    throw new Error(`${res.status} ${res.statusText}: ${text}`)
  }
  if (res.status === 204) return null
  return res.json()
}

export const api = {
  // PRD §4.2.1 — Portfolio view
  getPortfolio: (caId) => request(`/ca/${caId}/portfolio`),

  // PRD §4.2.2 — Single-business drill-down
  getBusinessInvoices: (caId, businessId) => 
    caId ? request(`/ca/${caId}/business/${businessId}/invoices`) : request(`/invoices/by-business/${businessId}`),
  getBusinessSuppliers: (caId, businessId) => 
    caId ? request(`/ca/${caId}/business/${businessId}/suppliers`) : request(`/businesses/${businessId}/suppliers`),
  getBusiness: (businessId) => request(`/businesses/${businessId}`),

  // Alerts (shared with bot)
  getAlerts: (businessId, openOnly = true) =>
    request(`/alerts/by-business/${businessId}?open_only=${openOnly}`),
  actOnAlert: (alertId, action, extra = {}) =>
    request(`/alerts/${alertId}/action`, {
      method: 'POST',
      body: JSON.stringify({ action, ...extra }),
    }),

  // Digest
  getDigest: (businessId, periodLabel = 'this period') =>
    request(`/digest/${businessId}?period_label=${encodeURIComponent(periodLabel)}`),

  // PRD §4.2.3 — Permissions
  updatePermission: (linkId, permission) =>
    request(`/ca/links/${linkId}/permission`, {
      method: 'PATCH',
      body: JSON.stringify({ permission }),
    }),

  // PRD §4.2.2 — Export
  exportInvoicesCsvUrl: (businessId) => `${BASE_URL}/export/business/${businessId}/invoices.csv`,
}

export function formatRupees(amount) {
  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    maximumFractionDigits: 0,
  }).format(amount)
}
