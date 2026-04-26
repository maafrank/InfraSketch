"""Billing endpoints: subscriptions, credits, promo codes, and the Clerk billing webhook."""

import base64
import json
import logging
import time

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from fastapi.encoders import jsonable_encoder
from fastapi.responses import HTMLResponse, JSONResponse, Response
from pydantic import BaseModel
from typing import Optional

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from app.agent.doc_generator import generate_design_document, generate_design_document_preview
from app.agent.graph import agent_graph, generate_suggestions, process_diagram_groups
from app.agent.name_generator import generate_session_name
from app.api.deps import get_current_user, verify_session_access
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


class RedeemPromoRequest(BaseModel):
    """Request body for redeeming a promo code."""
    code: str


CLERK_PLAN_ID_MAP = {
    "cplan_3ASdFvizPo0JbVeethbsS7UfLjp": "starter",
    "cplan_37cOR2Mjs1jWOjaJfUGTX0U1Jf4": "pro",
    "cplan_37cOpDf5Cm7GGUl2K8lUarQf7Bp": "enterprise",
}


def _get_plan_from_clerk_id(plan_id: str) -> str:
    """Map Clerk plan ID to our plan name."""
    # First check exact match
    if plan_id in CLERK_PLAN_ID_MAP:
        return CLERK_PLAN_ID_MAP[plan_id]
    # Fall back to fuzzy match on plan key
    plan_id_lower = plan_id.lower()
    if "starter" in plan_id_lower:
        return "starter"
    elif "pro" in plan_id_lower:
        return "pro"
    elif "enterprise" in plan_id_lower:
        return "enterprise"
    return "free"


@router.post("/subscribe", response_model=SubscriptionStatus)
async def subscribe(request: SubscribeRequest, http_request: Request,
    user_id: str = Depends(get_current_user)
):
    """
    Subscribe a user to email notifications.
    Creates a new subscriber record if one doesn't exist.
    """
    
    try:
        storage = get_subscriber_storage()
        subscriber = storage.create_subscriber(user_id, request.email)

        log_event(
            EventType.API_REQUEST,
            user_ip=http_request.client.host if http_request.client else None,
            metadata={
                "endpoint": "/subscribe",
                "user_id": user_id,
                "email": request.email[:3] + "***",  # Partially redact email
            }
        )

        return SubscriptionStatus(subscribed=subscriber.subscribed, email=subscriber.email)

    except Exception as e:
        log_error(
            error_type="subscribe_failed",
            error_message=str(e),
            user_ip=http_request.client.host if http_request.client else None,
        )
        raise HTTPException(status_code=500, detail=f"Failed to subscribe: {str(e)}")


@router.get("/subscription/status", response_model=SubscriptionStatus)
async def get_subscription_status(http_request: Request,
    user_id: str = Depends(get_current_user)
):
    """
    Get the current user's subscription status.
    """
    
    try:
        storage = get_subscriber_storage()
        subscriber = storage.get_subscriber(user_id)

        if not subscriber:
            # User not subscribed yet - return default state
            return SubscriptionStatus(subscribed=False, email="")

        return SubscriptionStatus(subscribed=subscriber.subscribed, email=subscriber.email)

    except Exception as e:
        log_error(
            error_type="get_subscription_status_failed",
            error_message=str(e),
            user_ip=http_request.client.host if http_request.client else None,
        )
        raise HTTPException(status_code=500, detail=f"Failed to get subscription status: {str(e)}")


@router.post("/unsubscribe")
async def unsubscribe_authenticated(http_request: Request,
    user_id: str = Depends(get_current_user)
):
    """
    Unsubscribe the current authenticated user from emails.
    """
    
    try:
        storage = get_subscriber_storage()
        success = storage.unsubscribe(user_id)

        if not success:
            raise HTTPException(status_code=404, detail="Subscriber not found")

        log_event(
            EventType.API_REQUEST,
            user_ip=http_request.client.host if http_request.client else None,
            metadata={
                "endpoint": "/unsubscribe",
                "user_id": user_id,
            }
        )

        return {"success": True, "message": "You have been unsubscribed from email notifications."}

    except HTTPException:
        raise
    except Exception as e:
        log_error(
            error_type="unsubscribe_failed",
            error_message=str(e),
            user_ip=http_request.client.host if http_request.client else None,
        )
        raise HTTPException(status_code=500, detail=f"Failed to unsubscribe: {str(e)}")


@router.post("/resubscribe")
async def resubscribe_authenticated(http_request: Request,
    user_id: str = Depends(get_current_user)
):
    """
    Re-subscribe the current authenticated user to marketing emails.
    """
    
    try:
        storage = get_subscriber_storage()
        success = storage.resubscribe(user_id)

        if not success:
            raise HTTPException(status_code=404, detail="Subscriber not found")

        log_event(
            EventType.API_REQUEST,
            user_ip=http_request.client.host if http_request.client else None,
            metadata={
                "endpoint": "/resubscribe",
                "user_id": user_id,
            }
        )

        return {"success": True, "message": "You have been re-subscribed to email notifications."}

    except HTTPException:
        raise
    except Exception as e:
        log_error(
            error_type="resubscribe_failed",
            error_message=str(e),
            user_ip=http_request.client.host if http_request.client else None,
        )
        raise HTTPException(status_code=500, detail=f"Failed to re-subscribe: {str(e)}")


@router.get("/unsubscribe/{token}", response_class=HTMLResponse)
async def unsubscribe_via_token(token: str, http_request: Request):
    """
    Public endpoint for unsubscribe links in emails.
    No authentication required - the token IS the authentication.
    Returns a simple HTML confirmation page.
    """
    try:
        storage = get_subscriber_storage()
        subscriber = storage.get_subscriber_by_token(token)

        if not subscriber:
            return HTMLResponse(
                content="""
                <!DOCTYPE html>
                <html>
                <head>
                    <title>Unsubscribe - InfraSketch</title>
                    <style>
                        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                               max-width: 600px; margin: 50px auto; padding: 20px; text-align: center; }
                        h1 { color: #dc2626; }
                        p { color: #6b7280; }
                        a { color: #2563eb; }
                    </style>
                </head>
                <body>
                    <h1>Invalid Link</h1>
                    <p>This unsubscribe link is invalid or has expired.</p>
                    <p><a href="https://infrasketch.net">Return to InfraSketch</a></p>
                </body>
                </html>
                """,
                status_code=404
            )

        # Perform unsubscribe
        storage.unsubscribe(subscriber.user_id)

        log_event(
            EventType.API_REQUEST,
            user_ip=http_request.client.host if http_request.client else None,
            metadata={
                "endpoint": "/unsubscribe/{token}",
                "user_id": subscriber.user_id,
            }
        )

        # Build re-subscribe URL with the same token
        resubscribe_url = f"https://b31htlojb0.execute-api.us-east-1.amazonaws.com/prod/api/resubscribe/{token}"

        return HTMLResponse(
            content=f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>Unsubscribed - InfraSketch</title>
                <style>
                    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                           max-width: 600px; margin: 50px auto; padding: 20px; text-align: center; }}
                    h1 {{ color: #10b981; }}
                    p {{ color: #6b7280; }}
                    a {{ color: #2563eb; }}
                    .emoji {{ font-size: 48px; margin-bottom: 20px; }}
                    .resubscribe-btn {{
                        display: inline-block;
                        background-color: #2563eb;
                        color: white !important;
                        padding: 12px 24px;
                        border-radius: 6px;
                        text-decoration: none;
                        margin: 20px 0;
                        font-weight: 500;
                    }}
                    .resubscribe-btn:hover {{ background-color: #1d4ed8; }}
                </style>
            </head>
            <body>
                <div class="emoji">✅</div>
                <h1>You've Been Unsubscribed</h1>
                <p>You will no longer receive feature announcement emails from InfraSketch.</p>
                <p>Changed your mind?</p>
                <a href="{resubscribe_url}" class="resubscribe-btn">Re-subscribe</a>
                <p><a href="https://infrasketch.net">Return to InfraSketch</a></p>
            </body>
            </html>
            """,
            status_code=200
        )

    except Exception as e:
        log_error(
            error_type="unsubscribe_via_token_failed",
            error_message=str(e),
            user_ip=http_request.client.host if http_request.client else None,
        )
        return HTMLResponse(
            content="""
            <!DOCTYPE html>
            <html>
            <head>
                <title>Error - InfraSketch</title>
                <style>
                    body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                           max-width: 600px; margin: 50px auto; padding: 20px; text-align: center; }
                    h1 { color: #dc2626; }
                    p { color: #6b7280; }
                    a { color: #2563eb; }
                </style>
            </head>
            <body>
                <h1>Something Went Wrong</h1>
                <p>We couldn't process your unsubscribe request. Please try again later.</p>
                <p><a href="https://infrasketch.net">Return to InfraSketch</a></p>
            </body>
            </html>
            """,
            status_code=500
        )


@router.get("/resubscribe/{token}", response_class=HTMLResponse)
async def resubscribe_via_token(token: str, http_request: Request):
    """
    Public endpoint for re-subscribe links.
    No authentication required - the token IS the authentication.
    Returns a simple HTML confirmation page.
    """
    try:
        storage = get_subscriber_storage()
        subscriber = storage.get_subscriber_by_token(token)

        if not subscriber:
            return HTMLResponse(
                content="""
                <!DOCTYPE html>
                <html>
                <head>
                    <title>Re-subscribe - InfraSketch</title>
                    <style>
                        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                               max-width: 600px; margin: 50px auto; padding: 20px; text-align: center; }
                        h1 { color: #dc2626; }
                        p { color: #6b7280; }
                        a { color: #2563eb; }
                    </style>
                </head>
                <body>
                    <h1>Invalid Link</h1>
                    <p>This re-subscribe link is invalid or has expired.</p>
                    <p><a href="https://infrasketch.net">Return to InfraSketch</a></p>
                </body>
                </html>
                """,
                status_code=404
            )

        # Perform re-subscribe
        storage.resubscribe(subscriber.user_id)

        log_event(
            EventType.API_REQUEST,
            user_ip=http_request.client.host if http_request.client else None,
            metadata={
                "endpoint": "/resubscribe/{token}",
                "user_id": subscriber.user_id,
            }
        )

        # Build unsubscribe URL in case they want to undo
        unsubscribe_url = f"https://b31htlojb0.execute-api.us-east-1.amazonaws.com/prod/api/unsubscribe/{token}"

        return HTMLResponse(
            content=f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>Re-subscribed - InfraSketch</title>
                <style>
                    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                           max-width: 600px; margin: 50px auto; padding: 20px; text-align: center; }}
                    h1 {{ color: #10b981; }}
                    p {{ color: #6b7280; }}
                    a {{ color: #2563eb; }}
                    .emoji {{ font-size: 48px; margin-bottom: 20px; }}
                </style>
            </head>
            <body>
                <div class="emoji">🎉</div>
                <h1>You're Re-subscribed!</h1>
                <p>You'll now receive feature announcement emails from InfraSketch.</p>
                <p>Changed your mind? <a href="{unsubscribe_url}">Unsubscribe again</a></p>
                <p><a href="https://infrasketch.net">Return to InfraSketch</a></p>
            </body>
            </html>
            """,
            status_code=200
        )

    except Exception as e:
        log_error(
            error_type="resubscribe_via_token_failed",
            error_message=str(e),
            user_ip=http_request.client.host if http_request.client else None,
        )
        return HTMLResponse(
            content="""
            <!DOCTYPE html>
            <html>
            <head>
                <title>Error - InfraSketch</title>
                <style>
                    body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                           max-width: 600px; margin: 50px auto; padding: 20px; text-align: center; }
                    h1 { color: #dc2626; }
                    p { color: #6b7280; }
                    a { color: #2563eb; }
                </style>
            </head>
            <body>
                <h1>Something Went Wrong</h1>
                <p>We couldn't process your re-subscribe request. Please try again later.</p>
                <p><a href="https://infrasketch.net">Return to InfraSketch</a></p>
            </body>
            </html>
            """,
            status_code=500
        )


@router.get("/user/credits")
async def get_user_credits(http_request: Request,
    user_id: str = Depends(get_current_user)
):
    """
    Get current user's credit balance and subscription status.

    Returns:
        JSON with plan, credit balances, and subscription info
    """
    
    storage = get_user_credits_storage()
    credits = storage.get_or_create_credits(user_id)

    return {
        "plan": credits.plan,
        "credits_balance": credits.credits_balance,
        "credits_monthly_allowance": credits.credits_monthly_allowance,
        "credits_used_this_period": credits.credits_used_this_period,
        "subscription_status": credits.subscription_status,
        "plan_started_at": credits.plan_started_at.isoformat() if credits.plan_started_at else None,
        "plan_expires_at": credits.plan_expires_at.isoformat() if credits.plan_expires_at else None,
        "last_credit_reset_at": credits.last_credit_reset_at.isoformat() if credits.last_credit_reset_at else None,
    }


@router.get("/user/credits/history")
async def get_credit_history(http_request: Request, limit: int = 50,
    user_id: str = Depends(get_current_user)
):
    """
    Get user's credit transaction history.

    Args:
        limit: Maximum number of transactions to return (default 50)

    Returns:
        JSON with list of transactions
    """
    
    storage = get_user_credits_storage()
    transactions = storage.get_transaction_history(user_id, limit=limit)

    return {
        "transactions": [
            {
                "transaction_id": t.transaction_id,
                "type": t.type,
                "amount": t.amount,
                "balance_after": t.balance_after,
                "action": t.action,
                "session_id": t.session_id,
                "metadata": t.metadata,
                "created_at": t.created_at.isoformat(),
            }
            for t in transactions
        ]
    }


@router.post("/promo/redeem")
async def redeem_promo(request: RedeemPromoRequest, http_request: Request,
    user_id: str = Depends(get_current_user)
):
    """
    Redeem a promo code for credits.

    Args:
        request: Request body with promo code

    Returns:
        JSON with success status and credits granted
    """
    
    success, error, credits_granted = redeem_promo_code(request.code, user_id)

    if not success:
        raise HTTPException(status_code=400, detail=error)

    # Get updated balance
    storage = get_user_credits_storage()
    updated_credits = storage.get_credits(user_id)

    return {
        "success": True,
        "credits_granted": credits_granted,
        "new_balance": updated_credits.credits_balance if updated_credits else credits_granted,
        "message": f"Successfully redeemed {credits_granted} credits!",
    }


@router.post("/promo/validate")
async def validate_promo(request: RedeemPromoRequest, http_request: Request,
    user_id: str = Depends(get_current_user)
):
    """
    Validate a promo code without redeeming it.

    Args:
        request: Request body with promo code

    Returns:
        JSON with validity status and code info
    """
    
    is_valid, error = validate_promo_code(request.code, user_id)

    if not is_valid:
        return {
            "valid": False,
            "error": error,
        }

    # Get code info for display
    code_info = get_promo_code_info(request.code)

    return {
        "valid": True,
        "credits": code_info["credits"] if code_info else 0,
    }


@router.post("/webhooks/clerk-billing")
async def clerk_billing_webhook(http_request: Request):
    """
    Handle Clerk Billing webhook events for subscription changes.

    Events handled:
    - subscription.created/updated/active/pastDue: Handle subscription state
    - subscriptionItem.created/updated/active/canceled/ended: Handle plan changes
    - user.created: Initialize credits for new users

    Note: This endpoint is exempt from Clerk auth middleware (public webhook).
    """
    import os
    from svix.webhooks import Webhook, WebhookVerificationError

    try:
        # Get raw body for signature verification
        body = await http_request.body()
        headers = dict(http_request.headers)

        # Verify webhook signature (if secret is configured)
        webhook_secret = os.environ.get("CLERK_BILLING_WEBHOOK_SECRET")
        if webhook_secret:
            try:
                wh = Webhook(webhook_secret)
                payload = wh.verify(body, headers)
            except WebhookVerificationError:
                logger.exception("Clerk billing webhook signature verification failed")
                raise HTTPException(status_code=401, detail="Invalid webhook signature")
        else:
            # In development, parse without verification
            payload = json.loads(body)
            logger.info("WARNING: Clerk billing webhook signature not verified (no secret configured)")

        event_type = payload.get("type")
        data = payload.get("data", {})

        logger.info(f"\n=== CLERK BILLING WEBHOOK ===")
        logger.info(f"Event type: {event_type}")
        logger.info(f"Data: {json.dumps(data, indent=2)}")

        storage = get_user_credits_storage()

        # Helper to extract user_id from webhook data
        # Clerk puts user_id in different places depending on event type:
        # - subscription.* events: data.payer.user_id
        # - subscriptionItem.* events: data.payer.user_id
        # - user.* events: data.id
        def get_user_id_from_data(d: dict) -> str | None:
            # Try payer.user_id first (subscription and subscriptionItem events)
            payer = d.get("payer", {})
            if payer and payer.get("user_id"):
                return payer.get("user_id")
            # Fall back to direct user_id
            return d.get("user_id")

        # Handle user.created - initialize credits for new users
        if event_type == "user.created":
            user_id = data.get("id")
            if user_id:
                # This will create credits with free tier defaults if not exists
                storage.get_or_create_credits(user_id)
                logger.info(f"Initialized credits for new user {user_id}")

        # Handle subscription events
        elif event_type in ["subscription.created", "subscription.active"]:
            user_id = get_user_id_from_data(data)
            plan_id = data.get("plan_id", "")
            subscription_id = data.get("id")
            stripe_customer_id = data.get("stripe_customer_id")

            if user_id:
                plan = _get_plan_from_clerk_id(plan_id)
                storage.update_plan(
                    user_id=user_id,
                    new_plan=plan,
                    clerk_subscription_id=subscription_id,
                    stripe_customer_id=stripe_customer_id,
                )
                logger.info(f"Created/activated subscription for user {user_id}: {plan}")

        elif event_type == "subscription.updated":
            user_id = get_user_id_from_data(data)
            plan_id = data.get("plan_id", "")
            subscription_id = data.get("id")

            if user_id:
                plan = _get_plan_from_clerk_id(plan_id)
                storage.update_plan(
                    user_id=user_id,
                    new_plan=plan,
                    clerk_subscription_id=subscription_id,
                )
                logger.info(f"Updated subscription for user {user_id}: {plan}")

        elif event_type == "subscription.pastDue":
            user_id = get_user_id_from_data(data)
            if user_id:
                credits = storage.get_credits(user_id)
                if credits:
                    credits.subscription_status = "past_due"
                    storage.save_credits(credits)
                    logger.info(f"Marked subscription as past_due for user {user_id}")

        # Handle subscriptionItem events (for plan changes)
        elif event_type in ["subscriptionItem.created", "subscriptionItem.active", "subscriptionItem.updated"]:
            # subscriptionItem contains plan details
            user_id = get_user_id_from_data(data)
            plan_id = data.get("plan_id", "")
            subscription_id = data.get("subscription_id")

            if user_id and plan_id:
                plan = _get_plan_from_clerk_id(plan_id)
                storage.update_plan(
                    user_id=user_id,
                    new_plan=plan,
                    clerk_subscription_id=subscription_id,
                )
                logger.info(f"SubscriptionItem {event_type} for user {user_id}: {plan}")

        elif event_type in ["subscriptionItem.canceled", "subscriptionItem.ended"]:
            # User canceled or subscription ended - revert to free
            user_id = get_user_id_from_data(data)
            if user_id:
                storage.update_plan(
                    user_id=user_id,
                    new_plan="free",
                )
                logger.info(f"Subscription canceled/ended for user {user_id}, reverted to free")

        elif event_type == "subscriptionItem.upcoming":
            # Upcoming renewal - could use this to reset credits
            user_id = get_user_id_from_data(data)
            if user_id:
                storage.reset_monthly_credits(user_id)
                logger.info(f"Reset monthly credits for upcoming renewal: user {user_id}")

        # Log unhandled events for debugging
        else:
            logger.info(f"Unhandled Clerk billing event: {event_type}")

        return {"received": True}

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error processing Clerk billing webhook: {e}")
        raise HTTPException(status_code=500, detail=f"Webhook processing failed: {str(e)}")
