"""
Centralized Claude model configuration.

When Anthropic releases new model versions, update ONLY this file
(and frontend/src/constants/models.js).
"""

# Current model aliases (auto-resolve to latest snapshot)
HAIKU = "claude-haiku-4-5"
SONNET = "claude-sonnet-4-6"
OPUS = "claude-opus-4-6"

# Default model for most operations
DEFAULT_MODEL = HAIKU

# Cost multipliers by tier
TIER_MULTIPLIERS = {
    "haiku": 1.0,
    "sonnet": 3.0,
    "opus": 5.0,
}


def get_model_tier(model_id: str) -> str:
    """
    Map any model ID (alias or snapshot) to its tier: 'haiku', 'sonnet', or 'opus'.
    Uses substring matching so old snapshot IDs (e.g. claude-sonnet-4-5-20251001)
    are handled automatically.
    """
    model_lower = model_id.lower()
    if "opus" in model_lower:
        return "opus"
    if "sonnet" in model_lower:
        return "sonnet"
    return "haiku"


def get_model_multiplier(model_id: str) -> float:
    """Get cost multiplier for any model ID."""
    tier = get_model_tier(model_id)
    return TIER_MULTIPLIERS[tier]
