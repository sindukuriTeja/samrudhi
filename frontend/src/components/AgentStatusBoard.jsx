import React, { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api.js'
import { useEventStream } from '../useEventStream.js'

const DEPT_ORDER = ['CEO', 'SAL', 'MKT', 'CEX', 'OPS', 'CRT', 'PMG', 'DAT', 'FIN', 'TEC', 'GOV']

export default function AgentStatusBoard() {
  const [agents, setAgents] = useState([])
  // live per-agent status: idle | working | done | failed
  const [live, setLive] = useState({})
  const [lastEvent, setLastEvent] = useState(null)

  useEffect(() => { api.agents.list().then(setAgents).catch(() => {}) }, [])

  const [events, connected] = useEventStream((e) => {
    if (!e.agent_id) return
    if (e.type === 'agent.start' || e.type === 'cycle.agent.start') {
      setLive(p => ({ ...p, [e.agent_id]: { state: 'working', ts: e.ts, aps: p[e.agent_id]?.aps } })
      setLastEvent(e)
    } else if (e.type === 'agent.done' || e.type === 'cycle.agent.done') {
      setLive(p => ({ ...p, [e.agent_id]: { state: 'done', ts: e.ts, aps: e.aps ?? p[e.agent_id]?.aps } })
      setLastEvent(e)
    } else if (e.type === 'agent.failed') {
      setLive(p => ({ ...p, [e.agent_id]: { state: 'failed', ts: e.ts, aps: p[e.agent_id]?.aps } })
      setLastEvent(e)
    }
  }, 400)

  const counts = useMemo(() => {
    const c = { working: 0, done: 0, failed: 0, idle: 0 }
    agents.forEach(a => {
      const s = live[a.id]?.state || 'idle'
      c[s] += 1
    })
    return c
  }, [agents, live])

  if (!agents.length) return <div className="empty"><span className="spinner" /> Loading…</div>

  const anyWorking = counts.working > 0

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
        <span className="chip">✓ {counts.done} done this cycle</span>
        <span className="chip">✕ {counts.failed} failed</span>
        <span className="chip dim">{counts.idle} idle</span>
      </div>

      {lastEvent && (
        <div className="dim small mono" style={{ marginBottom: 10, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
          ▸ {lastEvent.detail}
        </div>
      )}

      <div className="agent-grid">
        {DEPT_ORDER.map(dept => {
          const group = agents.filter(a => a.dept_code === dept)
          if (!group.length) return null
          return (
            <div key={dept} className="agent-grid-dept">
              <div className="agent-grid-dept-label">{dept} <span className="dim">· {group.length}</span></div>
              <div className="agent-grid-cells">
                {group.map(a => {
                  const s = live[a.id]?.state || 'idle'
                  return (
                    <Link key={a.id} to={'/agents/' + a.id}
                          title={`${a.name} — ${a.role}`}
                          className={'agent-cell agent-cell-' + s}>
                      <span className="agent-cell-dot" />
                      <span className="agent-cell-name">{a.name}</span>
                      {live[a.id]?.aps != null && s === 'done' && (
                        <span className="agent-cell-aps">{live[a.id].aps}</span>
                      )}
                    </Link>
                  )
                })}
              </div>
            </div>
          )
        })}
      </div>
      {anyWorking && (
        <div className="dim small" style={{ marginTop: 8 }}>
          <span className="spinner" style={{ width: 10, height: 10 }} /> workforce cycle in progress — cells light up as each agent completes
        </div>
      )}
    </div>
  )
}