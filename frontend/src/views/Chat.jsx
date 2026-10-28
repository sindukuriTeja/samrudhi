import React, { useEffect, useRef, useState } from 'react'
import { api, fmtTime } from '../api.js'
import { useToast } from '../App.jsx'

const TIER_COLORS = {
  executive: ['#f59e0b', '#d97706'],
  functional: ['#3b82f6', '#6366f1'],
  evaluation: ['#8b5cf6', '#a855f7'],
  ops: ['#2dd4bf', '#14b8a6'],
}

export default function Chat() {
  const toast = useToast()
  const [agents, setAgents] = useState([])
  const [agentId, setAgentId] = useState('SAM-AG-001')
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [busy, setBusy] = useState(false)
  const logRef = useRef(null)

  useEffect(() => {
    api.agents.list().then(setAgents).catch(() => {})
    api.chat.history().then(setMessages).catch(() => {})
  }, [])

  useEffect(() => {
    if (logRef.current) logRef.current.scrollTop = logRef.current.scrollHeight
  }, [messages, busy])

  const send = async (e) => {
    e?.preventDefault()
    const text = input.trim()
    if (!text || busy) return
    setBusy(true)
    setInput('')
    setMessages(m => [...m, { role: 'user', content: text, agent_id: agentId, ts: Date.now() / 1000 }])
    try {
      const res = await api.chat.send(text, agentId)
      setMessages(m => [...m, { role: 'assistant', content: res.reply, agent_id: res.agent_id, agent_name: res.agent_name, provider: res.provider, ts: Date.now() / 1000 }])
    } catch (err) {
      toast(err.message, 'err')
    }
    setBusy(false)
  }

  const agent = agents.find(a => a.id === agentId)
  const [c1, c2] = agent ? (TIER_COLORS[agent.tier] || TIER_COLORS.functional) : ['#3b82f6', '#6366f1']

  return (
    <>
      <div className="page-head">
        <div>
          <div className="page-title">Agent Console</div>
          <div className="page-sub">Talk to any agent in the digital workforce · {agent ? `${agent.name} — ${agent.role}` : ''}</div>
        </div>
        <select className="select" style={{ width: 300 }} value={agentId} onChange={e => setAgentId(e.target.value)}>
          {agents.map(a => <option key={a.id} value={a.id}>{a.name} — {a.role}</option>)}
        </select>
      </div>

      <div className="card chat-wrap" style={{ padding: 0 }}>
        <div className="chat-log" ref={logRef}>
          {messages.length === 0 && (
            <div className="empty">
              <div className="empty-icon">✉</div>
              Ask <strong>{agent?.name}</strong> about the pilot, a deliverable's status, or anything in their remit.<br />
              <span className="dim small">e.g. “Give me a status on the latest deliverable” or “What are your guardrails?”</span>
            </div>
          )}
          {messages.map((m, i) => (
            <div key={i} className={'msg ' + m.role}>
              {m.role === 'assistant' ? (
                <div className="avatar" style={{ '--av1': c1, '--av2': c2, width: 34, height: 34, fontSize: 12, borderRadius: 10 }}>
                  {(m.agent_name || 'S').slice(0, 2).toUpperCase()}
                </div>
              ) : null}
              <div>
                <div className="msg-meta">
                  {m.role === 'assistant' ? (m.agent_name || 'Agent') + (m.provider ? ` · ${m.provider}` : '') : 'You'}
                  <span className="dim" style={{ fontWeight: 400 }}> · {fmtTime(m.ts)}</span>
                </div>
                <div className="msg-bubble">{m.content}</div>
              </div>
            </div>
          ))}
          {busy && (
            <div className="msg">
              <div className="avatar" style={{ '--av1': c1, '--av2': c2, width: 34, height: 34, fontSize: 12, borderRadius: 10 }}>
                {(agent?.name || 'S').slice(0, 2).toUpperCase()}
              </div>
              <div className="msg-bubble"><span className="spinner" /></div>
            </div>
          )}
        </div>
        <form className="chat-input-row" onSubmit={send}>
          <input className="input" value={input} placeholder={`Message ${agent?.name || 'agent'}…`}
            onChange={e => setInput(e.target.value)} disabled={busy} />
          <button className="btn btn-primary" type="submit" disabled={busy || !input.trim()}>Send</button>
        </form>
      </div>
    </>
  )
}