"""Tests for streak tracking logic.

Covers: consecutive days, grace day, broken streaks, edge cases,
longest_streak tracking, and first-ever action.
"""

from unittest.mock import patch
from datetime import datetime, timedelta

from app.gamification.models import UserGamification
from app.gamification.streaks import update_streak


def _make_gamification(
    last_active_date=None,
    current_streak=0,
    longest_streak=0,
    streak_grace_used=False,
):
    """Helper to build a UserGamification with streak-relevant fields."""
    return UserGamification(
        user_id="test-user",
        last_active_date=last_active_date,
        current_streak=current_streak,
        longest_streak=longest_streak,
        streak_grace_used=streak_grace_used,
    )


def _mock_today(date_str):
    """Return a patch that makes datetime.utcnow() return the given date at noon UTC."""
    dt = datetime.strptime(date_str, "%Y-%m-%d").replace(hour=12)
    return patch("app.gamification.streaks.datetime", wraps=datetime, **{
        "utcnow.return_value": dt,
    })


# ── First-ever action ──

class TestFirstAction:
    def test_first_action_sets_streak_to_1(self):
        g = _make_gamification(last_active_date=None, current_streak=0)
        with _mock_today("2026-02-05"):
            result = update_streak(g)

        assert result["is_new_day"] is True
        assert result["streak_broken"] is False
        assert g.current_streak == 1
        assert g.last_active_date == "2026-02-05"
        assert g.longest_streak == 1
        assert g.streak_grace_used is False

    def test_first_action_updates_longest_streak(self):
        g = _make_gamification(last_active_date=None, current_streak=0, longest_streak=0)
        with _mock_today("2026-02-05"):
            update_streak(g)
        assert g.longest_streak == 1


# ── Same day (no change) ──

class TestSameDay:
    def test_same_day_returns_not_new(self):
        g = _make_gamification(last_active_date="2026-02-05", current_streak=3)
        with _mock_today("2026-02-05"):
            result = update_streak(g)

        assert result["is_new_day"] is False
        assert result["streak_broken"] is False
        assert g.current_streak == 3  # unchanged

    def test_same_day_does_not_modify_anything(self):
        g = _make_gamification(
            last_active_date="2026-02-05",
            current_streak=5,
            longest_streak=10,
            streak_grace_used=True,
        )
        with _mock_today("2026-02-05"):
            update_streak(g)

        assert g.current_streak == 5
        assert g.longest_streak == 10
        assert g.streak_grace_used is True
        assert g.last_active_date == "2026-02-05"


# ── Consecutive day ──

class TestConsecutiveDay:
    def test_next_day_increments_streak(self):
        g = _make_gamification(last_active_date="2026-02-04", current_streak=3)
        with _mock_today("2026-02-05"):
            result = update_streak(g)

        assert result["is_new_day"] is True
        assert result["streak_broken"] is False
        assert g.current_streak == 4
        assert g.last_active_date == "2026-02-05"

    def test_consecutive_resets_grace_flag(self):
        g = _make_gamification(
            last_active_date="2026-02-04",
            current_streak=5,
            streak_grace_used=True,
        )
        with _mock_today("2026-02-05"):
            update_streak(g)

        assert g.streak_grace_used is False

    def test_consecutive_updates_longest_streak(self):
        g = _make_gamification(
            last_active_date="2026-02-04",
            current_streak=9,
            longest_streak=9,
        )
        with _mock_today("2026-02-05"):
            update_streak(g)

        assert g.current_streak == 10
        assert g.longest_streak == 10

    def test_consecutive_does_not_lower_longest(self):
        g = _make_gamification(
            last_active_date="2026-02-04",
            current_streak=2,
            longest_streak=50,
        )
        with _mock_today("2026-02-05"):
            update_streak(g)

        assert g.current_streak == 3
        assert g.longest_streak == 50  # not lowered


# ── Grace day (skip 1 day) ──

class TestGraceDay:
    def test_one_day_gap_uses_grace(self):
        g = _make_gamification(
            last_active_date="2026-02-03",
            current_streak=5,
            streak_grace_used=False,
        )
        with _mock_today("2026-02-05"):
            result = update_streak(g)

        assert result["is_new_day"] is True
        assert result["streak_broken"] is False
        assert g.current_streak == 6
        assert g.streak_grace_used is True
        assert g.last_active_date == "2026-02-05"

    def test_grace_already_used_breaks_streak(self):
        g = _make_gamification(
            last_active_date="2026-02-03",
            current_streak=5,
            streak_grace_used=True,
        )
        with _mock_today("2026-02-05"):
            result = update_streak(g)

        assert result["is_new_day"] is True
        assert result["streak_broken"] is True
        assert g.current_streak == 1  # reset
        assert g.streak_grace_used is False

    def test_grace_day_still_updates_longest(self):
        g = _make_gamification(
            last_active_date="2026-02-03",
            current_streak=20,
            longest_streak=20,
            streak_grace_used=False,
        )
        with _mock_today("2026-02-05"):
            update_streak(g)

        assert g.current_streak == 21
        assert g.longest_streak == 21


# ── Broken streak (2+ day gap) ──

class TestBrokenStreak:
    def test_two_day_gap_breaks_streak(self):
        g = _make_gamification(
            last_active_date="2026-02-02",
            current_streak=10,
            streak_grace_used=False,
        )
        with _mock_today("2026-02-05"):
            result = update_streak(g)

        assert result["is_new_day"] is True
        assert result["streak_broken"] is True
        assert g.current_streak == 1
        assert g.streak_grace_used is False

    def test_large_gap_breaks_streak(self):
        g = _make_gamification(
            last_active_date="2026-01-01",
            current_streak=30,
        )
        with _mock_today("2026-02-05"):
            result = update_streak(g)

        assert result["streak_broken"] is True
        assert g.current_streak == 1

    def test_broken_streak_preserves_longest(self):
        g = _make_gamification(
            last_active_date="2026-01-01",
            current_streak=5,
            longest_streak=100,
        )
        with _mock_today("2026-02-05"):
            update_streak(g)

        assert g.current_streak == 1
        assert g.longest_streak == 100  # preserved


# ── Edge cases ──

class TestEdgeCases:
    def test_month_boundary_consecutive(self):
        """Jan 31 -> Feb 1 is consecutive."""
        g = _make_gamification(last_active_date="2026-01-31", current_streak=5)
        with _mock_today("2026-02-01"):
            result = update_streak(g)

        assert result["streak_broken"] is False
        assert g.current_streak == 6

    def test_month_boundary_grace(self):
        """Jan 30 -> Feb 1 is a grace day (1 day gap)."""
        g = _make_gamification(
            last_active_date="2026-01-30",
            current_streak=5,
            streak_grace_used=False,
        )
        with _mock_today("2026-02-01"):
            result = update_streak(g)

        assert result["streak_broken"] is False
        assert g.current_streak == 6
        assert g.streak_grace_used is True

    def test_year_boundary(self):
        """Dec 31 -> Jan 1 is consecutive."""
        g = _make_gamification(last_active_date="2025-12-31", current_streak=10)
        with _mock_today("2026-01-01"):
            result = update_streak(g)

        assert result["streak_broken"] is False
        assert g.current_streak == 11

    def test_leap_year_feb_28_to_mar_1_is_grace(self):
        """In non-leap 2026, Feb 28 -> Mar 1 is consecutive (1 day gap = grace)."""
        # 2026 is NOT a leap year, so Feb has 28 days
        g = _make_gamification(
            last_active_date="2026-02-27",
            current_streak=5,
            streak_grace_used=False,
        )
        with _mock_today("2026-03-01"):
            result = update_streak(g)

        # Feb 27 -> Mar 1 is 2 days gap, uses grace
        assert result["streak_broken"] is False
        assert g.current_streak == 6
        assert g.streak_grace_used is True

    def test_multiple_actions_same_day_only_first_counts(self):
        """Multiple calls on the same day should only count the first."""
        g = _make_gamification(last_active_date="2026-02-04", current_streak=3)
        with _mock_today("2026-02-05"):
            r1 = update_streak(g)
            r2 = update_streak(g)
            r3 = update_streak(g)

        assert r1["is_new_day"] is True
        assert r2["is_new_day"] is False
        assert r3["is_new_day"] is False
        assert g.current_streak == 4  # only incremented once

    def test_streak_rebuilding_after_break(self):
        """After a break, streak rebuilds from 1."""
        g = _make_gamification(
            last_active_date="2026-01-01",
            current_streak=50,
            longest_streak=50,
        )
        # Break the streak
        with _mock_today("2026-02-05"):
            update_streak(g)
        assert g.current_streak == 1
        assert g.longest_streak == 50

        # Rebuild day by day
        with _mock_today("2026-02-06"):
            update_streak(g)
        assert g.current_streak == 2

        with _mock_today("2026-02-07"):
            update_streak(g)
        assert g.current_streak == 3
        assert g.longest_streak == 50  # still 50
