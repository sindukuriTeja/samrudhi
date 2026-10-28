import React, { useMemo } from 'react'

// Minimal, safe Markdown renderer (no external deps, no raw HTML injection).
function renderInline(text, keyBase) {
  const parts = []
  // split on **bold**, `code`, *italic*
  const regex = /(\*\*[^*]+\*\*|`[^`]+`|\*[^*]+\*)/g
  let last = 0
  let m
  let i = 0
  while ((m = regex.exec(text)) !== null) {
    if (m.index > last) parts.push(text.slice(last, m.index))
    const tok = m[0]
    if (tok.startsWith('**')) parts.push(<strong key={`${keyBase}-b${i}`}>{tok.slice(2, -2)}</strong>)
    else if (tok.startsWith('`')) parts.push(<code key={`${keyBase}-c${i}`}>{tok.slice(1, -1)}</code>)
    else parts.push(<em key={`${keyBase}-i${i}`}>{tok.slice(1, -1)}</em>)
    last = m.index + tok.length
    i++
  }
  if (last < text.length) parts.push(text.slice(last))
  return parts
}

function Table({ rows }) {
  const [headers, ...body] = rows
  return (
    <table>
      <thead>
        <tr>{headers.map((h, i) => <th key={i}>{renderInline(h, `th${i}`)}</th>)}</tr>
      </thead>
      <tbody>
        {body.map((r, ri) => (
          <tr key={ri}>{r.map((c, ci) => <td key={ci}>{renderInline(c, `td${ri}-${ci}`)}</td>)}</tr>
        ))}
      </tbody>
    </table>
  )
}

export default function Markdown({ text }) {
  const blocks = useMemo(() => {
    if (!text) return []
    const lines = text.split('\n')
    const out = []
    let i = 0
    while (i < lines.length) {
      const line = lines[i]
      if (!line.trim()) { i++; continue }
      // table
      if (line.trim().startsWith('|') && i + 1 < lines.length && /^\s*\|?[\s:|-]+\|?\s*$/.test(lines[i + 1]) && lines[i + 1].includes('-')) {
        const rows = []
        while (i < lines.length && lines[i].trim().startsWith('|')) {
          const cells = lines[i].trim().replace(/^\||\|$/g, '').split('|').map(c => c.trim())
          rows.push(cells)
          i++
        }
        if (rows.length > 1) out.push({ type: 'table', rows, key: out.length })
        continue
      }
      const h = line.match(/^(#{1,4})\s+(.*)$/)
      if (h) { out.push({ type: 'h' + h[1].length, text: h[2], key: out.length }); i++; continue }
      if (/^(-{3,}|\*{3,})\s*$/.test(line.trim())) { out.push({ type: 'hr', key: out.length }); i++; continue }
      if (line.trim().startsWith('> ')) {
        const q = []
        while (i < lines.length && lines[i].trim().startsWith('> ')) { q.push(lines[i].trim().slice(2)); i++ }
        out.push({ type: 'quote', text: q.join(' '), key: out.length }); continue
      }
      if (/^\s*[-*]\s+/.test(line)) {
        const items = []
        while (i < lines.length && /^\s*[-*]\s+/.test(lines[i])) { items.push(lines[i].replace(/^\s*[-*]\s+/, '')); i++ }
        out.push({ type: 'ul', items, key: out.length }); continue
      }
      if (/^\s*\d+\.\s+/.test(line)) {
        const items = []
        while (i < lines.length && /^\s*\d+\.\s+/.test(lines[i])) { items.push(lines[i].replace(/^\s*\d+\.\s+/, '')); i++ }
        out.push({ type: 'ol', items, key: out.length }); continue
      }
      // paragraph: gather until blank line
      const para = [line]
      i++
      while (i < lines.length && lines[i].trim() && !/^(#{1,4}\s|\s*[-*]\s|\s*\d+\.\s|\||> )/.test(lines[i])) {
        para.push(lines[i]); i++
      }
      out.push({ type: 'p', text: para.join(' '), key: out.length })
    }
    return out
  }, [text])

  return (
    <div className="md">
      {blocks.map(b => {
        switch (b.type) {
          case 'h1': return <h1 key={b.key}>{renderInline(b.text, `h1${b.key}`)}</h1>
          case 'h2': return <h2 key={b.key}>{renderInline(b.text, `h2${b.key}`)}</h2>
          case 'h3': return <h3 key={b.key}>{renderInline(b.text, `h3${b.key}`)}</h3>
          case 'h4': return <h3 key={b.key}>{renderInline(b.text, `h4${b.key}`)}</h3>
          case 'hr': return <hr key={b.key} />
          case 'quote': return <blockquote key={b.key}>{renderInline(b.text, `q${b.key}`)}</blockquote>
          case 'ul': return <ul key={b.key}>{b.items.map((it, i) => <li key={i}>{renderInline(it, `ul${b.key}-${i}`)}</li>)}</ul>
          case 'ol': return <ol key={b.key}>{b.items.map((it, i) => <li key={i}>{renderInline(it, `ol${b.key}-${i}`)}</li>)}</ol>
          case 'table': return <Table key={b.key} rows={b.rows} />
          default: return <p key={b.key}>{renderInline(b.text, `p${b.key}`)}</p>
        }
      })}
    </div>
  )
}