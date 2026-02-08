/**
 * AchievementsPage - Standalone page for achievements, level progress, and streaks.
 * Accessible by clicking the gamification badge in the header.
 */

import { useNavigate } from 'react-router-dom';
import { SignedIn, SignedOut, SignInButton, UserButton } from '@clerk/clerk-react';
import { useTheme } from '../contexts/useTheme';
import ThemeToggle from './ThemeToggle';
import AchievementsSection from './AchievementsSection';
import './SettingsPage.css';

export default function AchievementsPage() {
  const navigate = useNavigate();
  const { theme } = useTheme();

  return (
    <div className="settings-page">
      <header className="settings-header">
        <div className="settings-header-left">
          <button className="back-button" onClick={() => navigate('/')}>
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M19 12H5M12 19l-7-7 7-7" />
            </svg>
            Back
          </button>
        </div>
        <h1 className="settings-header-title">Achievements</h1>
        <div className="settings-header-right">
          <ThemeToggle />
          <SignedOut>
            <SignInButton mode="modal">
              <button className="sign-in-button">Sign In</button>
            </SignInButton>
          </SignedOut>
          <SignedIn>
            <UserButton
              appearance={{
                elements: {
                  avatarBox: { width: 32, height: 32 },
                },
              }}
            />
          </SignedIn>
        </div>
      </header>

      <main className="settings-content">
        <SignedIn>
          <AchievementsSection />
        </SignedIn>

        <SignedOut>
          <div className="settings-signed-out">
            <h2>Sign in to view achievements</h2>
            <p>You need to be signed in to view your achievements and progress.</p>
            <SignInButton mode="modal">
              <button className="settings-button settings-button--primary">Sign In</button>
            </SignInButton>
          </div>
        </SignedOut>
      </main>

      <footer className="settings-footer">
        <div className="footer-content">
          <div className="footer-brand">
            <span className="footer-logo">InfraSketch</span>
            <p className="footer-tagline">AI-powered system design</p>
          </div>
          <div className="footer-links">
            <a href="/about">About</a>
            <a href="/blog">Blog</a>
            <a href="/pricing">Pricing</a>
            <a href="/careers">Careers</a>
            <a href="/privacy">Privacy Policy</a>
            <a href="/terms">Terms of Service</a>
            <a href="/contact">Contact</a>
          </div>
          <div className="footer-bottom">
            <p>&copy; 2026 InfraSketch. All rights reserved.</p>
          </div>
        </div>
      </footer>
    </div>
  );
}
