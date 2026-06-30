import React, { useEffect, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { api, formatRupees } from '../api/client.js'

export default function BusinessDetailPage({ caId }) {
  const { businessId } = useParams()
  const [business, setBusiness] = useState(null)
  const [invoices, setInvoices] = useState(null)
  const [suppliers, setSuppliers] = useState(null)
  const [alerts, setAlerts] = useState(null)
  const [tab, setTab] = useState('ledger')
  const [error, setError] = useState(null)

  useEffect(() => {
    setBusiness(null)
    setInvoices(null)
    setSuppliers(null)
    setAlerts(null)
    setError(null)

    Promise.all([
      api.getBusiness(businessId),
      api.getBusinessInvoices(caId, businessId),
      api.getBusinessSuppliers(caId, businessId),
      api.getAlerts(businessId, true),
    ])
      .then(([b, inv, sup, al]) => {
        setBusiness(b)
        setInvoices(inv)
        setSuppliers(sup)
        setAlerts(al)
      })
      .catch((e) => setError(e.message))
  }, [caId, businessId])

  async function handleAlertAction(alertId, action) {
    await api.actOnAlert(alertId, action)
    const fresh = await api.getAlerts(businessId, true)
    setAlerts(fresh)
  }

  if (error) {
    return (
      <div>
        <BackLink />
        <p style={{ color: 'var(--risk-700)' }}>{error}</p>
      </div>
    )
  }

  if (!business) {
    return <div style={{ color: 'var(--ink-500)' }}>Loading…</div>
  }

  return (
    <div>
      <BackLink />
      <div style={styles.headerRow}>
        <h1 style={styles.h1}>{business.name}</h1>
        <a href={api.exportInvoicesCsvUrl(businessId)} style={styles.exportBtn}>
          Export ledger (CSV)
        </a>
      </div>
      <div style={styles.metaRow}>
        <span>GSTIN: {business.gstin}</span>
        {business.state && <span> · {business.state}</span>}
      </div>

      <div style={styles.tabs}>
        <TabButton active={tab === 'ledger'} onClick={() => setTab('ledger')}>
          Invoice ledger
        </TabButton>
        <TabButton active={tab === 'suppliers'} onClick={() => setTab('suppliers')}>
          Supplier filing history
        </TabButton>
        <TabButton active={tab === 'alerts'} onClick={() => setTab('alerts')}>
          Open alerts {alerts && alerts.length > 0 ? `(${alerts.length})` : ''}
        </TabButton>
      </div>

      {tab === 'ledger' && <LedgerTable invoices={invoices} />}
      {tab === 'suppliers' && <SupplierHistoryTable suppliers={suppliers} />}
      {tab === 'alerts' && <AlertsList alerts={alerts} onAction={handleAlertAction} />}
    </div>
  )
}

function BackLink() {
  return (
    <Link to="/" style={styles.backLink}>
      ← Back to portfolio
    </Link>
  )
}

function TabButton({ active, onClick, children }) {
  return (
    <button onClick={onClick} style={active ? styles.tabActive : styles.tab}>
      {children}
    </button>
  )
}

function LedgerTable({ invoices }) {
  if (!invoices) return <div style={{ color: 'var(--ink-500)' }}>Loading ledger…</div>
  if (invoices.length === 0) return <EmptyPanel text="No invoices logged yet for this business." />

  return (
    <table style={styles.table} className="portfolio-table">
      <thead>
        <tr>
          <th style={styles.th}>Invoice #</th>
          <th style={styles.th}>Date</th>
          <th style={styles.th}>Counterparty</th>
          <th style={{ ...styles.th, textAlign: 'right' }}>Taxable value</th>
          <th style={{ ...styles.th, textAlign: 'right' }}>GST</th>
          <th style={styles.th}>ITC status</th>
        </tr>
      </thead>
      <tbody>
        {invoices.map((inv) => (
          <tr key={inv.invoice_id}>
            <td style={styles.td}>{inv.invoice_number || '—'}</td>
            <td style={styles.td}>{inv.invoice_date || '—'}</td>
            <td style={styles.td}>{inv.counterparty_name || inv.counterparty_gstin || '—'}</td>
            <td style={{ ...styles.td, textAlign: 'right' }} className="num">
              {inv.taxable_value != null ? formatRupees(inv.taxable_value) : '—'}
            </td>
            <td style={{ ...styles.td, textAlign: 'right' }} className="num">
              {inv.gst_amount != null ? formatRupees(inv.gst_amount) : '—'}
            </td>
            <td style={styles.td}>
              <ItcStatusBadge status={inv.itc_status} />
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}

function ItcStatusBadge({ status }) {
  const map = {
    verified_filed: { label: 'Verified', bg: 'var(--safe-100)', fg: 'var(--safe-600)' },
    at_risk_not_filed: { label: 'At risk', bg: 'var(--risk-100)', fg: 'var(--risk-700)' },
    pending_verification: { label: 'Pending', bg: 'var(--paper-100)', fg: 'var(--ink-500)' },
  }
  const s = map[status] || map.pending_verification
  return (
    <span
      style={{
        fontSize: 11,
        fontWeight: 600,
        textTransform: 'uppercase',
        letterSpacing: '0.03em',
        padding: '3px 8px',
        borderRadius: 999,
        background: s.bg,
        color: s.fg,
      }}
    >
      {s.label}
    </span>
  )
}

function SupplierHistoryTable({ suppliers }) {
  if (!suppliers) return <div style={{ color: 'var(--ink-500)' }}>Loading suppliers…</div>
  if (suppliers.length === 0) return <EmptyPanel text="No suppliers tracked yet for this business." />

  return (
    <table style={styles.table} className="portfolio-table">
      <thead>
        <tr>
          <th style={styles.th}>Supplier</th>
          <th style={{ ...styles.th, textAlign: 'right' }}>Risk score</th>
          <th style={styles.th}>Filing history (most recent periods)</th>
        </tr>
      </thead>
      <tbody>
        {suppliers.map((s) => (
          <tr key={s.supplier_gstin}>
            <td style={styles.td}>
              <div style={{ fontFamily: 'var(--font-display)', fontSize: 15 }}>{s.legal_name || s.supplier_gstin}</div>
              <div style={{ fontSize: 12, color: 'var(--ink-500)' }}>{s.supplier_gstin}</div>
            </td>
            <td style={{ ...styles.td, textAlign: 'right' }}>
              <RiskScoreBadge score={s.risk_score} />
            </td>
            <td style={styles.td}>
              <FilingHistoryDots history={s.filing_history} />
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}

function RiskScoreBadge({ score }) {
  if (score == null) return <span style={{ color: 'var(--ink-500)', fontSize: 13 }}>No data</span>
  const pct = Math.round(score * 100)
  const color = pct >= 50 ? 'var(--risk-700)' : pct >= 25 ? 'var(--warn-600)' : 'var(--safe-600)'
  return <span className="num" style={{ color, fontWeight: 600 }}>{pct}%</span>
}

function FilingHistoryDots({ history }) {
  if (!history || history.length === 0) return <span style={{ color: 'var(--ink-500)', fontSize: 13 }}>No history yet</span>
  const sorted = [...history].sort((a, b) => a.period.localeCompare(b.period))
  return (
    <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
      {sorted.map((h) => {
        const color = !h.filed ? 'var(--risk-600)' : h.filed_on_time === false ? 'var(--warn-600)' : 'var(--safe-600)'
        const title = `${h.period}: ${!h.filed ? 'not filed' : h.filed_on_time === false ? 'filed late' : 'filed on time'}`
        return (
          <span
            key={h.period}
            title={title}
            style={{ width: 10, height: 10, borderRadius: '50%', background: color, display: 'inline-block' }}
          />
        )
      })}
      <span style={{ fontSize: 11, color: 'var(--ink-500)', marginLeft: 4 }}>
        {sorted[0]?.period} → {sorted[sorted.length - 1]?.period}
      </span>
    </div>
  )
}

function AlertsList({ alerts, onAction }) {
  if (!alerts) return <div style={{ color: 'var(--ink-500)' }}>Loading alerts…</div>
  if (alerts.length === 0) return <EmptyPanel text="No open ITC risk alerts for this business." />

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-3)' }}>
      {alerts.map((a) => (
        <div key={a.alert_id} style={styles.alertCard}>
          <div>
            <div style={{ fontFamily: 'var(--font-display)', fontSize: 16 }}>
              {a.supplier_name || a.supplier_gstin}
            </div>
            <div style={{ fontSize: 13, color: 'var(--ink-500)' }}>Period {a.period}</div>
          </div>
          <div className="num num-risk" style={{ fontSize: 18 }}>{formatRupees(a.amount_at_risk)}</div>
          <div style={{ display: 'flex', gap: 8 }}>
            <button style={styles.actionBtn} onClick={() => onAction(a.alert_id, 'send_reminder')}>
              Draft reminder
            </button>
            <button style={styles.actionBtnGhost} onClick={() => onAction(a.alert_id, 'mark_resolved')}>
              Mark resolved
            </button>
          </div>
        </div>
      ))}
    </div>
  )
}

function EmptyPanel({ text }) {
  return <div style={styles.emptyPanel}>{text}</div>
}

const styles = {
  backLink: { fontSize: 13, color: 'var(--ink-500)', textDecoration: 'none', display: 'inline-block', marginBottom: 'var(--space-4)' },
  headerRow: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 'var(--space-3)' },
  h1: { fontFamily: 'var(--font-display)', fontSize: 28, fontWeight: 600, margin: 0, color: 'var(--ink-900)' },
  metaRow: { fontSize: 13, color: 'var(--ink-500)', margin: '6px 0 var(--space-5)' },
  exportBtn: {
    fontSize: 13, fontWeight: 600, color: 'var(--ink-900)', textDecoration: 'none',
    border: '1px solid var(--paper-100)', borderRadius: 'var(--radius-sm)', padding: '8px 14px', background: 'var(--white)',
  },
  tabs: { display: 'flex', gap: 4, marginBottom: 'var(--space-4)', borderBottom: '1px solid var(--paper-100)' },
  tab: {
    fontSize: 13, padding: '10px 14px', background: 'transparent', border: 'none',
    borderBottom: '2px solid transparent', color: 'var(--ink-500)', cursor: 'pointer',
  },
  tabActive: {
    fontSize: 13, fontWeight: 600, padding: '10px 14px', background: 'transparent', border: 'none',
    borderBottom: '2px solid var(--ink-900)', color: 'var(--ink-900)', cursor: 'pointer',
  },
  table: {
    width: '100%', borderCollapse: 'collapse', background: 'var(--white)',
    border: '1px solid var(--paper-100)', borderRadius: 'var(--radius-md)', overflow: 'hidden',
  },
  th: {
    textAlign: 'left', fontSize: 11, textTransform: 'uppercase', letterSpacing: '0.04em',
    color: 'var(--ink-500)', fontWeight: 600, padding: '12px 16px', borderBottom: '1px solid var(--paper-100)',
    background: 'var(--paper-50)',
  },
  td: { padding: '14px 16px', fontSize: 14, color: 'var(--ink-900)', borderBottom: '1px solid var(--paper-100)' },
  alertCard: {
    display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 'var(--space-4)',
    background: 'var(--white)', border: '1px solid var(--risk-100)', borderRadius: 'var(--radius-md)',
    padding: 'var(--space-4) var(--space-5)',
  },
  actionBtn: {
    fontSize: 12, fontWeight: 600, padding: '8px 12px', background: 'var(--ink-900)', color: 'var(--white)',
    border: 'none', borderRadius: 'var(--radius-sm)', cursor: 'pointer',
  },
  actionBtnGhost: {
    fontSize: 12, padding: '8px 12px', background: 'transparent', color: 'var(--ink-700)',
    border: '1px solid var(--paper-100)', borderRadius: 'var(--radius-sm)', cursor: 'pointer',
  },
  emptyPanel: {
    textAlign: 'center', padding: 'var(--space-7)', color: 'var(--ink-500)', fontSize: 14,
    background: 'var(--white)', border: '1px dashed var(--paper-100)', borderRadius: 'var(--radius-md)',
  },
}
