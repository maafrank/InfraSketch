import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { ClerkProvider } from '@clerk/clerk-react'
import { HelmetProvider } from 'react-helmet-async'
import ThemeProvider from './contexts/ThemeContext'
import './index.css'
import App from './App.jsx'
import SessionHistory from './components/SessionHistory.jsx'
import PrivacyPolicy from './components/PrivacyPolicy.jsx'
import TermsOfService from './components/TermsOfService.jsx'
import AboutPage from './components/AboutPage.jsx'
import CareersPage from './components/CareersPage.jsx'
import ContactPage from './components/ContactPage.jsx'
import BlogListPage from './components/BlogListPage.jsx'
import BlogPostPage from './components/BlogPostPage.jsx'
import SettingsPage from './components/SettingsPage.jsx'

const PUBLISHABLE_KEY = import.meta.env.VITE_CLERK_PUBLISHABLE_KEY

if (!PUBLISHABLE_KEY) {
  console.warn("Missing Publishable Key. Authentication features will not work.")
}

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <HelmetProvider>
      <ClerkProvider publishableKey={PUBLISHABLE_KEY} afterSignOutUrl="/">
        <ThemeProvider>
          <BrowserRouter>
            <Routes>
              <Route path="/" element={<App />} />
              <Route path="/history" element={<SessionHistory />} />
              <Route path="/session/:sessionId" element={<App resumeMode={true} />} />
              <Route path="/privacy" element={<PrivacyPolicy />} />
              <Route path="/terms" element={<TermsOfService />} />
              <Route path="/about" element={<AboutPage />} />
              <Route path="/careers" element={<CareersPage />} />
              <Route path="/contact" element={<ContactPage />} />
              <Route path="/blog" element={<BlogListPage />} />
              <Route path="/blog/:slug" element={<BlogPostPage />} />
              <Route path="/settings" element={<SettingsPage />} />
            </Routes>
          </BrowserRouter>
        </ThemeProvider>
      </ClerkProvider>
    </HelmetProvider>
  </StrictMode>,
)
