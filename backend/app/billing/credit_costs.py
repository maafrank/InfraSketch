"""
Credit cost configuration and calculation.
"""

from typing import Optional

from app.config.models import get_model_multiplier

# Credit costs by action
CREDIT_COSTS = {
    "diagram_generation": {"base": 5},
    "chat_message": {"base": 1},
    "design_doc_generation": {"base": 10},
    "design_doc_export": {"base": 2},
    "repo_analysis": {"base": 10},  # Higher cost due to multiple API calls + diagram generation
}

# Plan configurations
PLAN_CREDITS = {
    "free": 10,
    "starter": 50,
    "pro": 300,
    "enterprise": 2000,
}

# Plans that include design doc generation
DESIGN_DOC_PLANS = {"starter", "pro", "enterprise"}


def calculate_cost(action: str, model: Optional[str] = None) -> int:
    """
    Calculate credit cost for an action.

    Args:
        action: The action being performed (e.g., "diagram_generation")
        model: Optional model name for model-specific pricing

    Returns:
        Credit cost as an integer
    """
    cost_config = CREDIT_COSTS.get(action, {"base": 1})
    base_cost = cost_config["base"]

    # Apply model multiplier if specified
    multiplier = 1.0
    if model:
        multiplier = get_model_multiplier(model)

    return int(base_cost * multiplier)


def get_plan_credits(plan: str) -> int:
    """Get monthly credit allowance for a plan."""
    return PLAN_CREDITS.get(plan, PLAN_CREDITS["free"])
