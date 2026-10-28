import React, { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api, fmtTime } from '../api.js'
import { useToast } from '../App.jsx'

export default function Approvals() {
  const toast = useToast()
  const [pending, setPending] = useState(null)
  const [decisions, setDecisions] = useState([])
  const [forms, setForms] = useState({})
  const [busy, setBusy] = useState('')

  const load = () => Promise.all([
    api.approvals.list('pending'), api.approvals.list(),
  ]).then(([p, all]) => {
    setPending(p)
    setDecisions(all.filter(a => a.status !== 'pending').slice(0, 30))
  }).catch(e => toast(e.message, 'err'))
  useEffect(load, [])

  const decide = async (id, decision) => {
    const f = forms[id] || { reviewer: 'Human Reviewer', notes: '' }
    if (!f.reviewer.trim()) return toast('Enter the reviewer name', 'err')
    setBusy(id + decision)
    try {
      // find the deliverable id from the approval
      const ap = (pending || []).find(a => a.id === id)
      if (ap) {
        await api.deliverables.decision(ap.deliverable_id, { ...f, decision })
        toast(decision === 'approve' ? 'Approved — publishing now' : 'Rejected')
      }
      load()
    } catch (e) { toast(e.message, 'err') }
    setBusy('')
  }

  const getForm = (id) => forms[id] || { reviewer: 'Human Reviewer', notes: '' }
  const setForm = (id, f) => setForms(s => ({ ...s, [id]: f }))

  if (!pending) return <div className="empty"><span className="spinner" /> Loading…</div>

  return (
    <>
      <div className="page-head">
        <div>
          <div className="page-title">Approvals</div>
          <div className="page-sub">Human + client authority gate · agents cannot self-approve · every decision is audit-logged</div>
        </div>
      </div>

      <div className="card mb-2">
        <div className="card-title"><span>Awaiting Decision ({pending.length})</span></div>
        {pending.length === 0 && (
          <div className="empty"><div className="empty-icon">✓</div>Nothing waiting. New deliverables appear here once they clear QA, clinical screening and independent assurance.</div>
        )}
        {pending.map(ap => {
          const f = getForm(ap.id)
          return (
            <div key={ap.id} className="card" style={{ marginBottom: 14, background: 'var(--bg-2)' }}>
              <div className="flex-between mb-2">
                <div className="flex">
                  <span className="badge awaiting_approval">awaiting approval</span>
                  <Link to={'/deliverables/' + ap.deliverable_id} className="small" style={{ fontWeight: 600 }}>
                    View deliverable →
                  </Link>
                </div>
                <span className="dim small">{fmtTime(ap.created_at)}</span>
              </div>
              <div className="dim small mono mb-2">{ap.deliverable_id} · {ap.kind}</div>
              <div className="form-row">
                <div className="field">
                  <label>Reviewer</label>
                  <input className="input" value={f.reviewer} onChange={e => setForm(ap.id, { ...f, reviewer: e.target.value })} />
                </div>
                <div className="field">
                  <label>Notes</label>
                  <input className="input" value={f.notes} placeholder="Optional" onChange={e => setForm(ap.id, { ...f, notes: e.target.value })} />
                </div>
              </div>
              <div className="flex">
                <button className="btn btn-primary btn-sm" disabled={busy} onClick={() => decide(ap.id, 'approve')}>
                  {busy === ap.id + 'approve' ? <span className="spinner" /> : '✓ Approve & Publish'}
                </button>
                <button className="btn btn-danger btn-sm" disabled={busy} onClick={() => decide(ap.id, 'reject')}>
                  {busy === ap.id + 'reject' ? <span className="spinner" /> : '✕ Reject'}
                </button>
              </div>
            </div>
          )
        })}
      </div>

      <div className="card">
        <div className="card-title"><span>Decision History</span></div>
        <div className="table-wrap">
          <table>
            <thead><tr><th>Deliverable</th><th>Decision</th><th>Reviewer</th><th>Notes</th><th>When</th></tr></thead>
            <tbody>
              {decisions.map(ap => (
                <tr key={ap.id}>
                  <td><Link to={'/deliverables/' + ap.deliverable_id} className="mono small">{ap.deliverable_id}</Link></td>
                  <td><span className={'badge ' + (ap.status === 'approved' ? 'approved' : 'rejected')}>{ap.status}</span></td>
                  <td>{ap.reviewer || '—'}</td>
                  <td className="dim small">{ap.notes || '—'}</td>
                  <td className="dim small">{fmtTime(ap.decided_at)}</td>
                </tr>
              ))}
              {decisions.length === 0 && <tr><td colSpan="5" className="dim" style={{ textAlign: 'center', padding: 20 }}>No decisions yet.</td></tr>}
            </tbody>
          </table>
        </div>
      </div>
    </>
  )
}