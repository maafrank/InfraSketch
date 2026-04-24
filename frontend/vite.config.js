import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': new URL('./src', import.meta.url).pathname,
    },
  },
  build: {
    target: ['es2020', 'safari14', 'chrome90', 'firefox90', 'edge90'],
  },
  esbuild: {
    target: 'es2020',
  },
})
