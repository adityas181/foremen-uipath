import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// base: './' keeps asset paths relative — required if this is ever packaged as a
// UiPath Coded App (mounted at ORG.uipath.host/<app>), and harmless locally.
export default defineConfig({
  base: './',
  plugins: [react()],
  server: {
    port: 5173,
    open: true,
  },
})
