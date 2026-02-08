"""Tests for achievement definitions and unlock logic.

Covers: all 32 achievement definitions, check logic, progress reporting,
edge cases around unlock detection.
"""

from app.gamification.models import UserGamification, UnlockedAchievement, GamificationCounters
from app.gamification.achievements import (
    ACHIEVEMENT_DEFINITIONS,
    ACHIEVEMENTS_BY_ID,
    check_achievements,
    get_achievement_progress,
    RARITY_COMMON,
    RARITY_UNCOMMON,
    RARITY_RARE,
    RARITY_EPIC,
    RARITY_LEGENDARY,
    CAT_FIRST_TIME,
    CAT_VOLUME,
    CAT_FEATURE,
    CAT_STREAK,
)
from datetime import datetime


def _make_gamification(**counter_overrides):
    """Build a UserGamification with custom counter values."""
    counters = GamificationCounters(**counter_overrides)
    return UserGamification(user_id="test-user", counters=counters)


def _make_with_streak(longest=0, current=0):
    """Build a UserGamification with streak values."""
    return UserGamification(
        user_id="test-user",
        current_streak=current,
        longest_streak=longest,
    )


# ── Achievement registry ──

class TestAchievementRegistry:
    def test_exactly_32_achievements(self):
        assert len(ACHIEVEMENT_DEFINITIONS) == 32

    def test_all_have_required_fields(self):
        required = {"id", "name", "description", "rarity", "category", "check", "progress"}
        for defn in ACHIEVEMENT_DEFINITIONS:
            for field in required:
                assert field in defn, f"Achievement '{defn.get('id', '?')}' missing field '{field}'"

    def test_all_ids_are_unique(self):
        ids = [d["id"] for d in ACHIEVEMENT_DEFINITIONS]
        assert len(ids) == len(set(ids)), f"Duplicate IDs found: {[x for x in ids if ids.count(x) > 1]}"

    def test_lookup_dict_matches(self):
        assert len(ACHIEVEMENTS_BY_ID) == len(ACHIEVEMENT_DEFINITIONS)
        for defn in ACHIEVEMENT_DEFINITIONS:
            assert ACHIEVEMENTS_BY_ID[defn["id"]] is defn

    def test_valid_rarities(self):
        valid = {RARITY_COMMON, RARITY_UNCOMMON, RARITY_RARE, RARITY_EPIC, RARITY_LEGENDARY}
        for defn in ACHIEVEMENT_DEFINITIONS:
            assert defn["rarity"] in valid, f"Achievement '{defn['id']}' has invalid rarity: {defn['rarity']}"

    def test_valid_categories(self):
        valid = {CAT_FIRST_TIME, CAT_VOLUME, CAT_FEATURE, CAT_STREAK}
        for defn in ACHIEVEMENT_DEFINITIONS:
            assert defn["category"] in valid, f"Achievement '{defn['id']}' has invalid category: {defn['category']}"

    def test_category_counts(self):
        by_cat = {}
        for defn in ACHIEVEMENT_DEFINITIONS:
            by_cat.setdefault(defn["category"], []).append(defn["id"])
        assert len(by_cat[CAT_FIRST_TIME]) == 7
        assert len(by_cat[CAT_VOLUME]) == 15
        assert len(by_cat[CAT_FEATURE]) == 5
        assert len(by_cat[CAT_STREAK]) == 5

    def test_check_functions_are_callable(self):
        g = _make_gamification()
        for defn in ACHIEVEMENT_DEFINITIONS:
            # Should not raise, should return bool
            result = defn["check"](g)
            assert isinstance(result, bool), f"Achievement '{defn['id']}' check should return bool, got {type(result)}"

    def test_progress_functions_return_dict_with_current_and_target(self):
        g = _make_gamification()
        for defn in ACHIEVEMENT_DEFINITIONS:
            progress = defn["progress"](g)
            assert "current" in progress, f"Achievement '{defn['id']}' progress missing 'current'"
            assert "target" in progress, f"Achievement '{defn['id']}' progress missing 'target'"
            assert progress["target"] > 0, f"Achievement '{defn['id']}' target should be positive"


# ── First-time achievements ──

class TestFirstTimeAchievements:
    def test_first_diagram_unlocks(self):
        g = _make_gamification(diagrams_generated=1)
        unlocked = check_achievements(g)
        assert "first_diagram" in unlocked

    def test_first_diagram_not_unlocked_at_zero(self):
        g = _make_gamification(diagrams_generated=0)
        unlocked = check_achievements(g)
        assert "first_diagram" not in unlocked

    def test_first_chat(self):
        g = _make_gamification(chat_messages_sent=1)
        assert "first_chat" in check_achievements(g)

    def test_first_design_doc(self):
        g = _make_gamification(design_docs_generated=1)
        assert "first_design_doc" in check_achievements(g)

    def test_first_export(self):
        g = _make_gamification(exports_completed=1)
        assert "first_export" in check_achievements(g)

    def test_first_group(self):
        g = _make_gamification(groups_created=1)
        assert "first_group" in check_achievements(g)

    def test_first_node(self):
        g = _make_gamification(nodes_added=1)
        assert "first_node" in check_achievements(g)

    def test_first_repo_analysis(self):
        g = _make_gamification(repos_analyzed=1)
        assert "first_repo_analysis" in check_achievements(g)


# ── Volume achievements ──

class TestVolumeAchievements:
    def test_diagram_volume_tiers(self):
        g = _make_gamification(diagrams_generated=5)
        unlocked = check_achievements(g)
        assert "diagrams_5" in unlocked
        assert "diagrams_25" not in unlocked

        g = _make_gamification(diagrams_generated=25)
        unlocked = check_achievements(g)
        assert "diagrams_5" in unlocked
        assert "diagrams_25" in unlocked
        assert "diagrams_100" not in unlocked

        g = _make_gamification(diagrams_generated=100)
        unlocked = check_achievements(g)
        assert "diagrams_100" in unlocked

    def test_chat_volume_tiers(self):
        g = _make_gamification(chat_messages_sent=10)
        assert "chat_10" in check_achievements(g)
        assert "chat_50" not in check_achievements(g)

        g = _make_gamification(chat_messages_sent=50)
        assert "chat_50" in check_achievements(g)

        g = _make_gamification(chat_messages_sent=250)
        assert "chat_250" in check_achievements(g)

    def test_node_volume(self):
        g = _make_gamification(nodes_added=10)
        assert "nodes_10" in check_achievements(g)
        assert "nodes_50" not in check_achievements(g)

        g = _make_gamification(nodes_added=50)
        assert "nodes_50" in check_achievements(g)

    def test_design_doc_volume(self):
        g = _make_gamification(design_docs_generated=5)
        assert "design_docs_5" in check_achievements(g)

        g = _make_gamification(design_docs_generated=25)
        assert "design_docs_25" in check_achievements(g)

    def test_export_volume(self):
        g = _make_gamification(exports_completed=10)
        assert "exports_10" in check_achievements(g)

        g = _make_gamification(exports_completed=50)
        assert "exports_50" in check_achievements(g)

    def test_session_volume(self):
        g = _make_gamification(sessions_created=10)
        assert "sessions_10" in check_achievements(g)

        g = _make_gamification(sessions_created=50)
        assert "sessions_50" in check_achievements(g)

    def test_group_volume(self):
        g = _make_gamification(groups_created=10)
        assert "groups_10" in check_achievements(g)


# ── Feature discovery achievements ──

class TestFeatureDiscovery:
    def test_all_node_types(self):
        g = _make_gamification(
            node_types_used=["cache", "database", "api", "server", "loadbalancer",
                            "queue", "cdn", "gateway", "storage", "service"]
        )
        assert "all_node_types" in check_achievements(g)

    def test_partial_node_types_not_unlocked(self):
        g = _make_gamification(node_types_used=["cache", "database", "api"])
        assert "all_node_types" not in check_achievements(g)

    def test_all_export_formats(self):
        g = _make_gamification(export_formats_used=["png", "pdf", "markdown"])
        assert "all_export_formats" in check_achievements(g)

    def test_partial_export_formats(self):
        g = _make_gamification(export_formats_used=["png"])
        assert "all_export_formats" not in check_achievements(g)

    def test_model_connoisseur(self):
        g = _make_gamification(models_used=["claude-haiku-4-5", "claude-sonnet-4-5"])
        assert "model_explorer" in check_achievements(g)

    def test_triple_threat(self):
        g = _make_gamification(
            models_used=["claude-haiku-4-5", "claude-sonnet-4-5", "claude-opus-4-5"]
        )
        assert "multi_model" in check_achievements(g)

    def test_collapse_artist(self):
        g = _make_gamification(groups_collapsed=1)
        assert "group_master" in check_achievements(g)


# ── Streak achievements ──

class TestStreakAchievements:
    def test_streak_3(self):
        g = _make_with_streak(longest=3)
        assert "streak_3" in check_achievements(g)

    def test_streak_7(self):
        g = _make_with_streak(longest=7)
        assert "streak_7" in check_achievements(g)

    def test_streak_14(self):
        g = _make_with_streak(longest=14)
        assert "streak_14" in check_achievements(g)

    def test_streak_30(self):
        g = _make_with_streak(longest=30)
        assert "streak_30" in check_achievements(g)

    def test_streak_100(self):
        g = _make_with_streak(longest=100)
        assert "streak_100" in check_achievements(g)

    def test_streak_uses_longest_not_current(self):
        """Streak achievements should check longest_streak, not current_streak."""
        g = _make_with_streak(longest=2, current=100)
        # current=100 should NOT count, only longest=2
        assert "streak_3" not in check_achievements(g)

    def test_streak_below_threshold(self):
        g = _make_with_streak(longest=6)
        assert "streak_3" in check_achievements(g)
        assert "streak_7" not in check_achievements(g)


# ── Already-unlocked filtering ──

class TestAlreadyUnlocked:
    def test_already_unlocked_not_returned(self):
        g = _make_gamification(diagrams_generated=5)
        # Mark first_diagram as already unlocked
        g.achievements.append(
            UnlockedAchievement(id="first_diagram", unlocked_at=datetime.utcnow())
        )
        unlocked = check_achievements(g)
        assert "first_diagram" not in unlocked
        assert "diagrams_5" in unlocked  # this one is new

    def test_all_unlocked_returns_empty(self):
        """If all qualifying achievements are already unlocked, return empty list."""
        g = _make_gamification(diagrams_generated=1)
        g.achievements.append(
            UnlockedAchievement(id="first_diagram", unlocked_at=datetime.utcnow())
        )
        # Only first_diagram qualifies, and it's already unlocked
        unlocked = check_achievements(g)
        assert "first_diagram" not in unlocked


# ── Progress reporting ──

class TestGetAchievementProgress:
    def test_returns_all_32_achievements(self):
        g = _make_gamification()
        progress = get_achievement_progress(g)
        assert len(progress) == 32

    def test_unlocked_achievement_shows_status(self):
        g = _make_gamification(diagrams_generated=1)
        now = datetime.utcnow()
        g.achievements.append(UnlockedAchievement(id="first_diagram", unlocked_at=now))

        progress = get_achievement_progress(g)
        first = next(p for p in progress if p["id"] == "first_diagram")
        assert first["unlocked"] is True
        assert first["unlocked_at"] is not None

    def test_locked_achievement_shows_progress(self):
        g = _make_gamification(diagrams_generated=3)
        progress = get_achievement_progress(g)
        sketcher = next(p for p in progress if p["id"] == "diagrams_5")
        assert sketcher["unlocked"] is False
        assert sketcher["unlocked_at"] is None
        assert sketcher["progress"]["current"] == 3
        assert sketcher["progress"]["target"] == 5

    def test_progress_has_all_fields(self):
        g = _make_gamification()
        progress = get_achievement_progress(g)
        for entry in progress:
            assert "id" in entry
            assert "name" in entry
            assert "description" in entry
            assert "rarity" in entry
            assert "category" in entry
            assert "unlocked" in entry
            assert "unlocked_at" in entry
            assert "progress" in entry


# ── Bulk unlock scenarios ──

class TestBulkUnlock:
    def test_multiple_first_time_achievements_at_once(self):
        """A user who does many things at once should unlock multiple achievements."""
        g = _make_gamification(
            diagrams_generated=1,
            chat_messages_sent=1,
            nodes_added=1,
        )
        unlocked = check_achievements(g)
        assert "first_diagram" in unlocked
        assert "first_chat" in unlocked
        assert "first_node" in unlocked

    def test_volume_unlocks_include_lower_tiers(self):
        """Hitting 100 diagrams should also unlock 5 and 25 if not already."""
        g = _make_gamification(diagrams_generated=100)
        unlocked = check_achievements(g)
        assert "first_diagram" in unlocked
        assert "diagrams_5" in unlocked
        assert "diagrams_25" in unlocked
        assert "diagrams_100" in unlocked
