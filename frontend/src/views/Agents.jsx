import React, { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api.js'

const TIER_COLORS = {
  executive: ['#f59e0b', '#d97706'],
  functional: ['#3b82f6', '#6366f1'],
  evaluation: ['#8b5cf6', '#a855f7'],
  ops: ['#2dd4bf', '#14b8a6'],
}
const TIER_LABEL = { executive: 'Executive', functional: 'Functional', evaluation: 'Assurance', ops: 'AgentOps' }

export default function Agents() {
  const [agents, setAgents] = useState(null)
  const [tier, setTier] = useState('')
  const [dept, setDept] = useState('')

  useEffect(() => { api.agents.list().then(setAgents).catch(() => {}) }, [])
  if (!agents) return <div className="empty"><span className="spinner" /> Loading…</div>

  const depts = [...new Set(agents.map(a => a.dept_code))]
  const shown = agents.filter(a => (!tier || a.tier === tier) && (!dept || a.dept_code === dept))

  return (
    <>
      <div className="page-head">
        <div>
          <div className="page-title">Agent Registry</div>
          <div className="page-sub">194 canonical roles across 11 departments · all 194 executable · 24 wired into the content pipeline, the rest run role work cycles · shared model runtime, distinct identities, permissions & KPIs</div>
        </div>
        <div className="flex">
          <select className="select" style={{ width: 150 }} value={tier} onChange={e => setTier(e.target.value)}>
            <option value="">All tiers</option>
            {Object.entries(TIER_LABEL).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
          </select>
          <select className="select" style={{ width: 170 }} value={dept} onChange={e => setDept(e.target.value)}>
            <option value="">All departments</option>
            {depts.map(d => <option key={d} value={d}>{d}</option>)}
          </select>
        </div>
      </div>

      <div className="grid grid-3">
        {shown.map(a => {
          const [c1, c2] = TIER_COLORS[a.tier] || TIER_COLORS.functional
          return (
            <Link key={a.id} to={'/agents/' + a.id} className="card agent-card">
              <div className="agent-head">
                <div className="avatar" style={{ '--av1': c1, '--av2': c2 }}>{a.name.slice(0, 2).toUpperCase()}</div>
                <div style={{ minWidth: 0 }}>
                  <div className="agent-name">{a.name}</div>
                  <div className="agent-role">{a.role}</div>
                </div>
              </div>
              <div className="agent-meta">
                <span className="chip mono">{a.id}</span>
                <span className="chip">{a.dept_code}</span>
                <span className="chip">{TIER_LABEL[a.tier]}</span>
                <span className="chip">target {a.competency_target}</span>
              </div>
              <div className="kpi-list">
                {a.kpis.slice(0, 3).map((k, i) => <div key={i} className="kpi-item">{k}</div>)}
              </div>
            </Link>
          )
        })}
      </div>
    </>
  )
}