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
from app.billing.clerk_client import invalidate_clerk_cache_for_user, parse_clerk_timestamp
from app.billing.credit_costs import DESIGN_DOC_PLANS, calculate_cost
from app.billing.plans import (
    CLERK_PLAN_ID_MAP,
    UnknownClerkPlanError,
    extract_plan_id_from_item,
    get_plan_from_clerk_id,
)
from app.billing.promo_codes import get_promo_code_info, redeem_promo_code, validate_promo_code
from app.billing.storage import get_user_credits_storage
from app.billing.sync import DEFAULT_CANCELED_GRACE_SECONDS, sync_user_from_clerk
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


def _load_admin_user_ids() -> set[str]:
    import os
    raw = os.environ.get("ADMIN_USER_IDS", "")
    return {uid.strip() for uid in raw.split(",") if uid.strip()}


def require_admin(user_id: str = Depends(get_current_user)) -> str:
    if user_id not in _load_admin_user_ids():
        raise HTTPException(status_code=403, detail="admin only")
    return user_id


class RedeemPromoRequest(BaseModel):
    """Request body for redeeming a promo code."""
    code: str


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

    credits = sync_user_from_clerk(user_id)

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


@router.post("/admin/user/{target_user_id}/sync-plan")
async def admin_sync_user_plan(
    target_user_id: str,
    _: str = Depends(require_admin),
):
    """
    Force a Clerk -> DynamoDB plan sync for any user. Used by support to
    repair accounts where the billing webhook missed or stored the wrong plan.

    Surfaces Clerk failures as 502 so support sees a clear error rather than
    a misleading "already correct" 200.
    """
    try:
        credits = sync_user_from_clerk(target_user_id, force=True)
    except Exception as e:
        logger.exception("admin sync-plan failed for %s", target_user_id)
        raise HTTPException(
            status_code=502,
            detail=f"Clerk sync failed for {target_user_id}: {e}",
        )
    return {
        "user_id": target_user_id,
        "plan": credits.plan,
        "subscription_status": credits.subscription_status,
        "clerk_subscription_id": credits.clerk_subscription_id,
        "credits_balance": credits.credits_balance,
        "credits_monthly_allowance": credits.credits_monthly_allowance,
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

    success, error, credits_granted, design_docs_granted = redeem_promo_code(
        request.code, user_id
    )

    if not success:
        raise HTTPException(status_code=400, detail=error)

    # Get updated balance
    storage = get_user_credits_storage()
    updated_credits = storage.get_credits(user_id)

    if design_docs_granted > 0 and credits_granted > 0:
        message = (
            f"Successfully redeemed {credits_granted} credits and "
            f"{design_docs_granted} free design doc!"
        )
    elif design_docs_granted > 0:
        plural = "s" if design_docs_granted != 1 else ""
        message = (
            f"Code applied — you've unlocked {design_docs_granted} free "
            f"design doc{plural}. Click Generate to use it."
        )
    else:
        message = f"Successfully redeemed {credits_granted} credits!"

    return {
        "success": True,
        "credits_granted": credits_granted,
        "design_docs_granted": design_docs_granted,
        "new_balance": updated_credits.credits_balance if updated_credits else credits_granted,
        "free_design_docs_remaining": (
            updated_credits.free_design_docs_remaining if updated_credits else design_docs_granted
        ),
        "message": message,
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
        "design_docs_granted": code_info.get("grants_design_doc", 0) if code_info else 0,
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
            # Allow unsigned only when explicitly running unauthenticated locally.
            # In production, refuse rather than silently trusting unsigned traffic.
            if os.environ.get("DISABLE_CLERK_AUTH", "false").lower() != "true":
                logger.error("Clerk billing webhook rejected: CLERK_BILLING_WEBHOOK_SECRET not configured")
                raise HTTPException(status_code=500, detail="Webhook secret not configured")
            payload = json.loads(body)
            logger.warning("Clerk billing webhook signature not verified (DISABLE_CLERK_AUTH=true)")

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
        def get_user_id_from_data(d: dict) -> Optional[str]:
            payer = d.get("payer", {})
            if payer and payer.get("user_id"):
                return payer.get("user_id")
            return d.get("user_id")

        def _first_period_end(items: list) -> Optional[int]:
            """Return the period_end timestamp from the first dict item that has one."""
            for item in items or []:
                if isinstance(item, dict) and item.get("period_end"):
                    return item.get("period_end")
            return None

        def _expiry_with_grace_fallback(raw_period_end):
            """Parse a Clerk period_end timestamp, falling back to (now + grace)
            when missing. Bounds canceled subscriptions that never receive an
            ended webhook so service stops eventually."""
            from datetime import datetime as _dt, timedelta as _td
            parsed = parse_clerk_timestamp(raw_period_end)
            if parsed is not None:
                return parsed
            return _dt.utcnow() + _td(seconds=DEFAULT_CANCELED_GRACE_SECONDS)

        def extract_subscription_plan_id(d: dict) -> str:
            """
            Pull a plan identifier from a subscription.* event payload. Clerk's
            current shape nests the plan inside data.subscription_items[]; the
            top-level data.plan_id is typically empty for subscription.* events.
            This was the root cause of plan="free" being stored for an active
            starter subscriber.

            For each item we check plan_id, then nested plan.id, then nested
            plan.slug (same chain the Clerk API client uses for self-healing),
            so a payload variant that only exposes slug doesn't silently fail
            with missing_plan_id. Falls back to top-level data.plan_id last.
            """
            items = d.get("subscription_items") or []
            for item in items:
                if not isinstance(item, dict):
                    continue
                if item.get("status") and item.get("status") != "active":
                    continue
                pid = extract_plan_id_from_item(item)
                if pid:
                    return pid
            return d.get("plan_id", "") or ""

        webhook_user_id = get_user_id_from_data(data)
        log_event(
            EventType.CLERK_BILLING_WEBHOOK,
            metadata={"event_type": event_type, "user_id": webhook_user_id},
        )
        # Drop the per-process Clerk cache for this user BEFORE handling the
        # mutation. Any subsequent same-container service gate that fires
        # before the cache TTL would otherwise read the pre-mutation snapshot
        # (e.g. cached active sub from before this cancellation, or just-paid
        # user whose previous read was cached as 404 - though 404s are no
        # longer cached, this also catches active->canceled stale reads).
        # Cross-container staleness is bounded by the 60s cache TTL.
        invalidate_clerk_cache_for_user(webhook_user_id)

        # Handle user.created - initialize credits for new users
        if event_type == "user.created":
            user_id = data.get("id")
            if user_id:
                storage.get_or_create_credits(user_id)
                logger.info(f"Initialized credits for new user {user_id}")

        # Handle subscription events. For create/activate/update, an empty
        # plan_id after extraction (e.g. Clerk schema change, malformed
        # subscription_items) must NOT silently flow through to update_plan
        # with new_plan="" / "free" - that would mark a paying account as
        # canceled. Return 500 so Clerk retries and surfaces the bad payload.
        elif event_type in ["subscription.created", "subscription.active"]:
            user_id = get_user_id_from_data(data)
            plan_id = extract_subscription_plan_id(data)
            subscription_id = data.get("id")
            stripe_customer_id = data.get("stripe_customer_id")

            if not user_id:
                logger.warning(f"{event_type}: missing user_id in payload: {json.dumps(data)[:500]}")
            elif not plan_id:
                logger.error(f"{event_type}: empty plan_id after extraction for user {user_id}; payload: {json.dumps(data)[:500]}")
                return JSONResponse(status_code=500, content={"error": "missing_plan_id", "event_type": event_type})
            else:
                try:
                    plan = get_plan_from_clerk_id(plan_id, raise_on_unknown=True)
                except UnknownClerkPlanError:
                    logger.error(f"{event_type}: unknown plan_id {plan_id!r} for user {user_id}; returning 500 so Clerk retries")
                    return JSONResponse(status_code=500, content={"error": "unknown_plan_id", "plan_id": plan_id})
                storage.update_plan(
                    user_id=user_id,
                    new_plan=plan,
                    clerk_subscription_id=subscription_id,
                    stripe_customer_id=stripe_customer_id,
                )
                logger.info(f"Created/activated subscription for user {user_id}: {plan}")

        elif event_type == "subscription.updated":
            user_id = get_user_id_from_data(data)
            plan_id = extract_subscription_plan_id(data)
            subscription_id = data.get("id")
            sub_status = (data.get("status") or "").lower()
            sub_items = data.get("subscription_items") or []
            has_active_item = any(
                isinstance(it, dict) and (it.get("status") or "").lower() == "active"
                for it in sub_items
            )
            # canceled = user opted out, grace period until period_end -> keep plan
            # ended/expired = entitlement is over -> downgrade now
            all_items_canceled = bool(sub_items) and all(
                isinstance(it, dict) and (it.get("status") or "").lower() == "canceled"
                for it in sub_items
            )
            any_item_ended_or_expired = any(
                isinstance(it, dict)
                and (it.get("status") or "").lower() in {"ended", "expired"}
                for it in sub_items
            )

            if not user_id:
                logger.warning(f"{event_type}: missing user_id in payload: {json.dumps(data)[:500]}")
            elif sub_status in {"ended", "expired"} or (any_item_ended_or_expired and not has_active_item):
                # Hard end: entitlement is over (top-level OR an item shows
                # ended/expired with no compensating active item). Downgrade now.
                logger.info(
                    f"{event_type}: ended signal for user {user_id} "
                    f"(status={sub_status!r}, any_item_ended={any_item_ended_or_expired}); reverting to free"
                )
                storage.update_plan(user_id=user_id, new_plan="free")
            elif sub_status == "past_due":
                # Failed payment. Don't downgrade plan (retries may succeed)
                # but mark past_due so service gates block. Must come BEFORE
                # the canceled-by-items branch: items can be inactive during
                # past_due retries, which would otherwise mis-route to canceled.
                logger.info(
                    f"{event_type}: status=past_due for user {user_id}; marking past_due, keeping plan"
                )
                storage.set_subscription_status(user_id, "past_due")
            elif sub_status == "canceled" or all_items_canceled:
                # User opted out (top-level status) OR every item is explicitly
                # canceled. Retain features until period_end - mark canceled,
                # KEEP plan. A later subscription.ended / subscriptionItem.ended
                # event will downgrade to free at the actual expiry. If Clerk
                # omits period_end, fall back to a bounded grace so the
                # canceled state can't persist indefinitely.
                period_end = _expiry_with_grace_fallback(
                    _first_period_end(sub_items) or data.get("period_end")
                )
                logger.info(
                    f"{event_type}: canceled signal for user {user_id} "
                    f"(status={sub_status!r}, period_end={period_end}); keeping plan, marking canceled"
                )
                storage.mark_pending_cancellation(
                    user_id=user_id,
                    expires_at=period_end,
                    clerk_subscription_id=subscription_id,
                )
            elif not plan_id:
                logger.error(f"{event_type}: empty plan_id after extraction for user {user_id}; payload: {json.dumps(data)[:500]}")
                return JSONResponse(status_code=500, content={"error": "missing_plan_id", "event_type": event_type})
            else:
                try:
                    plan = get_plan_from_clerk_id(plan_id, raise_on_unknown=True)
                except UnknownClerkPlanError:
                    logger.error(f"{event_type}: unknown plan_id {plan_id!r} for user {user_id}; returning 500 so Clerk retries")
                    return JSONResponse(status_code=500, content={"error": "unknown_plan_id", "plan_id": plan_id})
                storage.update_plan(
                    user_id=user_id,
                    new_plan=plan,
                    clerk_subscription_id=subscription_id,
                )
                logger.info(f"Updated subscription for user {user_id}: {plan}")

        elif event_type in ["subscription.pastDue", "subscriptionItem.pastDue"]:
            # Payment failed but service is not blocked here. Surfaced via
            # /user/credits.subscription_status for the frontend to show a
            # "update payment" banner. Whether past_due should hard-block
            # paid features is a separate product decision.
            user_id = get_user_id_from_data(data)
            if user_id:
                storage.set_subscription_status(user_id, "past_due")
                logger.info(f"Marked subscription as past_due for user {user_id} ({event_type})")

        elif event_type in ["subscription.ended", "subscription.expired"]:
            # Authoritative entitlement end at the subscription level.
            user_id = get_user_id_from_data(data)
            if not user_id:
                logger.warning(f"{event_type}: missing user_id in payload: {json.dumps(data)[:500]}")
            else:
                storage.update_plan(user_id=user_id, new_plan="free")
                logger.info(f"{event_type}: reverted user {user_id} to free")

        # Handle subscriptionItem events (for plan changes). data here IS the
        # subscription_item (not a wrapper), so extract_plan_id_from_item is
        # the right helper - it handles plan_id / plan.id / plan.slug.
        #
        # subscriptionItem.updated can arrive with status=canceled/ended even
        # when the plan_id is still populated. Treating those as upgrade
        # signals would re-enable service for a non-active item. Route them
        # to the cancel/end handlers based on data.status.
        elif event_type in ["subscriptionItem.created", "subscriptionItem.active", "subscriptionItem.updated"]:
            user_id = get_user_id_from_data(data)
            plan_id = extract_plan_id_from_item(data)
            subscription_id = data.get("subscription_id")
            item_status = (data.get("status") or "").lower()

            if not user_id:
                logger.warning(f"{event_type}: missing user_id in payload: {json.dumps(data)[:500]}")
            elif item_status in {"ended", "expired"}:
                logger.info(
                    f"{event_type}: status={item_status!r} for user {user_id}; reverting to free"
                )
                storage.update_plan(user_id=user_id, new_plan="free")
            elif item_status == "canceled":
                # Use the grace fallback so a missing period_end gets bounded
                # to now+30d instead of writing None (which would leave the
                # user in canceled state with no expiry, gates passing forever).
                period_end = _expiry_with_grace_fallback(data.get("period_end"))
                logger.info(
                    f"{event_type}: canceled signal for user {user_id} "
                    f"(period_end={period_end}); keeping plan, marking canceled"
                )
                storage.mark_pending_cancellation(
                    user_id=user_id,
                    expires_at=period_end,
                    clerk_subscription_id=subscription_id,
                )
            elif item_status == "past_due":
                # Payment failed on this item. Mark stored past_due and do
                # NOT update_plan - applying a plan change while payment is
                # failing would re-enable service.
                logger.info(
                    f"{event_type}: status=past_due for user {user_id}; marking past_due, keeping plan"
                )
                storage.set_subscription_status(user_id, "past_due")
            elif not plan_id:
                logger.warning(f"{event_type}: missing plan_id for user {user_id}; ignoring")
            else:
                # Item is active (or status missing - treat as active per the
                # created/active naming). Apply the plan.
                try:
                    plan = get_plan_from_clerk_id(plan_id, raise_on_unknown=True)
                except UnknownClerkPlanError:
                    logger.error(f"{event_type}: unknown plan_id {plan_id!r} for user {user_id}; returning 500 so Clerk retries")
                    return JSONResponse(status_code=500, content={"error": "unknown_plan_id", "plan_id": plan_id})
                storage.update_plan(
                    user_id=user_id,
                    new_plan=plan,
                    clerk_subscription_id=subscription_id,
                )
                logger.info(f"SubscriptionItem {event_type} for user {user_id}: {plan}")

        elif event_type == "subscriptionItem.canceled":
            # User opted out of renewal. Per Clerk billing semantics they
            # retain entitlement until period_end - mark canceled, keep plan.
            # subscriptionItem.ended (or sync) will flip to free at expiry.
            # Fall back to a bounded grace if Clerk omits period_end so the
            # canceled state can't persist forever without an ended webhook.
            user_id = get_user_id_from_data(data)
            if not user_id:
                logger.warning(f"{event_type}: missing user_id in payload: {json.dumps(data)[:500]}")
            else:
                period_end = _expiry_with_grace_fallback(data.get("period_end"))
                logger.info(
                    f"{event_type}: canceled signal for user {user_id} "
                    f"(period_end={period_end}); keeping plan, marking canceled"
                )
                storage.mark_pending_cancellation(
                    user_id=user_id,
                    expires_at=period_end,
                    clerk_subscription_id=data.get("subscription_id"),
                )

        elif event_type == "subscriptionItem.ended":
            # Authoritative end of entitlement at the item level.
            user_id = get_user_id_from_data(data)
            if not user_id:
                logger.warning(f"{event_type}: missing user_id in payload: {json.dumps(data)[:500]}")
            else:
                storage.update_plan(user_id=user_id, new_plan="free")
                logger.info(f"{event_type}: reverted user {user_id} to free")

        elif event_type == "subscriptionItem.upcoming":
            user_id = get_user_id_from_data(data)
            if user_id:
                storage.reset_monthly_credits(user_id)
                logger.info(f"Reset monthly credits for upcoming renewal: user {user_id}")

        else:
            logger.info(f"Unhandled Clerk billing event: {event_type}")

        return {"received": True}

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error processing Clerk billing webhook: {e}")
        raise HTTPException(status_code=500, detail=f"Webhook processing failed: {str(e)}")
