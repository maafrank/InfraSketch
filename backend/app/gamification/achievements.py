"""Achievement definitions and unlock-check logic."""

from typing import List
from .models import UserGamification


# Rarity tiers for display
RARITY_COMMON = "common"
RARITY_UNCOMMON = "uncommon"
RARITY_RARE = "rare"
RARITY_EPIC = "epic"
RARITY_LEGENDARY = "legendary"

# Categories
CAT_FIRST_TIME = "first_time"
CAT_VOLUME = "volume"
CAT_FEATURE = "feature_discovery"
CAT_STREAK = "streaks"


ACHIEVEMENT_DEFINITIONS = [
    # ── First-time actions (7) ──
    {
        "id": "first_diagram",
        "name": "First Blueprint",
        "description": "Generated your first diagram",
        "rarity": RARITY_COMMON,
        "category": CAT_FIRST_TIME,
        "check": lambda g: g.counters.diagrams_generated >= 1,
        "progress": lambda g: {"current": g.counters.diagrams_generated, "target": 1},
    },
    {
        "id": "first_chat",
        "name": "Conversationalist",
        "description": "Sent your first chat message",
        "rarity": RARITY_COMMON,
        "category": CAT_FIRST_TIME,
        "check": lambda g: g.counters.chat_messages_sent >= 1,
        "progress": lambda g: {"current": g.counters.chat_messages_sent, "target": 1},
    },
    {
        "id": "first_design_doc",
        "name": "Documenter",
        "description": "Generated your first design document",
        "rarity": RARITY_COMMON,
        "category": CAT_FIRST_TIME,
        "check": lambda g: g.counters.design_docs_generated >= 1,
        "progress": lambda g: {"current": g.counters.design_docs_generated, "target": 1},
    },
    {
        "id": "first_export",
        "name": "Publisher",
        "description": "Exported a design for the first time",
        "rarity": RARITY_COMMON,
        "category": CAT_FIRST_TIME,
        "check": lambda g: g.counters.exports_completed >= 1,
        "progress": lambda g: {"current": g.counters.exports_completed, "target": 1},
    },
    {
        "id": "first_group",
        "name": "Organizer",
        "description": "Created your first node group",
        "rarity": RARITY_COMMON,
        "category": CAT_FIRST_TIME,
        "check": lambda g: g.counters.groups_created >= 1,
        "progress": lambda g: {"current": g.counters.groups_created, "target": 1},
    },
    {
        "id": "first_node",
        "name": "Foundation Stone",
        "description": "Added your first manual node",
        "rarity": RARITY_COMMON,
        "category": CAT_FIRST_TIME,
        "check": lambda g: g.counters.nodes_added >= 1,
        "progress": lambda g: {"current": g.counters.nodes_added, "target": 1},
    },
    {
        "id": "first_repo_analysis",
        "name": "Code Reader",
        "description": "Analyzed your first GitHub repository",
        "rarity": RARITY_COMMON,
        "category": CAT_FIRST_TIME,
        "check": lambda g: g.counters.repos_analyzed >= 1,
        "progress": lambda g: {"current": g.counters.repos_analyzed, "target": 1},
    },
    # ── Volume milestones (15) ──
    {
        "id": "diagrams_5",
        "name": "Sketcher",
        "description": "Generated 5 diagrams",
        "rarity": RARITY_UNCOMMON,
        "category": CAT_VOLUME,
        "check": lambda g: g.counters.diagrams_generated >= 5,
        "progress": lambda g: {"current": g.counters.diagrams_generated, "target": 5},
    },
    {
        "id": "diagrams_25",
        "name": "Draftsman",
        "description": "Generated 25 diagrams",
        "rarity": RARITY_RARE,
        "category": CAT_VOLUME,
        "check": lambda g: g.counters.diagrams_generated >= 25,
        "progress": lambda g: {"current": g.counters.diagrams_generated, "target": 25},
    },
    {
        "id": "diagrams_100",
        "name": "Master Planner",
        "description": "Generated 100 diagrams",
        "rarity": RARITY_LEGENDARY,
        "category": CAT_VOLUME,
        "check": lambda g: g.counters.diagrams_generated >= 100,
        "progress": lambda g: {"current": g.counters.diagrams_generated, "target": 100},
    },
    {
        "id": "chat_10",
        "name": "Curious Mind",
        "description": "Sent 10 chat messages",
        "rarity": RARITY_UNCOMMON,
        "category": CAT_VOLUME,
        "check": lambda g: g.counters.chat_messages_sent >= 10,
        "progress": lambda g: {"current": g.counters.chat_messages_sent, "target": 10},
    },
    {
        "id": "chat_50",
        "name": "Deep Thinker",
        "description": "Sent 50 chat messages",
        "rarity": RARITY_RARE,
        "category": CAT_VOLUME,
        "check": lambda g: g.counters.chat_messages_sent >= 50,
        "progress": lambda g: {"current": g.counters.chat_messages_sent, "target": 50},
    },
    {
        "id": "chat_250",
        "name": "AI Whisperer",
        "description": "Sent 250 chat messages",
        "rarity": RARITY_LEGENDARY,
        "category": CAT_VOLUME,
        "check": lambda g: g.counters.chat_messages_sent >= 250,
        "progress": lambda g: {"current": g.counters.chat_messages_sent, "target": 250},
    },
    {
        "id": "nodes_10",
        "name": "Builder",
        "description": "Added 10 nodes manually",
        "rarity": RARITY_UNCOMMON,
        "category": CAT_VOLUME,
        "check": lambda g: g.counters.nodes_added >= 10,
        "progress": lambda g: {"current": g.counters.nodes_added, "target": 10},
    },
    {
        "id": "nodes_50",
        "name": "Constructor",
        "description": "Added 50 nodes manually",
        "rarity": RARITY_RARE,
        "category": CAT_VOLUME,
        "check": lambda g: g.counters.nodes_added >= 50,
        "progress": lambda g: {"current": g.counters.nodes_added, "target": 50},
    },
    {
        "id": "design_docs_5",
        "name": "Technical Writer",
        "description": "Generated 5 design documents",
        "rarity": RARITY_UNCOMMON,
        "category": CAT_VOLUME,
        "check": lambda g: g.counters.design_docs_generated >= 5,
        "progress": lambda g: {"current": g.counters.design_docs_generated, "target": 5},
    },
    {
        "id": "design_docs_25",
        "name": "Documentation Lead",
        "description": "Generated 25 design documents",
        "rarity": RARITY_LEGENDARY,
        "category": CAT_VOLUME,
        "check": lambda g: g.counters.design_docs_generated >= 25,
        "progress": lambda g: {"current": g.counters.design_docs_generated, "target": 25},
    },
    {
        "id": "exports_10",
        "name": "Distributor",
        "description": "Completed 10 exports",
        "rarity": RARITY_UNCOMMON,
        "category": CAT_VOLUME,
        "check": lambda g: g.counters.exports_completed >= 10,
        "progress": lambda g: {"current": g.counters.exports_completed, "target": 10},
    },
    {
        "id": "exports_50",
        "name": "Publishing House",
        "description": "Completed 50 exports",
        "rarity": RARITY_LEGENDARY,
        "category": CAT_VOLUME,
        "check": lambda g: g.counters.exports_completed >= 50,
        "progress": lambda g: {"current": g.counters.exports_completed, "target": 50},
    },
    {
        "id": "sessions_10",
        "name": "Prolific Designer",
        "description": "Created 10 sessions",
        "rarity": RARITY_UNCOMMON,
        "category": CAT_VOLUME,
        "check": lambda g: g.counters.sessions_created >= 10,
        "progress": lambda g: {"current": g.counters.sessions_created, "target": 10},
    },
    {
        "id": "sessions_50",
        "name": "Design Factory",
        "description": "Created 50 sessions",
        "rarity": RARITY_LEGENDARY,
        "category": CAT_VOLUME,
        "check": lambda g: g.counters.sessions_created >= 50,
        "progress": lambda g: {"current": g.counters.sessions_created, "target": 50},
    },
    {
        "id": "groups_10",
        "name": "Architect of Order",
        "description": "Created 10 node groups",
        "rarity": RARITY_RARE,
        "category": CAT_VOLUME,
        "check": lambda g: g.counters.groups_created >= 10,
        "progress": lambda g: {"current": g.counters.groups_created, "target": 10},
    },
    # ── Feature discovery (5) ──
    {
        "id": "all_node_types",
        "name": "Full Spectrum",
        "description": "Used all available node types",
        "rarity": RARITY_EPIC,
        "category": CAT_FEATURE,
        "check": lambda g: len(g.counters.node_types_used) >= 10,
        "progress": lambda g: {"current": len(g.counters.node_types_used), "target": 10},
    },
    {
        "id": "all_export_formats",
        "name": "Format Master",
        "description": "Used all export formats (PNG, PDF, Markdown)",
        "rarity": RARITY_EPIC,
        "category": CAT_FEATURE,
        "check": lambda g: len(g.counters.export_formats_used) >= 3,
        "progress": lambda g: {"current": len(g.counters.export_formats_used), "target": 3},
    },
    {
        "id": "model_explorer",
        "name": "Model Connoisseur",
        "description": "Used at least 2 different AI models",
        "rarity": RARITY_EPIC,
        "category": CAT_FEATURE,
        "check": lambda g: len(g.counters.models_used) >= 2,
        "progress": lambda g: {"current": len(g.counters.models_used), "target": 2},
    },
    {
        "id": "group_master",
        "name": "Collapse Artist",
        "description": "Collapsed a group for the first time",
        "rarity": RARITY_EPIC,
        "category": CAT_FEATURE,
        "check": lambda g: g.counters.groups_collapsed >= 1,
        "progress": lambda g: {"current": g.counters.groups_collapsed, "target": 1},
    },
    {
        "id": "multi_model",
        "name": "Triple Threat",
        "description": "Used all 3 AI model tiers",
        "rarity": RARITY_EPIC,
        "category": CAT_FEATURE,
        "check": lambda g: len(g.counters.models_used) >= 3,
        "progress": lambda g: {"current": len(g.counters.models_used), "target": 3},
    },
    # ── Streak achievements (5) ──
    {
        "id": "streak_3",
        "name": "Warming Up",
        "description": "Maintained a 3-day streak",
        "rarity": RARITY_UNCOMMON,
        "category": CAT_STREAK,
        "check": lambda g: g.longest_streak >= 3,
        "progress": lambda g: {"current": g.longest_streak, "target": 3},
    },
    {
        "id": "streak_7",
        "name": "Weekly Warrior",
        "description": "Maintained a 7-day streak",
        "rarity": RARITY_RARE,
        "category": CAT_STREAK,
        "check": lambda g: g.longest_streak >= 7,
        "progress": lambda g: {"current": g.longest_streak, "target": 7},
    },
    {
        "id": "streak_14",
        "name": "Two-Week Titan",
        "description": "Maintained a 14-day streak",
        "rarity": RARITY_RARE,
        "category": CAT_STREAK,
        "check": lambda g: g.longest_streak >= 14,
        "progress": lambda g: {"current": g.longest_streak, "target": 14},
    },
    {
        "id": "streak_30",
        "name": "Monthly Master",
        "description": "Maintained a 30-day streak",
        "rarity": RARITY_EPIC,
        "category": CAT_STREAK,
        "check": lambda g: g.longest_streak >= 30,
        "progress": lambda g: {"current": g.longest_streak, "target": 30},
    },
    {
        "id": "streak_100",
        "name": "Centurion",
        "description": "Maintained a 100-day streak",
        "rarity": RARITY_LEGENDARY,
        "category": CAT_STREAK,
        "check": lambda g: g.longest_streak >= 100,
        "progress": lambda g: {"current": g.longest_streak, "target": 100},
    },
]

# Build a lookup dict by id for fast access
ACHIEVEMENTS_BY_ID = {a["id"]: a for a in ACHIEVEMENT_DEFINITIONS}


def check_achievements(gamification: UserGamification) -> List[str]:
    """Check all achievements and return list of newly unlocked achievement IDs."""
    already_unlocked = {a.id for a in gamification.achievements}
    newly_unlocked = []

    for defn in ACHIEVEMENT_DEFINITIONS:
        if defn["id"] in already_unlocked:
            continue
        if defn["check"](gamification):
            newly_unlocked.append(defn["id"])

    return newly_unlocked


def get_achievement_progress(gamification: UserGamification) -> list:
    """Return all achievements with unlock status and progress info."""
    already_unlocked = {a.id: a.unlocked_at for a in gamification.achievements}
    result = []

    for defn in ACHIEVEMENT_DEFINITIONS:
        entry = {
            "id": defn["id"],
            "name": defn["name"],
            "description": defn["description"],
            "rarity": defn["rarity"],
            "category": defn["category"],
            "unlocked": defn["id"] in already_unlocked,
            "unlocked_at": (
                already_unlocked[defn["id"]].isoformat()
                if defn["id"] in already_unlocked
                else None
            ),
            "progress": defn["progress"](gamification),
        }
        result.append(entry)

    return result
