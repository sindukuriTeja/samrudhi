import React from 'react'

const EVENT_STYLE = {
  'pipeline.start':      { icon: '▶', cls: 'ev-blue',  label: 'Pipeline' },
  'pipeline.complete':   { icon: '✓', cls: 'ev-green', label: 'Published' },
  'pipeline.failed':     { icon: '✕', cls: 'ev-red',   label: 'Pipeline' },
  'stage.start':         { icon: '→', cls: 'ev-blue',  label: 'Stage' },
  'stage.complete':      { icon: '✓', cls: 'ev-green', label: 'Stage' },
  'gate.blocked':        { icon: '⛔', cls: 'ev-red',  label: 'Safety Gate' },
  'approval.requested':  { icon: '⏸', cls: 'ev-amber', label: 'Human Gate' },
  'approval.decided':    { icon: '⚖', cls: 'ev-amber', label: 'Decision' },
  'agent.start':         { icon: '⚙', cls: 'ev-violet', label: 'Agent' },
  'agent.done':          { icon: '✓', cls: 'ev-green', label: 'Agent' },
  'agent.failed':        { icon: '✕', cls: 'ev-red',   label: 'Agent' },
  'cycle.start':         { icon: '⟳', cls: 'ev-blue',  label: 'Workforce' },
  'cycle.agent.start':   { icon: '⚙', cls: 'ev-violet', label: 'Workforce' },
  'cycle.agent.done':    { icon: '✓', cls: 'ev-green', label: 'Workforce' },
  'cycle.done':          { icon: '✓', cls: 'ev-green', label: 'Workforce' },
  'cycle.failed':        { icon: '✕', cls: 'ev-red',   label: 'Workforce' },
}

function fmtClock(ts) {
  return new Date(ts * 1000).toLocaleTimeString('en-IN',
    { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' })
}

export default function LiveFeed({ events, compact = false }) {
  if (!events.length) {
    return (
      <div className="dim small" style={{ padding: '14px 4px' }}>
        Waiting for live events… start a deliverable or a workforce cycle.
      </div>
    )
  }
  return (
    <div className={'live-feed' + (compact ? ' live-feed-compact' : '')}>
      {events.map((e, i) => {
        const st = EVENT_STYLE[e.type] || { icon: '·', cls: 'ev-dim', label: e.type }
        return (
          <div key={e.ts + '-' + i} className={'live-row ' + st.cls + (i === 0 ? ' live-row-new' : '')}>
            <span className="live-icon">{st.icon}</span>
            <div style={{ minWidth: 0, flex: 1 }}>
              <div className="live-detail">{e.detail}</div>
              {!compact && (
                <div className="live-meta">
                  <span className="live-tag">{st.label}</span>
                  {e.agent_id && <span className="mono">{e.agent_id}</span>}
                  {e.stage && <span className="mono">{e.stage}</span>}
                  {e.index && <span className="mono">{e.index}/{e.total}</span>}
                  {e.aps != null && <span className="mono">APS {e.aps}</span>}
                  <span className="live-time">{fmtClock(e.ts)}</span>
                </div>
              )}
            </div>
          </div>
        )
      })}
    </div>
  )
}