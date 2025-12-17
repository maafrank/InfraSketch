import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'

// eslint-disable-next-line no-undef
const isCI = process.env.CI === 'true'

export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',
    setupFiles: ['./tests/setup.js'],
    globals: true,
    css: true,
    include: ['src/**/*.{test,spec}.{js,jsx}', 'tests/**/*.{test,spec}.{js,jsx}'],
    // In CI, use forks with explicit memory settings and disable isolation
    // Workers/forks don't inherit NODE_OPTIONS, must pass via execArgv
    // isolate: false reduces memory by sharing module instances between tests
    ...(isCI && {
      pool: 'forks',
      isolate: false,
      poolOptions: {
        forks: {
          singleFork: true,
          execArgv: ['--max-old-space-size=4096'],
        },
      },
    }),
  },
})
