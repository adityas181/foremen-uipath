import { useEffect, useState, type ReactNode } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { Check, Copy, FileText, ShieldAlert, X } from 'lucide-react'

// Load every SKILL.md as raw text at build time, keyed by /skills/<id>.md
const SKILL_FILES = import.meta.glob('/skills/*.md', {
  eager: true,
  query: '?raw',
  import: 'default',
}) as Record<string, string>

export function skillFileExists(id: string): boolean {
  return !!SKILL_FILES[`/skills/${id}.md`]
}

// ── frontmatter (YAML-ish) + body split ─────────────────────────────────────
function parse(raw: string): { fm: [string, string][]; body: string } {
  const m = raw.match(/^---\r?\n([\s\S]*?)\r?\n---\r?\n?([\s\S]*)$/)
  if (!m) return { fm: [], body: raw }
  const fm: [string, string][] = []
  for (const line of m[1].split('\n')) {
    if (/^\s/.test(line)) {
      // nested (e.g. match_key:) — fold into the parent row
      const t = line.trim()
      if (fm.length && t) fm[fm.length - 1][1] += (fm[fm.length - 1][1] ? ' · ' : '') + clean(t)
    } else {
      const idx = line.indexOf(':')
      if (idx > -1) fm.push([line.slice(0, idx).trim(), clean(line.slice(idx + 1).trim())])
    }
  }
  return { fm, body: m[2] }
}

function clean(v: string): string {
  return v.replace(/^\[|\]$/g, '').replace(/"/g, '').trim()
}

// ── inline markdown (**bold**, `code`) ──────────────────────────────────────
function inline(text: string): ReactNode[] {
  const out: ReactNode[] = []
  const re = /\*\*([^*]+)\*\*|`([^`]+)`/g
  let last = 0
  let m: RegExpExecArray | null
  let k = 0
  while ((m = re.exec(text))) {
    if (m.index > last) out.push(text.slice(last, m.index))
    if (m[1] !== undefined) out.push(<strong key={k++} className="font-semibold text-ink-900">{m[1]}</strong>)
    else out.push(<code key={k++} className="rounded bg-ink-900/[0.05] px-1 py-0.5 font-mono text-[12px] text-brand-700">{m[2]}</code>)
    last = re.lastIndex
  }
  if (last < text.length) out.push(text.slice(last))
  return out
}

// ── block-level markdown ────────────────────────────────────────────────────
type Block =
  | { t: 'h'; level: number; text: string }
  | { t: 'p'; text: string }
  | { t: 'ul' | 'ol'; items: string[] }
  | { t: 'hr' }

function parseBody(body: string): Block[] {
  const blocks: Block[] = []
  let cur: Block | null = null
  const push = () => { if (cur) { blocks.push(cur); cur = null } }
  for (const raw of body.split('\n')) {
    const indented = /^\s/.test(raw)
    const t = raw.trim()
    if (t === '') { push(); continue }
    const h = t.match(/^(#{1,4})\s+(.*)$/)
    if (h) { push(); blocks.push({ t: 'h', level: h[1].length, text: h[2] }); continue }
    if (/^---+$/.test(t)) { push(); blocks.push({ t: 'hr' }); continue }
    const bullet = t.match(/^[-*]\s+(.*)$/)
    if (bullet) {
      if (!cur || cur.t !== 'ul') { push(); cur = { t: 'ul', items: [] } }
      ;(cur as { items: string[] }).items.push(bullet[1])
      continue
    }
    const ol = t.match(/^\d+\.\s+(.*)$/)
    if (ol) {
      if (!cur || cur.t !== 'ol') { push(); cur = { t: 'ol', items: [] } }
      ;(cur as { items: string[] }).items.push(ol[1])
      continue
    }
    // continuation of a list item / paragraph, or a fresh paragraph
    if (cur && (cur.t === 'ul' || cur.t === 'ol') && indented) {
      const items = (cur as { items: string[] }).items
      items[items.length - 1] += ' ' + t
    } else if (cur && cur.t === 'p') {
      cur.text += ' ' + t
    } else {
      push()
      cur = { t: 'p', text: t }
    }
  }
  push()
  return blocks
}

function Body({ body }: { body: string }) {
  return (
    <div className="space-y-3">
      {parseBody(body).map((b, i) => {
        if (b.t === 'hr') return <hr key={i} className="border-ink-900/[0.08]" />
        if (b.t === 'h')
          return (
            <h3 key={i} className={b.level <= 1 ? 'pt-1 text-[17px] font-semibold text-ink-900' : 'pt-1 text-[14px] font-semibold text-ink-800'}>
              {inline(b.text)}
            </h3>
          )
        if (b.t === 'p') return <p key={i} className="text-[13px] leading-relaxed text-ink-600">{inline(b.text)}</p>
        const cls = 'ml-1 space-y-1.5 text-[13px] leading-relaxed text-ink-600'
        return b.t === 'ul' ? (
          <ul key={i} className={cls}>
            {b.items.map((it, j) => (
              <li key={j} className="flex gap-2">
                <span className="mt-[7px] h-1 w-1 shrink-0 rounded-full bg-brand-500/60" />
                <span>{inline(it)}</span>
              </li>
            ))}
          </ul>
        ) : (
          <ol key={i} className={cls}>
            {b.items.map((it, j) => (
              <li key={j} className="flex gap-2.5">
                <span className="mt-px font-mono text-[11px] font-semibold text-brand-600/70">{String(j + 1).padStart(2, '0')}</span>
                <span>{inline(it)}</span>
              </li>
            ))}
          </ol>
        )
      })}
    </div>
  )
}

// ── the modal ────────────────────────────────────────────────────────────────
export function SkillFileModal({ id, onClose }: { id: string | null; onClose: () => void }) {
  const [copied, setCopied] = useState(false)

  useEffect(() => {
    if (!id) return
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && onClose()
    window.addEventListener('keydown', onKey)
    document.body.style.overflow = 'hidden'
    setCopied(false)
    return () => {
      window.removeEventListener('keydown', onKey)
      document.body.style.overflow = ''
    }
  }, [id, onClose])

  const raw = id ? SKILL_FILES[`/skills/${id}.md`] : undefined
  const { fm, body } = raw ? parse(raw) : { fm: [], body: '' }
  const meta = Object.fromEntries(fm)
  const title = (meta.title || id || '').replace(/^"|"$/g, '')
  const chips = ['domain', 'severity', 'status', 'approve_count'].filter((k) => meta[k])
  const standards = (meta.standards || '').split(/·|,/).map((s) => s.trim()).filter(Boolean)

  return (
    <AnimatePresence>
      {id && raw && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="fixed inset-0 z-[100] flex items-center justify-center p-4"
        >
          <div className="absolute inset-0 bg-carbon-950/45 backdrop-blur-sm" onClick={onClose} />
          <motion.div
            initial={{ opacity: 0, y: 14, scale: 0.98 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 14, scale: 0.98 }}
            transition={{ type: 'spring', stiffness: 260, damping: 24 }}
            className="relative flex max-h-[86vh] w-full max-w-3xl flex-col overflow-hidden rounded-2xl border border-ink-900/[0.10] bg-white shadow-glow"
          >
            {/* header */}
            <div className="flex items-center justify-between gap-3 border-b border-ink-900/[0.07] bg-paper-50 px-5 py-3.5">
              <div className="flex min-w-0 items-center gap-2.5">
                <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-brand-500/10 text-brand-600">
                  <FileText size={15} />
                </span>
                <div className="min-w-0">
                  <div className="font-mono text-[12.5px] font-semibold text-ink-900">{id}</div>
                  <div className="font-mono text-[10px] text-ink-400">skills/{id}.md</div>
                </div>
              </div>
              <div className="flex items-center gap-1.5">
                <button
                  onClick={() => { navigator.clipboard?.writeText(raw); setCopied(true); setTimeout(() => setCopied(false), 1400) }}
                  className="inline-flex items-center gap-1.5 rounded-md border border-ink-900/[0.10] bg-white px-2.5 py-1 text-[11px] font-medium text-ink-600 transition-colors hover:bg-paper-50"
                >
                  {copied ? <Check size={12} className="text-ok" /> : <Copy size={12} />}
                  {copied ? 'Copied' : 'Copy'}
                </button>
                <button onClick={onClose} className="flex h-7 w-7 items-center justify-center rounded-full text-ink-400 transition-colors hover:bg-ink-900/[0.06] hover:text-ink-900">
                  <X size={16} />
                </button>
              </div>
            </div>

            {/* scroll body */}
            <div className="min-h-0 flex-1 overflow-y-auto px-6 py-5">
              <h2 className="font-display text-[19px] font-semibold leading-snug tracking-tight text-ink-900">{title}</h2>

              {/* meta chips */}
              <div className="mt-3 flex flex-wrap items-center gap-1.5">
                {chips.map((k) => (
                  <span key={k} className="inline-flex items-center gap-1 rounded-md border border-ink-900/[0.10] bg-paper-50 px-2 py-0.5 text-[10.5px] text-ink-600">
                    <span className="text-ink-400">{k.replace(/_/g, ' ')}</span>
                    <span className="font-mono font-medium text-ink-800">{meta[k]}</span>
                  </span>
                ))}
                {meta.safety_protocol === 'true' && (
                  <span className="inline-flex items-center gap-1 rounded-md border border-danger/30 bg-danger/10 px-2 py-0.5 text-[10.5px] font-semibold text-danger">
                    <ShieldAlert size={11} /> safety-critical
                  </span>
                )}
              </div>

              {/* standards */}
              {standards.length > 0 && (
                <div className="mt-2.5 flex flex-wrap items-center gap-1.5">
                  <span className="text-[10px] uppercase tracking-wide text-ink-400">standards</span>
                  {standards.map((s) => (
                    <span key={s} className="rounded-md border border-ink-900/[0.07] bg-paper-50 px-1.5 py-0.5 font-mono text-[10px] text-ink-500">{s}</span>
                  ))}
                </div>
              )}

              {/* match-key / fingerprint */}
              {meta.match_key && (
                <div className="mt-3 rounded-xl border border-brand-400/20 bg-brand-500/[0.04] px-3 py-2 font-mono text-[11px] text-ink-600">
                  <span className="text-ink-400">match_key · </span>
                  {meta.match_key}
                </div>
              )}

              <hr className="my-4 border-ink-900/[0.07]" />

              <Body body={body} />

              {/* citations / source */}
              <div className="mt-5 flex flex-col gap-2 border-t border-ink-900/[0.07] pt-4">
                {meta.citations && (
                  <Line label="citations" value={meta.citations} />
                )}
                {meta.source_cases && <Line label="source cases" value={meta.source_cases} />}
              </div>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  )
}

function Line({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex flex-wrap items-center gap-1.5">
      <span className="text-[10px] uppercase tracking-wide text-ink-400">{label}</span>
      {value.split(/·|,/).map((v) => v.trim()).filter(Boolean).map((v) => (
        <span key={v} className="rounded-md border border-ink-900/[0.07] bg-paper-50 px-1.5 py-0.5 font-mono text-[10px] text-ink-500">{v}</span>
      ))}
    </div>
  )
}
