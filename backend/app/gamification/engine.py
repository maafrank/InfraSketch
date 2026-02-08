"""Gamification engine - main entry point for processing user actions."""

from datetime import datetime
from .models import UserGamification, UnlockedAchievement, PendingNotification
from .storage import get_gamification_storage
from .achievements import check_achievements, ACHIEVEMENTS_BY_ID
from .xp import XP_VALUES, calculate_level, get_xp_for_action
from .streaks import update_streak


# Maps action names to counter fields and list-append metadata keys
_COUNTER_MAP = {
    "diagram_generated": ("diagrams_generated", None),
    "chat_message": ("chat_messages_sent", None),
    "design_doc_generated": ("design_docs_generated", None),
    "export_completed": ("exports_completed", None),
    "node_added": ("nodes_added", None),
    "edge_added": ("edges_added", None),
    "group_created": ("groups_created", None),
    "group_collapsed": ("groups_collapsed", None),
    "repo_analyzed": ("repos_analyzed", None),
    "session_created": ("sessions_created", None),
}

# Actions that append to set-like lists
_LIST_APPEND_MAP = {
    "node_added": ("node_types_used", "node_type"),
    "export_completed": ("export_formats_used", "format"),
    "diagram_generated": ("models_used", "model"),
    "chat_message": ("models_used", "model"),
    "session_created": ("models_used", "model"),
}


def _update_counters(gamification: UserGamification, action: str, metadata: dict):
    """Increment the appropriate counter and append to set-lists."""
    counter_info = _COUNTER_MAP.get(action)
    if counter_info:
        field_name = counter_info[0]
        current = getattr(gamification.counters, field_name)
        setattr(gamification.counters, field_name, current + 1)

    list_info = _LIST_APPEND_MAP.get(action)
    if list_info and metadata:
        list_field, meta_key = list_info
        value = metadata.get(meta_key)
        if value:
            current_list = getattr(gamification.counters, list_field)
            if value not in current_list:
                current_list.append(value)


def process_action(user_id: str, action: str, metadata: dict = None) -> dict:
    """Process a user action for gamification purposes.

    Called after the primary operation succeeds. Failures here are logged
    but do not propagate to the caller.

    Args:
        user_id: Clerk user ID
        action: Action type (e.g., "diagram_generated", "chat_message")
        metadata: Extra context (e.g., {"node_type": "database", "model": "claude-haiku-4-5"})

    Returns:
        dict with: xp_gained, level_up, new_level, new_level_name,
                   new_achievements, current_streak
    """
    if metadata is None:
        metadata = {}

    result = {
        "xp_gained": 0,
        "level_up": False,
        "new_level": None,
        "new_level_name": None,
        "new_achievements": [],
        "current_streak": 0,
    }

    try:
        storage = get_gamification_storage()
        gamification = storage.get_or_create(user_id)

        # 1. Update counters
        _update_counters(gamification, action, metadata)

        # 2. Update streak
        streak_result = update_streak(gamification)
        if streak_result["is_new_day"]:
            gamification.xp_total += XP_VALUES["daily_login"]
            result["xp_gained"] += XP_VALUES["daily_login"]
        result["current_streak"] = gamification.current_streak

        # 3. Award XP for this action
        action_xp = get_xp_for_action(action)
        gamification.xp_total += action_xp
        result["xp_gained"] += action_xp

        # 4. Check for level up
        new_level, new_name = calculate_level(gamification.xp_total)
        if new_level > gamification.level:
            gamification.level = new_level
            gamification.level_name = new_name
            result["level_up"] = True
            result["new_level"] = new_level
            result["new_level_name"] = new_name

        # 5. Check achievements
        newly_unlocked = check_achievements(gamification)
        now = datetime.utcnow()
        for achievement_id in newly_unlocked:
            # Record the unlock
            gamification.achievements.append(
                UnlockedAchievement(id=achievement_id, unlocked_at=now)
            )
            # Add to pending notifications
            gamification.pending_notifications.append(
                PendingNotification(id=achievement_id, unlocked_at=now)
            )
            # Bonus XP
            gamification.xp_total += XP_VALUES["achievement_unlocked"]
            result["xp_gained"] += XP_VALUES["achievement_unlocked"]

            # Include achievement details in result
            defn = ACHIEVEMENTS_BY_ID.get(achievement_id, {})
            result["new_achievements"].append({
                "id": achievement_id,
                "name": defn.get("name", achievement_id),
                "description": defn.get("description", ""),
                "rarity": defn.get("rarity", "common"),
            })

        # Re-check level after achievement bonus XP
        if newly_unlocked:
            new_level, new_name = calculate_level(gamification.xp_total)
            if new_level > gamification.level:
                gamification.level = new_level
                gamification.level_name = new_name
                result["level_up"] = True
                result["new_level"] = new_level
                result["new_level_name"] = new_name

        # 6. Save
        storage.save(gamification)

    except Exception as e:
        print(f"Gamification error for user {user_id}, action {action}: {e}")
        # Fail silently, don't break the primary operation

    return result
