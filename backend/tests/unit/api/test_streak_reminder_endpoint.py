"""Tests for PATCH /user/gamification/streak-reminders endpoint
and streak_reminders_enabled in GET /user/gamification response.
"""

from unittest.mock import patch, MagicMock

from app.gamification.models import UserGamification


class TestUpdateStreakReminderPreference:
    @patch("app.api.routes.get_gamification_storage")
    def test_enable_streak_reminders(self, mock_get_storage, client):
        g = UserGamification(user_id="local-dev-user", streak_reminders_enabled=False)
        mock_storage = MagicMock()
        mock_storage.get_or_create.return_value = g
        mock_get_storage.return_value = mock_storage

        response = client.patch(
            "/api/user/gamification/streak-reminders",
            json={"enabled": True},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["streak_reminders_enabled"] is True
        assert g.streak_reminders_enabled is True
        mock_storage.save.assert_called_once()

    @patch("app.api.routes.get_gamification_storage")
    def test_disable_streak_reminders(self, mock_get_storage, client):
        g = UserGamification(user_id="local-dev-user", streak_reminders_enabled=True)
        mock_storage = MagicMock()
        mock_storage.get_or_create.return_value = g
        mock_get_storage.return_value = mock_storage

        response = client.patch(
            "/api/user/gamification/streak-reminders",
            json={"enabled": False},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["streak_reminders_enabled"] is False
        assert g.streak_reminders_enabled is False

    @patch("app.api.routes.get_gamification_storage")
    def test_toggle_saves_to_storage(self, mock_get_storage, client):
        g = UserGamification(user_id="local-dev-user")
        mock_storage = MagicMock()
        mock_storage.get_or_create.return_value = g
        mock_get_storage.return_value = mock_storage

        client.patch(
            "/api/user/gamification/streak-reminders",
            json={"enabled": False},
        )

        mock_storage.save.assert_called_once_with(g)


    @patch("app.api.routes.get_gamification_storage")
    def test_toggle_roundtrip(self, mock_get_storage, client):
        """Verify toggling off then on updates model state correctly."""
        g = UserGamification(user_id="local-dev-user", streak_reminders_enabled=True)
        mock_storage = MagicMock()
        mock_storage.get_or_create.return_value = g
        mock_get_storage.return_value = mock_storage

        # Disable
        resp1 = client.patch(
            "/api/user/gamification/streak-reminders",
            json={"enabled": False},
        )
        assert resp1.json()["streak_reminders_enabled"] is False
        assert g.streak_reminders_enabled is False

        # Re-enable
        resp2 = client.patch(
            "/api/user/gamification/streak-reminders",
            json={"enabled": True},
        )
        assert resp2.json()["streak_reminders_enabled"] is True
        assert g.streak_reminders_enabled is True

    def test_missing_body_returns_422(self, client):
        """PATCH without a body should return validation error."""
        response = client.patch("/api/user/gamification/streak-reminders")
        assert response.status_code == 422


class TestGetGamificationIncludesStreakReminders:
    @patch("app.api.routes.get_gamification_storage")
    def test_includes_streak_reminders_enabled_true(self, mock_get_storage, client):
        g = UserGamification(user_id="local-dev-user", streak_reminders_enabled=True)
        mock_storage = MagicMock()
        mock_storage.get_or_create.return_value = g
        mock_get_storage.return_value = mock_storage

        response = client.get("/api/user/gamification")

        assert response.status_code == 200
        data = response.json()
        assert "streak_reminders_enabled" in data
        assert data["streak_reminders_enabled"] is True

    @patch("app.api.routes.get_gamification_storage")
    def test_includes_streak_reminders_enabled_false(self, mock_get_storage, client):
        g = UserGamification(user_id="local-dev-user", streak_reminders_enabled=False)
        mock_storage = MagicMock()
        mock_storage.get_or_create.return_value = g
        mock_get_storage.return_value = mock_storage

        response = client.get("/api/user/gamification")

        assert response.status_code == 200
        data = response.json()
        assert data["streak_reminders_enabled"] is False
