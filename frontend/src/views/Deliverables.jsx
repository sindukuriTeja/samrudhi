import React, { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { api, fmtTime } from '../api.js'
import { useToast } from '../App.jsx'

const STAGE_LABELS = {
  intake: 'Brief Intake', planning: 'Planning & Calendar', research: 'Research',
  drafting: 'Copywriting', creative: 'Visual Production', qa: 'QA & Screening',
  assurance: 'Independent Assurance', approval: 'Human Approval',
  publish: 'Publishing', reporting: 'Reporting', improvement: 'Learning',
  complete: 'Complete',
}

const CONTENT_TYPES = ['static post', 'carousel', 'short-form script', 'long-form article']

export default function Deliverables() {
  const navigate = useNavigate()
  const toast = useToast()
  const [items, setItems] = useState(null)
  const [clients, setClients] = useState([])
  const [filter, setFilter] = useState('')
  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState({ client_id: '', title: '', content_type: 'static post', topic: '' })
  const [starting, setStarting] = useState('')

  const load = () => Promise.all([api.deliverables.list(), api.clients.list()])
    .then(([d, c]) => { setItems(d); setClients(c) })
    .catch(e => toast(e.message, 'err'))
  useEffect(() => { load() }, [])

  const create = async (e) => {
    e.preventDefault()
    if (!form.client_id) return toast('Select a client', 'err')
    try {
      const d = await api.deliverables.create(form)
      toast('Deliverable created — starting pipeline')
      setShowForm(false)
      setForm({ client_id: '', title: '', content_type: 'static post', topic: '' })
      await api.deliverables.start(d.id)
      navigate('/deliverables/' + d.id)
    } catch (err) { toast(err.message, 'err') }
  }

  const start = async (id) => {
    setStarting(id)
    try {
      await api.deliverables.start(id)
      toast('Pipeline started')
      navigate('/deliverables/' + id)
    } catch (err) { toast(err.message, 'err'); setStarting('') }
  }

  if (!items) return <div className="empty"><span className="spinner" /> Loading…</div>
  const shown = filter ? items.filter(d => d.client_id === filter) : items

  return (
    <>
      <div className="page-head">
        <div>
          <div className="page-title">Deliverables</div>
          <div className="page-sub">Content lifecycle pipeline · brief → research → copy → QA → assurance → approval → publish</div>
        </div>
        <div className="flex">
          <select className="select" style={{ width: 210 }} value={filter} onChange={e => setFilter(e.target.value)}>
            <option value="">All clients</option>
            {clients.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
          </select>
          <button className="btn btn-primary" onClick={() => setShowForm(v => !v)}>
            {showForm ? 'Cancel' : '+ New Deliverable'}
          </button>
        </div>
      </div>

      {showForm && (
        <form className="card mb-2" onSubmit={create}>
          <div className="card-title">New Content Deliverable</div>
          <div className="form-row">
            <div className="field">
              <label>Client</label>
              <select className="select" value={form.client_id} onChange={e => setForm({ ...form, client_id: e.target.value })} required>
                <option value="">Select client…</option>
                {clients.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
              </select>
            </div>
            <div className="field">
              <label>Content type</label>
              <select className="select" value={form.content_type} onChange={e => setForm({ ...form, content_type: e.target.value })}>
                {CONTENT_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
              </select>
            </div>
          </div>
          <div className="field">
            <label>Title</label>
            <input className="input" value={form.title} placeholder="e.g. Understanding Angina: When Chest Pain Needs a Doctor"
              onChange={e => setForm({ ...form, title: e.target.value })} required />
          </div>
          <div className="field">
            <label>Topic (what the content covers)</label>
            <input className="input" value={form.topic} placeholder="e.g. recognising angina and when to seek emergency care"
              onChange={e => setForm({ ...form, topic: e.target.value })} />
          </div>
          <button className="btn btn-primary" type="submit">Create & Start Pipeline</button>
          <span className="dim small" style={{ marginLeft: 12 }}>Runs 10 stages across 15 agents, then pauses at the human approval gate.</span>
        </form>
      )}

      <div className="card">
        {shown.length === 0 && (
          <div className="empty"><div className="empty-icon">▤</div>No deliverables. Create one to begin.</div>
        )}
        <div className="table-wrap">
          <table>
            <thead><tr><th>Deliverable</th><th>Client</th><th>Type</th><th>Stage</th><th>Status</th><th>Updated</th><th></th></tr></thead>
            <tbody>
              {shown.map(d => {
                const client = clients.find(c => c.id === d.client_id)
                return (
                  <tr key={d.id} style={{ cursor: 'pointer' }} onClick={() => navigate('/deliverables/' + d.id)}>
                    <td style={{ fontWeight: 600 }}>{d.title}</td>
                    <td className="dim">{client?.name || d.client_id}</td>
                    <td><span className="chip mono">{d.content_type}</span></td>
                    <td>{STAGE_LABELS[d.current_stage] || '—'}</td>
                    <td><span className={'badge ' + d.status}>{d.status.replace('_', ' ')}</span></td>
                    <td className="dim small">{fmtTime(d.updated_at)}</td>
                    <td onClick={e => e.stopPropagation()}>
                      {['created', 'rejected'].includes(d.status) && (
                        <button className="btn btn-sm" disabled={starting === d.id} onClick={() => start(d.id)}>
                          {starting === d.id ? <span className="spinner" /> : '▶ Run'}
                        </button>
                      )}
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      </div>
    </>
  )
}