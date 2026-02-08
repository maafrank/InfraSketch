import { StrictMode } from 'react'
import { createRoot, hydrateRoot } from 'react-dom/client'
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
import AchievementsPage from './components/AchievementsPage.jsx'
import PricingPage from './components/PricingPage.jsx'
import SystemDesignToolPage from './components/SystemDesignToolPage.jsx'
import AIDiagramGeneratorPage from './components/AIDiagramGeneratorPage.jsx'
import ArchitectureDiagramToolPage from './components/ArchitectureDiagramToolPage.jsx'
import DesignDocGeneratorPage from './components/DesignDocGeneratorPage.jsx'
import ComparePage from './components/ComparePage.jsx'
import InfraSketchVsEraserPage from './components/InfraSketchVsEraserPage.jsx'
import InfraSketchVsLucidchartPage from './components/InfraSketchVsLucidchartPage.jsx'

const PUBLISHABLE_KEY = import.meta.env.VITE_CLERK_PUBLISHABLE_KEY

if (!PUBLISHABLE_KEY) {
  console.warn("Missing Publishable Key. Authentication features will not work.")
}

const AppRoot = (
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
              <Route path="/achievements" element={<AchievementsPage />} />
              <Route path="/pricing" element={<PricingPage />} />
              <Route path="/tools/system-design-tool" element={<SystemDesignToolPage />} />
              <Route path="/tools/ai-diagram-generator" element={<AIDiagramGeneratorPage />} />
              <Route path="/tools/architecture-diagram-tool" element={<ArchitectureDiagramToolPage />} />
              <Route path="/tools/design-doc-generator" element={<DesignDocGeneratorPage />} />
              <Route path="/compare" element={<ComparePage />} />
              <Route path="/compare/eraser" element={<InfraSketchVsEraserPage />} />
              <Route path="/compare/lucidchart" element={<InfraSketchVsLucidchartPage />} />
            </Routes>
          </BrowserRouter>
        </ThemeProvider>
      </ClerkProvider>
    </HelmetProvider>
  </StrictMode>
)

const rootElement = document.getElementById('root')

// Use hydration if the page was prerendered (has content)
if (rootElement.hasChildNodes()) {
  hydrateRoot(rootElement, AppRoot)
} else {
  createRoot(rootElement).render(AppRoot)
}
