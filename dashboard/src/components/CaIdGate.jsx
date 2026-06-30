import React, { useState, useEffect } from 'react'
import { api } from '../api/client.js'

export default function CaIdGate({ onSubmit }) {
  const [value, setValue] = useState('')
  const [role, setRole] = useState('ca')
  
  // Hardcoded for MVP ease of testing based on seed data.
  // These IDs are created fresh each time `python -m scripts.seed` is run;
  // update them here if you re-seed. Values below match the current seeded DB.
  const MOCK_CA_ID = '53f55976-e0cc-4c24-9457-ba28e6004fff'
  const MOCK_BUSINESS_ID = '64cf8ebb-543a-45a0-8833-73938538b7c6'

  return (
    <div style={styles.wrap}>
      <div style={styles.card}>
        <div style={styles.brand}>GiSTo</div>
        <p style={styles.lead}>
          Sign in to your dashboard. Select your role and paste your ID (a real login replaces this — see PRD §4.2.3).
        </p>
        
        <div style={styles.roleToggle}>
          <button 
            type="button" 
            onClick={() => { setRole('ca'); setValue(''); }} 
            style={role === 'ca' ? styles.roleBtnActive : styles.roleBtn}
          >
            CA
          </button>
          <button 
            type="button" 
            onClick={() => { setRole('business'); setValue(''); }} 
            style={role === 'business' ? styles.roleBtnActive : styles.roleBtn}
          >
            Business Owner
          </button>
        </div>

        <form
          onSubmit={(e) => {
            e.preventDefault()
            if (value.trim()) onSubmit(value.trim(), role)
          }}
        >
          <input
            autoFocus
            placeholder={role === 'ca' ? "CA ID" : "Business ID"}
            value={value}
            onChange={(e) => setValue(e.target.value)}
            style={styles.input}
          />
          <button type="submit" style={styles.button}>
            Continue
          </button>
        </form>
        
        <div style={{ marginTop: '20px', fontSize: '12px', color: 'var(--ink-500)', textAlign: 'center' }}>
          <p>For testing, click to autofill:</p>
          <button onClick={() => { setRole('ca'); setValue(MOCK_CA_ID); }} style={styles.mockBtn}>Test CA</button>
          <button onClick={() => { setRole('business'); setValue(MOCK_BUSINESS_ID); }} style={styles.mockBtn}>Test Business</button>
        </div>
      </div>
    </div>
  )
}

const styles = {
  wrap: {
    height: '100vh',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    background: 'var(--paper-0)',
  },
  card: {
    width: 420,
    background: 'var(--white)',
    border: '1px solid var(--paper-100)',
    borderRadius: 'var(--radius-md)',
    padding: 'var(--space-7)',
    boxShadow: 'var(--shadow-card)',
  },
  brand: {
    fontFamily: 'var(--font-display)',
    fontSize: 28,
    fontWeight: 600,
    color: 'var(--ink-900)',
    marginBottom: 'var(--space-3)',
  },
  lead: {
    color: 'var(--ink-500)',
    fontSize: 14,
    lineHeight: 1.6,
    marginBottom: 'var(--space-5)',
  },
  roleToggle: {
    display: 'flex',
    gap: '8px',
    marginBottom: 'var(--space-4)',
  },
  roleBtn: {
    flex: 1,
    padding: '8px',
    background: 'var(--paper-100)',
    border: '1px solid transparent',
    borderRadius: 'var(--radius-sm)',
    cursor: 'pointer',
    color: 'var(--ink-700)',
  },
  roleBtnActive: {
    flex: 1,
    padding: '8px',
    background: 'var(--white)',
    border: '1px solid var(--ink-900)',
    borderRadius: 'var(--radius-sm)',
    cursor: 'pointer',
    fontWeight: 'bold',
    color: 'var(--ink-900)',
  },
  input: {
    width: '100%',
    padding: '10px 12px',
    fontSize: 14,
    border: '1px solid var(--paper-100)',
    borderRadius: 'var(--radius-sm)',
    marginBottom: 'var(--space-4)',
    fontFamily: 'var(--font-mono)',
  },
  button: {
    width: '100%',
    padding: '10px 12px',
    fontSize: 14,
    fontWeight: 600,
    background: 'var(--ink-900)',
    color: 'var(--white)',
    border: 'none',
    borderRadius: 'var(--radius-sm)',
    cursor: 'pointer',
  },
  mockBtn: {
    background: 'transparent',
    border: '1px solid var(--paper-100)',
    borderRadius: '4px',
    padding: '4px 8px',
    margin: '0 4px',
    cursor: 'pointer',
    fontSize: '11px'
  }
}
