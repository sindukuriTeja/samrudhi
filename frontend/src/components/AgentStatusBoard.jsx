import React, { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api.js'
import { useEventStream } from '../useEventStream.js'
import { useToast } from '../App.jsx'

const DEPT_ORDER = ['CEO', 'SAL', 'MKT', 'CEX', 'OPS', 'CRT', 'PMG', 'DAT', 'FIN', 'TEC', 'GOV']

export default function AgentStatusBoard() {
  const toast = useToast()
  const [agents, setAgents] = useState([])
  // persisted baseline: last run state + APS per agent (survives reloads)
  const [baseline, setBaseline] = useState({})
  // transient live state from the SSE stream (overrides baseline)
  const [live, setLive] = useState({})
  const [lastEvent, setLastEvent] = useState(null)
  // run-all trigger
  const [deliverables, setDeliverables] = useState([])
  const [target, setTarget] = useState('')
  const [cycle, setCycle] = useState(null)

  const loadBaseline = () => {
    api.agents.status().then(list => {
      const m = {}
      list.forEach(s => { m[s.id] = s })
      setBaseline(m)
    }).catch(() => {})
  }

  useEffect(() => {
    api.agents.list().then(setAgents).catch(() => {})
    api.deliverables.list().then(setDeliverables).catch(() => {})
    loadBaseline()
  }, [])

  // auto-select the first deliverable as the cycle anchor
  useEffect(() => {
    if (!target && deliverables.length) setTarget(deliverables[0].id)
  }, [deliverables, target])

  const [events, connected] = useEventStream((e) => {
    if (!e.agent_id) return
    if (e.type === 'agent.start' || e.type === 'cycle.agent.start') {
      setLive(p => ({ ...p, [e.agent_id]: { state: 'working', ts: e.ts, aps: p[e.agent_id]?.aps } }))
      setLastEvent(e)
    } else if (e.type === 'agent.done' || e.type === 'cycle.agent.done') {
      setLive(p => ({ ...p, [e.agent_id]: { state: 'done', ts: e.ts, aps: e.aps ?? p[e.agent_id]?.aps } }))
      setLastEvent(e)
    } else if (e.type === 'agent.failed') {
      setLive(p => ({ ...p, [e.agent_id]: { state: 'failed', ts: e.ts, aps: p[e.agent_id]?.aps } }))
      setLastEvent(e)
    }
    if (e.type === 'cycle.done' || e.type === 'cycle.failed') {
      loadBaseline()
    }
  }, 400)

  // poll cycle progress while running
  useEffect(() => {
    if (cycle?.status !== 'running') return
    const iv = setInterval(() => {
      api.workforce.status().then(s => setCycle(s.current)).catch(() => {})
    }, 2000)
    return () => clearInterval(iv)
  }, [cycle?.status])

  const startCycle = async () => {
    if (!target) return toast('Select a deliverable to anchor the cycle', 'err')
    try {
      const c = await api.workforce.start(target)
      setCycle(c)
      toast(`Workforce cycle started — all 194 agents`)
    } catch (e) { toast(e.message, 'err') }
  }

  // effective state: live event wins, else persisted baseline, else idle
  const stateOf = (id) => live[id]?.state || baseline[id]?.state || 'idle'
  const apsOf = (id) => (live[id]?.aps ?? baseline[id]?.aps ?? null)

  const counts = useMemo(() => {
    const c = { working: 0, done: 0, failed: 0, idle: 0 }
    agents.forEach(a => { c[stateOf(a.id)] += 1 })
    return c
  }, [agents, live, baseline])

  const running = cycle?.status === 'running'
  const pct = cycle?.total_agents ? Math.round((cycle.completed_agents / cycle.total_agents) * 100) : 0

  if (!agents.length) return <div className="empty"><span className="spinner" /> Loading…</div>

  return (
    <div className="card">
      <div className="card-title">
        <span>Live Agent Status — all 194</span>
        <span className="flex" style={{ gap: 6 }}>
          <span className={'dot ' + (connected ? 'ok' : 'warn')} />
          <span className="dim small">{connected ? 'stream live' : 'reconnecting…'}</span>
        </span>
      </div>

      <div className="flex" style={{ gap: 14, marginBottom: 10, flexWrap: 'wrap' }}>
        <span className="chip" style={{ borderColor: 'rgba(59,130,246,0.5)' }}>
          <span className="dot ok" style={{ display: 'inline-block', marginRight: 5 }} />{counts.working} working
        </span>
        <span className="chip">✓ {counts.done} done</span>
        <span className="chip">✕ {counts.failed} failed</span>
        <span className="chip dim">{counts.idle} idle (never run)</span>
      </div>

      {lastEvent && (
        <div className="dim small mono" style={{ marginBottom: 10, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
          ▸ {lastEvent.detail}
        </div>
      )}

      {running && (
        <div style={{ marginBottom: 10 }}>
          <div className="score-bar" style={{ height: 8 }}>
            <div className="score-fill" style={{ width: pct + '%' }} />
          </div>
          <div className="flex-between dim small" style={{ marginTop: 4 }}>
            <span>cycle in progress — {cycle.completed_agents}/{cycle.total_agents} agents · {cycle.failed_agents} failed</span>
            <span>live…</span>
          </div>
        </div>
      )}

      <div className="flex" style={{ gap: 8, marginBottom: 12 }}>
        <select className="select" style={{ flex: 1 }} value={target}
                onChange={e => setTarget(e.target.value)} disabled={running}>
          <option value="">Anchor deliverable…</option>
          {deliverables.map(d => <option key={d.id} value={d.id}>{d.title}</option>)}
        </select>
        <button className="btn btn-primary" onClick={startCycle} disabled={running || !target}>
          {running ? <span className="spinner" /> : '⟳ Run all 194 agents'}
        </button>
      </div>

      <div className="agent-grid">
        {DEPT_ORDER.map(dept => {
          const group = agents.filter(a => a.dept_code === dept)
          if (!group.length) return null
          return (
            <div key={dept} className="agent-grid-dept">
              <div className="agent-grid-dept-label">{dept} <span className="dim">· {group.length}</span></div>
              <div className="agent-grid-cells">
                {group.map(a => {
                  const s = stateOf(a.id)
                  const aps = apsOf(a.id)
                  return (
                    <Link key={a.id} to={'/agents/' + a.id}
                          title={`${a.name} — ${a.role}${baseline[a.id]?.stage ? ' · last: ' + baseline[a.id].stage : ''}`}
                          className={'agent-cell agent-cell-' + s}>
                      <span className="agent-cell-dot" />
                      <span className="agent-cell-name">{a.name}</span>
                      {aps != null && s !== 'working' && (
                        <span className="agent-cell-aps">{aps}</span>
                      )}
                    </Link>
                  )
                })}
              </div>
            </div>
          )
        })}
      </div>
      {counts.idle > 0 && !running && (
        <div className="dim small" style={{ marginTop: 8 }}>
          <span className="spinner" style={{ width: 10, height: 10 }} /> {counts.idle} agent(s) have never executed — run a full cycle to light them up
        </div>
      )}
    </div>
  )
}