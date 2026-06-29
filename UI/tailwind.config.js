/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        // Warm near-black (kept for dark image frames / rare contrast accents)
        carbon: {
          950: '#08090b',
          900: '#0d0f12',
          850: '#121519',
          800: '#171b20',
          750: '#1d2228',
          700: '#252b33',
          600: '#323a44',
          500: '#454f5c',
        },
        // Ink — text on light surfaces
        ink: {
          900: '#14171c',
          800: '#23272e',
          700: '#383f48',
          600: '#4d5560',
          500: '#697079',
          400: '#969ca5',
          300: '#bdc2c9',
          200: '#dcdfe3',
        },
        // Paper / page surfaces (clean cool near-white — calm, editorial)
        page: '#f6f7fb',
        paper: {
          DEFAULT: '#ffffff',
          50: '#f8f9fc',
          100: '#f1f3f9',
          200: '#e7eaf1',
        },
        // Legacy cream (still used as light surfaces in a few places)
        cream: {
          50: '#ffffff',
          100: '#f6f5f0',
          200: '#edebe4',
          300: '#e2dfd6',
          400: '#d3cec1',
        },
        // FOREMAN brand blue
        brand: {
          50: '#eef5ff',
          100: '#d9e9ff',
          200: '#b6d3ff',
          300: '#85b4ff',
          400: '#4f8dff',
          500: '#2f6dff',
          600: '#1a52f0',
          700: '#1740c4',
          800: '#17379b',
          900: '#18327a',
        },
        // Pastel accent family (TwelveLabs blob hues — green/blue/cyan + warm)
        pastel: {
          pink: '#f6c9e0',
          rose: '#fbd6cf',
          amber: '#f6d79a',
          lemon: '#f1ecae',
          mint: '#b9e6ad',
          sky: '#aed3f4',
          periwinkle: '#bcc6f3',
          lilac: '#d3c3f1',
          aqua: '#a8e6e0',
        },
        // Semantic status palette (tuned for legibility on white)
        ok: '#1aa251',
        warn: '#c77b08',
        danger: '#e23b3b',
        info: '#1d84d6',
        violet: '#7c5cdb',
      },
      fontFamily: {
        // Editorial serif for big display headings (the elegant, professional voice)
        serif: ['Fraunces', 'Georgia', 'Cambria', 'serif'],
        display: ['"General Sans"', 'Inter', 'system-ui', '-apple-system', 'Segoe UI', 'sans-serif'],
        sans: ['Inter', 'system-ui', '-apple-system', 'Segoe UI', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'ui-monospace', 'SFMono-Regular', 'Menlo', 'monospace'],
      },
      letterSpacing: {
        tightest: '-0.018em',
      },
      borderRadius: {
        '4xl': '2rem',
        '5xl': '2.5rem',
      },
      backgroundImage: {
        // Signature soft pastel mesh (the TwelveLabs blob palette: green/blue/cyan + warm)
        'mesh-pastel':
          'radial-gradient(55% 70% at 10% 20%, #cdeec6 0%, transparent 60%), radial-gradient(50% 60% at 80% 14%, #b9dff6 0%, transparent 58%), radial-gradient(55% 65% at 88% 78%, #f7d6e6 0%, transparent 60%), radial-gradient(50% 60% at 18% 86%, #d6c9f3 0%, transparent 60%)',
        'mesh-pastel-soft':
          'radial-gradient(45% 55% at 12% 18%, #d9f0d2 0%, transparent 62%), radial-gradient(42% 52% at 84% 18%, #cfe7f9 0%, transparent 60%), radial-gradient(46% 56% at 82% 84%, #f9e2ec 0%, transparent 62%), radial-gradient(42% 52% at 20% 86%, #e0d6f5 0%, transparent 62%)',
        // Hero blob field (green -> cyan -> blue, like Theme.png)
        'blob-cool':
          'radial-gradient(40% 60% at 20% 70%, #b6e8b0 0%, transparent 62%), radial-gradient(45% 65% at 55% 60%, #a7dcf2 0%, transparent 62%), radial-gradient(40% 60% at 85% 45%, #9fd0f5 0%, transparent 62%)',
        'brand-sheen': 'linear-gradient(115deg, #2f6dff 0%, #7c5cdb 48%, #e26fb0 100%)',
        'page-texture':
          'radial-gradient(60% 50% at 85% 0%, rgba(120,190,255,0.10) 0%, transparent 60%), radial-gradient(50% 50% at 5% 100%, rgba(150,230,180,0.10) 0%, transparent 60%)',
      },
      boxShadow: {
        glow: '0 1px 2px rgba(20,23,28,0.04), 0 20px 60px -22px rgba(47,109,255,0.22)',
        'card-light': '0 1px 2px rgba(20,23,28,0.03), 0 12px 34px -26px rgba(20,23,28,0.14)',
        'card-soft': '0 1px 0 rgba(20,23,28,0.02), 0 8px 24px -20px rgba(20,23,28,0.12)',
        'card-flat': '0 1px 2px rgba(20,23,28,0.03)',
        'card-hover': '0 1px 2px rgba(20,23,28,0.04), 0 22px 48px -28px rgba(28,40,90,0.30)',
        pill: '0 1px 2px rgba(20,23,28,0.04), 0 8px 22px -16px rgba(20,23,28,0.18)',
        sidebar: '1px 0 0 rgba(20,23,28,0.05)',
      },
      keyframes: {
        'pulse-ring': {
          '0%': { boxShadow: '0 0 0 0 rgba(47,109,255,0.35)' },
          '70%': { boxShadow: '0 0 0 12px rgba(47,109,255,0)' },
          '100%': { boxShadow: '0 0 0 0 rgba(47,109,255,0)' },
        },
        'fade-up': {
          '0%': { opacity: '0', transform: 'translateY(10px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        float: {
          '0%,100%': { transform: 'translateY(0)' },
          '50%': { transform: 'translateY(-12px)' },
        },
        'float-slow': {
          '0%,100%': { transform: 'translateY(0) rotate(0deg)' },
          '50%': { transform: 'translateY(-18px) rotate(1.5deg)' },
        },
        drift: {
          '0%': { backgroundPosition: '0% 50%' },
          '50%': { backgroundPosition: '100% 50%' },
          '100%': { backgroundPosition: '0% 50%' },
        },
        waveform: {
          '0%,100%': { transform: 'scaleY(0.5)' },
          '50%': { transform: 'scaleY(1)' },
        },
        marquee: {
          '0%': { transform: 'translateX(0)' },
          '100%': { transform: 'translateX(-50%)' },
        },
        shimmer: {
          '100%': { transform: 'translateX(100%)' },
        },
        'fade-in': {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
      },
      animation: {
        'pulse-ring': 'pulse-ring 1.8s cubic-bezier(0.4,0,0.6,1) infinite',
        'fade-up': 'fade-up 0.45s ease-out both',
        float: 'float 6s ease-in-out infinite',
        'float-slow': 'float-slow 9s ease-in-out infinite',
        drift: 'drift 14s ease infinite',
        waveform: 'waveform 1.2s ease-in-out infinite',
        marquee: 'marquee 40s linear infinite',
        shimmer: 'shimmer 1.6s ease-in-out infinite',
        'fade-in': 'fade-in 0.4s ease-out both',
      },
    },
  },
  plugins: [],
}
