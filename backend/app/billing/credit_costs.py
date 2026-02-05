"""
Credit cost configuration and calculation.
"""

from typing import Optional

# Credit costs by action and model
CREDIT_COSTS = {
    "diagram_generation": {
        "base": 5,
        "model_multipliers": {
            "claude-haiku-4-5": 1.0,
            "claude-haiku-4-5-20251001": 1.0,
            "claude-sonnet-4-5": 3.0,
            "claude-sonnet-4-5-20251001": 3.0,
            "claude-opus-4-5": 5.0,
            "claude-opus-4-5-20251101": 5.0,
        },
    },
    "chat_message": {
        "base": 1,
        "model_multipliers": {
            "claude-haiku-4-5": 1.0,
            "claude-haiku-4-5-20251001": 1.0,
            "claude-sonnet-4-5": 3.0,
            "claude-sonnet-4-5-20251001": 3.0,
            "claude-opus-4-5": 5.0,
            "claude-opus-4-5-20251101": 5.0,
        },
    },
    "design_doc_generation": {
        "base": 10,
        "model_multipliers": {},
    },
    "design_doc_export": {
        "base": 2,
        "model_multipliers": {},
    },
    "repo_analysis": {
        "base": 10,  # Higher cost due to multiple API calls + diagram generation
        "model_multipliers": {
            "claude-haiku-4-5": 1.0,
            "claude-haiku-4-5-20251001": 1.0,
            "claude-sonnet-4-5": 3.0,
            "claude-sonnet-4-5-20251001": 3.0,
            "claude-opus-4-5": 5.0,
            "claude-opus-4-5-20251101": 5.0,
        },
    },
}

# Plan configurations
PLAN_CREDITS = {
    "free": 25,
    "pro": 500,
    "enterprise": 2000,
}


def calculate_cost(action: str, model: Optional[str] = None) -> int:
    """
    Calculate credit cost for an action.

    Args:
        action: The action being performed (e.g., "diagram_generation")
        model: Optional model name for model-specific pricing

    Returns:
        Credit cost as an integer
    """
    cost_config = CREDIT_COSTS.get(action, {"base": 1, "model_multipliers": {}})
    base_cost = cost_config["base"]

    # Apply model multiplier if specified
    multiplier = 1.0
    if model:
        multiplier = cost_config.get("model_multipliers", {}).get(model, 1.0)

    return int(base_cost * multiplier)


def get_plan_credits(plan: str) -> int:
    """Get monthly credit allowance for a plan."""
    return PLAN_CREDITS.get(plan, PLAN_CREDITS["free"])
