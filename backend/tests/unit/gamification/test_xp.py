"""Tests for XP values and level calculations.

Covers: XP values, level boundaries, max level, level progress info.
"""

from app.gamification.xp import (
    XP_VALUES,
    LEVELS,
    calculate_level,
    get_xp_for_action,
    get_level_progress,
)


# ── XP values ──

class TestXPValues:
    def test_all_expected_actions_have_xp(self):
        expected = [
            "diagram_generated", "chat_message", "design_doc_generated",
            "export_completed", "node_added", "edge_added", "group_created",
            "group_collapsed", "repo_analyzed", "session_created",
            "daily_login", "achievement_unlocked",
        ]
        for action in expected:
            assert action in XP_VALUES, f"Missing XP value for {action}"
            assert XP_VALUES[action] > 0, f"XP for {action} should be positive"

    def test_get_xp_for_known_action(self):
        assert get_xp_for_action("diagram_generated") == 25
        assert get_xp_for_action("chat_message") == 5
        assert get_xp_for_action("repo_analyzed") == 35

    def test_get_xp_for_unknown_action(self):
        assert get_xp_for_action("nonexistent_action") == 0
        assert get_xp_for_action("") == 0


# ── Level calculations ──

class TestCalculateLevel:
    def test_zero_xp_is_level_1(self):
        level, name = calculate_level(0)
        assert level == 1
        assert name == "Intern"

    def test_just_below_level_2(self):
        level, name = calculate_level(49)
        assert level == 1
        assert name == "Intern"

    def test_exact_level_2_threshold(self):
        level, name = calculate_level(50)
        assert level == 2
        assert name == "Junior Designer"

    def test_between_levels(self):
        level, name = calculate_level(200)
        assert level == 3
        assert name == "Designer"

    def test_max_level_exact(self):
        level, name = calculate_level(6000)
        assert level == 10
        assert name == "Chief Architect"

    def test_above_max_level(self):
        """XP above max threshold should still be level 10."""
        level, name = calculate_level(99999)
        assert level == 10
        assert name == "Chief Architect"

    def test_all_level_boundaries(self):
        """Test exact boundary for each level."""
        expected = [
            (0, 1, "Intern"),
            (50, 2, "Junior Designer"),
            (150, 3, "Designer"),
            (350, 4, "Senior Designer"),
            (600, 5, "Architect"),
            (1000, 6, "Senior Architect"),
            (1600, 7, "Lead Architect"),
            (2500, 8, "Principal Architect"),
            (4000, 9, "Distinguished Architect"),
            (6000, 10, "Chief Architect"),
        ]
        for xp, expected_level, expected_name in expected:
            level, name = calculate_level(xp)
            assert level == expected_level, f"At {xp} XP, expected level {expected_level} but got {level}"
            assert name == expected_name

    def test_just_below_each_threshold(self):
        """One XP below each threshold should be the previous level."""
        thresholds = [50, 150, 350, 600, 1000, 1600, 2500, 4000, 6000]
        for i, threshold in enumerate(thresholds):
            level, _ = calculate_level(threshold - 1)
            assert level == i + 1, f"At {threshold - 1} XP, expected level {i + 1} but got {level}"

    def test_levels_are_monotonically_increasing(self):
        """LEVELS thresholds must be strictly increasing."""
        for i in range(1, len(LEVELS)):
            assert LEVELS[i][0] > LEVELS[i - 1][0], (
                f"Level {i + 1} threshold ({LEVELS[i][0]}) must be greater than "
                f"level {i} threshold ({LEVELS[i - 1][0]})"
            )

    def test_exactly_10_levels(self):
        assert len(LEVELS) == 10


# ── Level progress ──

class TestGetLevelProgress:
    def test_new_user_progress(self):
        progress = get_level_progress(0)
        assert progress["level"] == 1
        assert progress["level_name"] == "Intern"
        assert progress["xp_total"] == 0
        assert progress["xp_current_level_start"] == 0
        assert progress["xp_next_level_threshold"] == 50
        assert progress["xp_to_next_level"] == 50

    def test_mid_level_progress(self):
        progress = get_level_progress(75)
        assert progress["level"] == 2
        assert progress["level_name"] == "Junior Designer"
        assert progress["xp_current_level_start"] == 50
        assert progress["xp_next_level_threshold"] == 150
        assert progress["xp_to_next_level"] == 75

    def test_max_level_progress(self):
        progress = get_level_progress(6000)
        assert progress["level"] == 10
        assert progress["level_name"] == "Chief Architect"
        assert progress["xp_to_next_level"] == 0

    def test_above_max_level_progress(self):
        progress = get_level_progress(10000)
        assert progress["level"] == 10
        assert progress["xp_to_next_level"] == 0

    def test_progress_has_color(self):
        progress = get_level_progress(0)
        assert "level_color" in progress
        assert progress["level_color"] == "#888888"

    def test_all_levels_have_colors(self):
        for threshold, name, color in LEVELS:
            assert color.startswith("#"), f"Level '{name}' has invalid color: {color}"
            assert len(color) == 7, f"Level '{name}' color should be 7 chars: {color}"
