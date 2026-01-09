/**
 * SettingsPage - User settings and preferences.
 * Allows users to replay the tutorial and manage other preferences.
 */

import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { SignedIn, SignedOut, SignInButton, UserButton, useAuth } from '@clerk/clerk-react';
import { SubscriptionDetailsButton } from '@clerk/clerk-react/experimental';
import { useTheme } from '../contexts/useTheme';
import { resetTutorial, setClerkTokenGetter, getUserCredits, getCreditHistory } from '../api/client';
import ThemeToggle from './ThemeToggle';
import './SettingsPage.css';

export default function SettingsPage() {
  const navigate = useNavigate();
  const { theme } = useTheme();
  const { getToken, isSignedIn } = useAuth();

  // Set up Clerk token getter for API calls
  useEffect(() => {
    setClerkTokenGetter(getToken);
  }, [getToken]);
  const [resettingTutorial, setResettingTutorial] = useState(false);
  const [tutorialResetSuccess, setTutorialResetSuccess] = useState(false);

  // Billing state
  const [credits, setCredits] = useState(null);
  const [creditsLoading, setCreditsLoading] = useState(true);
  const [transactions, setTransactions] = useState([]);
  const [showHistory, setShowHistory] = useState(false);

  // Fetch credits on mount
  const fetchCredits = useCallback(async () => {
    if (!isSignedIn) return;
    try {
      const data = await getUserCredits();
      setCredits(data);
    } catch (error) {
      console.error('Failed to fetch credits:', error);
    } finally {
      setCreditsLoading(false);
    }
  }, [isSignedIn]);

  useEffect(() => {
    fetchCredits();
  }, [fetchCredits]);

  const handleViewHistory = async () => {
    if (showHistory) {
      setShowHistory(false);
      return;
    }

    try {
      const data = await getCreditHistory(20);
      setTransactions(data.transactions || []);
      setShowHistory(true);
    } catch (error) {
      console.error('Failed to fetch credit history:', error);
    }
  };

  const formatDate = (isoString) => {
    const date = new Date(isoString);
    return date.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const getTransactionLabel = (txn) => {
    switch (txn.action) {
      case 'diagram_generation':
        return 'Diagram Generation';
      case 'chat_message':
        return 'Chat Message';
      case 'design_doc_generation':
        return 'Design Doc Generation';
      case 'design_doc_export':
        return 'Design Doc Export';
      case 'promo_code':
        return `Promo Code: ${txn.metadata?.promo_code || 'Applied'}`;
      case 'initial_signup':
        return 'Welcome Credits';
      case 'monthly_reset':
        return 'Monthly Reset';
      case 'plan_change':
        return `Plan: ${txn.metadata?.old_plan} → ${txn.metadata?.new_plan}`;
      default:
        return txn.action;
    }
  };

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
        </div>
        <h1 className="settings-header-title">Settings</h1>
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
          {/* Subscription & Credits Section */}
          <section className="settings-section">
            <h2>Subscription & Credits</h2>
            {creditsLoading ? (
              <p className="settings-description">Loading billing info...</p>
            ) : credits ? (
              <>
                <div className="settings-row">
                  <div>
                    <h3>Current Plan</h3>
                    <p className="settings-description">
                      {credits.plan === 'free' ? 'Free Plan' : `${credits.plan.charAt(0).toUpperCase() + credits.plan.slice(1)} Plan`}
                    </p>
                  </div>
                  <div className="settings-row-control settings-row-control--buttons">
                    {credits.plan !== 'free' && (
                      <SubscriptionDetailsButton
                        onSubscriptionCancel={() => {
                          // Refresh credits after cancellation
                          fetchCredits();
                        }}
                      >
                        <button className="settings-button settings-button--secondary">
                          Manage Subscription
                        </button>
                      </SubscriptionDetailsButton>
                    )}
                    <button
                      className="settings-button settings-button--primary"
                      onClick={() => navigate('/pricing')}
                    >
                      {credits.plan === 'free' ? 'Upgrade' : 'Change Plan'}
                    </button>
                  </div>
                </div>

                <div className="settings-row">
                  <div>
                    <h3>Credits</h3>
                    <p className="settings-description">
                      <span className="credits-balance">{credits.credits_balance}</span> / {credits.credits_monthly_allowance} credits remaining this month
                    </p>
                  </div>
                </div>

                <div className="settings-row">
                  <div>
                    <h3>Usage History</h3>
                    <p className="settings-description">
                      View your recent credit usage.
                    </p>
                  </div>
                  <div className="settings-row-control">
                    <button
                      className="settings-button settings-button--secondary"
                      onClick={handleViewHistory}
                    >
                      {showHistory ? 'Hide History' : 'View History'}
                    </button>
                  </div>
                </div>

                {showHistory && transactions.length > 0 && (
                  <div className="credit-history">
                    <table className="credit-history-table">
                      <thead>
                        <tr>
                          <th>Date</th>
                          <th>Action</th>
                          <th>Credits</th>
                          <th>Balance</th>
                        </tr>
                      </thead>
                      <tbody>
                        {transactions.map((txn) => (
                          <tr key={txn.transaction_id}>
                            <td>{formatDate(txn.created_at)}</td>
                            <td>{getTransactionLabel(txn)}</td>
                            <td className={txn.amount >= 0 ? 'positive' : 'negative'}>
                              {txn.amount >= 0 ? '+' : ''}{txn.amount}
                            </td>
                            <td>{txn.balance_after}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}

                {showHistory && transactions.length === 0 && (
                  <p className="settings-description">No transaction history yet.</p>
                )}
              </>
            ) : (
              <p className="settings-description">Unable to load billing information.</p>
            )}
          </section>

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
