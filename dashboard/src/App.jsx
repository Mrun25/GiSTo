import React, { useState, useEffect } from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import Layout from './components/Layout.jsx'
import PortfolioPage from './pages/PortfolioPage.jsx'
import BusinessDetailPage from './pages/BusinessDetailPage.jsx'
import CaIdGate from './components/CaIdGate.jsx'

// MVP auth note: PRD §4.2.3 specifies a real CA dashboard login created
// on invite-accept. That login/session system is out of scope for this
// build; CaIdGate stands in for it by letting whoever runs the dashboard
// supply a CA id directly (stored in localStorage for convenience),
// which is the same identifier a real login would resolve to.
export default function App() {
  const [authId, setAuthId] = useState(() => localStorage.getItem('gisto_auth_id') || '')
  const [role, setRole] = useState(() => localStorage.getItem('gisto_role') || '')

  useEffect(() => {
    if (authId) localStorage.setItem('gisto_auth_id', authId)
    if (role) localStorage.setItem('gisto_role', role)
  }, [authId, role])

  if (!authId || !role) {
    return <CaIdGate onSubmit={(id, selectedRole) => { setAuthId(id); setRole(selectedRole); }} />
  }

  return (
    <BrowserRouter>
      <Routes>
        <Route element={<Layout role={role} onSwitchCa={() => { setAuthId(''); setRole(''); localStorage.removeItem('gisto_auth_id'); localStorage.removeItem('gisto_role'); }} />}>
          {role === 'ca' ? (
            <>
              <Route path="/" element={<PortfolioPage caId={authId} />} />
              <Route path="/business/:businessId" element={<BusinessDetailPage caId={authId} />} />
              <Route path="*" element={<Navigate to="/" replace />} />
            </>
          ) : (
            <>
              <Route path="/" element={<Navigate to={`/business/${authId}`} replace />} />
              <Route path="/business/:businessId" element={<BusinessDetailPage caId={null} />} />
              <Route path="*" element={<Navigate to="/" replace />} />
            </>
          )}
        </Route>
      </Routes>
    </BrowserRouter>
  )
}

