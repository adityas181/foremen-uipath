// ─────────────────────────────────────────────────────────────────────────────
// Live presentation transforms.
//
// In LIVE mode the chat / media / activity all stream from the real agents. A few
// of those raw payloads aren't browser-friendly (the worker clip is a Twilio media
// SID the browser can't fetch; the weather log is a bare timestamp). These helpers
// are PRESENTATION-ONLY: they swap in the real local clip + SOP, attach the SOP to
// the bot's analysis reply, warm up one terse line, and turn the weather timestamp
// into its safe-window sentence — and each one only fires when the matching real
// event actually arrives, so the view stays in sync with the data.
// ─────────────────────────────────────────────────────────────────────────────
import realVideo from '../assets/field-clip.mp4'
import realSop from '../assets/mc4-connector-install-spec.pdf'

export const REAL_VIDEO_URL: string = realVideo
export const REAL_SOP_URL: string = realSop
export const REAL_SOP_NAME = 'mc4-connector-install-spec.pdf'

// The worker's "(sent a photo / video)" placeholder → render the real clip.
export const isMediaMessage = (text: string): boolean =>
  /\bsent (a|the)?\s*(photo|video|clip|media)\b/i.test(text) || /\bphoto\s*\/\s*video\b/i.test(text)

// The bot's analysis reply that carries the SOP → attach the SOP document.
export const isSopMessage = (from: string, text: string): boolean =>
  from === 'foreman' && /(step[-\s]?by[-\s]?step\s*sop|sop\s*attached|analysis\s*complete)/i.test(text)

// Warm up the agent's terse confirm line (kept in sync by matching its text).
export function rewriteMessageText(text: string): string {
  if (/got everything i need/i.test(text)) {
    return "Thanks — I've got the media, the issue and the asset. Analysing now."
  }
  return text
}

// Weather activity entries arrive as a bare timestamp ("2026-06-27 16:30 IST").
// Show the human-readable safe window instead — no raw clock time.
const SAFE_WINDOW_TEXT = 'Dry and lightning-free — a safe 3-hour window for the work.'

export const isWeatherTiming = (source: string, text: string): boolean =>
  /weather/i.test(source) &&
  (/^\s*\d{4}-\d{2}-\d{2}/.test(text) || /\b\d{1,2}:\d{2}\b.*\bIST\b/i.test(text) || /\bIST\b\s*$/i.test(text.trim()))

export function rewriteLogText(source: string, text: string): string {
  if (isWeatherTiming(source, text)) return SAFE_WINDOW_TEXT
  return text
}
