"""Tests for gamification API endpoints.

Covers: GET /user/gamification, GET /user/gamification/achievements,
POST /user/gamification/notifications/dismiss
"""

from unittest.mock import patch, MagicMock
from datetime import datetime

from app.gamification.models import (
    UserGamification,
    GamificationCounters,
    UnlockedAchievement,
    PendingNotification,
)


def _make_test_gamification(user_id="local-dev-user"):
    """Build a UserGamification with some progress."""
    return UserGamification(
        user_id=user_id,
        xp_total=200,
        level=3,
        level_name="Designer",
        current_streak=5,
        longest_streak=12,
        last_active_date="2026-02-05",
        counters=GamificationCounters(
            diagrams_generated=8,
            chat_messages_sent=20,
            nodes_added=15,
        ),
        achievements=[
            UnlockedAchievement(id="first_diagram", unlocked_at=datetime(2026, 1, 15)),
            UnlockedAchievement(id="first_chat", unlocked_at=datetime(2026, 1, 16)),
        ],
        pending_notifications=[
            PendingNotification(id="diagrams_5", unlocked_at=datetime(2026, 2, 1)),
        ],
    )


# ── GET /user/gamification ──

class TestGetGamification:
    @patch("app.api.routes.get_gamification_storage")
    def test_returns_gamification_state(self, mock_get_storage, client):
        g = _make_test_gamification()
        mock_storage = MagicMock()
        mock_storage.get_or_create.return_value = g
        mock_get_storage.return_value = mock_storage

        response = client.get("/api/user/gamification")

        assert response.status_code == 200
        data = response.json()
        assert data["level"] == 3
        assert data["level_name"] == "Designer"
        assert data["xp_total"] == 200
        assert data["current_streak"] == 5
        assert data["longest_streak"] == 12

    @patch("app.api.routes.get_gamification_storage")
    def test_includes_level_progress(self, mock_get_storage, client):
        g = _make_test_gamification()
        mock_storage = MagicMock()
        mock_storage.get_or_create.return_value = g
        mock_get_storage.return_value = mock_storage

        response = client.get("/api/user/gamification")
        data = response.json()

        assert "xp_current_level_start" in data
        assert "xp_next_level_threshold" in data
        assert "xp_to_next_level" in data
        assert "level_color" in data

    @patch("app.api.routes.get_gamification_storage")
    def test_includes_pending_notifications(self, mock_get_storage, client):
        g = _make_test_gamification()
        mock_storage = MagicMock()
        mock_storage.get_or_create.return_value = g
        mock_get_storage.return_value = mock_storage

        response = client.get("/api/user/gamification")
        data = response.json()

        assert "pending_notifications" in data
        assert len(data["pending_notifications"]) == 1
        assert data["pending_notifications"][0]["id"] == "diagrams_5"

    @patch("app.api.routes.get_gamification_storage")
    def test_new_user_returns_defaults(self, mock_get_storage, client):
        g = UserGamification(user_id="local-dev-user")
        mock_storage = MagicMock()
        mock_storage.get_or_create.return_value = g
        mock_get_storage.return_value = mock_storage

        response = client.get("/api/user/gamification")
        data = response.json()

        assert data["level"] == 1
        assert data["level_name"] == "Intern"
        assert data["xp_total"] == 0
        assert data["current_streak"] == 0


# ── GET /user/gamification/achievements ──

class TestGetAchievements:
    @patch("app.api.routes.get_gamification_storage")
    def test_returns_all_achievements(self, mock_get_storage, client):
        g = _make_test_gamification()
        mock_storage = MagicMock()
        mock_storage.get_or_create.return_value = g
        mock_get_storage.return_value = mock_storage

        response = client.get("/api/user/gamification/achievements")

        assert response.status_code == 200
        data = response.json()
        assert "achievements" in data
        assert len(data["achievements"]) == 32

    @patch("app.api.routes.get_gamification_storage")
    def test_shows_unlocked_status(self, mock_get_storage, client):
        g = _make_test_gamification()
        mock_storage = MagicMock()
        mock_storage.get_or_create.return_value = g
        mock_get_storage.return_value = mock_storage

        response = client.get("/api/user/gamification/achievements")
        data = response.json()

        # first_diagram should be unlocked
        first_diagram = next(a for a in data["achievements"] if a["id"] == "first_diagram")
        assert first_diagram["unlocked"] is True
        assert first_diagram["unlocked_at"] is not None

        # diagrams_100 should be locked
        master = next(a for a in data["achievements"] if a["id"] == "diagrams_100")
        assert master["unlocked"] is False

    @patch("app.api.routes.get_gamification_storage")
    def test_includes_stats(self, mock_get_storage, client):
        g = _make_test_gamification()
        mock_storage = MagicMock()
        mock_storage.get_or_create.return_value = g
        mock_get_storage.return_value = mock_storage

        response = client.get("/api/user/gamification/achievements")
        data = response.json()

        assert "stats" in data
        assert "unlocked" in data["stats"]
        assert "total" in data["stats"]
        assert data["stats"]["total"] == 32
        assert data["stats"]["unlocked"] == 2  # first_diagram, first_chat

    @patch("app.api.routes.get_gamification_storage")
    def test_includes_category_stats(self, mock_get_storage, client):
        g = _make_test_gamification()
        mock_storage = MagicMock()
        mock_storage.get_or_create.return_value = g
        mock_get_storage.return_value = mock_storage

        response = client.get("/api/user/gamification/achievements")
        data = response.json()

        assert "by_category" in data["stats"]
        assert "first_time" in data["stats"]["by_category"]
        assert "volume" in data["stats"]["by_category"]

    @patch("app.api.routes.get_gamification_storage")
    def test_includes_progress_for_locked(self, mock_get_storage, client):
        g = _make_test_gamification()
        mock_storage = MagicMock()
        mock_storage.get_or_create.return_value = g
        mock_get_storage.return_value = mock_storage

        response = client.get("/api/user/gamification/achievements")
        data = response.json()

        diagrams_25 = next(a for a in data["achievements"] if a["id"] == "diagrams_25")
        assert diagrams_25["progress"]["current"] == 8
        assert diagrams_25["progress"]["target"] == 25


# ── POST /user/gamification/notifications/dismiss ──

class TestDismissNotifications:
    @patch("app.api.routes.get_gamification_storage")
    def test_dismiss_clears_notifications(self, mock_get_storage, client):
        g = _make_test_gamification()
        mock_storage = MagicMock()
        mock_storage.get_or_create.return_value = g
        mock_get_storage.return_value = mock_storage

        response = client.post(
            "/api/user/gamification/notifications/dismiss",
            json={"achievement_ids": ["diagrams_5"]},
        )

        assert response.status_code == 200
        assert len(g.pending_notifications) == 0
        mock_storage.save.assert_called_once()

    @patch("app.api.routes.get_gamification_storage")
    def test_dismiss_partial_list(self, mock_get_storage, client):
        g = _make_test_gamification()
        # Add another notification
        g.pending_notifications.append(
            PendingNotification(id="first_chat", unlocked_at=datetime(2026, 2, 2))
        )
        mock_storage = MagicMock()
        mock_storage.get_or_create.return_value = g
        mock_get_storage.return_value = mock_storage

        response = client.post(
            "/api/user/gamification/notifications/dismiss",
            json={"achievement_ids": ["diagrams_5"]},
        )

        assert response.status_code == 200
        assert len(g.pending_notifications) == 1
        assert g.pending_notifications[0].id == "first_chat"

    @patch("app.api.routes.get_gamification_storage")
    def test_dismiss_nonexistent_id_is_harmless(self, mock_get_storage, client):
        g = _make_test_gamification()
        mock_storage = MagicMock()
        mock_storage.get_or_create.return_value = g
        mock_get_storage.return_value = mock_storage

        response = client.post(
            "/api/user/gamification/notifications/dismiss",
            json={"achievement_ids": ["nonexistent_achievement"]},
        )

        assert response.status_code == 200
        # Original notification should still be there
        assert len(g.pending_notifications) == 1

    @patch("app.api.routes.get_gamification_storage")
    def test_dismiss_empty_list(self, mock_get_storage, client):
        g = _make_test_gamification()
        mock_storage = MagicMock()
        mock_storage.get_or_create.return_value = g
        mock_get_storage.return_value = mock_storage

        response = client.post(
            "/api/user/gamification/notifications/dismiss",
            json={"achievement_ids": []},
        )

        assert response.status_code == 200
