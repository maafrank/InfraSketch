"""Tests for streak reminder model field and backwards compatibility.

Covers: streak_reminders_enabled default, explicit set, backwards compat
for records missing the field, serialization.
"""

from app.gamification.models import UserGamification


class TestStreakRemindersEnabled:
    def test_default_is_true(self):
        g = UserGamification(user_id="test")
        assert g.streak_reminders_enabled is True

    def test_can_set_to_false(self):
        g = UserGamification(user_id="test", streak_reminders_enabled=False)
        assert g.streak_reminders_enabled is False

    def test_can_set_to_true_explicitly(self):
        g = UserGamification(user_id="test", streak_reminders_enabled=True)
        assert g.streak_reminders_enabled is True

    def test_backwards_compat_missing_field(self):
        """Old records without the field should default to True."""
        data = {
            "user_id": "test",
            "xp_total": 100,
            "level": 2,
            "level_name": "Junior Designer",
            "current_streak": 5,
        }
        g = UserGamification(**data)
        assert g.streak_reminders_enabled is True

    def test_serialization_includes_field(self):
        g = UserGamification(user_id="test", streak_reminders_enabled=False)
        data = g.model_dump()
        assert "streak_reminders_enabled" in data
        assert data["streak_reminders_enabled"] is False

    def test_serialization_roundtrip(self):
        g = UserGamification(user_id="test", streak_reminders_enabled=False)
        json_str = g.model_dump_json()
        g2 = UserGamification.model_validate_json(json_str)
        assert g2.streak_reminders_enabled is False

    def test_field_does_not_affect_other_defaults(self):
        """Adding streak_reminders_enabled should not change other defaults."""
        g = UserGamification(user_id="test")
        assert g.xp_total == 0
        assert g.level == 1
        assert g.current_streak == 0
        assert g.streak_grace_used is False
        assert g.streak_reminders_enabled is True
