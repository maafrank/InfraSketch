import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',
    setupFiles: ['./tests/setup.js'],
    globals: true,
    css: true,
    include: ['src/**/*.{test,spec}.{js,jsx}', 'tests/**/*.{test,spec}.{js,jsx}'],
    // Disable file parallelism in CI to avoid worker memory limits
    // Workers have hardcoded ~1.4GB heap that can't be overridden
    // This runs all tests sequentially in the main process
    // eslint-disable-next-line no-undef
    fileParallelism: process.env.CI ? false : true,
  },
})
