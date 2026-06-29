import { Layers } from 'lucide-react'
import uipath from '../assets/logos/uipath.png'
import maestro from '../assets/logos/maestro.png'
import actionCenter from '../assets/logos/action-center.png'
import langgraph from '../assets/logos/langgraph.png'
import neo4j from '../assets/logos/neo4j.png'
import gemini from '../assets/logos/gemini.png'
import gmail from '../assets/logos/gmail.png'
import claudeCode from '../assets/logos/claude-code.png'
import twilioWhatsapp from '../assets/logos/twilio-whatsapp.png'

// The stack FOREMAN is built on — rendered as a continuous, paused-on-hover chain.
const STACK_LOGOS: { src: string; alt: string }[] = [
  { src: uipath, alt: 'UiPath' },
  { src: maestro, alt: 'UiPath Maestro' },
  { src: actionCenter, alt: 'UiPath Action Center' },
  { src: langgraph, alt: 'LangGraph' },
  { src: claudeCode, alt: 'Claude' },
  { src: gemini, alt: 'Google Gemini' },
  { src: neo4j, alt: 'Neo4j' },
  { src: twilioWhatsapp, alt: 'Twilio + WhatsApp' },
  { src: gmail, alt: 'Gmail' },
]

export function LogoMarquee() {
  // duplicated once so translateX(-50%) loops seamlessly
  const items = [...STACK_LOGOS, ...STACK_LOGOS]
  return (
    <section className="relative border-y border-ink-900/[0.06] bg-white/60 py-6">
      <div className="mx-auto max-w-[1340px] px-6">
        <div className="group flex items-center gap-5">
          {/* fixed "Built on" pill — the chain scrolls past it */}
          <div className="relative z-10 flex shrink-0 items-center gap-2 rounded-lg border border-ink-900/[0.08] bg-white px-3.5 py-2 shadow-card-soft">
            <span className="flex h-6 w-6 items-center justify-center rounded-full bg-brand-500/12 text-brand-600">
              <Layers size={13} />
            </span>
            <span className="whitespace-nowrap text-[12.5px] font-semibold text-ink-700">Built Using</span>
          </div>

          {/* moving chain */}
          <div className="relative flex-1 overflow-hidden [mask-image:linear-gradient(to_right,transparent,#000_5%,#000_95%,transparent)]">
            <div className="fm-marquee flex w-max items-center">
              {items.map((l, i) => (
                <div
                  key={i}
                  className="mr-3 flex h-14 shrink-0 items-center justify-center overflow-hidden rounded-xl border border-ink-900/[0.06] bg-white px-6 shadow-card-soft"
                  aria-hidden={i >= STACK_LOGOS.length}
                >
                  <img
                    src={l.src}
                    alt={l.alt}
                    draggable={false}
                    className="h-7 w-auto select-none object-contain opacity-90 transition-opacity duration-200 hover:opacity-100"
                  />
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}
