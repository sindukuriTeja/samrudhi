import React, { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { api, fmtTime, fmtDur } from '../api.js'
import Markdown from '../Markdown.jsx'
import { useToast } from '../App.jsx'

const TIER_COLORS = {
  executive: ['#f59e0b', '#d97706'],
  functional: ['#3b82f6', '#6366f1'],
  evaluation: ['#8b5cf6', '#a855f7'],
  ops: ['#2dd4bf', '#14b8a6'],
}

function scoreClass(v) { return v >= 80 ? '' : v >= 60 ? 'mid' : 'low' }

export default function AgentDetail() {
  const { id } = useParams()
  const toast = useToast()
  const [agent, setAgent] = useState(null)
  const [deliverables, setDeliverables] = useState([])
  const [runTarget, setRunTarget] = useState('')
  const [running, setRunning] = useState(false)
  const [lastRun, setLastRun] = useState(null)

  const load = () => {
    api.agents.get(id).then(setAgent).catch(e => toast(e.message, 'err'))
    api.deliverables.list().then(setDeliverables).catch(() => {})
  }
  useEffect(load, [id])

  if (!agent) return <div className="empty"><span className="spinner" /> Loading…</div>
  const [c1, c2] = TIER_COLORS[agent.tier] || TIER_COLORS.functional
  const sc = agent.scorecard

  const runAdhoc = async () => {
    if (!runTarget) return toast('Select a deliverable to run this agent on', 'err')
    setRunning(true)
    try {
      const r = await api.agents.run(id, runTarget)
      setLastRun(r)
      toast(`${agent.name} run complete (${r.provider})`)
      load()
    } catch (e) { toast(e.message, 'err') }
    setRunning(false)
  }

  return (
    <>
      <div className="page-head">
        <div>
          <div className="flex" style={{ marginBottom: 6 }}>
            <Link to="/agents" className="dim small">← Agent Registry</Link>
            <span className="chip mono">{agent.id}</span>
            <span className="chip">{agent.position}</span>
          </div>
          <div className="flex" style={{ gap: 14 }}>
            <div className="avatar" style={{ '--av1': c1, '--av2': c2, width: 54, height: 54, fontSize: 20 }}>{agent.name.slice(0, 2).toUpperCase()}</div>
            <div>
              <div className="page-title">{agent.name}</div>
              <div className="page-sub">{agent.role} · {agent.department}</div>
            </div>
          </div>
        </div>
      </div>

      <div className="grid" style={{ gridTemplateColumns: '1fr 340px' }}>
        <div style={{ minWidth: 0 }}>
          <div className="card">
            <div className="card-title">Operating Instructions (system prompt)</div>
            <Markdown text={agent.system_prompt} />
          </div>

          <div className="card section-gap">
            <div className="card-title"><span>Recent Runs</span><span className="dim small">{sc.runs} total</span></div>
            <div className="table-wrap">
              <table>
                <thead><tr><th>When</th><th>Stage</th><th>Deliverable</th><th>Model</th><th>Duration</th><th>Tokens</th><th>Status</th></tr></thead>
                <tbody>
                  {(agent.recent_runs || []).map(r => (
                    <tr key={r.id}>
                      <td className="dim small">{fmtTime(r.started_at)}</td>
                      <td><span className="chip mono">{r.stage}</span></td>
                      <td className="dim small mono">{r.deliverable_id}</td>
                      <td className="dim small mono">{r.provider}</td>
                      <td className="small">{fmtDur(r.duration_ms)}</td>
                      <td className="small mono">{r.tokens_in + r.tokens_out}</td>
                      <td><span className={'badge ' + (r.status === 'completed' ? 'completed' : r.status)}>{r.status}</span></td>
                    </tr>
                  ))}
                  {(agent.recent_runs || []).length === 0 && (
                    <tr><td colSpan="7" className="dim" style={{ textAlign: 'center', padding: 20 }}>No runs yet.</td></tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          <div className="card">
            <div className="card-title">Identity</div>
            {[
              ['Department', agent.department],
              ['Reports to', agent.reports_to],
              ['Autonomy', agent.autonomy],
              ['Competency target', agent.competency_target],
              ['Tier', agent.tier],
              ['Pipeline stage', agent.stage || 'orchestration / on-demand'],
            ].map(([k, v]) => (
              <div key={k} className="flex-between" style={{ marginBottom: 8 }}>
                <span className="dim small">{k}</span>
                <span className="small" style={{ fontWeight: 600, textAlign: 'right' }}>{v}</span>
              </div>
            ))}
            <div className="divider" />
            <div className="card-title" style={{ marginBottom: 6 }}>Key Result Areas</div>
            {agent.kpis.map((k, i) => <div key={i} className="kpi-item">{k}</div>)}
          </div>

          <div className="card">
            <div className="card-title">SAPI Scorecard</div>
            {sc.runs ? (
              <>
                <div className="flex-between mb-2">
                  <div>
                    <div className="stat-value" style={{ fontSize: 34 }}>{sc.aps}</div>
                    <div className="stat-sub">Agent Performance Score</div>
                  </div>
                  {sc.gates_failed > 0 && <span className="badge blocked">{sc.gates_failed} gate failures</span>}
                </div>
                {Object.entries(sc.dimensions).map(([k, v]) => (
                  <div key={k} style={{ marginBottom: 9 }}>
                    <div className="flex-between small" style={{ marginBottom: 4 }}>
                      <span style={{ textTransform: 'capitalize', color: 'var(--text-dim)' }}>{k}</span>
                      <span className="mono">{v}</span>
                    </div>
                    <div className="score-bar"><div className={'score-fill ' + scoreClass(v)} style={{ width: v + '%' }} /></div>
                  </div>
                ))}
              </>
            ) : (
              <div className="dim small">No runs yet — scorecard appears after the agent executes.</div>
            )}
          </div>

          <div className="card">
            <div className="card-title">Run This Agent</div>
            <div className="field">
              <label>On deliverable</label>
              <select className="select" value={runTarget} onChange={e => setRunTarget(e.target.value)}>
                <option value="">Select…</option>
                {deliverables.map(d => <option key={d.id} value={d.id}>{d.title}</option>)}
              </select>
            </div>
            <button className="btn btn-primary" style={{ width: '100%' }} disabled={running} onClick={runAdhoc}>
              {running ? <span className="spinner" /> : '▶ Execute agent'}
            </button>
            {lastRun && (
              <div className="mt-2">
                <div className="card-title" style={{ marginBottom: 6 }}>Latest output ({lastRun.provider})</div>
                <div className="scroll-y max-h-360"><Markdown text={lastRun.output} /></div>
              </div>
            )}
          </div>
        </div>
      </div>
    </>
  )
}