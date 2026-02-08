"""Streak tracking logic with one grace day per streak."""

from datetime import datetime, timedelta
from .models import UserGamification


def update_streak(gamification: UserGamification) -> dict:
    """Update streak based on today's date (UTC).

    Returns dict with:
        is_new_day: whether this is the first action today (triggers daily bonus)
        streak_broken: whether the streak was reset
    """
    today = datetime.utcnow().date().isoformat()  # "YYYY-MM-DD"
    result = {"is_new_day": False, "streak_broken": False}

    last = gamification.last_active_date

    if last == today:
        # Already active today, no streak change
        return result

    result["is_new_day"] = True

    if last is None:
        # First ever action
        gamification.current_streak = 1
        gamification.streak_grace_used = False
    else:
        last_date = datetime.strptime(last, "%Y-%m-%d").date()
        today_date = datetime.strptime(today, "%Y-%m-%d").date()
        gap = (today_date - last_date).days

        if gap == 1:
            # Consecutive day
            gamification.current_streak += 1
            gamification.streak_grace_used = False
        elif gap == 2 and not gamification.streak_grace_used:
            # One day missed, use grace period
            gamification.current_streak += 1
            gamification.streak_grace_used = True
        else:
            # Streak broken
            result["streak_broken"] = True
            gamification.current_streak = 1
            gamification.streak_grace_used = False

    # Update longest streak
    if gamification.current_streak > gamification.longest_streak:
        gamification.longest_streak = gamification.current_streak

    gamification.last_active_date = today
    return result
