"""
Pydantic models for email subscription management.
"""
from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field


class Subscriber(BaseModel):
    """Email subscriber record."""
    user_id: str = Field(..., description="Clerk user ID")
    email: str = Field(..., description="User's email address")
    subscribed: bool = Field(default=True, description="Whether user is subscribed to emails")
    unsubscribe_token: str = Field(..., description="Unique token for unsubscribe links")
    created_at: str = Field(..., description="ISO timestamp when subscriber was added")
    updated_at: str = Field(..., description="ISO timestamp of last preference change")
    unsubscribed_at: Optional[str] = Field(default=None, description="ISO timestamp when unsubscribed")


class SubscriptionStatus(BaseModel):
    """Response model for subscription status endpoint."""
    subscribed: bool
    email: str


class SubscribeRequest(BaseModel):
    """Request model for subscribe endpoint."""
    email: str
