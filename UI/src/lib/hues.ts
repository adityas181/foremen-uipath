import type { PastelHue } from '../types'

export const HUE_HEX: Record<PastelHue, string> = {
  sky: '#7fb4f5',
  lilac: '#b79df0',
  mint: '#74c96a',
  amber: '#e6ab3e',
  rose: '#ef8084',
  periwinkle: '#8e9cf0',
  pink: '#e98fc4',
  lemon: '#cdbf52',
}

// Soft pastel gradient backgrounds for LIGHT cards (the Search/Analyze/Embed look)
export const HUE_SOFT: Record<PastelHue, string> = {
  sky: 'bg-gradient-to-br from-pastel-sky via-white to-pastel-periwinkle',
  lilac: 'bg-gradient-to-br from-pastel-lilac via-white to-pastel-pink',
  mint: 'bg-gradient-to-br from-pastel-mint via-white to-pastel-lemon',
  amber: 'bg-gradient-to-br from-pastel-amber via-white to-pastel-rose',
  rose: 'bg-gradient-to-br from-pastel-rose via-white to-pastel-pink',
  periwinkle: 'bg-gradient-to-br from-pastel-periwinkle via-white to-pastel-sky',
  pink: 'bg-gradient-to-br from-pastel-pink via-white to-pastel-lilac',
  lemon: 'bg-gradient-to-br from-pastel-lemon via-white to-pastel-mint',
}

export type Tone = 'info' | 'ok' | 'warn' | 'danger' | 'human' | 'agent' | 'muted'

export const TONE_HEX: Record<Tone, string> = {
  info: '#3ba7f0',
  ok: '#34c759',
  warn: '#f5a623',
  danger: '#ff4d4f',
  human: '#9b7bf0',
  agent: '#7fb4f5',
  muted: '#7c8696',
}
