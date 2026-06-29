import { useEffect, useRef, type CSSProperties } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import {
  CheckCheck,
  Download,
  FileAudio,
  FileText,
  FileVideo,
  Image as ImageIcon,
  Mic,
  Paperclip,
  Phone,
  Search,
  Smile,
  Video,
} from 'lucide-react'
import type { ChatMessage, MediaItem } from '../types'
import { clsx } from '../lib/format'
import {
  REAL_SOP_NAME,
  REAL_SOP_URL,
  REAL_VIDEO_URL,
  isMediaMessage,
  isSopMessage,
  rewriteMessageText,
} from '../lib/livePresentation'

const MEDIA_ICON = { video: FileVideo, audio: FileAudio, image: ImageIcon, document: FileText }

// faint WhatsApp-style backdrop (beige + a low-contrast texture)
const WA_BG: CSSProperties = {
  backgroundColor: '#efeae2',
  backgroundImage:
    'radial-gradient(rgba(120,110,90,0.05) 1px, transparent 1px), radial-gradient(rgba(120,110,90,0.04) 1px, transparent 1px)',
  backgroundSize: '24px 24px, 24px 24px',
  backgroundPosition: '0 0, 12px 12px',
}

export function WhatsAppThread({
  messages,
  name,
  phone,
}: {
  messages: ChatMessage[]
  name?: string
  phone?: string
}) {
  const ref = useRef<HTMLDivElement>(null)
  useEffect(() => {
    if (ref.current) ref.current.scrollTop = ref.current.scrollHeight
  }, [messages.length])

  const display = name || 'Field worker'
  const initial = display.trim().charAt(0).toUpperCase()

  return (
    <div className="flex h-full flex-col overflow-hidden rounded-2xl">
      {/* header — WhatsApp Web style */}
      <div className="flex items-center gap-3 border-b border-black/[0.06] bg-[#f0f2f5] px-3.5 py-2.5">
        <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-[#25d366]/20 text-[13px] font-semibold text-[#1aa251]">
          {initial}
        </div>
        <div className="min-w-0 flex-1">
          <div className="truncate text-[13.5px] font-semibold text-[#111b21]">{display}</div>
          <div className="truncate text-[11px] text-[#667781]">{phone || 'online'}</div>
        </div>
        <div className="flex items-center gap-4 text-[#54656f]">
          <Video size={18} />
          <Search size={17} />
          <Phone size={16} />
        </div>
      </div>

      {/* messages */}
      <div ref={ref} className="relative flex-1 space-y-1.5 overflow-y-auto px-4 py-3" style={WA_BG}>
        <div className="flex justify-center py-1">
          <span className="rounded-md bg-[#ffffff]/85 px-2.5 py-1 text-[10px] font-medium uppercase tracking-wide text-[#54656f] shadow-sm">
            Today
          </span>
        </div>
        <div className="flex justify-center pb-1">
          <span className="max-w-[88%] rounded-md bg-[#fdf3d2] px-2.5 py-1 text-center text-[10.5px] leading-snug text-[#54656f] shadow-sm">
            Messages are end-to-end encrypted. Incident intake routed via Twilio.
          </span>
        </div>

        <AnimatePresence initial={false}>
          {messages.map((m) => {
            const mine = m.from === 'foreman'
            // Presentation transforms — fire only when the matching real event arrives.
            const text = rewriteMessageText(m.text)
            const showVideo = !mine && isMediaMessage(m.text)
            const showSop = isSopMessage(m.from, m.text)
            return (
              <motion.div
                key={m.id}
                initial={{ opacity: 0, y: 6, scale: 0.98 }}
                animate={{ opacity: 1, y: 0, scale: 1 }}
                transition={{ duration: 0.25 }}
                className={clsx('flex', mine ? 'justify-end' : 'justify-start')}
              >
                <div
                  className={clsx(
                    'relative max-w-[82%] rounded-lg px-2 py-1.5 shadow-[0_1px_0.5px_rgba(11,20,26,0.13)]',
                    mine ? 'rounded-tr-sm bg-[#d9fdd3]' : 'rounded-tl-sm bg-white',
                  )}
                >
                  {/* tail */}
                  <span
                    className={clsx('absolute top-0 h-0 w-0 border-[6px] border-transparent', mine ? '-right-[5px]' : '-left-[5px]')}
                    style={mine ? { borderTopColor: '#d9fdd3', borderLeftColor: '#d9fdd3' } : { borderTopColor: '#ffffff', borderRightColor: '#ffffff' }}
                  />
                  {mine && (
                    <div className="text-[11px] font-semibold leading-tight text-[#1fa855]">FOREMAN · bot</div>
                  )}

                  {showVideo ? (
                    <div className="mt-0.5 overflow-hidden rounded-lg">
                      <video
                        src={REAL_VIDEO_URL}
                        controls
                        preload="metadata"
                        playsInline
                        className="block w-full max-w-[250px] rounded-lg bg-black"
                      />
                    </div>
                  ) : (
                    <div className="whitespace-pre-wrap px-0.5 text-[13px] leading-[1.35] text-[#111b21]">{text}</div>
                  )}

                  {showSop && <SopAttachment mine={mine} />}

                  {m.media && m.media.length > 0 && (
                    <div className="mt-1.5 space-y-1">
                      {m.media.map((md) => (
                        <MediaRow key={md.label} md={md} mine={mine} />
                      ))}
                    </div>
                  )}

                  {m.options && (
                    <div className="mt-1.5 flex flex-wrap gap-1.5">
                      {m.options.map((o) => (
                        <span
                          key={o}
                          className={clsx(
                            'rounded-full px-2.5 py-1 text-[11px] font-medium',
                            mine ? 'border border-[#1fa855]/30 bg-white/60 text-[#1a7f4b]' : 'border border-black/10 bg-black/[0.03] text-[#54656f]',
                          )}
                        >
                          {o}
                        </span>
                      ))}
                    </div>
                  )}

                  <div className="mt-0.5 flex items-center justify-end gap-1 px-0.5">
                    <span className="text-[10px] text-[#667781]">{m.ts}</span>
                    {mine && <CheckCheck size={15} className="text-[#53bdeb]" />}
                  </div>
                </div>
              </motion.div>
            )
          })}
        </AnimatePresence>

        {messages.length === 0 && (
          <div className="py-8 text-center text-xs text-[#54656f]">No messages yet.</div>
        )}
      </div>

      {/* composer */}
      <div className="flex items-center gap-2.5 bg-[#f0f2f5] px-3 py-2.5">
        <Smile size={22} className="text-[#54656f]" />
        <Paperclip size={20} className="-rotate-45 text-[#54656f]" />
        <div className="flex-1 rounded-full bg-white px-3.5 py-2 text-[12.5px] text-[#8696a0]">Type a message</div>
        <Mic size={20} className="text-[#54656f]" />
      </div>
    </div>
  )
}

// SOP attached to the bot's analysis reply (the real mc4 install-spec PDF).
function SopAttachment({ mine }: { mine: boolean }) {
  return (
    <a
      href={REAL_SOP_URL}
      target="_blank"
      rel="noreferrer"
      className={clsx(
        'mt-1.5 flex items-center gap-2.5 rounded-lg px-2.5 py-2 transition-colors',
        mine ? 'bg-white/70 hover:bg-white' : 'bg-black/[0.04] hover:bg-black/[0.06]',
      )}
    >
      <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-md bg-[#ea4335]/12 text-[#ea4335]">
        <FileText size={18} />
      </span>
      <div className="min-w-0 flex-1">
        <div className="truncate text-[12px] font-medium text-[#111b21]">{REAL_SOP_NAME}</div>
        <div className="text-[10.5px] text-[#667781]">PDF · 2 pages</div>
      </div>
      <Download size={15} className="shrink-0 text-[#54656f]" />
    </a>
  )
}

function MediaRow({ md, mine }: { md: MediaItem; mine: boolean }) {
  const Icon = MEDIA_ICON[md.kind] ?? FileText
  return (
    <div
      className={clsx(
        'flex items-center gap-2 rounded-md px-2 py-1.5',
        mine ? 'bg-white/55' : 'bg-black/[0.035]',
      )}
    >
      <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded bg-black/[0.06] text-[#54656f]">
        <Icon size={14} />
      </span>
      <div className="min-w-0">
        <div className="truncate text-[11.5px] font-medium text-[#111b21]">{md.label}</div>
        <div className="text-[10px] text-[#667781]">
          {md.meta ?? md.duration ?? md.kind}
        </div>
      </div>
    </div>
  )
}
