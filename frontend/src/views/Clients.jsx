import React, { useEffect, useState } from 'react'
import { api, fmtTime } from '../api.js'
import { useToast } from '../App.jsx'

const EMPTY = { name: '', specialty: '', geography: '', tone: 'warm, trustworthy, professional', audience: 'patients and their families', channels: 'Instagram, Facebook', brand_do: '', brand_dont: '' }

export default function Clients() {
  const toast = useToast()
  const [clients, setClients] = useState(null)
  const [deliverables, setDeliverables] = useState([])
  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState(EMPTY)

  const load = () => Promise.all([api.clients.list(), api.deliverables.list()])
    .then(([c, d]) => { setClients(c); setDeliverables(d) })
    .catch(e => toast(e.message, 'err'))
  useEffect(() => { load() }, [])

  const create = async (e) => {
    e.preventDefault()
    if (!form.name.trim()) return toast('Client name is required', 'err')
    try {
      await api.clients.create(form)
      toast('Client created')
      setForm(EMPTY); setShowForm(false)
      load()
    } catch (err) { toast(err.message, 'err') }
  }

  if (!clients) return <div className="empty"><span className="spinner" /> Loading…</div>

  return (
    <>
      <div className="page-head">
        <div>
          <div className="page-title">Pilot Clients</div>
          <div className="page-sub">2–3 consenting healthcare clients · client data is isolated per account (Rule 08)</div>
        </div>
        <button className="btn btn-primary" onClick={() => setShowForm(v => !v)}>{showForm ? 'Cancel' : '+ Add Client'}</button>
      </div>

      {showForm && (
        <form className="card mb-2" onSubmit={create}>
          <div className="card-title">New Healthcare Client</div>
          <div className="form-row">
            <div className="field"><label>Name *</label><input className="input" value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} /></div>
            <div className="field"><label>Specialty</label><input className="input" value={form.specialty} placeholder="e.g. cardiology clinic" onChange={e => setForm({ ...form, specialty: e.target.value })} /></div>
          </div>
          <div className="form-row">
            <div className="field"><label>Geography</label><input className="input" value={form.geography} placeholder="e.g. Bengaluru, India" onChange={e => setForm({ ...form, geography: e.target.value })} /></div>
            <div className="field"><label>Channels</label><input className="input" value={form.channels} onChange={e => setForm({ ...form, channels: e.target.value })} /></div>
          </div>
          <div className="form-row">
            <div className="field"><label>Tone of voice</label><input className="input" value={form.tone} onChange={e => setForm({ ...form, tone: e.target.value })} /></div>
            <div className="field"><label>Primary audience</label><input className="input" value={form.audience} onChange={e => setForm({ ...form, audience: e.target.value })} /></div>
          </div>
          <div className="form-row">
            <div className="field"><label>Brand DO</label><input className="input" value={form.brand_do} placeholder="what the brand should do" onChange={e => setForm({ ...form, brand_do: e.target.value })} /></div>
            <div className="field"><label>Brand DON'T</label><input className="input" value={form.brand_dont} placeholder="what the brand must never do" onChange={e => setForm({ ...form, brand_dont: e.target.value })} /></div>
          </div>
          <button className="btn btn-primary" type="submit">Create Client</button>
        </form>
      )}

      <div className="grid grid-3">
        {clients.map(c => {
          const count = deliverables.filter(d => d.client_id === c.id).length
          return (
            <div key={c.id} className="card agent-card">
              <div className="agent-head">
                <div className="avatar" style={{ '--av1': '#0e7c66', '--av2': '#2dd4bf' }}>{c.name.slice(0, 2).toUpperCase()}</div>
                <div style={{ minWidth: 0 }}>
                  <div className="agent-name">{c.name}</div>
                  <div className="agent-role">{c.specialty || 'healthcare'}</div>
                </div>
              </div>
              <div className="agent-meta">
                {c.geography && <span className="chip">📍 {c.geography}</span>}
                <span className="chip">{count} deliverable{count === 1 ? '' : 's'}</span>
              </div>
              <div className="dim small" style={{ lineHeight: 1.6 }}>
                {c.tone && <div><strong style={{ color: 'var(--text-dim)' }}>Tone:</strong> {c.tone}</div>}
                {c.audience && <div><strong style={{ color: 'var(--text-dim)' }}>Audience:</strong> {c.audience}</div>}
                {c.channels && <div><strong style={{ color: 'var(--text-dim)' }}>Channels:</strong> {c.channels}</div>}
              </div>
              {(c.brand_do || c.brand_dont) && (
                <div className="dim small">
                  {c.brand_do && <div>✓ {c.brand_do}</div>}
                  {c.brand_dont && <div style={{ color: 'var(--red)' }}>✕ {c.brand_dont}</div>}
                </div>
              )}
              <div className="dim small mono">added {fmtTime(c.created_at)}</div>
            </div>
          )
        })}
      </div>
    </>
  )
}