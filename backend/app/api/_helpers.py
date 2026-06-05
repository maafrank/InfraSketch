"""Cross-file helpers shared by the routes_*.py modules.

These were extracted from routes.py when it was split by domain so each
split file could remain self-contained. Importable from any routes_*.py.
"""

import logging

from fastapi import HTTPException

from app.agent.name_generator import generate_session_name
from app.billing.credit_costs import calculate_cost
from app.billing.storage import get_user_credits_storage
from app.billing.sync import sync_user_from_clerk
from app.models import Diagram
from app.session.manager import session_manager
from app.utils.secrets import get_anthropic_api_key

logger = logging.getLogger(__name__)


async def check_and_deduct_credits(
    user_id: str,
    action: str,
    model: str = None,
    session_id: str = None,
    metadata: dict = None,
) -> int:
    """
    Check if user has sufficient credits and deduct if so.

    Args:
        user_id: The authenticated user's ID
        action: The action being performed (e.g., "diagram_generation")
        model: Optional model name for model-specific pricing
        session_id: Optional session ID for audit trail
        metadata: Optional additional metadata for logging

    Returns:
        The number of credits deducted

    Raises:
        HTTPException 402 if insufficient credits
    """
    # Ensure stored plan reflects current Clerk state BEFORE charging. A paid
    # user whose webhook was missed would otherwise be billed (or blocked) on
    # the wrong plan tier. gate_check=True tightens the paid throttle to 1h
    # so a missed `ended` webhook can't grant >1h of free service. Non-active
    # stored status bypasses the throttle entirely inside sync. Fail-open if
    # Clerk is down.
    synced = sync_user_from_clerk(user_id, gate_check=True)

    # Failed recurring payment stops service. Stored credits at the time of
    # failure don't matter - the user hasn't paid for the current period.
    # Frontend can prompt "update payment" using the subscription_status
    # surfaced in /user/credits.
    if synced.subscription_status == "past_due":
        raise HTTPException(
            status_code=402,
            detail={
                "error": "subscription_past_due",
                "message": "Your payment failed. Update your payment method to resume service.",
            },
        )

    # Fail closed on locally-known expired entitlement. plan_expires_at is
    # set on cancellation; if Clerk sync is failing (transient outage) we
    # still must NOT keep serving a user whose grace period ended.
    from datetime import datetime
    if (synced.plan != "free"
        and synced.plan_expires_at
        and synced.plan_expires_at < datetime.utcnow()):
        raise HTTPException(
            status_code=402,
            detail={
                "error": "subscription_expired",
                "message": "Your subscription has ended. Resubscribe to resume service.",
            },
        )

    cost = calculate_cost(action, model)
    storage = get_user_credits_storage()

    success, credits = storage.deduct_credits(
        user_id=user_id,
        amount=cost,
        action=action,
        session_id=session_id,
        metadata=metadata or {},
    )

    if not success:
        raise HTTPException(
            status_code=402,
            detail={
                "error": "insufficient_credits",
                "required": cost,
                "available": credits.credits_balance,
                "message": "You don't have enough credits. Please upgrade your plan or purchase more credits.",
            },
        )

    return cost


def generate_system_overview(diagram: Diagram) -> str:
    """
    Generate a formatted system overview message from a diagram.
    This is what the user sees in chat after diagram generation.

    Args:
        diagram: The generated diagram

    Returns:
        Formatted markdown system overview message
    """
    node_count = len(diagram.nodes)
    node_types = sorted(set(node.type for node in diagram.nodes))

    overview = f"""## System Overview
I've generated a system architecture with {node_count} components.

**Component Types**
{chr(10).join(f"- {node_type}" for node_type in node_types)}

**What's Next?**
- Click any node to focus the conversation on that component
- Ask questions about the overall system design
- Request changes to add, remove, or modify components

Feel free to explore the diagram and ask me anything!"""

    return overview


def _should_generate_session_name(session) -> bool:
    """Check if session needs a name generated."""
    # Skip if already generated
    if session.name_generated:
        return False

    # Skip if name is set to something other than None or "Untitled Design"
    if session.name and session.name != "Untitled Design":
        return False

    return True


def _generate_session_name_from_content(session_id: str, model: str):
    """
    Background task to generate session name from session content.
    Uses first message or node descriptions if no messages exist.
    """
    import os

    try:
        session = session_manager.get_session(session_id)
        if not session:
            logger.info(f"Session {session_id} not found for name generation")
            return

        # Skip if already generated
        if not _should_generate_session_name(session):
            logger.info(f"Session {session_id} already has a name: {session.name}")
            return

        logger.info(f"\n=== BACKGROUND: GENERATE SESSION NAME ===")
        logger.info(f"Session ID: {session_id}")

        # Build prompt from session content
        # Priority: 1) First user message, 2) Node descriptions
        prompt = None

        if session.messages:
            # Find first user message
            for msg in session.messages:
                if msg.role == "user":
                    prompt = msg.content
                    logger.info(f"Using first user message: {prompt[:100]}...")
                    break

        if not prompt and session.diagram and session.diagram.nodes:
            # Use node descriptions/labels
            node_descriptions = [f"{node.label}: {node.description}" for node in session.diagram.nodes[:5]]
            prompt = "System with: " + ", ".join(node_descriptions)
            logger.info(f"Using node descriptions: {prompt[:100]}...")

        if not prompt:
            logger.info("No content available for name generation, skipping")
            return

        # Get API key from environment or secrets
        api_key = get_anthropic_api_key()

        # Generate name using LLM (synchronous - no asyncio.run needed)
        name = generate_session_name(prompt, api_key, model)

        # Update session using proper method
        session_manager.update_session_name(session_id, name)

        logger.info(f"Generated name: {name}")
        logger.info(f"=========================================\n")

    except Exception as e:
        logger.exception(f"Error generating session name: {e}")
        # Set fallback name so we don't retry
        try:
            session_manager.update_session_name(session_id, "Untitled Design")
        except:
            pass
