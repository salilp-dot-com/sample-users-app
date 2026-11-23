import react from '@vitejs/plugin-react'
import { defineConfig } from 'vitest/config'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',
    setupFiles: ['./src/test/setup.ts'],
    // Tests use the default auth mode unless a test stubs VITE_AUTH_MODE itself.
    env: { VITE_AUTH_MODE: 'localStorage', VITE_API_URL: 'http://api.test' },
  },
})
