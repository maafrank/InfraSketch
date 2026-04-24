import js from '@eslint/js'
import globals from 'globals'
import reactHooks from 'eslint-plugin-react-hooks'
import reactRefresh from 'eslint-plugin-react-refresh'
import { defineConfig, globalIgnores } from 'eslint/config'

export default defineConfig([
  globalIgnores(['dist']),
  {
    files: ['**/*.{js,jsx}'],
    extends: [
      js.configs.recommended,
      reactHooks.configs['recommended-latest'],
      reactRefresh.configs.vite,
    ],
    languageOptions: {
      ecmaVersion: 2020,
      globals: globals.browser,
      parserOptions: {
        ecmaVersion: 'latest',
        ecmaFeatures: { jsx: true },
        sourceType: 'module',
      },
    },
    rules: {
      'no-unused-vars': ['error', { varsIgnorePattern: '^[A-Z_]' }],
    },
  },
  // Test files and config files need Node.js globals
  {
    files: [
      '**/*.test.{js,jsx}',
      '**/*.spec.{js,jsx}',
      'vitest.config.js',
      'playwright.config.js',
      'tests/**/*.{js,jsx}',
      'e2e/**/*.{js,jsx}',
    ],
    languageOptions: {
      globals: {
        ...globals.node,
      },
    },
  },
])
