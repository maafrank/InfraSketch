"""
Promo code validation and redemption.
"""

from typing import Optional, Tuple
from datetime import datetime
from .models import PromoCode
from .storage import get_user_credits_storage

# Promo code definitions
# In production, these could be stored in DynamoDB or environment variables
PROMO_CODES = {
    "LAUNCH100": PromoCode(
        code="LAUNCH100",
        credits=100,
        expires_at=datetime(2025, 6, 1),
        max_uses=1000,
    ),
    "BETA50": PromoCode(
        code="BETA50",
        credits=50,
        expires_at=None,
        max_uses=None,
    ),
    "WELCOME25": PromoCode(
        code="WELCOME25",
        credits=25,
        expires_at=None,
        max_uses=None,
    ),
    "FREE100": PromoCode(
        code="FREE100",
        credits=100,
        expires_at=None,
        max_uses=None,
    ),
}


def validate_promo_code(code: str, user_id: str) -> Tuple[bool, Optional[str]]:
    """
    Validate a promo code.

    Args:
        code: The promo code to validate
        user_id: The user attempting to redeem

    Returns:
        Tuple of (is_valid, error_message)
    """
    code_upper = code.upper().strip()

    # Check if code exists
    if code_upper not in PROMO_CODES:
        return (False, "Invalid promo code")

    promo = PROMO_CODES[code_upper]

    # Check if code is active
    if not promo.is_active:
        return (False, "This promo code is no longer active")

    # Check expiration
    if promo.expires_at and datetime.utcnow() > promo.expires_at:
        return (False, "This promo code has expired")

    # Check max uses
    if promo.max_uses is not None and promo.current_uses >= promo.max_uses:
        return (False, "This promo code has reached its usage limit")

    # Check if user already redeemed this code
    storage = get_user_credits_storage()
    if storage.has_redeemed_promo(user_id, code_upper):
        return (False, "You have already redeemed this promo code")

    return (True, None)


def redeem_promo_code(code: str, user_id: str) -> Tuple[bool, Optional[str], int]:
    """
    Redeem a promo code for a user.

    Args:
        code: The promo code to redeem
        user_id: The user redeeming the code

    Returns:
        Tuple of (success, error_message, credits_granted)
    """
    code_upper = code.upper().strip()

    # Validate first
    is_valid, error = validate_promo_code(code_upper, user_id)
    if not is_valid:
        return (False, error, 0)

    promo = PROMO_CODES[code_upper]
    storage = get_user_credits_storage()

    # Add credits to user
    storage.add_credits(
        user_id=user_id,
        amount=promo.credits,
        reason="promo_code",
        metadata={"promo_code": code_upper},
    )

    # Mark as redeemed
    storage.mark_promo_redeemed(user_id, code_upper)

    # Increment usage counter (in-memory, would need DynamoDB for persistence)
    promo.current_uses += 1

    return (True, None, promo.credits)


def get_promo_code_info(code: str) -> Optional[dict]:
    """Get info about a promo code (for display purposes)."""
    code_upper = code.upper().strip()
    if code_upper not in PROMO_CODES:
        return None

    promo = PROMO_CODES[code_upper]
    return {
        "code": promo.code,
        "credits": promo.credits,
        "expires_at": promo.expires_at.isoformat() if promo.expires_at else None,
        "is_active": promo.is_active,
    }
