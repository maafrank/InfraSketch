/**
 * SettingsPage - User settings and preferences.
 * Allows users to replay the tutorial and manage other preferences.
 */

import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { SignedIn, SignedOut, SignInButton, UserButton, useAuth } from '@clerk/clerk-react';
import { useTheme } from '../contexts/useTheme';
import { resetTutorial, setClerkTokenGetter } from '../api/client';
import ThemeToggle from './ThemeToggle';
import './SettingsPage.css';

export default function SettingsPage() {
  const navigate = useNavigate();
  const { theme } = useTheme();
  const { getToken } = useAuth();

  // Set up Clerk token getter for API calls
  useEffect(() => {
    setClerkTokenGetter(getToken);
  }, [getToken]);
  const [resettingTutorial, setResettingTutorial] = useState(false);
  const [tutorialResetSuccess, setTutorialResetSuccess] = useState(false);

  const handleReplayTutorial = async () => {
    setResettingTutorial(true);
    setTutorialResetSuccess(false);

    try {
      await resetTutorial();
      setTutorialResetSuccess(true);
      // Redirect to home after a short delay to show success message
      setTimeout(() => {
        navigate('/');
      }, 1500);
    } catch (error) {
      console.error('Failed to reset tutorial:', error);
      alert('Failed to reset tutorial. Please try again.');
    } finally {
      setResettingTutorial(false);
    }
  };

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
          <h1>Settings</h1>
        </div>
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
          {/* Tutorial Section */}
          <section className="settings-section">
            <h2>Tutorial</h2>
            <p className="settings-description">
              Replay the onboarding tutorial to learn about all the features InfraSketch has to offer.
            </p>
            <button
              className="settings-button settings-button--primary"
              onClick={handleReplayTutorial}
              disabled={resettingTutorial || tutorialResetSuccess}
            >
              {resettingTutorial ? (
                'Resetting...'
              ) : tutorialResetSuccess ? (
                <>
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M20 6L9 17l-5-5" />
                  </svg>
                  Tutorial Reset! Redirecting...
                </>
              ) : (
                'Replay Tutorial'
              )}
            </button>
          </section>

          {/* Appearance Section */}
          <section className="settings-section">
            <h2>Appearance</h2>
            <div className="settings-row">
              <div>
                <h3>Theme</h3>
                <p className="settings-description">
                  Choose between light and dark mode for the interface.
                </p>
              </div>
              <div className="settings-row-control">
                <span className="theme-label">{theme === 'dark' ? 'Dark' : 'Light'}</span>
                <ThemeToggle />
              </div>
            </div>
          </section>

          {/* About Section */}
          <section className="settings-section">
            <h2>About</h2>
            <div className="settings-links">
              <a href="/about" className="settings-link">About InfraSketch</a>
              <a href="/privacy" className="settings-link">Privacy Policy</a>
              <a href="/terms" className="settings-link">Terms of Service</a>
              <a href="/contact" className="settings-link">Contact Us</a>
            </div>
          </section>
        </SignedIn>

        <SignedOut>
          <div className="settings-signed-out">
            <h2>Sign in to access settings</h2>
            <p>You need to be signed in to view and modify your settings.</p>
            <SignInButton mode="modal">
              <button className="settings-button settings-button--primary">Sign In</button>
            </SignInButton>
          </div>
        </SignedOut>
      </main>
    </div>
  );
}
