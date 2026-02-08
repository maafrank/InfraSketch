"""Pydantic models for the gamification system."""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class UnlockedAchievement(BaseModel):
    id: str
    unlocked_at: datetime


class PendingNotification(BaseModel):
    id: str
    unlocked_at: datetime


class GamificationCounters(BaseModel):
    diagrams_generated: int = 0
    chat_messages_sent: int = 0
    design_docs_generated: int = 0
    exports_completed: int = 0
    nodes_added: int = 0
    edges_added: int = 0
    groups_created: int = 0
    groups_collapsed: int = 0
    models_used: List[str] = Field(default_factory=list)
    node_types_used: List[str] = Field(default_factory=list)
    export_formats_used: List[str] = Field(default_factory=list)
    repos_analyzed: int = 0
    sessions_created: int = 0


class UserGamification(BaseModel):
    user_id: str

    # XP & Levels
    xp_total: int = 0
    level: int = 1
    level_name: str = "Intern"

    # Streaks
    current_streak: int = 0
    longest_streak: int = 0
    last_active_date: Optional[str] = None  # "YYYY-MM-DD" in UTC
    streak_grace_used: bool = False
    streak_reminders_enabled: bool = True

    # Achievements
    achievements: List[UnlockedAchievement] = Field(default_factory=list)

    # Counters
    counters: GamificationCounters = Field(default_factory=GamificationCounters)

    # Pending notifications (unseen achievements)
    pending_notifications: List[PendingNotification] = Field(default_factory=list)

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
