/**
 * Gamification Context - manages XP, levels, streaks, and achievements.
 * Fetches state on mount, processes gamification results from API responses,
 * and queues toast notifications for new achievements and level-ups.
 */

import React, { createContext, useState, useCallback, useEffect } from 'react';
import {
  getUserGamification,
  dismissGamificationNotifications,
  setClerkTokenGetter,
} from '../api/client';

const GamificationContext = createContext(null);

export const GamificationProvider = ({ children, isSignedIn, getToken }) => {
  const [gamification, setGamification] = useState(null);
  const [loading, setLoading] = useState(true);
  const [pendingToasts, setPendingToasts] = useState([]);

  // Fetch gamification state on mount (when signed in)
  useEffect(() => {
    const fetchGamification = async () => {
      if (!isSignedIn || !getToken) {
        setLoading(false);
        return;
      }

      try {
        setClerkTokenGetter(getToken);
        const data = await getUserGamification();
        setGamification(data);

        // Queue any pending notifications as toasts
        if (data.pending_notifications?.length > 0) {
          const toasts = data.pending_notifications.map((notif) => ({
            type: 'achievement',
            id: notif.id,
            name: notif.name,
            description: notif.description,
            rarity: notif.rarity,
          }));
          setPendingToasts(toasts);

          // Dismiss them server-side
          dismissGamificationNotifications(
            data.pending_notifications.map((n) => n.id)
          ).catch(() => {});
        }
      } catch (error) {
        console.error('Failed to fetch gamification:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchGamification();
  }, [isSignedIn, getToken]);

  // Process gamification result from any API response
  const processGamificationResult = useCallback((result) => {
    if (!result) return;

    // Update local state with new XP/level/streak
    setGamification((prev) => {
      if (!prev) return prev;
      return {
        ...prev,
        xp_total: (prev.xp_total || 0) + (result.xp_gained || 0),
        current_streak: result.current_streak ?? prev.current_streak,
        level: result.new_level || prev.level,
        level_name: result.new_level_name || prev.level_name,
        achievement_count:
          (prev.achievement_count || 0) +
          (result.new_achievements?.length || 0),
      };
    });

    const newToasts = [];

    // Queue achievement toasts and dismiss server-side so they don't re-appear on refresh
    if (result.new_achievements?.length > 0) {
      for (const achievement of result.new_achievements) {
        newToasts.push({
          type: 'achievement',
          id: achievement.id,
          name: achievement.name,
          description: achievement.description,
          rarity: achievement.rarity,
        });
      }
      dismissGamificationNotifications(
        result.new_achievements.map((a) => a.id)
      ).catch(() => {});
    }

    // Queue level-up toast
    if (result.level_up) {
      newToasts.push({
        type: 'level_up',
        level: result.new_level,
        level_name: result.new_level_name,
      });
    }

    if (newToasts.length > 0) {
      setPendingToasts((prev) => [...prev, ...newToasts]);
    }
  }, []);

  // Dismiss the first toast in the queue
  const dismissToast = useCallback(() => {
    setPendingToasts((prev) => prev.slice(1));
  }, []);

  // Force refresh gamification data from the server
  const refresh = useCallback(async () => {
    try {
      const data = await getUserGamification();
      setGamification(data);

      // Process any pending notifications into toasts
      if (data.pending_notifications?.length > 0) {
        const toasts = data.pending_notifications.map((notif) => ({
          type: 'achievement',
          id: notif.id,
          name: notif.name,
          description: notif.description,
          rarity: notif.rarity,
        }));
        setPendingToasts((prev) => [...prev, ...toasts]);

        // Dismiss server-side so they don't re-appear
        dismissGamificationNotifications(
          data.pending_notifications.map((n) => n.id)
        ).catch(() => {});
      }
    } catch (error) {
      console.error('Failed to refresh gamification:', error);
    }
  }, []);

  const value = {
    gamification,
    loading,
    pendingToasts,
    processGamificationResult,
    dismissToast,
    refresh,
  };

  return (
    <GamificationContext.Provider value={value}>
      {children}
    </GamificationContext.Provider>
  );
};

export default GamificationContext;
