import React, { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { api, fmtTime } from '../api.js'
import Markdown from '../Markdown.jsx'

const STAGE_LABELS = {
  intake: 'Brief Intake', planning: 'Planning & Calendar', research: 'Research',
  drafting: 'Copywriting', creative: 'Visual Production', qa: 'QA & Screening',
  assurance: 'Independent Assurance', approval: 'Human Approval',
  publish: 'Publishing', reporting: 'Reporting', improvement: 'Learning',
  complete: 'Complete',
}

function StatCard({ label, value, sub, glow }) {
  return (
    <div className="card stat-card" style={{ '--glow': glow }}>
      <div className="stat-label">{label}</div>
      <div className="stat-value">{value}</div>
      {sub && <div className="stat-sub">{sub}</div>}
    </div>
  )
}

export default function Dashboard() {
  const navigate = useNavigate()
  const [stats, setStats] = useState(null)
  const [deliverables, setDeliverables] = useState([])
  const [agents, setAgents] = useState([])
  const [weights, setWeights] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    const load = () => Promise.all([
      api.stats(), api.deliverables.list(), api.agents.list(), api.sapi.weights(),
    ]).then(([s, d, a, w]) => {
      setStats(s); setDeliverables(d); setAgents(a); setWeights(w)
    }).catch(e => setError(e.message))
    load()
    const iv = setInterval(load, 5000)
    return () => clearInterval(iv)
  }, [])

  if (error) return <div className="card"><div className="empty"><div className="empty-icon">⚠</div>Cannot reach backend: {error}</div></div>
  if (!stats) return <div className="empty"><span className="spinner" /> Loading command centre…</div>

  const active = deliverables.filter(d => ['running', 'awaiting_approval'].includes(d.status))
  const awaiting = deliverables.filter(d => d.status === 'awaiting_approval')
  const published = deliverables.filter(d => d.status === 'published')
  const blocked = deliverables.filter(d => d.status === 'blocked' || d.status === 'failed')

  return (
    <>
      <div className="page-head">
        <div>
          <div className="page-title">Command Centre</div>
          <div className="page-sub">SAMRUDHI Agentic OS · Healthcare content pilot · 194-agent digital workforce</div>
        </div>
        <Link to="/live" className="btn">◉ Live Operations</Link>
        <Link to="/deliverables" className="btn btn-primary">+ New Deliverable</Link>
      </div>

      <div className="grid grid-4">
        <StatCard label="Active Deliverables" value={active.length}
          sub={`${awaiting.length} awaiting approval`} glow="rgba(59,130,246,0.18)" />
        <StatCard label="Published" value={published.length}
          sub={`${stats.deliverables} total deliverables`} glow="rgba(45,212,191,0.18)" />
        <StatCard label="Agent Runs" value={stats.runs}
          sub={`${stats.tokens_in.toLocaleString()} in · ${stats.tokens_out.toLocaleString()} out tokens`} glow="rgba(139,92,246,0.18)" />
        <StatCard label="Safety Gates" value={blocked.length}
          sub={blocked.length ? 'blocked deliverables' : 'no critical violations'} glow="rgba(248,113,113,0.18)" />
      </div>

      <div className="grid grid-2 section-gap" style={{ gridTemplateColumns: '1.6fr 1fr' }}>
        <div className="card">
          <div className="card-title">
            <span>Live Pipeline</span>
            <Link to="/deliverables" className="dim small">view all →</Link>
          </div>
          {deliverables.length === 0 && (
            <div className="empty"><div className="empty-icon">▤</div>No deliverables yet. Create one to start the pipeline.</div>
          )}
          <div className="table-wrap">
            <table>
              <thead><tr><th>Deliverable</th><th>Stage</th><th>Status</th><th>Updated</th></tr></thead>
              <tbody>
                {deliverables.slice(0, 8).map(d => (
                  <tr key={d.id} style={{ cursor: 'pointer' }} onClick={() => navigate('/deliverables/' + d.id)}>
                    <td>
                      <div style={{ fontWeight: 600 }}>{d.title}</div>
                      <div className="dim small mono">{d.content_type}</div>
                    </td>
                    <td>{STAGE_LABELS[d.current_stage] || d.current_stage || '—'}</td>
                    <td><span className={'badge ' + d.status}>{d.status.replace('_', ' ')}</span></td>
                    <td className="dim small">{fmtTime(d.updated_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        <div className="card">
          <div className="card-title">Workforce & Model</div>
          <div className="flex-between mb-2">
            <div>
              <div className="stat-value" style={{ fontSize: 24 }}>{stats.agents}</div>
              <div className="stat-sub">agents in registry</div>
            </div>
            <div>
              <div className="stat-value" style={{ fontSize: 24 }}>{stats.clients}</div>
              <div className="stat-sub">pilot clients</div>
            </div>
            <div>
              <div className="stat-value" style={{ fontSize: 24 }}>{stats.pending_approvals}</div>
              <div className="stat-sub">pending approvals</div>
            </div>
          </div>
          <div className="divider" />
          <div className="flex-between">
            <div>
              <div style={{ fontWeight: 700, fontSize: 13 }}>
                {stats.llm?.ollama_reachable ? 'Ollama (local model)' : 'Deterministic mock engine'}
              </div>
              <div className="dim small mono">{stats.llm?.ollama_model || 'samrudhi-deterministic-v1'}</div>
            </div>
            <span className={'dot ' + (stats.llm?.ollama_reachable ? 'ok' : 'warn')} />
          </div>
          <div className="divider" />
          <div className="card-title" style={{ marginBottom: 8 }}>SAPI Scorecard Weights</div>
          {weights && Object.entries(weights.weights).map(([k, w]) => (
            <div key={k} className="flex-between" style={{ marginBottom: 7 }}>
              <span className="small" style={{ textTransform: 'capitalize', color: 'var(--text-dim)' }}>{k}</span>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, flex: 1, marginLeft: 12 }}>
                <div className="score-bar" style={{ flex: 1 }}>
                  <div className="score-fill" style={{ width: (w / 0.3 * 100) + '%' }} />
                </div>
                <span className="mono small">{Math.round(w * 100)}%</span>
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="grid grid-3 section-gap">
        {awaiting.slice(0, 3).map(d => (
          <div key={d.id} className="card agent-card">
            <div className="flex-between">
              <span className="badge awaiting_approval">awaiting approval</span>
              <span className="dim small">{fmtTime(d.updated_at)}</span>
            </div>
            <div style={{ fontWeight: 700, fontSize: 14 }}>{d.title}</div>
            <div className="dim small">Cleared by Shuddhi (clinical) + Gunvatta (assurance). Ready for human + client decision.</div>
            <Link to={'/deliverables/' + d.id} className="btn btn-primary btn-sm" style={{ marginTop: 4 }}>Review & Decide</Link>
          </div>
        ))}
        {awaiting.length === 0 && (
          <div className="card" style={{ gridColumn: 'span 3' }}>
            <div className="empty" style={{ padding: '22px' }}>
              <div className="empty-icon">✓</div>
              No items awaiting approval. {active.length > 0 ? 'Pipeline is running.' : 'Start a deliverable to see the workflow in action.'}
            </div>
          </div>
        )}
      </div>
    </>
  )
}