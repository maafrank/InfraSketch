"""
Self-healing plan sync between Clerk and DynamoDB.

Called from:
- GET /user/credits route, on every call (throttled by tier).
- POST /admin/user/{id}/sync-plan endpoint (force=True).
- scripts/sync_user_plan.py CLI (force=True).

Decision matrix:

  Clerk state                                              | Action
  ---------------------------------------------------------|----------------------------
  not_found (404) AND stored plan paid                     | Downgrade to free
  not_found AND stored plan free                           | No-op
  has_active_item, plan matches stored, no canceled_at     | No-op (force may refresh meta)
  has_active_item, plan matches stored, canceled_at set    | Mark canceled, keep plan
  has_active_item, plan differs from stored                | update_plan
  No active item, status in {ended, expired}               | Downgrade to free
  No active item, status="canceled", period_end in past    | Downgrade to free
  No active item, status="canceled", period_end in future  | Mark canceled, keep plan
  No active item, any other status                         | No-op, log (ambiguous)

Failure handling:
- Non-forced: fail open. Return stored credits, bump throttle, log warning.
  The user-facing /user/credits endpoint must never 500 because Clerk is down.
- Forced: re-raise. Support relies on a clear failure signal; silent success
  would make a misconfigured account look already-correct.

Per-tier throttle:
- Free users: 5 minutes between Clerk hits.
- Paid users: 24 hours between Clerk hits. This is the safety net for a
  missed `ended` webhook. The window matches typical billing reconciliation
  cadence; a dedicated cron is a future enhancement.
"""

import logging
from datetime import datetime, timedelta

from app.billing.clerk_client import ClerkSubscription, get_clerk_client
from app.billing.models import UserCredits
from app.billing.storage import get_user_credits_storage
from app.utils.logger import EventType, log_event

logger = logging.getLogger(__name__)


FREE_SYNC_INTERVAL_SECONDS = 300            # 5 min - background polls
PAID_SYNC_INTERVAL_SECONDS = 86400          # 24 h  - background reconciliation
# Fallback grace period when Clerk reports canceled but omits period_end.
# Bounds "canceled but no ended webhook ever arrived" indefinite paid access.
DEFAULT_CANCELED_GRACE_SECONDS = 30 * 86400


def _period_end_passed(period_end) -> bool:
    return period_end is not None and period_end < datetime.utcnow()


def _log_heal(user_id: str, old_plan: str, new_plan: str, sub: ClerkSubscription, reason: str) -> None:
    logger.info(
        "Self-healing user %s plan %s -> %s (reason=%s, clerk plan_id=%s, status=%s)",
        user_id, old_plan, new_plan, reason, sub.plan_id, sub.status,
    )
    log_event(
        EventType.PLAN_SELF_HEAL,
        metadata={
            "user_id": user_id,
            "old_plan": old_plan,
            "new_plan": new_plan,
            "reason": reason,
            "clerk_plan_id": sub.plan_id,
            "clerk_subscription_id": sub.subscription_id,
            "clerk_status": sub.status,
        },
    )


def sync_user_from_clerk(user_id: str, force: bool = False, gate_check: bool = False) -> UserCredits:
    """
    Args:
        user_id: Clerk user_id.
        force: Bypass app throttle, bypass plan-only-free guard, re-raise on
            failure. Use for admin/CLI repair flows.
        gate_check: Caller is a service entitlement gate (charge, paid-plan
            check, auto-sync). Bypasses the app throttle entirely so a stale
            stored plan can't grant or deny service. The ClerkClient's 60s
            in-memory cache absorbs bursts - a tight loop of gate calls
            within 60s hits Clerk once. Background paths (/user/credits
            poll, periodic reconciliation) leave gate_check=False and use
            the app throttle.

    The app throttle is also bypassed for paid users with non-active stored
    status (past_due, canceled, trialing). Those are the exact states where
    a missed recovery webhook causes user-facing pain.
    """
    storage = get_user_credits_storage()
    credits = storage.get_or_create_credits(user_id)

    # App-throttle bypass conditions:
    #   - force=True (admin/CLI repair)
    #   - gate_check=True (service decisions need fresh state; cache is the
    #     backstop, not the app throttle)
    #   - First-ever sync (no last_clerk_sync_at)
    #   - Paid user with non-active stored status (past_due/canceled/trialing)
    paid_user_in_problem_state = (
        credits.plan != "free" and credits.subscription_status != "active"
    )
    if (not force
        and not gate_check
        and credits.last_clerk_sync_at
        and not paid_user_in_problem_state):
        interval = FREE_SYNC_INTERVAL_SECONDS if credits.plan == "free" else PAID_SYNC_INTERVAL_SECONDS
        elapsed = (datetime.utcnow() - credits.last_clerk_sync_at).total_seconds()
        if elapsed < interval:
            return credits

    # Fail-open scope covers BOTH the Clerk fetch and state application. A
    # bug or unexpected data in _apply_clerk_state (timestamp comparison,
    # storage write failure, anything else) must never 500 the user-facing
    # /user/credits or block service in _user_is_paid. force=True re-raises
    # so support sees the error.
    try:
        sub = get_clerk_client().get_user_subscription(user_id)
        _apply_clerk_state(storage, credits, sub, user_id, force)
    except Exception as e:
        logger.warning("Clerk sync failed for %s: %s", user_id, e, exc_info=True)
        if force:
            raise
        storage.touch_clerk_sync_timestamp(user_id)
        credits.last_clerk_sync_at = datetime.utcnow()
        return credits

    # Bump throttle atomically. Don't rewrite the whole row.
    storage.touch_clerk_sync_timestamp(user_id)
    # Re-fetch in case an update_plan / mark_pending_cancellation changed
    # other fields. Falls back to the in-memory credits if the read fails.
    fresh = storage.get_credits(user_id)
    if fresh is None:
        credits.last_clerk_sync_at = datetime.utcnow()
        return credits
    return fresh


def _apply_clerk_state(storage, credits: UserCredits, sub: ClerkSubscription, user_id: str, force: bool) -> None:
    # 1. 404: subscription record gone. Downgrade if stored is paid.
    if sub.not_found:
        if credits.plan != "free":
            _log_heal(user_id, credits.plan, "free", sub, reason="clerk_not_found")
            storage.update_plan(user_id=user_id, new_plan="free")
        return

    clerk_status = (sub.status or "").lower()

    # 2. PAST_DUE takes precedence over plan reconciliation. Payment is
    # failing right now. We never apply a plan upgrade and never overwrite
    # status with "active" while Clerk says past_due. Just mark stored
    # past_due so service gates block. Plan stays whatever it was - if a
    # plan change is needed too, it'll be applied once payment recovers
    # (Clerk will report active+new_plan and the next sync will update_plan).
    if clerk_status == "past_due":
        if credits.subscription_status != "past_due":
            logger.info(
                "Marking user %s subscription as past_due from sync "
                "(Clerk status=past_due, has_active_item=%s)",
                user_id, sub.has_active_item,
            )
            storage.set_subscription_status(user_id, "past_due")
        return

    # 3. Active item: user IS entitled to a paid plan right now.
    if sub.has_active_item:
        if sub.plan != credits.plan:
            _log_heal(user_id, credits.plan, sub.plan, sub, reason="plan_changed")
            storage.update_plan(
                user_id=user_id,
                new_plan=sub.plan,
                clerk_subscription_id=sub.subscription_id,
                stripe_customer_id=sub.stripe_customer_id,
            )
            return

        # Plan matches stored.
        if sub.canceled_at:
            # Repair status OR missing plan_expires_at. Same bug class as the
            # no-active-item canceled branch: if a prior webhook wrote None
            # for plan_expires_at, we'd never re-apply the grace and the
            # user would stay canceled with no expiry forever.
            if credits.subscription_status != "canceled" or credits.plan_expires_at is None:
                fallback_expiry = sub.period_end or credits.plan_expires_at or (
                    datetime.utcnow() + timedelta(seconds=DEFAULT_CANCELED_GRACE_SECONDS)
                )
                logger.info(
                    "Marking user %s subscription as canceled-pending-expiry "
                    "(clerk_period_end=%s, applied=%s)",
                    user_id, sub.period_end, fallback_expiry,
                )
                storage.mark_pending_cancellation(
                    user_id=user_id,
                    expires_at=fallback_expiry,
                    clerk_subscription_id=sub.subscription_id,
                )
            return

        # Active, plan matches, not canceled, not past_due. Reconcile any
        # non-active stored status back to active (recovery from past_due,
        # canceled, etc).
        if credits.subscription_status != "active":
            logger.info(
                "Reconciling stored subscription_status %s -> active for user %s "
                "(Clerk active item, plan matches)",
                credits.subscription_status, user_id,
            )
            storage.set_subscription_status(user_id, "active")

        if force and credits.plan != "free":
            target_stripe = sub.stripe_customer_id or credits.stripe_customer_id
            if (credits.clerk_subscription_id != sub.subscription_id
                or (sub.stripe_customer_id and credits.stripe_customer_id != sub.stripe_customer_id)):
                logger.info(
                    "Refreshing stale Clerk metadata for user %s (csub: %s -> %s)",
                    user_id, credits.clerk_subscription_id, sub.subscription_id,
                )
                storage.set_clerk_metadata(
                    user_id=user_id,
                    clerk_subscription_id=sub.subscription_id,
                    stripe_customer_id=target_stripe,
                    subscription_status="active",
                )
        return

    # 4. No active item, not past_due. Already free? Nothing to do.
    if credits.plan == "free":
        return

    # 5. Stored is paid; decide whether to downgrade based on AUTHORITATIVE
    # Clerk state. Anything ambiguous -> leave plan alone.
    if clerk_status in {"ended", "expired"}:
        _log_heal(user_id, credits.plan, "free", sub, reason=f"status_{clerk_status}")
        storage.update_plan(user_id=user_id, new_plan="free")
    elif clerk_status == "canceled":
        # Determine an effective expiry. Prefer Clerk's period_end. If absent,
        # fall back to any stored plan_expires_at (set by an earlier webhook).
        # If neither is available, apply a conservative default grace so the
        # canceled state has a bounded life - otherwise a missed ended-webhook
        # plus a missing period_end would leave paid service active forever.
        effective_expiry = sub.period_end or credits.plan_expires_at
        if _period_end_passed(effective_expiry):
            _log_heal(user_id, credits.plan, "free", sub, reason="canceled_period_passed")
            storage.update_plan(user_id=user_id, new_plan="free")
        elif credits.subscription_status != "canceled" or credits.plan_expires_at is None:
            # Repair either of the two bad states:
            #   - status is wrong (e.g. still "active"), OR
            #   - status is canceled but expiry is missing (a prior webhook
            #     wrote None - without re-applying the grace, this user would
            #     stay canceled-with-no-expiry forever and gates would never
            #     fail closed via plan_expires_at.
            fallback_expiry = effective_expiry or (
                datetime.utcnow() + timedelta(seconds=DEFAULT_CANCELED_GRACE_SECONDS)
            )
            logger.info(
                "Marking user %s subscription as canceled-pending-expiry from sync "
                "(clerk_period_end=%s, stored_expires_at=%s, applied=%s)",
                user_id, sub.period_end, credits.plan_expires_at, fallback_expiry,
            )
            storage.mark_pending_cancellation(
                user_id=user_id,
                expires_at=fallback_expiry,
                clerk_subscription_id=sub.subscription_id,
            )
    else:
        logger.warning(
            "Ambiguous Clerk state for user %s: no active item, status=%r; leaving plan=%s unchanged",
            user_id, clerk_status, credits.plan,
        )
