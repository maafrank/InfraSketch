import { useState, useEffect, useCallback } from 'react';
import { useAuth } from '@clerk/clerk-react';
import { getUserCredits, setClerkTokenGetter } from '../api/client';
import './CreditBalance.css';

/**
 * CreditBalance - Shows credit balance in header.
 * Displays current credits and links to upgrade when low.
 */
export default function CreditBalance({ onUpgradeClick, onRefresh }) {
  const { getToken, isSignedIn } = useAuth();
  const [credits, setCredits] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchCredits = useCallback(async () => {
    if (!isSignedIn) {
      setLoading(false);
      return;
    }

    // Wait for getToken to be available before making API calls
    // This prevents race conditions where API calls happen before auth is ready
    if (!getToken) {
      // Don't set loading to false - we'll retry when getToken becomes available
      return;
    }

    try {
      // Ensure token getter is set before every API call
      setClerkTokenGetter(getToken);

      const data = await getUserCredits();
      setCredits(data);
      setError(null);
    } catch (err) {
      console.error('Failed to fetch credits:', err);
      setError('Failed to load credits');
    } finally {
      setLoading(false);
    }
  }, [isSignedIn, getToken]);

  // Initial fetch and periodic refresh
  useEffect(() => {
    fetchCredits();

    // Refresh every 30 seconds
    const interval = setInterval(fetchCredits, 30000);
    return () => clearInterval(interval);
  }, [fetchCredits]);

  // Expose refresh function to parent
  useEffect(() => {
    if (onRefresh) {
      onRefresh(fetchCredits);
    }
  }, [onRefresh, fetchCredits]);

  if (!isSignedIn) return null;
  if (loading) {
    return (
      <div className="credit-balance loading">
        <span className="credit-icon">⚡</span>
        <span className="credit-count">...</span>
      </div>
    );
  }
  if (error) return null;

  const balance = credits?.credits_balance || 0;
  const isLow = balance < 10;
  const isCritical = balance < 3;

  return (
    <div
      className={`credit-balance ${isLow ? 'low' : ''} ${isCritical ? 'critical' : ''}`}
      onClick={onUpgradeClick}
      onKeyDown={(e) => e.key === 'Enter' && onUpgradeClick?.()}
      role="button"
      tabIndex={0}
      title="View pricing"
    >
      <span className="credit-icon">⚡</span>
      <span className="credit-count">{balance}</span>
      <span className="credit-label">credits</span>
      {isLow && (
        <button
          className="upgrade-button"
          onClick={(e) => {
            e.stopPropagation();
            onUpgradeClick?.();
          }}
          title="Get more credits"
        >
          Get More
        </button>
      )}
    </div>
  );
}
