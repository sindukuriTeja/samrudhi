import React, { useEffect, useState } from 'react'
import { api, fmtTime } from '../api.js'
import { useToast } from '../App.jsx'

export default function WorkforcePanel({ onCycleEvent }) {
  const toast = useToast()
  const [status, setStatus] = useState(null)
  const [deliverables, setDeliverables] = useState([])
  const [target, setTarget] = useState('')
  const [starting, setStarting] = useState(false)

  const load = () => {
    api.workforce.status().then(setStatus).catch(() => {})
    api.deliverables.list().then(setDeliverables).catch(() => {})
  }
  useEffect(() => {
    load()
    const iv = setInterval(load, 2000)
    return () => clearInterval(iv)
  }, [])

  // refresh immediately on cycle events
  useEffect(() => {
    if (onCycleEvent) onCycleEvent(load)
  }, [onCycleEvent])

  const start = async () => {
    if (!target) return toast('Select a deliverable to anchor the cycle', 'err')
    setStarting(true)
    try {
      const c = await api.workforce.start(target)
      toast(`Workforce cycle ${c.id} started — 194 agents`)
      load()
    } catch (e) { toast(e.message, 'err') }
    setStarting(false)
  }

  const c = status?.current
  const running = c?.status === 'running'
  const pct = c?.total_agents ? Math.round((c.completed_agents / c.total_agents) * 100) : 0

  return (
    <div className="card">
      <div className="card-title">
        <span>Full Workforce Cycle</span>
        <span className={'dot ' + (running ? 'ok' : 'idle')} />
      </div>
      <div className="dim small" style={{ marginBottom: 10 }}>
        Run all <strong>194 agents</strong> through one operational cycle on a
        deliverable. Every agent executes its role work, in real time.
      </div>

      {c ? (
        <div style={{ marginBottom: 12 }}>
          <div className="flex-between small" style={{ marginBottom: 5 }}>
            <span className="mono">{c.id}</span>
            <span className={'badge ' + (running ? 'running' : c.status === 'completed' ? 'completed' : 'failed')}>
              {c.status}
            </span>
          </div>
          <div className="score-bar" style={{ height: 10 }}>
            <div className={'score-fill ' + (c.status === 'failed' ? 'low' : '')}
                 style={{ width: pct + '%' }} />
          </div>
          <div className="flex-between dim small" style={{ marginTop: 5 }}>
            <span>{c.completed_agents}/{c.total_agents} agents · {c.failed_agents} failed</span>
            <span>{c.status === 'running' ? 'live…' : fmtTime(c.finished_at)}</span>
          </div>
        </div>
      ) : (
        <div className="dim small" style={{ marginBottom: 12 }}>No cycle run yet.</div>
      )}

      <div className="flex" style={{ gap: 8 }}>
        <select className="select" style={{ flex: 1 }} value={target}
                onChange={e => setTarget(e.target.value)} disabled={running}>
          <option value="">Anchor deliverable…</option>
          {deliverables.map(d => <option key={d.id} value={d.id}>{d.title}</option>)}
        </select>
        <button className="btn btn-primary" onClick={start}
                disabled={starting || running}>
          {starting ? <span className="spinner" /> : '⟳ Run all 194'}
        </button>
      </div>

      {status?.history?.length > 1 && (
        <>
          <div className="divider" />
          <div className="card-title" style={{ marginBottom: 6 }}>Previous cycles</div>
          <div className="scroll-y" style={{ maxHeight: 150 }}>
            {status.history.slice(1).map(h => (
              <div key={h.id} className="flex-between small" style={{ padding: '5px 0', borderBottom: '1px solid rgba(34,48,79,0.4)' }}>
                <span className="mono dim">{h.id}</span>
                <span>{h.completed_agents}/{h.total_agents} · {h.failed_agents} failed</span>
                <span className="dim">{fmtTime(h.started_at)}</span>
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  )
}