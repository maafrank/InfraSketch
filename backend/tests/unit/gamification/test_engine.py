"""Tests for the gamification engine (process_action orchestration).

Covers: counter increments, XP awards, level-ups, streak handling,
achievement unlocking, failure isolation, and list-append behavior.
"""

from unittest.mock import patch, MagicMock
from datetime import datetime

from app.gamification.models import UserGamification, GamificationCounters
from app.gamification.engine import process_action, _update_counters
from app.gamification.xp import XP_VALUES


def _fresh_gamification(user_id="test-user", **kwargs):
    """Create a fresh UserGamification for testing."""
    return UserGamification(user_id=user_id, **kwargs)


def _mock_storage(gamification=None):
    """Create a mocked storage that returns the given gamification object."""
    mock = MagicMock()
    if gamification is None:
        gamification = _fresh_gamification()
    mock.get_or_create.return_value = gamification
    return mock


# ── Counter updates ──

class TestUpdateCounters:
    def test_diagram_counter(self):
        g = _fresh_gamification()
        _update_counters(g, "diagram_generated", {"model": "claude-haiku-4-5"})
        assert g.counters.diagrams_generated == 1

    def test_chat_counter(self):
        g = _fresh_gamification()
        _update_counters(g, "chat_message", {})
        assert g.counters.chat_messages_sent == 1

    def test_node_counter(self):
        g = _fresh_gamification()
        _update_counters(g, "node_added", {"node_type": "database"})
        assert g.counters.nodes_added == 1

    def test_edge_counter(self):
        g = _fresh_gamification()
        _update_counters(g, "edge_added", {})
        assert g.counters.edges_added == 1

    def test_group_counter(self):
        g = _fresh_gamification()
        _update_counters(g, "group_created", {})
        assert g.counters.groups_created == 1

    def test_export_counter(self):
        g = _fresh_gamification()
        _update_counters(g, "export_completed", {"format": "pdf"})
        assert g.counters.exports_completed == 1

    def test_design_doc_counter(self):
        g = _fresh_gamification()
        _update_counters(g, "design_doc_generated", {})
        assert g.counters.design_docs_generated == 1

    def test_repo_counter(self):
        g = _fresh_gamification()
        _update_counters(g, "repo_analyzed", {})
        assert g.counters.repos_analyzed == 1

    def test_session_counter(self):
        g = _fresh_gamification()
        _update_counters(g, "session_created", {})
        assert g.counters.sessions_created == 1

    def test_unknown_action_does_nothing(self):
        g = _fresh_gamification()
        _update_counters(g, "unknown_action", {})
        assert g.counters.diagrams_generated == 0

    def test_counter_increments(self):
        g = _fresh_gamification()
        _update_counters(g, "chat_message", {})
        _update_counters(g, "chat_message", {})
        _update_counters(g, "chat_message", {})
        assert g.counters.chat_messages_sent == 3


# ── List appends ──

class TestListAppends:
    def test_node_type_appended(self):
        g = _fresh_gamification()
        _update_counters(g, "node_added", {"node_type": "database"})
        assert "database" in g.counters.node_types_used

    def test_node_type_deduplication(self):
        g = _fresh_gamification()
        _update_counters(g, "node_added", {"node_type": "database"})
        _update_counters(g, "node_added", {"node_type": "database"})
        assert g.counters.node_types_used.count("database") == 1

    def test_multiple_node_types(self):
        g = _fresh_gamification()
        _update_counters(g, "node_added", {"node_type": "database"})
        _update_counters(g, "node_added", {"node_type": "cache"})
        assert set(g.counters.node_types_used) == {"database", "cache"}

    def test_export_format_appended(self):
        g = _fresh_gamification()
        _update_counters(g, "export_completed", {"format": "pdf"})
        assert "pdf" in g.counters.export_formats_used

    def test_model_appended(self):
        g = _fresh_gamification()
        _update_counters(g, "diagram_generated", {"model": "claude-haiku-4-5"})
        assert "claude-haiku-4-5" in g.counters.models_used

    def test_missing_metadata_key_does_not_append(self):
        g = _fresh_gamification()
        _update_counters(g, "node_added", {})  # no "node_type" key
        assert g.counters.node_types_used == []

    def test_none_metadata_does_not_crash(self):
        g = _fresh_gamification()
        _update_counters(g, "node_added", None)
        assert g.counters.nodes_added == 1
        assert g.counters.node_types_used == []


# ── Full process_action ──

class TestProcessAction:
    @patch("app.gamification.engine.get_gamification_storage")
    def test_basic_action_returns_xp(self, mock_get_storage):
        g = _fresh_gamification()
        storage = _mock_storage(g)
        mock_get_storage.return_value = storage

        result = process_action("test-user", "diagram_generated", {"model": "claude-haiku-4-5"})

        assert result["xp_gained"] >= XP_VALUES["diagram_generated"]
        assert g.counters.diagrams_generated == 1
        storage.save.assert_called_once_with(g)

    @patch("app.gamification.engine.get_gamification_storage")
    def test_first_action_triggers_daily_bonus(self, mock_get_storage):
        g = _fresh_gamification()
        storage = _mock_storage(g)
        mock_get_storage.return_value = storage

        result = process_action("test-user", "chat_message", {})

        # Should include daily_login bonus (first action ever = new day)
        # Also unlocks "first_chat" achievement (50 XP bonus)
        expected = XP_VALUES["chat_message"] + XP_VALUES["daily_login"] + XP_VALUES["achievement_unlocked"]
        assert result["xp_gained"] == expected

    @patch("app.gamification.engine.get_gamification_storage")
    def test_level_up_detected(self, mock_get_storage):
        # Start at 45 XP (level 1), add a diagram (25 XP) + daily (15 XP) = 85 XP (level 2)
        g = _fresh_gamification()
        g.xp_total = 45
        g.level = 1
        g.level_name = "Intern"
        storage = _mock_storage(g)
        mock_get_storage.return_value = storage

        result = process_action("test-user", "diagram_generated", {"model": "claude-haiku-4-5"})

        assert result["level_up"] is True
        assert result["new_level"] == 2
        assert result["new_level_name"] == "Junior Designer"

    @patch("app.gamification.engine.get_gamification_storage")
    def test_no_level_up_when_same_level(self, mock_get_storage):
        g = _fresh_gamification()
        g.xp_total = 60  # Level 2
        g.level = 2
        g.level_name = "Junior Designer"
        g.last_active_date = datetime.utcnow().date().isoformat()  # same day
        storage = _mock_storage(g)
        mock_get_storage.return_value = storage

        result = process_action("test-user", "chat_message", {})

        assert result["level_up"] is False
        assert result["new_level"] is None

    @patch("app.gamification.engine.get_gamification_storage")
    def test_achievement_unlock(self, mock_get_storage):
        g = _fresh_gamification()
        g.counters.diagrams_generated = 0  # Will become 1 after action
        g.last_active_date = datetime.utcnow().date().isoformat()
        storage = _mock_storage(g)
        mock_get_storage.return_value = storage

        result = process_action("test-user", "diagram_generated", {"model": "claude-haiku-4-5"})

        # Should unlock "first_diagram"
        achievement_ids = [a["id"] for a in result["new_achievements"]]
        assert "first_diagram" in achievement_ids
        # Achievement bonus XP
        assert result["xp_gained"] >= XP_VALUES["diagram_generated"] + XP_VALUES["achievement_unlocked"]

    @patch("app.gamification.engine.get_gamification_storage")
    def test_achievement_adds_pending_notification(self, mock_get_storage):
        g = _fresh_gamification()
        g.last_active_date = datetime.utcnow().date().isoformat()
        storage = _mock_storage(g)
        mock_get_storage.return_value = storage

        process_action("test-user", "diagram_generated", {"model": "claude-haiku-4-5"})

        assert len(g.pending_notifications) > 0
        assert any(n.id == "first_diagram" for n in g.pending_notifications)

    @patch("app.gamification.engine.get_gamification_storage")
    def test_streak_tracked(self, mock_get_storage):
        g = _fresh_gamification()
        storage = _mock_storage(g)
        mock_get_storage.return_value = storage

        result = process_action("test-user", "chat_message", {})

        assert result["current_streak"] == 1

    @patch("app.gamification.engine.get_gamification_storage")
    def test_failure_returns_default_result(self, mock_get_storage):
        """Engine failures should return a safe default, not raise."""
        mock_get_storage.side_effect = Exception("DynamoDB is down!")

        result = process_action("test-user", "chat_message", {})

        assert result["xp_gained"] == 0
        assert result["level_up"] is False
        assert result["new_achievements"] == []
        assert result["current_streak"] == 0

    @patch("app.gamification.engine.get_gamification_storage")
    def test_save_failure_does_not_raise(self, mock_get_storage):
        """If save fails, the action should still return gracefully."""
        g = _fresh_gamification()
        storage = _mock_storage(g)
        storage.save.side_effect = Exception("DynamoDB write failed!")
        mock_get_storage.return_value = storage

        # Should not raise
        result = process_action("test-user", "chat_message", {})
        # Result will be default because exception is caught
        assert isinstance(result, dict)

    @patch("app.gamification.engine.get_gamification_storage")
    def test_achievement_xp_can_trigger_level_up(self, mock_get_storage):
        """Achievement bonus XP should be checked for level-up too."""
        g = _fresh_gamification()
        # Set XP just below level 2 threshold (50), after action XP + achievement bonus
        # chat_message = 5 XP, daily = 15 XP, achievement = 50 XP = 70 total
        g.xp_total = 0
        g.level = 1
        g.level_name = "Intern"
        storage = _mock_storage(g)
        mock_get_storage.return_value = storage

        # This will unlock first_chat (50 XP bonus) + daily (15) + action (5) = 70 XP
        result = process_action("test-user", "chat_message", {})

        assert result["level_up"] is True
        assert result["new_level"] == 2

    @patch("app.gamification.engine.get_gamification_storage")
    def test_multiple_achievements_at_once(self, mock_get_storage):
        """Multiple achievements can unlock in a single action."""
        g = _fresh_gamification()
        g.counters.diagrams_generated = 4  # Will become 5 (unlocks first_diagram + diagrams_5)
        g.last_active_date = datetime.utcnow().date().isoformat()
        storage = _mock_storage(g)
        mock_get_storage.return_value = storage

        result = process_action("test-user", "diagram_generated", {"model": "claude-haiku-4-5"})

        achievement_ids = [a["id"] for a in result["new_achievements"]]
        assert "diagrams_5" in achievement_ids

    @patch("app.gamification.engine.get_gamification_storage")
    def test_none_metadata_handled(self, mock_get_storage):
        """Passing None metadata should not crash."""
        g = _fresh_gamification()
        storage = _mock_storage(g)
        mock_get_storage.return_value = storage

        result = process_action("test-user", "edge_added", None)

        assert g.counters.edges_added == 1
        assert result["xp_gained"] > 0
