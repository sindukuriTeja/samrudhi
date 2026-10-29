import React, { useCallback, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api.js'
import { useEventStream } from '../useEventStream.js'
import LiveFeed from '../components/LiveFeed.jsx'
import WorkforcePanel from '../components/WorkforcePanel.jsx'
import AgentStatusBoard from '../components/AgentStatusBoard.jsx'

export default function Live() {
  const [events, connected] = useEventStream(null, 250)
  const [filter, setFilter] = useState('')
  const [refresh, setRefresh] = useState(0)

  const onCycleEvent = useCallback((reload) => {
    setRefresh(r => r + 1)
  }, [])

  const shown = filter
    ? events.filter(e => e.type.startsWith(filter))
    : events

  return (
    <>
      <div className="page-head">
        <div>
          <div className="page-title">Live Operations</div>
          <div className="page-sub">
            Real-time event stream · every agent, stage, gate and decision as it happens
          </div>
        </div>
        <div className="flex" style={{ gap: 8 }}>
          <span className={'chip ' + (connected ? '' : 'dim')}>
            <span className={'dot ' + (connected ? 'ok' : 'warn')} style={{ display: 'inline-block', marginRight: 6 }} />
            {connected ? 'stream connected' : 'reconnecting…'}
          </span>
          <select className="select" style={{ width: 170 }} value={filter}
                  onChange={e => setFilter(e.target.value)}>
            <option value="">All events</option>
            <option value="pipeline">Pipeline</option>
            <option value="stage">Stages</option>
            <option value="agent">Agents</option>
            <option value="cycle">Workforce cycle</option>
            <option value="approval">Approvals</option>
            <option value="gate">Safety gates</option>
          </select>
        </div>
      </div>

      <div className="grid" style={{ gridTemplateColumns: '1fr 360px' }}>
        <div style={{ minWidth: 0 }}>
          <div className="card">
            <div className="card-title">
              <span>Live Activity Feed</span>
              <span className="dim small">{shown.length} events in buffer</span>
            </div>
            <div className="scroll-y" style={{ maxHeight: 460 }}>
              <LiveFeed events={shown} />
            </div>
          </div>
          <div className="section-gap">
            <AgentStatusBoard />
          </div>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          <WorkforcePanel onCycleEvent={onCycleEvent} />
          <div className="card">
            <div className="card-title">Quick Actions</div>
            <div className="dim small" style={{ marginBottom: 10 }}>
              Trigger real-time activity from anywhere in the command centre —
              the feed updates instantly.
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              <Link to="/deliverables" className="btn btn-primary">+ New Deliverable</Link>
              <Link to="/deliverables" className="btn">▶ Start a pipeline run</Link>
              <Link to="/approvals" className="btn">⚖ Review approvals</Link>
            </div>
          </div>
          <div className="card">
            <div className="card-title">How the stream works</div>
            <div className="dim small">
              The backend publishes every lifecycle event to an in-process
              event bus and streams it over Server-Sent Events
              (<span className="mono">/api/events</span>). Each event is also
              written to the audit ledger, so the live feed and the immutable
              history always agree.
            </div>
          </div>
        </div>
      </div>
    </>
  )
}