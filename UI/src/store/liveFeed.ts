import { useEffect } from 'react'
import type { CaseEvent } from '../types'
import { FEED_WS_URL } from '../config'
import { useStore } from './store'

// Wire shape the view-backend pushes over the socket:
//   { case_id: "CASE-0916", event: { kind: "perception.ready", ... } }
// or a snapshot on (re)connect so a late client catches up to current truth:
//   { type: "snapshot", case_id: "CASE-0916", events: [ ...CaseEvent ] }
type WireMsg =
  | { case_id: string; event: CaseEvent }
  | { type: 'snapshot'; case_id: string; events: CaseEvent[] }

// Connect to the live CaseEvent stream and dispatch each event into the store.
// Auto-reconnects with backoff. Returns a disconnect function.
export function connectLiveFeed(url = FEED_WS_URL): () => void {
  let ws: WebSocket | null = null
  let closed = false
  let retry = 0

  const connect = () => {
    if (closed) return
    ws = new WebSocket(url)

    ws.onopen = () => {
      retry = 0
    }

    ws.onmessage = (ev) => {
      const ingest = useStore.getState().ingestEvent
      try {
        const data = JSON.parse(ev.data) as WireMsg | WireMsg[]
        const msgs = Array.isArray(data) ? data : [data]
        for (const m of msgs) {
          if ('type' in m && m.type === 'snapshot') {
            m.events.forEach((e) => ingest(m.case_id, e))
          } else if ('event' in m) {
            ingest(m.case_id, m.event)
          }
        }
      } catch {
        /* ignore malformed frames */
      }
    }

    ws.onclose = () => {
      if (closed) return
      retry += 1
      setTimeout(connect, Math.min(800 * retry, 8000))
    }
    ws.onerror = () => ws?.close()
  }

  connect()
  return () => {
    closed = true
    ws?.close()
  }
}

// Mount once in the dashboard — connects the live CaseEvent socket.
export function useLiveFeed() {
  useEffect(() => {
    return connectLiveFeed()
  }, [])
}
