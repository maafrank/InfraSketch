"""
Pydantic models for billing and credits.
"""

from pydantic import BaseModel, Field
from typing import Optional, Literal, List
from datetime import datetime


class UserCredits(BaseModel):
    """User credit balance and subscription state."""

    user_id: str
    plan: Literal["free", "pro", "enterprise"] = "free"
    plan_started_at: Optional[datetime] = None
    plan_expires_at: Optional[datetime] = None

    # Credit balances
    credits_balance: int = 25  # Current available credits (from subscription)
    credits_monthly_allowance: int = 25  # Credits granted each billing cycle
    credits_used_this_period: int = 0  # Usage tracking for analytics

    # Subscription tracking (synced from Clerk)
    clerk_subscription_id: Optional[str] = None
    stripe_customer_id: Optional[str] = None
    subscription_status: Literal[
        "active", "canceled", "past_due", "trialing", "none"
    ] = "none"

    # Promo codes redeemed (to prevent re-use)
    redeemed_promo_codes: List[str] = Field(default_factory=list)

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    last_credit_reset_at: Optional[datetime] = None


class CreditTransaction(BaseModel):
    """Audit log for credit changes."""

    transaction_id: str
    user_id: str
    type: Literal["deduction", "grant", "promo", "reset", "upgrade", "downgrade"]
    amount: int  # Positive for grants, negative for deductions
    balance_after: int
    action: str  # What triggered this (e.g., "diagram_generation", "chat_message")
    session_id: Optional[str] = None
    metadata: dict = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class PromoCode(BaseModel):
    """Promo code definition."""

    code: str
    credits: int
    expires_at: Optional[datetime] = None
    max_uses: Optional[int] = None
    current_uses: int = 0
    is_active: bool = True


class CreditCheckResult(BaseModel):
    """Result of a credit check operation."""

    success: bool
    cost: int
    balance_before: int
    balance_after: int
    error: Optional[str] = None
