"""Tests for backend/app/billing/sync.py - decision matrix and throttle behavior."""

from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

from app.billing.clerk_client import ClerkAPIError, ClerkSubscription
from app.billing.models import UserCredits
from app.billing.plans import UnknownClerkPlanError
from app.billing import sync as sync_module


def _make_credits(
    plan: str = "free",
    last_sync: datetime | None = None,
    subscription_status: str = "none",
    clerk_subscription_id: str | None = None,
    stripe_customer_id: str | None = None,
) -> UserCredits:
    return UserCredits(
        user_id="user_test",
        plan=plan,
        credits_balance=10,
        credits_monthly_allowance=10,
        last_clerk_sync_at=last_sync,
        subscription_status=subscription_status,
        clerk_subscription_id=clerk_subscription_id,
        stripe_customer_id=stripe_customer_id,
    )


def _active_sub(plan: str = "starter", subscription_id: str = "csub_x",
                stripe_customer_id: str | None = "cus_x", canceled_at: datetime | None = None,
                period_end: datetime | None = None) -> ClerkSubscription:
    return ClerkSubscription(
        plan=plan,
        subscription_id=subscription_id,
        plan_id="cplan_3ASdFvizPo0JbVeethbsS7UfLjp" if plan == "starter" else f"cplan_{plan}",
        status="active",
        stripe_customer_id=stripe_customer_id,
        has_active_item=True,
        period_end=period_end,
        canceled_at=canceled_at,
    )


def _no_active_sub(status: str = "canceled", period_end: datetime | None = None,
                   canceled_at: datetime | None = None, not_found: bool = False) -> ClerkSubscription:
    return ClerkSubscription(
        plan="free",
        subscription_id=None if not_found else "csub_inactive",
        plan_id=None,
        status=None if not_found else status,
        has_active_item=False,
        not_found=not_found,
        period_end=period_end,
        canceled_at=canceled_at,
    )


@pytest.fixture
def mock_storage():
    storage = MagicMock()
    storage.get_or_create_credits.return_value = _make_credits()
    # update_plan returns a UserCredits reflecting the new plan
    storage.update_plan.side_effect = lambda user_id, new_plan, **kwargs: _make_credits(plan=new_plan)
    # get_credits used at end of sync to return the freshest row
    storage.get_credits.side_effect = lambda user_id: storage.get_or_create_credits.return_value
    return storage


@pytest.fixture
def patched(mock_storage):
    with patch.object(sync_module, "get_user_credits_storage", return_value=mock_storage), \
         patch.object(sync_module, "get_clerk_client") as mock_get_client:
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        yield mock_storage, mock_client


# ---------------------------------------------------------------------------
# Throttle
# ---------------------------------------------------------------------------

class TestThrottle:
    def test_free_user_throttled_within_5_min(self, patched):
        storage, clerk = patched
        storage.get_or_create_credits.return_value = _make_credits(
            plan="free", last_sync=datetime.utcnow() - timedelta(minutes=2),
        )
        sync_module.sync_user_from_clerk("user_test")
        clerk.get_user_subscription.assert_not_called()

    def test_free_user_synced_after_5_min(self, patched):
        storage, clerk = patched
        storage.get_or_create_credits.return_value = _make_credits(
            plan="free", last_sync=datetime.utcnow() - timedelta(minutes=10),
        )
        clerk.get_user_subscription.return_value = _no_active_sub()
        sync_module.sync_user_from_clerk("user_test")
        clerk.get_user_subscription.assert_called_once()

    def test_paid_active_user_throttled_within_24_hours(self, patched):
        # Must explicitly set status=active - a non-active paid user bypasses
        # throttle so the recovery path heals immediately.
        storage, clerk = patched
        storage.get_or_create_credits.return_value = _make_credits(
            plan="starter", subscription_status="active",
            last_sync=datetime.utcnow() - timedelta(hours=12),
        )
        sync_module.sync_user_from_clerk("user_test")
        clerk.get_user_subscription.assert_not_called()

    def test_paid_user_synced_after_24_hours(self, patched):
        # This is the safety net for a missed `ended` webhook.
        storage, clerk = patched
        storage.get_or_create_credits.return_value = _make_credits(
            plan="starter", subscription_status="active",
            last_sync=datetime.utcnow() - timedelta(hours=25),
        )
        clerk.get_user_subscription.return_value = _active_sub(plan="starter")
        sync_module.sync_user_from_clerk("user_test")
        clerk.get_user_subscription.assert_called_once()

    def test_paid_user_past_due_bypasses_throttle(self, patched):
        # CRITICAL regression: a past_due user who has paid must heal
        # immediately on the next gate check, not wait up to 24h.
        storage, clerk = patched
        storage.get_or_create_credits.return_value = _make_credits(
            plan="starter", subscription_status="past_due",
            last_sync=datetime.utcnow() - timedelta(minutes=1),  # just synced
        )
        clerk.get_user_subscription.return_value = _active_sub(plan="starter")
        sync_module.sync_user_from_clerk("user_test")
        clerk.get_user_subscription.assert_called_once()

    def test_paid_user_canceled_bypasses_throttle(self, patched):
        # Canceled state needs to see ended-event visibility quickly.
        storage, clerk = patched
        storage.get_or_create_credits.return_value = _make_credits(
            plan="starter", subscription_status="canceled",
            last_sync=datetime.utcnow() - timedelta(minutes=1),
        )
        clerk.get_user_subscription.return_value = _no_active_sub(
            status="canceled", period_end=datetime.utcnow() + timedelta(days=10),
        )
        sync_module.sync_user_from_clerk("user_test")
        clerk.get_user_subscription.assert_called_once()

    def test_free_user_status_none_still_throttled(self, patched):
        # Free users default to subscription_status="none". That must NOT
        # be treated as a "problem state" - otherwise the 5min throttle
        # would never apply and free users would hit Clerk on every request.
        storage, clerk = patched
        storage.get_or_create_credits.return_value = _make_credits(
            plan="free", subscription_status="none",
            last_sync=datetime.utcnow() - timedelta(minutes=2),
        )
        sync_module.sync_user_from_clerk("user_test")
        clerk.get_user_subscription.assert_not_called()

    def test_paid_active_non_gate_keeps_24h_throttle(self, patched):
        # /user/credits poll path (gate_check=False) keeps the 24h throttle.
        # A 90-min-old sync is still within 24h.
        storage, clerk = patched
        storage.get_or_create_credits.return_value = _make_credits(
            plan="starter", subscription_status="active",
            last_sync=datetime.utcnow() - timedelta(minutes=90),
        )
        sync_module.sync_user_from_clerk("user_test", gate_check=False)
        clerk.get_user_subscription.assert_not_called()

    def test_gate_check_bypasses_free_user_throttle(self, patched):
        # Regression: a recently-synced free user who paid mid-window would
        # be stuck on free for up to 5 min on service gates. gate_check=True
        # must hit Clerk despite the recent sync timestamp.
        storage, clerk = patched
        storage.get_or_create_credits.return_value = _make_credits(
            plan="free", subscription_status="none",
            last_sync=datetime.utcnow() - timedelta(seconds=30),
        )
        clerk.get_user_subscription.return_value = _active_sub(plan="starter")
        sync_module.sync_user_from_clerk("user_test", gate_check=True)
        clerk.get_user_subscription.assert_called_once()

    def test_gate_check_bypasses_paid_active_throttle(self, patched):
        # Same principle for paid active users - gates need fresh state.
        # The 60s ClerkClient cache (not app throttle) absorbs bursts.
        storage, clerk = patched
        storage.get_or_create_credits.return_value = _make_credits(
            plan="starter", subscription_status="active",
            last_sync=datetime.utcnow() - timedelta(seconds=10),
        )
        clerk.get_user_subscription.return_value = _active_sub(plan="starter")
        sync_module.sync_user_from_clerk("user_test", gate_check=True)
        clerk.get_user_subscription.assert_called_once()

    def test_force_bypasses_throttle(self, patched):
        storage, clerk = patched
        storage.get_or_create_credits.return_value = _make_credits(
            plan="free", last_sync=datetime.utcnow() - timedelta(seconds=10),
        )
        clerk.get_user_subscription.return_value = _active_sub(plan="starter")
        sync_module.sync_user_from_clerk("user_test", force=True)
        clerk.get_user_subscription.assert_called_once()


# ---------------------------------------------------------------------------
# Active-item paths
# ---------------------------------------------------------------------------

class TestActiveItem:
    def test_stored_free_clerk_starter_upgrades(self, patched):
        storage, clerk = patched
        storage.get_or_create_credits.return_value = _make_credits(plan="free")
        clerk.get_user_subscription.return_value = _active_sub(plan="starter", subscription_id="csub_1")
        sync_module.sync_user_from_clerk("user_test")
        storage.update_plan.assert_called_once()
        assert storage.update_plan.call_args.kwargs["new_plan"] == "starter"
        assert storage.update_plan.call_args.kwargs["clerk_subscription_id"] == "csub_1"

    def test_active_with_canceled_at_marks_pending(self, patched):
        # User canceled mid-period. Clerk still says active for now, but
        # canceled_at is set. We keep the plan and mark subscription_status.
        storage, clerk = patched
        storage.get_or_create_credits.return_value = _make_credits(
            plan="starter", subscription_status="active",
        )
        period_end = datetime.utcnow() + timedelta(days=20)
        clerk.get_user_subscription.return_value = _active_sub(
            plan="starter", subscription_id="csub_x",
            canceled_at=datetime.utcnow() - timedelta(days=1),
            period_end=period_end,
        )
        sync_module.sync_user_from_clerk("user_test")
        storage.update_plan.assert_not_called()
        storage.mark_pending_cancellation.assert_called_once()
        kwargs = storage.mark_pending_cancellation.call_args.kwargs
        assert kwargs["expires_at"] == period_end

    def test_active_with_canceled_at_noop_when_already_canceled(self, patched):
        # Idempotent: don't write again if subscription_status is already
        # canceled AND plan_expires_at is set (complete state, nothing to fix).
        storage, clerk = patched
        stored = _make_credits(plan="starter", subscription_status="canceled")
        stored.plan_expires_at = datetime.utcnow() + timedelta(days=20)
        storage.get_or_create_credits.return_value = stored
        clerk.get_user_subscription.return_value = _active_sub(
            plan="starter",
            canceled_at=datetime.utcnow() - timedelta(days=1),
            period_end=datetime.utcnow() + timedelta(days=20),
        )
        sync_module.sync_user_from_clerk("user_test")
        storage.mark_pending_cancellation.assert_not_called()

    def test_force_refreshes_stale_subscription_id_on_matching_plan(self, patched):
        storage, clerk = patched
        storage.get_or_create_credits.return_value = _make_credits(
            plan="starter", subscription_status="active", clerk_subscription_id="csub_OLD",
        )
        clerk.get_user_subscription.return_value = _active_sub(
            plan="starter", subscription_id="csub_NEW", stripe_customer_id="cus_x",
        )
        sync_module.sync_user_from_clerk("user_test", force=True)
        storage.update_plan.assert_not_called()
        storage.set_clerk_metadata.assert_called_once()
        assert storage.set_clerk_metadata.call_args.kwargs["clerk_subscription_id"] == "csub_NEW"


# ---------------------------------------------------------------------------
# No-active-item paths (cancellation / ended semantics)
# ---------------------------------------------------------------------------

class TestNoActiveItem:
    def test_stored_free_clerk_free_no_action(self, patched):
        storage, clerk = patched
        storage.get_or_create_credits.return_value = _make_credits(plan="free")
        clerk.get_user_subscription.return_value = _no_active_sub(status=None)
        sync_module.sync_user_from_clerk("user_test")
        storage.update_plan.assert_not_called()
        storage.mark_pending_cancellation.assert_not_called()

    def test_status_ended_downgrades(self, patched):
        storage, clerk = patched
        storage.get_or_create_credits.return_value = _make_credits(plan="starter")
        clerk.get_user_subscription.return_value = _no_active_sub(status="ended")
        sync_module.sync_user_from_clerk("user_test")
        storage.update_plan.assert_called_once()
        assert storage.update_plan.call_args.kwargs["new_plan"] == "free"

    def test_status_expired_downgrades(self, patched):
        storage, clerk = patched
        storage.get_or_create_credits.return_value = _make_credits(plan="starter")
        clerk.get_user_subscription.return_value = _no_active_sub(status="expired")
        sync_module.sync_user_from_clerk("user_test")
        storage.update_plan.assert_called_once()

    def test_canceled_with_period_end_in_past_downgrades(self, patched):
        storage, clerk = patched
        storage.get_or_create_credits.return_value = _make_credits(plan="starter")
        clerk.get_user_subscription.return_value = _no_active_sub(
            status="canceled", period_end=datetime.utcnow() - timedelta(days=1),
        )
        sync_module.sync_user_from_clerk("user_test")
        storage.update_plan.assert_called_once()
        assert storage.update_plan.call_args.kwargs["new_plan"] == "free"

    def test_canceled_with_period_end_in_future_keeps_plan(self, patched):
        # Grace period: user is still entitled. Mark canceled, don't downgrade.
        storage, clerk = patched
        storage.get_or_create_credits.return_value = _make_credits(
            plan="starter", subscription_status="active",
        )
        clerk.get_user_subscription.return_value = _no_active_sub(
            status="canceled", period_end=datetime.utcnow() + timedelta(days=20),
        )
        sync_module.sync_user_from_clerk("user_test")
        storage.update_plan.assert_not_called()
        storage.mark_pending_cancellation.assert_called_once()

    def test_canceled_with_unknown_period_end_applies_default_grace(self, patched):
        # Regression: previously this just marked canceled with no expiry,
        # leaving paid access active forever if the ended webhook never
        # arrived. Now: fall back to (now + DEFAULT_CANCELED_GRACE_SECONDS)
        # so the canceled state is bounded.
        storage, clerk = patched
        storage.get_or_create_credits.return_value = _make_credits(
            plan="starter", subscription_status="active",
        )
        clerk.get_user_subscription.return_value = _no_active_sub(
            status="canceled", period_end=None,
        )
        sync_module.sync_user_from_clerk("user_test")
        storage.update_plan.assert_not_called()
        storage.mark_pending_cancellation.assert_called_once()
        kwargs = storage.mark_pending_cancellation.call_args.kwargs
        # Effective expiry must be set, not None.
        assert kwargs["expires_at"] is not None
        # And it must be roughly now + grace, not in the past.
        assert kwargs["expires_at"] > datetime.utcnow()

    def test_canceled_repairs_missing_expiry_even_when_status_already_canceled(self, patched):
        # Regression: a prior subscriptionItem.updated webhook with no
        # period_end could leave stored as canceled + plan_expires_at=None.
        # Sync would skip applying grace because status was already canceled,
        # leaving the user in canceled-with-no-expiry forever (gates pass).
        storage, clerk = patched
        stored = _make_credits(plan="starter", subscription_status="canceled")
        stored.plan_expires_at = None  # explicit
        storage.get_or_create_credits.return_value = stored
        clerk.get_user_subscription.return_value = _no_active_sub(
            status="canceled", period_end=None,
        )
        sync_module.sync_user_from_clerk("user_test")
        storage.mark_pending_cancellation.assert_called_once()
        kwargs = storage.mark_pending_cancellation.call_args.kwargs
        assert kwargs["expires_at"] is not None
        assert kwargs["expires_at"] > datetime.utcnow()

    def test_active_item_canceled_at_repairs_missing_expiry(self, patched):
        # Same bug class on the active-item canceled_at branch.
        storage, clerk = patched
        stored = _make_credits(plan="starter", subscription_status="canceled")
        stored.plan_expires_at = None
        storage.get_or_create_credits.return_value = stored
        sub = _active_sub(
            plan="starter",
            canceled_at=datetime.utcnow() - timedelta(days=1),
            period_end=None,
        )
        clerk.get_user_subscription.return_value = sub
        sync_module.sync_user_from_clerk("user_test")
        storage.mark_pending_cancellation.assert_called_once()
        kwargs = storage.mark_pending_cancellation.call_args.kwargs
        assert kwargs["expires_at"] is not None

    def test_canceled_uses_stored_plan_expires_at_when_clerk_missing(self, patched):
        # Defense in depth: if Clerk omits period_end but a prior webhook set
        # plan_expires_at, respect that. If it's already past, downgrade.
        storage, clerk = patched
        past_expiry = datetime.utcnow() - timedelta(days=1)
        stored = _make_credits(plan="starter", subscription_status="canceled")
        stored.plan_expires_at = past_expiry
        storage.get_or_create_credits.return_value = stored
        clerk.get_user_subscription.return_value = _no_active_sub(
            status="canceled", period_end=None,
        )
        sync_module.sync_user_from_clerk("user_test")
        storage.update_plan.assert_called_once()
        assert storage.update_plan.call_args.kwargs["new_plan"] == "free"

    def test_404_not_found_downgrades_paid_user(self, patched):
        # Subscription was hard-deleted in Clerk - authoritative.
        storage, clerk = patched
        storage.get_or_create_credits.return_value = _make_credits(plan="starter")
        clerk.get_user_subscription.return_value = _no_active_sub(not_found=True)
        sync_module.sync_user_from_clerk("user_test")
        storage.update_plan.assert_called_once()
        assert storage.update_plan.call_args.kwargs["new_plan"] == "free"

    def test_404_not_found_noop_for_free_user(self, patched):
        storage, clerk = patched
        storage.get_or_create_credits.return_value = _make_credits(plan="free")
        clerk.get_user_subscription.return_value = _no_active_sub(not_found=True)
        sync_module.sync_user_from_clerk("user_test")
        storage.update_plan.assert_not_called()

    def test_ambiguous_status_leaves_plan_alone(self, patched, caplog):
        # paused / pending / unknown status -> fail safe, keep paid plan.
        storage, clerk = patched
        storage.get_or_create_credits.return_value = _make_credits(plan="starter")
        clerk.get_user_subscription.return_value = _no_active_sub(status="paused")
        sync_module.sync_user_from_clerk("user_test")
        storage.update_plan.assert_not_called()
        storage.mark_pending_cancellation.assert_not_called()


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------

class TestStatusReconciliation:
    """Non-force sync reconciles subscription_status in BOTH directions:
    past_due -> active when Clerk reports recovery, and active -> past_due
    when Clerk reports payment failure (catches missed webhooks)."""

    def test_stored_past_due_clerk_active_matching_plan_flips_to_active(self, patched):
        # Regression: a stale past_due (recovery webhook missed) would block
        # service forever because non-force sync was a no-op on matching plan.
        storage, clerk = patched
        storage.get_or_create_credits.return_value = _make_credits(
            plan="starter", subscription_status="past_due",
        )
        clerk.get_user_subscription.return_value = _active_sub(plan="starter")
        sync_module.sync_user_from_clerk("user_test")  # NON-force
        storage.set_subscription_status.assert_called_with("user_test", "active")

    def test_stored_canceled_clerk_active_matching_plan_flips_to_active(self, patched):
        # Resubscribe-after-cancel: user canceled, then resubscribed. Clerk
        # active again. Stored status was canceled -> flip to active.
        storage, clerk = patched
        storage.get_or_create_credits.return_value = _make_credits(
            plan="starter", subscription_status="canceled",
        )
        clerk.get_user_subscription.return_value = _active_sub(plan="starter")
        sync_module.sync_user_from_clerk("user_test")
        storage.set_subscription_status.assert_called_with("user_test", "active")

    def test_stored_active_clerk_active_no_write(self, patched):
        # Idempotent: already-active stored status produces no write.
        storage, clerk = patched
        storage.get_or_create_credits.return_value = _make_credits(
            plan="starter", subscription_status="active",
        )
        clerk.get_user_subscription.return_value = _active_sub(plan="starter")
        sync_module.sync_user_from_clerk("user_test")
        storage.set_subscription_status.assert_not_called()

    def test_stored_active_clerk_past_due_with_active_item_marks_past_due(self, patched):
        # Catches missed pastDue webhook during grace-period retries: Clerk
        # reports active item (still entitled) but top-level status=past_due.
        storage, clerk = patched
        storage.get_or_create_credits.return_value = _make_credits(
            plan="starter", subscription_status="active",
        )
        sub = _active_sub(plan="starter")
        sub.status = "past_due"  # Clerk's top-level status
        clerk.get_user_subscription.return_value = sub
        sync_module.sync_user_from_clerk("user_test")
        storage.set_subscription_status.assert_called_with("user_test", "past_due")

    def test_past_due_blocks_plan_upgrade(self, patched):
        # Regression: previously update_plan() returned early before
        # past_due reconciliation, so a payload of (Clerk plan=starter,
        # status=past_due, stored plan=free) wrote status="active" via
        # update_plan and re-enabled service.
        storage, clerk = patched
        storage.get_or_create_credits.return_value = _make_credits(
            plan="free", subscription_status="none",
        )
        sub = _active_sub(plan="starter")
        sub.status = "past_due"
        clerk.get_user_subscription.return_value = sub
        sync_module.sync_user_from_clerk("user_test")
        # MUST NOT upgrade plan or set active.
        storage.update_plan.assert_not_called()
        storage.set_subscription_status.assert_called_with("user_test", "past_due")

    def test_past_due_blocks_plan_change_for_paid_user(self, patched):
        # Same trap, paid-to-paid plan change while payment fails.
        storage, clerk = patched
        storage.get_or_create_credits.return_value = _make_credits(
            plan="starter", subscription_status="active",
        )
        sub = _active_sub(plan="pro")
        sub.status = "past_due"
        clerk.get_user_subscription.return_value = sub
        sync_module.sync_user_from_clerk("user_test")
        # Don't apply the pro upgrade while payment is failing.
        storage.update_plan.assert_not_called()
        storage.set_subscription_status.assert_called_with("user_test", "past_due")

    def test_stored_active_clerk_past_due_no_active_item_marks_past_due(self, patched):
        # Catches missed pastDue webhook where retries exhausted item: no
        # active item, Clerk status=past_due. We DON'T downgrade plan yet
        # (recovery possible), just mark past_due.
        storage, clerk = patched
        storage.get_or_create_credits.return_value = _make_credits(
            plan="starter", subscription_status="active",
        )
        clerk.get_user_subscription.return_value = _no_active_sub(status="past_due")
        sync_module.sync_user_from_clerk("user_test")
        storage.update_plan.assert_not_called()  # don't downgrade
        storage.set_subscription_status.assert_called_with("user_test", "past_due")


class TestFailureModes:
    def test_clerk_api_error_does_not_raise_on_non_force(self, patched):
        storage, clerk = patched
        clerk.get_user_subscription.side_effect = ClerkAPIError("boom")
        result = sync_module.sync_user_from_clerk("user_test")
        assert result.plan == "free"
        storage.update_plan.assert_not_called()
        storage.touch_clerk_sync_timestamp.assert_called_with("user_test")
        storage.save_credits.assert_not_called()

    def test_force_reraises_clerk_api_error(self, mock_storage):
        with patch.object(sync_module, "get_user_credits_storage", return_value=mock_storage), \
             patch.object(sync_module, "get_clerk_client") as mock_get_client:
            mock_get_client.return_value.get_user_subscription.side_effect = ClerkAPIError("401")
            with pytest.raises(ClerkAPIError):
                sync_module.sync_user_from_clerk("user_test", force=True)
        mock_storage.update_plan.assert_not_called()

    def test_force_reraises_missing_clerk_secret(self, mock_storage):
        with patch.object(sync_module, "get_user_credits_storage", return_value=mock_storage), \
             patch.object(sync_module, "get_clerk_client",
                          side_effect=ValueError("Could not retrieve secret")):
            with pytest.raises(ValueError, match="Could not retrieve secret"):
                sync_module.sync_user_from_clerk("user_test", force=True)

    def test_force_reraises_unknown_plan_for_active_subscription(self, mock_storage):
        with patch.object(sync_module, "get_user_credits_storage", return_value=mock_storage), \
             patch.object(sync_module, "get_clerk_client") as mock_get_client:
            mock_get_client.return_value.get_user_subscription.side_effect = UnknownClerkPlanError("cplan_new")
            with pytest.raises(UnknownClerkPlanError):
                sync_module.sync_user_from_clerk("user_test", force=True)
        mock_storage.update_plan.assert_not_called()

    def test_iso_period_end_does_not_crash_non_force(self, patched):
        # Regression: parse_clerk_timestamp used to return tz-aware datetimes
        # for ISO strings, which crashed _period_end_passed and either 500'd
        # /user/credits or made _user_is_paid treat the user as free.
        from app.billing.clerk_client import parse_clerk_timestamp
        storage, clerk = patched
        storage.get_or_create_credits.return_value = _make_credits(plan="starter")
        clerk.get_user_subscription.return_value = _no_active_sub(
            status="canceled",
            period_end=parse_clerk_timestamp("2026-05-04T12:00:00Z"),
        )
        # Must not raise. Period is in past => downgrade.
        result = sync_module.sync_user_from_clerk("user_test")
        assert result is not None
        storage.update_plan.assert_called_once()
        assert storage.update_plan.call_args.kwargs["new_plan"] == "free"

    def test_iso_period_end_in_future_keeps_plan_non_force(self, patched):
        from app.billing.clerk_client import parse_clerk_timestamp
        storage, clerk = patched
        storage.get_or_create_credits.return_value = _make_credits(
            plan="starter", subscription_status="active",
        )
        clerk.get_user_subscription.return_value = _no_active_sub(
            status="canceled",
            period_end=parse_clerk_timestamp("2099-01-01T00:00:00Z"),
        )
        sync_module.sync_user_from_clerk("user_test")
        storage.update_plan.assert_not_called()
        storage.mark_pending_cancellation.assert_called_once()

    def test_apply_clerk_state_failure_fails_open_on_non_force(self, patched):
        # Any unexpected error in _apply_clerk_state (storage write, bad data,
        # future bug) must not 500 /user/credits or block service gates.
        storage, clerk = patched
        storage.get_or_create_credits.return_value = _make_credits(plan="free")
        clerk.get_user_subscription.return_value = _active_sub(plan="starter")
        storage.update_plan.side_effect = RuntimeError("DynamoDB blew up")
        result = sync_module.sync_user_from_clerk("user_test")
        assert result.plan == "free"  # stored state preserved
        # Throttle still bumped so we don't retry on every request.
        storage.touch_clerk_sync_timestamp.assert_called_with("user_test")

    def test_apply_clerk_state_failure_reraises_on_force(self, patched):
        storage, clerk = patched
        storage.get_or_create_credits.return_value = _make_credits(plan="free")
        clerk.get_user_subscription.return_value = _active_sub(plan="starter")
        storage.update_plan.side_effect = RuntimeError("DynamoDB blew up")
        with pytest.raises(RuntimeError, match="DynamoDB blew up"):
            sync_module.sync_user_from_clerk("user_test", force=True)

    def test_missing_clerk_secret_fails_open_on_non_force(self, mock_storage):
        with patch.object(sync_module, "get_user_credits_storage", return_value=mock_storage), \
             patch.object(sync_module, "get_clerk_client",
                          side_effect=ValueError("Could not retrieve secret")):
            result = sync_module.sync_user_from_clerk("user_test")
        assert result.plan == "free"
        mock_storage.update_plan.assert_not_called()
        mock_storage.touch_clerk_sync_timestamp.assert_called_with("user_test")
