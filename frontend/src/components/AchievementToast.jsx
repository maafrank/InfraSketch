/**
 * AchievementToast - Slide-in notification for new achievements and level-ups.
 * Auto-dismisses after 5 seconds.
 */

import { useEffect, useState } from 'react';
import { useGamification } from '../contexts/useGamification';
import './AchievementToast.css';

const RARITY_COLORS = {
  common: '#888888',
  uncommon: '#4CAF50',
  rare: '#2196F3',
  epic: '#9C27B0',
  legendary: '#FFD700',
};

const RARITY_LABELS = {
  common: 'Common',
  uncommon: 'Uncommon',
  rare: 'Rare',
  epic: 'Epic',
  legendary: 'Legendary',
};

export default function AchievementToast() {
  const { pendingToasts, dismissToast } = useGamification();
  const [visible, setVisible] = useState(false);

  const currentToast = pendingToasts[0] || null;

  useEffect(() => {
    if (!currentToast) {
      setVisible(false);
      return;
    }

    // Slide in
    const showTimer = setTimeout(() => setVisible(true), 50);

    // Auto-dismiss after 5 seconds
    const dismissTimer = setTimeout(() => {
      setVisible(false);
      // Wait for slide-out animation before removing from queue
      setTimeout(dismissToast, 300);
    }, 5000);

    return () => {
      clearTimeout(showTimer);
      clearTimeout(dismissTimer);
    };
  }, [currentToast, dismissToast]);

  if (!currentToast) return null;

  const handleDismiss = () => {
    setVisible(false);
    setTimeout(dismissToast, 300);
  };

  if (currentToast.type === 'level_up') {
    return (
      <div
        className={`achievement-toast level-up ${visible ? 'visible' : ''}`}
        onClick={handleDismiss}
        role="alert"
      >
        <div className="toast-icon">&#x2B50;</div>
        <div className="toast-content">
          <div className="toast-title">Level Up!</div>
          <div className="toast-description">
            You reached Level {currentToast.level}: {currentToast.level_name}
          </div>
        </div>
        <button className="toast-close" onClick={handleDismiss} aria-label="Dismiss">
          &#x2715;
        </button>
      </div>
    );
  }

  // Achievement toast
  const rarityColor = RARITY_COLORS[currentToast.rarity] || RARITY_COLORS.common;
  const rarityLabel = RARITY_LABELS[currentToast.rarity] || 'Common';

  return (
    <div
      className={`achievement-toast ${visible ? 'visible' : ''}`}
      style={{ borderLeftColor: rarityColor }}
      onClick={handleDismiss}
      role="alert"
    >
      <div className="toast-icon">&#x1F3C6;</div>
      <div className="toast-content">
        <div className="toast-title">Achievement Unlocked!</div>
        <div className="toast-achievement-name">{currentToast.name}</div>
        <div className="toast-description">{currentToast.description}</div>
        <div className="toast-rarity" style={{ color: rarityColor }}>
          {rarityLabel}
        </div>
      </div>
      <button className="toast-close" onClick={handleDismiss} aria-label="Dismiss">
        &#x2715;
      </button>
    </div>
  );
}
