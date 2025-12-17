"""Pydantic models for user preferences."""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class UserPreferences(BaseModel):
    """User preferences stored in DynamoDB."""

    user_id: str  # Clerk user ID (partition key)
    tutorial_completed: bool = False  # Whether user has completed the tutorial
    tutorial_completed_at: Optional[datetime] = None  # When tutorial was completed
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
