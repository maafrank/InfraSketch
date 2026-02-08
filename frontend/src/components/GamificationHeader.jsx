/**
 * GamificationHeader - Compact header widget showing level badge and streak.
 * Sits next to CreditBalance in the app header.
 */

import { useNavigate } from 'react-router-dom';
import { useGamification } from '../contexts/useGamification';
import './GamificationHeader.css';

const LEVEL_COLORS = {
  1: '#888888',
  2: '#4CAF50',
  3: '#4CAF50',
  4: '#2196F3',
  5: '#2196F3',
  6: '#9C27B0',
  7: '#9C27B0',
  8: '#FF9800',
  9: '#FF9800',
  10: '#FFD700',
};

export default function GamificationHeader() {
  const navigate = useNavigate();
  const { gamification, loading } = useGamification();

  if (loading || !gamification) return null;

  const { level, level_name, current_streak, xp_total } = gamification;
  const color = gamification.level_color || LEVEL_COLORS[level] || '#888888';

  return (
    <div
      className="gamification-header"
      title={`${level_name} \u2022 ${xp_total} XP \u2022 Click to view achievements`}
      onClick={() => navigate('/achievements')}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => { if (e.key === 'Enter') navigate('/achievements'); }}
    >
      <div className="level-badge" style={{ borderColor: color, color }}>
        <span className="level-number">{level}</span>
      </div>
      {current_streak > 0 && (
        <div
          className="streak-indicator"
          title={`${current_streak}-day streak`}
        >
          <span className="streak-fire" role="img" aria-label="streak">
            &#x1F525;
          </span>
          <span className="streak-count">{current_streak}</span>
        </div>
      )}
    </div>
  );
}
