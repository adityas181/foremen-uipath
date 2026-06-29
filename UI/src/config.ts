// Live feed: the UI binds to a real WebSocket stream of CaseEvents from the
// view-backend.   .env →  VITE_FEED_WS_URL=wss://your-backend/ws
export const FEED_WS_URL: string =
  (import.meta.env.VITE_FEED_WS_URL as string) || 'ws://localhost:8000/ws'

// HTTP(S) origin of the view-backend, derived from the WS URL. Used to resolve
// relative media URLs the backend emits (e.g. proxied call recordings:
// "/recording/<acct>/<sid>"  →  "https://<backend-host>/recording/...").
export const FEED_HTTP_BASE: string = FEED_WS_URL
  .replace(/^ws/, 'http') // ws→http, wss→https (only the leading scheme)
  .replace(/\/ws\/?$/, '') // strip the trailing /ws path

// Resolve a possibly-relative media URL against the backend origin.
export function resolveMediaUrl(url?: string): string | undefined {
  if (!url) return undefined
  return url.startsWith('/') ? FEED_HTTP_BASE + url : url
}
