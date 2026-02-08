/**
 * AchievementsSection - Full achievements display for the Settings page.
 * Shows level progress, streak info, and achievement grid by category.
 */

import { useState, useEffect, useCallback } from 'react';
import { useAuth } from '@clerk/clerk-react';
import { getUserAchievements, getUserGamification, setClerkTokenGetter } from '../api/client';
import './AchievementsSection.css';

const RARITY_COLORS = {
  common: '#888888',
  uncommon: '#4CAF50',
  rare: '#2196F3',
  epic: '#9C27B0',
  legendary: '#FFD700',
};

const CATEGORY_LABELS = {
  first_time: 'First Steps',
  volume: 'Milestones',
  feature_discovery: 'Explorer',
  streaks: 'Streaks',
};

const CATEGORY_ORDER = ['first_time', 'volume', 'feature_discovery', 'streaks'];

export default function AchievementsSection() {
  const { getToken, isSignedIn } = useAuth();
  const [gamification, setGamification] = useState(null);
  const [achievements, setAchievements] = useState(null);
  const [loading, setLoading] = useState(true);
  const [activeCategory, setActiveCategory] = useState('first_time');

  const fetchData = useCallback(async () => {
    if (!isSignedIn || !getToken) return;

    try {
      setClerkTokenGetter(getToken);
      const [gamData, achData] = await Promise.all([
        getUserGamification(),
        getUserAchievements(),
      ]);
      setGamification(gamData);
      setAchievements(achData);
    } catch (error) {
      console.error('Failed to fetch achievements:', error);
    } finally {
      setLoading(false);
    }
  }, [isSignedIn, getToken]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  if (loading) {
    return (
      <section className="settings-section">
        <h2>Achievements & Progress</h2>
        <p className="settings-description">Loading achievements...</p>
      </section>
    );
  }

  if (!gamification || !achievements) {
    return (
      <section className="settings-section">
        <h2>Achievements & Progress</h2>
        <p className="settings-description">Unable to load achievements.</p>
      </section>
    );
  }

  // Level progress calculation
  const xpInCurrentLevel = gamification.xp_total - gamification.xp_current_level_start;
  const xpNeededForLevel =
    gamification.xp_next_level_threshold - gamification.xp_current_level_start;
  const progressPercent =
    xpNeededForLevel > 0
      ? Math.min((xpInCurrentLevel / xpNeededForLevel) * 100, 100)
      : 100;

  // Group achievements by category
  const grouped = {};
  for (const cat of CATEGORY_ORDER) {
    grouped[cat] = achievements.achievements.filter((a) => a.category === cat);
  }

  const formatDate = (isoString) => {
    return new Date(isoString).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
    });
  };

  return (
    <section className="settings-section achievements-section">
      <h2>Achievements & Progress</h2>

      {/* Stats summary */}
      <div className="achievements-stats-row">
        <div className="stat-card">
          <div className="stat-value">{achievements.stats.unlocked}</div>
          <div className="stat-label">
            of {achievements.stats.total} Achievements
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-value">{gamification.xp_total}</div>
          <div className="stat-label">Total XP</div>
        </div>
        <div className="stat-card">
          <div className="stat-value">
            {gamification.current_streak > 0 && (
              <span className="streak-fire-icon">&#x1F525;</span>
            )}
            {gamification.current_streak}
          </div>
          <div className="stat-label">Day Streak</div>
        </div>
        <div className="stat-card">
          <div className="stat-value">{gamification.longest_streak}</div>
          <div className="stat-label">Best Streak</div>
        </div>
      </div>

      {/* Level progress */}
      <div className="level-progress-section">
        <div className="level-progress-header">
          <span
            className="level-title"
            style={{ color: gamification.level_color }}
          >
            Level {gamification.level}: {gamification.level_name}
          </span>
          {gamification.xp_to_next_level > 0 && (
            <span className="xp-remaining">
              {gamification.xp_to_next_level} XP to next level
            </span>
          )}
          {gamification.xp_to_next_level === 0 && (
            <span className="xp-remaining max-level">Max Level!</span>
          )}
        </div>
        <div className="level-progress-bar">
          <div
            className="level-progress-fill"
            style={{
              width: `${progressPercent}%`,
              background: gamification.level_color,
            }}
          />
        </div>
        <div className="level-progress-labels">
          <span>{gamification.xp_current_level_start} XP</span>
          <span>{gamification.xp_next_level_threshold} XP</span>
        </div>
      </div>

      {/* Category tabs */}
      <div className="achievement-tabs">
        {CATEGORY_ORDER.map((cat) => {
          const stats = achievements.stats.by_category[cat] || {
            unlocked: 0,
            total: 0,
          };
          return (
            <button
              key={cat}
              className={`achievement-tab ${activeCategory === cat ? 'active' : ''}`}
              onClick={() => setActiveCategory(cat)}
            >
              {CATEGORY_LABELS[cat]}
              <span className="tab-count">
                {stats.unlocked}/{stats.total}
              </span>
            </button>
          );
        })}
      </div>

      {/* Achievement grid */}
      <div className="achievement-grid">
        {grouped[activeCategory]?.map((achievement) => (
          <div
            key={achievement.id}
            className={`achievement-card ${achievement.unlocked ? 'unlocked' : 'locked'}`}
            style={{
              borderColor: achievement.unlocked
                ? RARITY_COLORS[achievement.rarity]
                : 'transparent',
            }}
          >
            <div className="achievement-card-header">
              <span className="achievement-name">{achievement.name}</span>
              {achievement.unlocked && (
                <span className="achievement-check">&#x2713;</span>
              )}
            </div>
            <p className="achievement-description">{achievement.description}</p>

            {!achievement.unlocked && achievement.progress && (
              <div className="achievement-progress">
                <div className="achievement-progress-bar">
                  <div
                    className="achievement-progress-fill"
                    style={{
                      width: `${Math.min(
                        (achievement.progress.current / achievement.progress.target) * 100,
                        100
                      )}%`,
                    }}
                  />
                </div>
                <span className="achievement-progress-text">
                  {achievement.progress.current} / {achievement.progress.target}
                </span>
              </div>
            )}

            {achievement.unlocked && achievement.unlocked_at && (
              <div className="achievement-unlock-date">
                {formatDate(achievement.unlocked_at)}
              </div>
            )}

            <div
              className="achievement-rarity"
              style={{ color: RARITY_COLORS[achievement.rarity] }}
            >
              {achievement.rarity}
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
