import React, { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { api } from '../api.js'

function scoreClass(v) { return v >= 80 ? '' : v >= 60 ? 'mid' : 'low' }

export default function Performance() {
  const navigate = useNavigate()
  const [cards, setCards] = useState(null)
  const [weights, setWeights] = useState(null)
  const [feedback, setFeedback] = useState([])

  useEffect(() => {
    api.sapi.scorecards().then(setCards).catch(() => {})
    api.sapi.weights().then(setWeights).catch(() => {})
    api.feedback().then(setFeedback).catch(() => {})
  }, [])

  if (!cards) return <div className="empty"><span className="spinner" /> Loading…</div>

  const withRuns = cards.filter(c => c.runs > 0).sort((a, b) => b.aps - a.aps)
  const noRuns = cards.filter(c => c.runs === 0)
  const avg = withRuns.length ? (withRuns.reduce((s, c) => s + c.aps, 0) / withRuns.length).toFixed(1) : '—'
  const totalGates = cards.reduce((s, c) => s + c.gates_failed, 0)

  return (
    <>
      <div className="page-head">
        <div>
          <div className="page-title">SAPI Performance</div>
          <div className="page-sub">Samrudhi Agent Performance Intelligence · APS = Σ wᵢ·Sᵢ · critical gates override all scores</div>
        </div>
      </div>

      <div className="grid grid-4 mb-2">
        <div className="card stat-card" style={{ '--glow': 'rgba(45,212,191,0.18)' }}>
          <div className="stat-label">Mean APS (active agents)</div>
          <div className="stat-value">{avg}</div>
          <div className="stat-sub">across {withRuns.length} evaluated agents</div>
        </div>
        <div className="card stat-card" style={{ '--glow': 'rgba(248,113,113,0.18)' }}>
          <div className="stat-label">Critical Gate Failures</div>
          <div className="stat-value">{totalGates}</div>
          <div className="stat-sub">{totalGates ? 'publication blocked' : 'no violations detected'}</div>
        </div>
        <div className="card stat-card" style={{ '--glow': 'rgba(139,92,246,0.18)' }}>
          <div className="stat-label">Scorecard Dimensions</div>
          <div className="stat-value">5</div>
          <div className="stat-sub">quality · efficiency · reliability · business · adaptability</div>
        </div>
        <div className="card stat-card" style={{ '--glow': 'rgba(59,130,246,0.18)' }}>
          <div className="stat-label">Open Feedback Items</div>
          <div className="stat-value">{feedback.filter(f => f.status === 'open').length}</div>
          <div className="stat-sub">unified feedback ledger</div>
        </div>
      </div>

      <div className="grid" style={{ gridTemplateColumns: '1fr 320px' }}>
        <div className="card">
          <div className="card-title"><span>Agent Scorecards</span><span className="dim small">ranked by APS</span></div>
          {withRuns.length === 0 && (
            <div className="empty"><div className="empty-icon">◔</div>No evaluated runs yet. Run a deliverable to populate scorecards.</div>
          )}
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Agent</th><th>APS</th>
                  {weights && Object.keys(weights.weights).map(k => <th key={k}>{k.slice(0, 4)}</th>)}
                  <th>Runs</th><th>Gates</th>
                </tr>
              </thead>
              <tbody>
                {withRuns.map(c => (
                  <tr key={c.agent_id} style={{ cursor: 'pointer' }} onClick={() => navigate('/agents/' + c.agent_id)}>
                    <td>
                      <span style={{ fontWeight: 600 }}>{c.agent_id}</span>
                    </td>
                    <td>
                      <div className="flex" style={{ gap: 8 }}>
                        <span className="mono" style={{ fontWeight: 700 }}>{c.aps}</span>
                        <div className="score-bar" style={{ width: 70 }}>
                          <div className={'score-fill ' + scoreClass(c.aps)} style={{ width: c.aps + '%' }} />
                        </div>
                      </div>
                    </td>
                    {weights && Object.keys(weights.weights).map(k => (
                      <td key={k} className="mono small">{c.dimensions?.[k] ?? '—'}</td>
                    ))}
                    <td className="small">{c.runs}</td>
                    <td>{c.gates_failed > 0 ? <span className="badge blocked">{c.gates_failed}</span> : <span className="dim">0</span>}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {noRuns.length > 0 && (
            <div className="dim small mt-2">Not yet evaluated: {noRuns.map(c => c.agent_id).join(', ')}</div>
          )}
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          <div className="card">
            <div className="card-title">Scoring Model</div>
            {weights && Object.entries(weights.weights).map(([k, w]) => (
              <div key={k} className="flex-between" style={{ marginBottom: 8 }}>
                <span className="small" style={{ textTransform: 'capitalize', color: 'var(--text-dim)' }}>{k}</span>
                <span className="mono small">{Math.round(w * 100)}%</span>
              </div>
            ))}
            <div className="divider" />
            <div className="small dim">
              Each dimension is scored 0–100 per run. The weighted sum (APS) is
              <strong> never allowed to override a critical safety gate</strong> —
              an unauthorised medical claim or cross-client data access blocks
              publication regardless of score.
            </div>
          </div>

          <div className="card">
            <div className="card-title"><span>Feedback Ledger</span><span className="dim small">latest</span></div>
            <div className="scroll-y max-h-360">
              {feedback.slice(0, 12).map(f => (
                <div key={f.id} style={{ padding: '8px 0', borderBottom: '1px solid rgba(34,48,79,0.4)' }}>
                  <div className="flex-between">
                    <span className={'badge ' + (f.severity === 'critical' ? 'blocked' : f.severity === 'high' ? 'rejected' : 'pending')} style={{ fontSize: 10 }}>{f.severity}</span>
                    <span className="dim small mono">{f.agent_id || 'human'}</span>
                  </div>
                  <div className="small mt-1" style={{ color: 'var(--text-dim)' }}>{f.finding}</div>
                  {f.corrective_action && <div className="dim small">→ {f.corrective_action}</div>}
                </div>
              ))}
              {feedback.length === 0 && <div className="dim small">No feedback recorded yet.</div>}
            </div>
          </div>
        </div>
      </div>
    </>
  )
}