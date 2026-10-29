import { useEffect, useRef, useState } from 'react'

// Singleton SSE client shared by all views. One EventSource per browser tab.
let source = null
let listeners = new Set()
let refCount = 0

function ensureSource() {
  if (source) return source
  source = new EventSource('/api/events')
  source.onmessage = (e) => {
    let event
    try { event = JSON.parse(e.data) } catch { return }
    listeners.forEach(fn => { try { fn(event) } catch { /* ignore */ } })
  }
  return source
}

/**
 * Subscribe to the real-time event stream.
 * Returns [events, connected] where `events` is the live buffer (newest first,
 * capped) and `connected` reflects the EventSource state.
 */
export function useEventStream(onEvent, limit = 200) {
  const [events, setEvents] = useState([])
  const [connected, setConnected] = useState(false)
  const cb = useRef(onEvent)
  cb.current = onEvent

  useEffect(() => {
    const handler = (event) => {
      setEvents(prev => [event, ...prev].slice(0, limit))
      cb.current?.(event)
    }
    listeners.add(handler)
    refCount += 1
    const s = ensureSource()
    const onOpen = () => setConnected(s.readyState === EventSource.OPEN)
    const onClose = () => setConnected(false)
    s.addEventListener('open', onOpen)
    s.addEventListener('close', onClose)
    setConnected(s.readyState === EventSource.OPEN)
    return () => {
      listeners.delete(handler)
      refCount -= 1
      s.removeEventListener('open', onOpen)
      s.removeEventListener('close', onClose)
      if (refCount <= 0 && source) {
        source.close()
        source = null
      }
    }
  }, [limit])

  return [events, connected]
}