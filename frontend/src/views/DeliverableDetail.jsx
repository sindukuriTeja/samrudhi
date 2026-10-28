import React, { useCallback, useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { api, fmtTime, fmtDur } from '../api.js'
import Markdown from '../Markdown.jsx'
import { useToast } from '../App.jsx'

const STAGES = [
  { id: 'intake', label: 'Brief Intake', agents: ['Shruti'] },
  { id: 'planning', label: 'Planning & Calendar', agents: ['Yojana', 'Disha', 'Kalpana'] },
  { id: 'research', label: 'Healthcare Research', agents: ['Anvesh'] },
  { id: 'drafting', label: 'Copywriting', agents: ['Lekha'] },
  { id: 'creative', label: 'Visual Production', agents: ['Chitra'] },
  { id: 'qa', label: 'QA & Clinical Screening', agents: ['Shuddhi', 'Pariksha'] },
  { id: 'assurance', label: 'Independent Assurance', agents: ['Gunvatta', 'Swasthya'] },
  { id: 'approval', label: 'Human Approval Gate', agents: ['Mitra → Human + Client'] },
  { id: 'publish', label: 'Publishing', agents: ['Prakash'] },
  { id: 'reporting', label: 'Client Reporting & Cost', agents: ['Prativedan', 'Lagaat'] },
  { id: 'improvement', label: 'Learning & Improvement', agents: ['Medha', 'Satya'] },
]

const OUTPUT_TABS = [
  { key: 'brief', label: 'Brief' },
  { key: 'plan', label: 'Plan' },
  { key: 'strategy', label: 'Strategy' },
  { key: 'calendar', label: 'Calendar' },
  { key: 'research', label: 'Research' },
  { key: 'copy', label: 'Copy' },
  { key: 'creative', label: 'Creative' },
  { key: 'screening', label: 'Clinical Screen' },
  { key: 'qa_report', label: 'Technical QA' },
  { key: 'assurance', label: 'Assurance' },
  { key: 'published', label: 'Published' },
  { key: 'report', label: 'Client Report' },
  { key: 'improvement', label: 'Improvement' },
]

export default function DeliverableDetail() {
  const { id } = useParams()
  const toast = useToast()
  const [d, setD] = useState(null)
  const [tab, setTab] = useState('copy')
  const [ledger, setLedger] = useState([])
  const [decision, setDecision] = useState({ reviewer: 'Human Reviewer', notes: '' })
  const [deciding, setDeciding] = useState('')

  const load = useCallback(() => {
    api.deliverables.get(id).then(setD).catch(e => toast(e.message, 'err'))
    api.deliverables.ledger(id).then(setLedger).catch(() => {})
  }, [id])

  useEffect(() => {
    load()
    const iv = setInterval(load, 3000)
    return () => clearInterval(iv)
  }, [load])

  if (!d) return <div className="empty"><span className="spinner" /> Loading…</div>

  const progress = d.progress || { stages: [] }
  const stageState = Object.fromEntries(progress.stages.map(s => [s.stage, s.state]))
  const runs = d.runs || []

  const decide = async (decisionType) => {
    setDeciding(decisionType)
    try {
      await api.deliverables.decision(id, { ...decision, decision: decisionType })
      toast(decisionType === 'approve' ? 'Approved — publishing now' : 'Rejected — feedback recorded')
      load()
    } catch (e) { toast(e.message, 'err') }
    setDeciding('')
  }

  const activeTab = OUTPUT_TABS.find(t => t.key === tab) || OUTPUT_TABS[0]

  return (
    <>
      <div className="page-head">
        <div style={{ minWidth: 0 }}>
          <div className="flex" style={{ marginBottom: 6 }}>
            <Link to="/deliverables" className="dim small">← Deliverables</Link>
            <span className={'badge ' + d.status}>{d.status.replace('_', ' ')}</span>
            <span className="chip mono">{d.id}</span>
          </div>
          <div className="page-title">{d.title}</div>
          <div className="page-sub mono">{d.content_type} · {d.topic}</div>
        </div>
        {['created', 'rejected'].includes(d.status) && (
          <button className="btn btn-primary" onClick={async () => {
            try { await api.deliverables.start(id); toast('Pipeline started'); load() }
            catch (e) { toast(e.message, 'err') }
          }}>▶ {d.status === 'rejected' ? 'Re-run Pipeline' : 'Start Pipeline'}</button>
        )}
      </div>

      {d.error && (
        <div className="card mb-2" style={{ borderColor: 'rgba(248,113,113,0.4)' }}>
          <div className="flex-between">
            <span className="badge blocked">{d.status === 'blocked' ? 'blocked by safety gate' : 'failed'}</span>
            <span className="small" style={{ color: 'var(--red)' }}>{d.error}</span>
          </div>
        </div>
      )}

      <div className="grid" style={{ gridTemplateColumns: '300px 1fr' }}>
        {/* pipeline */}
        <div className="card" style={{ alignSelf: 'start' }}>
          <div className="card-title">Pipeline</div>
          <div className="pipeline">
            {STAGES.map((s, i) => (
              <div key={s.id} className={'pipe-stage ' + (stageState[s.id] || 'pending')}>
                <div className="pipe-rail">
                  <div className="pipe-node">
                    {stageState[s.id] === 'done' ? '✓' : stageState[s.id] === 'failed' ? '✕' : i + 1}
                  </div>
                  <div className="pipe-line" />
                </div>
                <div className="pipe-body">
                  <div className="pipe-head">
                    <span className="pipe-name">{s.label}</span>
                    {stageState[s.id] === 'current' && <span className="badge running">in progress</span>}
                  </div>
                  <div className="pipe-agents">
                    {s.agents.map(a => <span key={a} className="chip">{a}</span>)}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* main column */}
        <div style={{ minWidth: 0 }}>
          {/* approval gate */}
          {d.status === 'awaiting_approval' && (
            <div className="card mb-2" style={{ borderColor: 'rgba(251,191,36,0.45)', background: 'linear-gradient(180deg, rgba(251,191,36,0.06), var(--bg-2))' }}>
              <div className="flex-between mb-2">
                <div className="flex">
                  <span className="badge awaiting_approval">⏸ Human approval gate</span>
                  <span className="dim small">Mitra prepared the package · Shuddhi + Gunvatta cleared it</span>
                </div>
              </div>
              <div className="form-row">
                <div className="field">
                  <label>Reviewer (human + client representative)</label>
                  <input className="input" value={decision.reviewer} onChange={e => setDecision({ ...decision, reviewer: e.target.value })} />
                </div>
                <div className="field">
                  <label>Notes</label>
                  <input className="input" value={decision.notes} placeholder="Optional reviewer notes"
                    onChange={e => setDecision({ ...decision, notes: e.target.value })} />
                </div>
              </div>
              <div className="flex">
                <button className="btn btn-primary" disabled={deciding} onClick={() => decide('approve')}>
                  {deciding === 'approve' ? <span className="spinner" /> : '✓ Approve & Publish'}
                </button>
                <button className="btn btn-danger" disabled={deciding} onClick={() => decide('reject')}>
                  {deciding === 'reject' ? <span className="spinner" /> : '✕ Reject'}
                </button>
                <span className="dim small">Approval is recorded to the audit ledger. No publication happens without it.</span>
              </div>
            </div>
          )}

          {/* outputs */}
          <div className="card">
            <div className="tabs">
              {OUTPUT_TABS.map(t => (
                <button key={t.key} className={'tab' + (activeTab.key === t.key ? ' active' : '')}
                  onClick={() => setTab(t.key)}
                  style={d[t.key] ? {} : { opacity: 0.4 }}>
                  {t.label}
                </button>
              ))}
            </div>
            {d[activeTab.key] ? (
              <Markdown text={d[activeTab.key]} />
            ) : (
              <div className="empty">
                <div className="empty-icon">◌</div>
                Not produced yet — this stage has not run.
              </div>
            )}
          </div>

          {/* runs + ledger */}
          <div className="grid grid-2 section-gap">
            <div className="card">
              <div className="card-title"><span>Agent Runs ({runs.length})</span></div>
              <div className="scroll-y max-h-480">
                {runs.map(r => (
                  <div key={r.id} className="ledger-row" style={{ alignItems: 'flex-start' }}>
                    <span className="ledger-ts">{fmtTime(r.started_at)}</span>
                    <span className="ledger-agent" style={{ width: 110 }}>{r.agent_id.replace('SAM-AG-', '')}</span>
                    <div style={{ minWidth: 0 }}>
                      <span className="badge completed" style={{ fontSize: 10 }}>{r.stage}</span>{' '}
                      <span className="dim small mono">{r.provider} · {fmtDur(r.duration_ms)} · {r.tokens_in + r.tokens_out} tok</span>
                    </div>
                  </div>
                ))}
                {runs.length === 0 && <div className="empty small">No runs yet.</div>}
              </div>
            </div>
            <div className="card">
              <div className="card-title"><span>Audit Ledger</span><span className="dim small">append-only</span></div>
              <div className="scroll-y max-h-480">
                {ledger.slice(0, 60).map(l => (
                  <div key={l.id} className="ledger-row">
                    <span className="ledger-ts">{fmtTime(l.ts)}</span>
                    <span className="ledger-agent">{l.agent_id || '—'}</span>
                    <span className="ledger-event">{l.event}{l.detail ? ` · ${l.detail}` : ''}</span>
                  </div>
                ))}
                {ledger.length === 0 && <div className="empty small">No events yet.</div>}
              </div>
            </div>
          </div>
        </div>
      </div>
    </>
  )
}