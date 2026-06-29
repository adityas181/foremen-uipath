export function inr(n: number): string {
  return '₹' + n.toLocaleString('en-IN')
}

export function inrCompact(n: number): string {
  if (n >= 100000) return '₹' + (n / 100000).toFixed(n % 100000 === 0 ? 0 : 1) + 'L'
  if (n >= 1000) return '₹' + (n / 1000).toFixed(n % 1000 === 0 ? 0 : 1) + 'k'
  return '₹' + n
}

export function pct(n: number): string {
  return Math.round(n * 100) + '%'
}

export function clsx(...parts: (string | false | null | undefined)[]): string {
  return parts.filter(Boolean).join(' ')
}

// Format a relative ms offset as a wall-clock-ish demo timestamp (14:3x).
export function demoClock(ms: number): string {
  const base = 14 * 3600 + 28 * 60 // 14:28:00
  const t = base + Math.floor(ms / 1000)
  const h = Math.floor(t / 3600) % 24
  const m = Math.floor((t % 3600) / 60)
  const s = t % 60
  return `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`
}
