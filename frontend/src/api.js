const BASE = '/api'

async function req(path, opts = {}) {
  const res = await fetch(BASE + path, {
    headers: { 'Content-Type': 'application/json' },
    ...opts,
  })
  if (!res.ok) {
    let msg = res.statusText
    try { msg = (await res.json()).detail || msg } catch { /* ignore */ }
    throw new Error(msg)
  }
  return res.json()
}

export const api = {
  health: () => req('/health'),
  stats: () => req('/stats'),
  llmStatus: () => req('/llm/status'),

  clients: {
    list: () => req('/clients'),
    create: (body) => req('/clients', { method: 'POST', body: JSON.stringify(body) }),
  },
  deliverables: {
    list: (clientId) => req('/deliverables' + (clientId ? `?client_id=${clientId}` : '')),
    get: (id) => req(`/deliverables/${id}`),
    create: (body) => req('/deliverables', { method: 'POST', body: JSON.stringify(body) }),
    start: (id) => req(`/deliverables/${id}/start`, { method: 'POST' }),
    decision: (id, body) => req(`/deliverables/${id}/decision`, { method: 'POST', body: JSON.stringify(body) }),
    progress: (id) => req(`/deliverables/${id}/progress`),
    runs: (id) => req(`/deliverables/${id}/runs`),
    ledger: (id) => req(`/deliverables/${id}/ledger`),
  },
  approvals: { list: (status) => req('/approvals' + (status ? `?status=${status}` : '')) },
  agents: {
    list: () => req('/agents'),
    get: (id) => req(`/agents/${id}`),
    run: (id, deliverableId) => req(`/agents/${id}/run`, { method: 'POST', body: JSON.stringify({ deliverable_id: deliverableId }) }),
  },
  sapi: {
    weights: () => req('/sapi/weights'),
    scorecards: () => req('/sapi/scorecards'),
    scorecard: (id) => req(`/sapi/scorecards/${id}`),
  },
  feedback: (params = {}) => {
    const qs = new URLSearchParams(params).toString()
    return req('/feedback' + (qs ? `?${qs}` : ''))
  },
  chat: {
    send: (message, agentId) => req('/chat', { method: 'POST', body: JSON.stringify({ message, agent_id: agentId }) }),
    history: () => req('/chat'),
  },
  workforce: {
    start: (deliverableId) => req('/workforce/cycle', { method: 'POST', body: JSON.stringify({ deliverable_id: deliverableId }) }),
    status: () => req('/workforce/cycle'),
  },
  events: {
    history: (limit = 100) => req(`/events/history?limit=${limit}`),
  },
}

export function fmtTime(ts) {
  if (!ts) return '—'
  return new Date(ts * 1000).toLocaleString('en-IN', {
    day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit',
  })
}

export function fmtDur(ms) {
  if (ms == null) return '—'
  if (ms < 1000) return `${ms}ms`
  return `${(ms / 1000).toFixed(1)}s`
}