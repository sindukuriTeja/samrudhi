import React, { createContext, useContext, useEffect, useState, useCallback } from 'react'
import { Routes, Route, NavLink, useLocation } from 'react-router-dom'
import { api } from './api.js'
import Dashboard from './views/Dashboard.jsx'
import Deliverables from './views/Deliverables.jsx'
import DeliverableDetail from './views/DeliverableDetail.jsx'
import Agents from './views/Agents.jsx'
import AgentDetail from './views/AgentDetail.jsx'
import Approvals from './views/Approvals.jsx'
import Performance from './views/Performance.jsx'
import Chat from './views/Chat.jsx'
import Clients from './views/Clients.jsx'

const ToastCtx = createContext(() => {})
export const useToast = () => useContext(ToastCtx)

const NAV = [
  { section: 'Operations', items: [
    { to: '/', label: 'Command Centre', icon: '◈', end: true },
    { to: '/deliverables', label: 'Deliverables', icon: '▤' },
    { to: '/approvals', label: 'Approvals', icon: '✓' },
  ]},
  { section: 'Digital Workforce', items: [
    { to: '/agents', label: 'Agent Registry', icon: '⬡' },
    { to: '/performance', label: 'SAPI Performance', icon: '◔' },
  ]},
  { section: 'Engage', items: [
    { to: '/chat', label: 'Agent Console', icon: '✉' },
    { to: '/clients', label: 'Clients', icon: '⚑' },
  ]},
]

function Sidebar({ llm }) {
  const location = useLocation()
  const pending = location.pathname === '/approvals' ? '' : ''
  return (
    <aside className="sidebar">
      <div className="brand">
        <div className="brand-mark">S</div>
        <div>
          <div className="brand-name">SAMRUDHI</div>
          <div className="brand-sub">Agentic OS</div>
        </div>
      </div>
      {NAV.map(sec => (
        <div key={sec.section}>
          <div className="nav-section">{sec.section}</div>
          {sec.items.map(it => (
            <NavLink key={it.to} to={it.to} end={it.end}
              className={({ isActive }) => 'nav-item' + (isActive ? ' active' : '')}>
              <span className="nav-icon">{it.icon}</span>{it.label}
            </NavLink>
          ))}
        </div>
      ))}
      <div className="sidebar-foot">
        <div className="llm-pill">
          <span className={'dot ' + (llm?.ollama_reachable ? 'ok' : llm ? 'warn' : 'idle')} />
          <div style={{ minWidth: 0 }}>
            <div style={{ fontWeight: 600, fontSize: 11.5 }}>
              {llm?.ollama_reachable ? 'Ollama · ' + llm.ollama_model : 'Mock engine'}
            </div>
            <div className="dim" style={{ fontSize: 10.5 }}>
              {llm?.ollama_reachable ? 'local model live' : 'deterministic fallback'}
            </div>
          </div>
        </div>
      </div>
    </aside>
  )
}

export default function App() {
  const [llm, setLlm] = useState(null)
  const [toasts, setToasts] = useState([])

  const toast = useCallback((msg, type = 'ok') => {
    const id = Date.now() + Math.random()
    setToasts(t => [...t, { id, msg, type }])
    setTimeout(() => setToasts(t => t.filter(x => x.id !== id)), 4200)
  }, [])

  useEffect(() => {
    let stop = false
    const load = () => api.llmStatus().then(s => !stop && setLlm(s)).catch(() => {})
    load()
    const iv = setInterval(load, 20000)
    return () => { stop = true; clearInterval(iv) }
  }, [])

  return (
    <ToastCtx.Provider value={toast}>
      <div className="app-shell">
        <Sidebar llm={llm} />
        <main className="main">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/deliverables" element={<Deliverables />} />
            <Route path="/deliverables/:id" element={<DeliverableDetail />} />
            <Route path="/agents" element={<Agents />} />
            <Route path="/agents/:id" element={<AgentDetail />} />
            <Route path="/approvals" element={<Approvals />} />
            <Route path="/performance" element={<Performance />} />
            <Route path="/chat" element={<Chat />} />
            <Route path="/clients" element={<Clients />} />
          </Routes>
        </main>
      </div>
      {toasts.map(t => (
        <div key={t.id} className={'toast' + (t.type === 'err' ? ' err' : '')}>{t.msg}</div>
      ))}
    </ToastCtx.Provider>
  )
}