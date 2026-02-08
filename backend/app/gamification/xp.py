"""XP values per action and level threshold definitions."""

# XP awarded for each action type
XP_VALUES = {
    "diagram_generated": 25,
    "chat_message": 5,
    "design_doc_generated": 30,
    "export_completed": 10,
    "node_added": 3,
    "edge_added": 2,
    "group_created": 8,
    "group_collapsed": 2,
    "repo_analyzed": 35,
    "session_created": 5,
    "daily_login": 15,
    "achievement_unlocked": 50,
}

# Level definitions: (cumulative XP threshold, display name, color hex)
LEVELS = [
    (0, "Intern", "#888888"),
    (50, "Junior Designer", "#4CAF50"),
    (150, "Designer", "#4CAF50"),
    (350, "Senior Designer", "#2196F3"),
    (600, "Architect", "#2196F3"),
    (1000, "Senior Architect", "#9C27B0"),
    (1600, "Lead Architect", "#9C27B0"),
    (2500, "Principal Architect", "#FF9800"),
    (4000, "Distinguished Architect", "#FF9800"),
    (6000, "Chief Architect", "#FFD700"),
]


def calculate_level(xp_total: int) -> tuple:
    """Return (level_number, level_name) for the given XP total.

    Level numbers are 1-indexed (1 through 10).
    """
    level_num = 1
    level_name = LEVELS[0][1]

    for i, (threshold, name, _color) in enumerate(LEVELS):
        if xp_total >= threshold:
            level_num = i + 1
            level_name = name

    return level_num, level_name


def get_xp_for_action(action: str) -> int:
    """Return XP value for the given action, or 0 if unknown."""
    return XP_VALUES.get(action, 0)


def get_level_progress(xp_total: int) -> dict:
    """Return progress info for the current level.

    Returns dict with: level, level_name, level_color, xp_total,
    xp_current_level_start, xp_next_level_threshold, xp_to_next_level.
    """
    level_num, level_name = calculate_level(xp_total)
    level_idx = level_num - 1
    current_threshold = LEVELS[level_idx][0]
    level_color = LEVELS[level_idx][2]

    if level_idx < len(LEVELS) - 1:
        next_threshold = LEVELS[level_idx + 1][0]
        xp_to_next = next_threshold - xp_total
    else:
        next_threshold = LEVELS[-1][0]
        xp_to_next = 0  # Max level

    return {
        "level": level_num,
        "level_name": level_name,
        "level_color": level_color,
        "xp_total": xp_total,
        "xp_current_level_start": current_threshold,
        "xp_next_level_threshold": next_threshold,
        "xp_to_next_level": max(xp_to_next, 0),
    }
