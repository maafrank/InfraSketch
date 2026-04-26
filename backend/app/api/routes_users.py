"""User-scoped endpoints: sessions list, preferences, tutorials, gamification, and the Clerk auth webhook (provisions users)."""

import base64
import json
import logging
import time

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request
from fastapi.encoders import jsonable_encoder
from fastapi.responses import HTMLResponse, JSONResponse, Response
from pydantic import BaseModel
from typing import Optional

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from app.agent.doc_generator import generate_design_document, generate_design_document_preview
from app.agent.graph import agent_graph, generate_suggestions, process_diagram_groups
from app.agent.name_generator import generate_session_name
from app.api.deps import verify_session_access
from app.api._helpers import (
    check_and_deduct_credits,
    generate_system_overview,
    _should_generate_session_name,
    _generate_session_name_from_content,
)
from app.billing.credit_costs import DESIGN_DOC_PLANS, calculate_cost
from app.billing.promo_codes import get_promo_code_info, redeem_promo_code, validate_promo_code
from app.billing.storage import get_user_credits_storage
from app.config.models import DEFAULT_MODEL
from app.gamification.achievements import (
    ACHIEVEMENT_DEFINITIONS,
    ACHIEVEMENTS_BY_ID,
    get_achievement_progress,
)
from app.gamification.engine import process_action
from app.gamification.storage import get_gamification_storage
from app.gamification.streaks import check_streak_expired
from app.gamification.xp import get_level_progress
from app.github.analyzer import (
    GitHubAnalyzer,
    GitHubRateLimitError,
    RepoAccessDeniedError,
    RepoNotFoundError,
)
from app.github.prompts import format_repo_analysis_prompt
from app.models import (
    AnalyzeRepoRequest,
    AnalyzeRepoResponse,
    ChatRequest,
    ChatResponse,
    CreateGroupRequest,
    CreateGroupResponse,
    Diagram,
    Edge,
    GenerateRequest,
    GenerateResponse,
    Message,
    Node,
    NodeMetadata,
    NodePosition,
    SessionState,
)
from app.session.manager import session_manager
from app.subscription.models import SubscribeRequest, SubscriptionStatus
from app.subscription.storage import get_subscriber_storage
from app.user.models import UserPreferences
from app.user.storage import get_user_preferences_storage
from app.utils.badge_generator import get_monthly_visitors_badge_svg
from app.utils.diagram_export import convert_markdown_to_pdf, generate_diagram_png
from app.utils.logger import (
    EventType,
    log_chat_interaction,
    log_design_doc_generation,
    log_diagram_generation,
    log_error,
    log_event,
    log_export,
)
from app.utils.secrets import get_anthropic_api_key

logger = logging.getLogger(__name__)
router = APIRouter()


class UserPreferencesResponse(BaseModel):
    """Response model for user preferences."""

    user_id: str
    tutorial_completed: bool
    tutorial_completed_at: Optional[str] = None


class DismissNotificationsRequest(BaseModel):
    achievement_ids: list[str]


class StreakReminderPreferenceRequest(BaseModel):
    enabled: bool


@router.get("/user/sessions")
async def get_user_sessions(http_request: Request):
    """
    Get all sessions belonging to the authenticated user.

    Returns:
        List of sessions with metadata, sorted by most recent first
    """
    user_id = getattr(http_request.state, "user_id", None)
    if not user_id:
        raise HTTPException(status_code=401, detail="User authentication required")

    try:
        # Get all sessions for this user
        sessions = session_manager.get_user_sessions(user_id)

        # Format response with session previews
        sessions_data = []
        for session in sessions:
            sessions_data.append({
                "session_id": session.session_id,
                "created_at": session.created_at.isoformat() if session.created_at else None,
                "node_count": len(session.diagram.nodes),
                "edge_count": len(session.diagram.edges),
                "message_count": len(session.messages),
                "has_design_doc": session.design_doc is not None,
                "model": session.model,
                "name": session.name,
            })

        log_event(
            EventType.API_REQUEST,
            user_ip=http_request.client.host if http_request.client else None,
            metadata={
                "endpoint": "/user/sessions",
                "session_count": len(sessions_data)
            }
        )

        return JSONResponse(content={"sessions": sessions_data, "total": len(sessions_data)})

    except Exception as e:
        log_error(
            error_type="get_user_sessions_failed",
            error_message=str(e),
            user_ip=http_request.client.host if http_request.client else None,
        )
        raise HTTPException(status_code=500, detail=f"Failed to retrieve sessions: {str(e)}")


@router.post("/webhooks/clerk")
async def clerk_webhook(request: Request):
    """
    Handle Clerk webhook events.
    Automatically subscribes new users to email list on signup.

    Clerk webhooks use Svix for delivery and signature verification.
    The signing secret is used to verify that requests are authentic.
    """
    import os
    from svix.webhooks import Webhook, WebhookVerificationError

    # Get raw body (required for signature verification - must be exact bytes)
    payload = await request.body()
    headers = dict(request.headers)

    # Get webhook secret from environment
    webhook_secret = os.getenv("CLERK_WEBHOOK_SECRET")
    if not webhook_secret:
        log_error(
            error_type="webhook_config_error",
            error_message="CLERK_WEBHOOK_SECRET not configured",
        )
        raise HTTPException(status_code=500, detail="Webhook secret not configured")

    # Verify webhook signature using Svix
    try:
        wh = Webhook(webhook_secret)
        event = wh.verify(payload, headers)
    except WebhookVerificationError as e:
        log_error(
            error_type="webhook_verification_failed",
            error_message=str(e),
            user_ip=request.client.host if request.client else None,
        )
        raise HTTPException(status_code=400, detail="Invalid webhook signature")

    # Handle user.created event
    event_type = event.get("type")

    if event_type == "user.created":
        user_data = event.get("data", {})
        user_id = user_data.get("id")

        # Extract primary email address
        primary_email_id = user_data.get("primary_email_address_id")
        email = None
        for email_obj in user_data.get("email_addresses", []):
            if email_obj.get("id") == primary_email_id:
                email = email_obj.get("email_address")
                break

        # Fallback to first email if no primary designated
        if not email:
            email_addresses = user_data.get("email_addresses", [])
            if email_addresses:
                email = email_addresses[0].get("email_address")

        if user_id and email:
            try:
                storage = get_subscriber_storage()
                subscriber = storage.create_subscriber(user_id, email)

                log_event(
                    EventType.API_REQUEST,
                    user_ip=request.client.host if request.client else None,
                    metadata={
                        "endpoint": "/webhooks/clerk",
                        "event_type": "user.created",
                        "user_id": user_id,
                        "new_subscriber": subscriber.created_at == subscriber.updated_at,
                    }
                )
            except Exception as e:
                log_error(
                    error_type="webhook_subscriber_creation_failed",
                    error_message=str(e),
                    metadata={"user_id": user_id},
                )
                # Don't fail the webhook - Clerk would retry

    # Always return success to acknowledge receipt
    # (even if we didn't process the event type)
    return {"status": "received", "type": event_type}


@router.get("/user/preferences", response_model=UserPreferencesResponse)
async def get_user_preferences(http_request: Request):
    """
    Get the current user's preferences (tutorial status, etc.).

    Returns default preferences if none exist yet.
    """
    user_id = getattr(http_request.state, "user_id", None)
    if not user_id:
        raise HTTPException(status_code=401, detail="User authentication required")

    storage = get_user_preferences_storage()
    prefs = storage.get_or_create_preferences(user_id)

    return UserPreferencesResponse(
        user_id=prefs.user_id,
        tutorial_completed=prefs.tutorial_completed,
        tutorial_completed_at=(
            prefs.tutorial_completed_at.isoformat() if prefs.tutorial_completed_at else None
        ),
    )


@router.post("/user/tutorial/complete")
async def complete_tutorial(http_request: Request):
    """
    Mark the tutorial as completed for the current user.
    """
    user_id = getattr(http_request.state, "user_id", None)
    if not user_id:
        raise HTTPException(status_code=401, detail="User authentication required")

    storage = get_user_preferences_storage()
    success = storage.mark_tutorial_completed(user_id)

    if not success:
        raise HTTPException(status_code=500, detail="Failed to save tutorial completion")

    return {"success": True, "message": "Tutorial marked as completed"}


@router.post("/user/tutorial/reset")
async def reset_tutorial(http_request: Request):
    """
    Reset the tutorial status so the user can replay it.
    """
    user_id = getattr(http_request.state, "user_id", None)
    if not user_id:
        raise HTTPException(status_code=401, detail="User authentication required")

    storage = get_user_preferences_storage()
    success = storage.reset_tutorial(user_id)

    if not success:
        raise HTTPException(status_code=500, detail="Failed to reset tutorial status")

    return {"success": True, "message": "Tutorial reset successfully"}


@router.get("/user/gamification")
async def get_user_gamification(http_request: Request):
    """Get the user's gamification state (level, XP, streak, pending notifications)."""
    user_id = getattr(http_request.state, "user_id", None)
    if not user_id:
        raise HTTPException(status_code=401, detail="User authentication required")

    storage = get_gamification_storage()
    gamification = storage.get_or_create(user_id)

    # Reset streak if user has been inactive too long
    if check_streak_expired(gamification):
        storage.save(gamification)

    level_info = get_level_progress(gamification.xp_total)

    # Build pending notification details
    pending = []
    for notif in gamification.pending_notifications:
        defn = ACHIEVEMENTS_BY_ID.get(notif.id, {})
        pending.append({
            "id": notif.id,
            "unlocked_at": notif.unlocked_at.isoformat(),
            "name": defn.get("name", notif.id),
            "description": defn.get("description", ""),
            "rarity": defn.get("rarity", "common"),
        })

    return {
        "xp_total": gamification.xp_total,
        "xp_to_next_level": level_info["xp_to_next_level"],
        "xp_current_level_start": level_info["xp_current_level_start"],
        "xp_next_level_threshold": level_info["xp_next_level_threshold"],
        "level": gamification.level,
        "level_name": gamification.level_name,
        "level_color": level_info["level_color"],
        "current_streak": gamification.current_streak,
        "longest_streak": gamification.longest_streak,
        "achievement_count": len(gamification.achievements),
        "total_achievements": len(ACHIEVEMENT_DEFINITIONS),
        "pending_notifications": pending,
        "streak_reminders_enabled": gamification.streak_reminders_enabled,
    }


@router.get("/user/gamification/achievements")
async def get_user_achievements(http_request: Request):
    """Get all achievement definitions with unlock status and progress."""
    user_id = getattr(http_request.state, "user_id", None)
    if not user_id:
        raise HTTPException(status_code=401, detail="User authentication required")

    storage = get_gamification_storage()
    gamification = storage.get_or_create(user_id)

    achievements = get_achievement_progress(gamification)

    # Compute stats by category
    by_category = {}
    for a in achievements:
        cat = a["category"]
        if cat not in by_category:
            by_category[cat] = {"unlocked": 0, "total": 0}
        by_category[cat]["total"] += 1
        if a["unlocked"]:
            by_category[cat]["unlocked"] += 1

    unlocked_count = sum(1 for a in achievements if a["unlocked"])

    return {
        "achievements": achievements,
        "stats": {
            "unlocked": unlocked_count,
            "total": len(achievements),
            "by_category": by_category,
        },
    }


@router.post("/user/gamification/notifications/dismiss")
async def dismiss_gamification_notifications(
    request: DismissNotificationsRequest, http_request: Request
):
    """Clear pending notifications after the user has seen them."""
    user_id = getattr(http_request.state, "user_id", None)
    if not user_id:
        raise HTTPException(status_code=401, detail="User authentication required")

    storage = get_gamification_storage()
    gamification = storage.get_or_create(user_id)

    ids_to_dismiss = set(request.achievement_ids)
    gamification.pending_notifications = [
        n for n in gamification.pending_notifications if n.id not in ids_to_dismiss
    ]
    storage.save(gamification)

    return {"success": True}


@router.patch("/user/gamification/streak-reminders")
async def update_streak_reminder_preference(
    request: StreakReminderPreferenceRequest, http_request: Request
):
    """Update whether the user receives streak reminder emails."""
    user_id = getattr(http_request.state, "user_id", None)
    if not user_id:
        raise HTTPException(status_code=401, detail="User authentication required")

    storage = get_gamification_storage()
    gamification = storage.get_or_create(user_id)
    gamification.streak_reminders_enabled = request.enabled
    storage.save(gamification)

    return {"success": True, "streak_reminders_enabled": request.enabled}
