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

# Per-tier API limits. context_window covers input + output combined.
# Source: https://docs.claude.com/en/docs/about-claude/models/overview
MODEL_LIMITS = {
    "haiku": {"context_window": 200_000, "max_output": 64_000},
    "sonnet": {"context_window": 1_000_000, "max_output": 64_000},
    "opus": {"context_window": 1_000_000, "max_output": 128_000},
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


def get_model_limits(model_id: str) -> dict:
    """Get {context_window, max_output} for a model ID."""
    return MODEL_LIMITS[get_model_tier(model_id)]


def estimate_input_tokens(text_or_messages) -> int:
    """
    Rough character-based token estimate. Overestimates slightly (uses 3 chars/token
    instead of ~4) so dynamic max_tokens stays on the safe side of context limits.

    Accepts a string, a list of strings, or a list of message-like dicts/objects
    with a ``content`` attribute or key.
    """
    if not text_or_messages:
        return 0

    if isinstance(text_or_messages, str):
        return len(text_or_messages) // 3 + 1

    total_chars = 0
    for item in text_or_messages:
        if isinstance(item, str):
            total_chars += len(item)
        elif isinstance(item, dict):
            content = item.get("content", "")
            if isinstance(content, str):
                total_chars += len(content)
            elif isinstance(content, list):
                for block in content:
                    if isinstance(block, dict):
                        total_chars += len(str(block.get("text", "")))
                    else:
                        total_chars += len(str(block))
        else:
            content = getattr(item, "content", "")
            if isinstance(content, str):
                total_chars += len(content)
            elif isinstance(content, list):
                for block in content:
                    if isinstance(block, dict):
                        total_chars += len(str(block.get("text", "")))
                    else:
                        total_chars += len(str(block))
    return total_chars // 3 + 1


def compute_max_output_tokens(
    model_id: str,
    estimated_input_tokens: int = 0,
    safety_buffer: int = 4_000,
    minimum: int = 1_024,
    requested_max: int | None = None,
) -> int:
    """
    Compute max_tokens for a Claude API call, sized to fit the model's context window.

    The Anthropic API rejects requests where input_tokens + max_tokens > context_window.
    This shrinks max_tokens when input is large so large user inputs do not get rejected.

    Args:
        model_id: Model ID (alias or snapshot).
        estimated_input_tokens: Rough token count of the input (see estimate_input_tokens).
        safety_buffer: Reserved headroom in tokens to absorb estimation error.
        minimum: Floor so callers always get a usable output budget.
        requested_max: Optional ceiling (e.g. for tasks that only need a short reply).
            The returned value will not exceed this.

    Returns:
        max_tokens value to pass to ChatAnthropic / Anthropic SDK.
    """
    limits = get_model_limits(model_id)
    ceiling = limits["max_output"]
    if requested_max is not None:
        ceiling = min(ceiling, requested_max)

    available = limits["context_window"] - estimated_input_tokens - safety_buffer
    if available < minimum:
        return minimum
    return min(ceiling, available)
