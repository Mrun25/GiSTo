import React, { useEffect, useState, useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import { api, formatRupees } from '../api/client.js'

const SORTABLE_COLUMNS = {
  risk: (a, b) => b.itc_at_risk_current_period - a.itc_at_risk_current_period,
  name: (a, b) => a.name.localeCompare(b.name),
  suppliers: (a, b) => b.non_compliant_supplier_count - a.non_compliant_supplier_count,
}

export default function PortfolioPage({ caId }) {
  const [portfolio, setPortfolio] = useState(null)
  const [error, setError] = useState(null)
  const [sortBy, setSortBy] = useState('risk')
  const [filterAtRiskOnly, setFilterAtRiskOnly] = useState(false)
  const navigate = useNavigate()

  useEffect(() => {
    api
      .getPortfolio(caId)
      .then(setPortfolio)
      .catch((e) => setError(e.message))
  }, [caId])

  const rows = useMemo(() => {
    if (!portfolio) return []
    let list = [...portfolio.businesses]
    if (filterAtRiskOnly) list = list.filter((b) => b.itc_at_risk_current_period > 0)
    list.sort(SORTABLE_COLUMNS[sortBy])
    return list
  }, [portfolio, sortBy, filterAtRiskOnly])

  if (error) {
    return (
      <EmptyState
        title="Couldn't load your portfolio"
        body={`${error}. Check that the backend is running and this CA ID is linked to at least one business.`}
      />
    )
  }

  if (!portfolio) {
    return <div style={styles.loading}>Loading portfolio…</div>
  }

  if (portfolio.businesses.length === 0) {
    return (
      <EmptyState
        title="No linked businesses yet"
        body="Once an owner invites you from the GiSTo Telegram bot and you accept, their business will appear here."
      />
    )
  }

  return (
    <div>
      <div style={styles.headerRow}>
        <div>
          <h1 style={styles.h1}>Portfolio</h1>
          <p style={styles.subhead}>
            {rows.length} of {portfolio.businesses.length} client{portfolio.businesses.length !== 1 ? 's' : ''} shown
          </p>
        </div>
        <div style={styles.totalCard}>
          <div style={styles.totalLabel}>Total ITC at risk — this period</div>
          <div className="num num-risk" style={styles.totalAmount}>
            {formatRupees(portfolio.total_itc_at_risk)}
          </div>
        </div>
      </div>

      <div style={styles.controls}>
        <label style={styles.checkboxLabel}>
          <input
            type="checkbox"
            checked={filterAtRiskOnly}
            onChange={(e) => setFilterAtRiskOnly(e.target.checked)}
          />
          At-risk clients only
        </label>
        <div style={styles.sortGroup}>
          <span style={styles.sortLabel}>Sort by</span>
          {Object.keys(SORTABLE_COLUMNS).map((key) => (
            <button
              key={key}
              onClick={() => setSortBy(key)}
              style={sortBy === key ? styles.sortBtnActive : styles.sortBtn}
            >
              {key === 'risk' ? 'ITC at risk' : key === 'name' ? 'Name' : 'Non-compliant suppliers'}
            </button>
          ))}
        </div>
      </div>

      <table style={styles.table} className="portfolio-table">
        <thead>
          <tr>
            <th style={styles.th}>Business</th>
            <th style={{ ...styles.th, textAlign: 'right' }}>ITC at risk</th>
            <th style={{ ...styles.th, textAlign: 'right' }}>Non-compliant suppliers</th>
            <th style={{ ...styles.th, textAlign: 'right' }}>Last invoice sync</th>
            <th style={{ ...styles.th, textAlign: 'right' }}>Access</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((b) => (
            <tr
              key={b.business_id}
              style={styles.tr}
              onClick={() => navigate(`/business/${b.business_id}`)}
            >
              <td style={styles.tdName}>{b.name}</td>
              <td style={{ ...styles.td, textAlign: 'right' }}>
                <span className={`num ${b.itc_at_risk_current_period > 0 ? 'num-risk' : 'num-safe'}`}>
                  {formatRupees(b.itc_at_risk_current_period)}
                </span>
              </td>
              <td style={{ ...styles.td, textAlign: 'right' }} className="num">
                {b.non_compliant_supplier_count}
              </td>
              <td style={{ ...styles.td, textAlign: 'right', color: 'var(--ink-500)', fontSize: 13 }}>
                {b.last_invoice_sync_date ? new Date(b.last_invoice_sync_date).toLocaleDateString('en-IN') : '—'}
              </td>
              <td style={{ ...styles.td, textAlign: 'right' }}>
                <PermissionBadge permission={b.permission} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function PermissionBadge({ permission }) {
  const canAct = permission === 'can_act'
  return (
    <span
      style={{
        fontSize: 11,
        fontWeight: 600,
        textTransform: 'uppercase',
        letterSpacing: '0.04em',
        padding: '3px 8px',
        borderRadius: 999,
        background: canAct ? 'var(--safe-100)' : 'var(--paper-100)',
        color: canAct ? 'var(--safe-600)' : 'var(--ink-500)',
      }}
    >
      {canAct ? 'Can act' : 'View only'}
    </span>
  )
}

function EmptyState({ title, body }) {
  return (
    <div style={styles.empty}>
      <h2 style={styles.emptyTitle}>{title}</h2>
      <p style={styles.emptyBody}>{body}</p>
    </div>
  )
}

const styles = {
  loading: { color: 'var(--ink-500)', padding: 'var(--space-7)' },
  headerRow: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: 'var(--space-6)',
    gap: 'var(--space-5)',
    flexWrap: 'wrap',
  },
  h1: {
    fontFamily: 'var(--font-display)',
    fontSize: 30,
    fontWeight: 600,
    margin: 0,
    color: 'var(--ink-900)',
  },
  subhead: { color: 'var(--ink-500)', fontSize: 13, margin: '4px 0 0' },
  totalCard: {
    background: 'var(--white)',
    border: '1px solid var(--paper-100)',
    borderRadius: 'var(--radius-md)',
    padding: 'var(--space-4) var(--space-5)',
    boxShadow: 'var(--shadow-card)',
    minWidth: 260,
  },
  totalLabel: {
    fontSize: 11,
    color: 'var(--ink-500)',
    textTransform: 'uppercase',
    letterSpacing: '0.05em',
    marginBottom: 4,
  },
  totalAmount: { fontSize: 26, fontWeight: 600 },
  controls: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 'var(--space-4)',
    flexWrap: 'wrap',
    gap: 'var(--space-3)',
  },
  checkboxLabel: { display: 'flex', alignItems: 'center', gap: 6, fontSize: 13, color: 'var(--ink-700)' },
  sortGroup: { display: 'flex', alignItems: 'center', gap: 6 },
  sortLabel: { fontSize: 12, color: 'var(--ink-500)', marginRight: 4 },
  sortBtn: {
    fontSize: 12,
    padding: '5px 10px',
    border: '1px solid var(--paper-100)',
    background: 'var(--white)',
    borderRadius: 999,
    cursor: 'pointer',
    color: 'var(--ink-700)',
  },
  sortBtnActive: {
    fontSize: 12,
    padding: '5px 10px',
    border: '1px solid var(--ink-900)',
    background: 'var(--ink-900)',
    color: 'var(--white)',
    borderRadius: 999,
    cursor: 'pointer',
  },
  table: {
    width: '100%',
    borderCollapse: 'collapse',
    background: 'var(--white)',
    border: '1px solid var(--paper-100)',
    borderRadius: 'var(--radius-md)',
    overflow: 'hidden',
  },
  th: {
    textAlign: 'left',
    fontSize: 11,
    textTransform: 'uppercase',
    letterSpacing: '0.04em',
    color: 'var(--ink-500)',
    fontWeight: 600,
    padding: '12px 16px',
    borderBottom: '1px solid var(--paper-100)',
    background: 'var(--paper-50)',
  },
  tr: { cursor: 'pointer', borderBottom: '1px solid var(--paper-100)' },
  td: { padding: '14px 16px', fontSize: 14, color: 'var(--ink-900)' },
  tdName: { padding: '14px 16px', fontFamily: 'var(--font-display)', fontSize: 16, fontWeight: 500 },
  empty: { textAlign: 'center', padding: 'var(--space-8) var(--space-5)' },
  emptyTitle: { fontFamily: 'var(--font-display)', fontSize: 22, color: 'var(--ink-900)' },
  emptyBody: { color: 'var(--ink-500)', fontSize: 14, maxWidth: 440, margin: '8px auto 0' },
}
