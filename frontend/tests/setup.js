/**
 * Vitest setup file
 * Configures testing-library and mocks for React component tests
 */

import '@testing-library/jest-dom'
import { cleanup } from '@testing-library/react'
import { vi, beforeAll, afterAll, afterEach } from 'vitest'
import { server } from './mocks/server'

// Start MSW server before all tests
beforeAll(() => server.listen({ onUnhandledRequest: 'bypass' }))

// Reset handlers and clean up DOM after each test (important for test isolation)
afterEach(() => {
  server.resetHandlers()
  cleanup()
})

// Clean up after all tests
afterAll(() => server.close())

// jsdom usually provides window.localStorage, but in some vitest+jsdom
// configurations the bare global `localStorage` (used by code like
// App.jsx draft restoration) resolves to undefined. Polyfill both forms
// against an in-memory store so component effects run cleanly in tests.
if (typeof globalThis.localStorage === 'undefined' || typeof globalThis.localStorage.getItem !== 'function') {
  const store = new Map()
  const fakeStorage = {
    getItem: (k) => (store.has(k) ? store.get(k) : null),
    setItem: (k, v) => { store.set(k, String(v)) },
    removeItem: (k) => { store.delete(k) },
    clear: () => { store.clear() },
    key: (i) => Array.from(store.keys())[i] ?? null,
    get length() { return store.size },
  }
  globalThis.localStorage = fakeStorage
  if (typeof window !== 'undefined') {
    Object.defineProperty(window, 'localStorage', { value: fakeStorage, writable: true })
  }
}

// Mock window.matchMedia for components that use media queries
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: vi.fn().mockImplementation(query => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: vi.fn(),
    removeListener: vi.fn(),
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })),
})

// Mock ResizeObserver (used by React Flow and other components)
globalThis.ResizeObserver = vi.fn().mockImplementation(() => ({
  observe: vi.fn(),
  unobserve: vi.fn(),
  disconnect: vi.fn(),
}))

// Mock IntersectionObserver
globalThis.IntersectionObserver = vi.fn().mockImplementation(() => ({
  observe: vi.fn(),
  unobserve: vi.fn(),
  disconnect: vi.fn(),
}))

// Mock scrollIntoView (used by ChatPanel and other components)
window.HTMLElement.prototype.scrollIntoView = vi.fn()

// Mock Clerk - hooks must return stable references across renders.
// Returning fresh objects (e.g. fresh getToken vi.fn()) on every call causes
// any useEffect that includes `getToken` in its dep array to re-fire every
// render, infinite-looping until the worker OOMs.
const __clerkAuth = {
  isLoaded: true,
  isSignedIn: true,
  userId: 'test-user-id',
  getToken: vi.fn().mockResolvedValue('test-token'),
}
const __clerkUser = {
  isLoaded: true,
  isSignedIn: true,
  user: {
    id: 'test-user-id',
    firstName: 'Test',
    lastName: 'User',
    emailAddresses: [{ emailAddress: 'test@example.com' }],
  },
}
const __clerk = {
  openSignIn: vi.fn(),
  openSignUp: vi.fn(),
  signOut: vi.fn(),
}
vi.mock('@clerk/clerk-react', () => ({
  useAuth: () => __clerkAuth,
  useUser: () => __clerkUser,
  useClerk: () => __clerk,
  ClerkProvider: ({ children }) => children,
  SignedIn: ({ children }) => children,
  SignedOut: () => null,
  SignInButton: () => null,
  SignOutButton: () => null,
  UserButton: () => null,
}))

// Mock React Router. The mocked hooks must return stable references across
// renders, otherwise effects that include `navigate`/`location` in their dep
// arrays re-fire every render and infinite-loop the test (OOM the worker).
const __stableNavigate = vi.fn()
const __stableLocation = { pathname: '/', search: '', hash: '', state: null }
const __stableParams = {}
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom')
  return {
    ...actual,
    useNavigate: () => __stableNavigate,
    useLocation: () => __stableLocation,
    useParams: () => __stableParams,
  }
})

// Suppress console errors during tests (optional - can be removed for debugging)
// const originalError = console.error
// beforeAll(() => {
//   console.error = (...args) => {
//     if (args[0]?.includes('Warning:')) return
//     originalError.call(console, ...args)
//   }
// })
// afterAll(() => {
//   console.error = originalError
// })
