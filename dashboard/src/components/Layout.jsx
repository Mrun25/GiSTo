import React from 'react'
import { Outlet, Link } from 'react-router-dom'

export default function Layout({ role, onSwitchCa }) {
  return (
    <div style={styles.shell}>
      <header style={styles.header}>
        <Link to="/" style={styles.brandLink}>
          <span style={styles.brand}>GiSTo</span>
          <span style={styles.brandSub}>{role === 'ca' ? 'CA Dashboard' : 'Business Dashboard'}</span>
        </Link>
        <button onClick={onSwitchCa} style={styles.switchBtn}>
          Switch account
        </button>
      </header>
      <main style={styles.main}>
        <Outlet />
      </main>
    </div>
  )
}

const styles = {
  shell: {
    minHeight: '100vh',
    display: 'flex',
    flexDirection: 'column',
  },
  header: {
    height: 64,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: '0 var(--space-6)',
    background: 'var(--ink-900)',
    flexShrink: 0,
  },
  brandLink: {
    display: 'flex',
    alignItems: 'baseline',
    gap: 'var(--space-3)',
    textDecoration: 'none',
  },
  brand: {
    fontFamily: 'var(--font-display)',
    fontSize: 22,
    fontWeight: 600,
    color: 'var(--white)',
    letterSpacing: '0.01em',
  },
  brandSub: {
    fontFamily: 'var(--font-ui)',
    fontSize: 12,
    color: 'rgba(255,255,255,0.6)',
    textTransform: 'uppercase',
    letterSpacing: '0.08em',
  },
  switchBtn: {
    fontSize: 12,
    color: 'rgba(255,255,255,0.75)',
    background: 'transparent',
    border: '1px solid rgba(255,255,255,0.25)',
    borderRadius: 'var(--radius-sm)',
    padding: '6px 10px',
    cursor: 'pointer',
  },
  main: {
    flex: 1,
    padding: 'var(--space-6)',
    maxWidth: 1180,
    width: '100%',
    margin: '0 auto',
  },
}
