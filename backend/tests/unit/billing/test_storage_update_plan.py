"""Tests for UserCreditsStorage.update_plan, focused on the downgrade path.

A canceled subscription must not leave the user with subscription_status="active"
and an old clerk_subscription_id, or pricing UIs and downstream gates will treat
them as still subscribed.
"""

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from app.billing.models import UserCredits
from app.billing.storage import UserCreditsStorage


@pytest.fixture
def storage():
    # Build a UserCreditsStorage without touching real DynamoDB. Patch the
    # resource/client at the boto3 layer; _ensure_tables_exist is a no-op
    # because the mocked client returns a fake describe_table.
    with patch("app.billing.storage.boto3.resource") as mock_resource, \
         patch("app.billing.storage.boto3.client") as mock_client:
        mock_resource.return_value.Table.return_value = MagicMock()
        mock_client.return_value.describe_table.return_value = {"Table": {"TableStatus": "ACTIVE"}}
        s = UserCreditsStorage()
    return s


def _starter_credits() -> UserCredits:
    return UserCredits(
        user_id="user_x",
        plan="starter",
        credits_balance=50,
        credits_monthly_allowance=50,
        clerk_subscription_id="csub_old",
        stripe_customer_id="cus_keep_me",
        subscription_status="active",
        plan_started_at=datetime.utcnow(),
    )


class TestDowngradeToFree:
    def test_downgrade_marks_status_canceled(self, storage):
        with patch.object(storage, "get_or_create_credits", return_value=_starter_credits()), \
             patch.object(storage, "save_credits", return_value=True) as mock_save, \
             patch.object(storage, "_log_transaction"):
            result = storage.update_plan(user_id="user_x", new_plan="free")
        assert result.plan == "free"
        assert result.subscription_status == "canceled"
        # save was called - DynamoDB will see the new state
        assert mock_save.called

    def test_downgrade_clears_stale_clerk_subscription_id(self, storage):
        with patch.object(storage, "get_or_create_credits", return_value=_starter_credits()), \
             patch.object(storage, "save_credits", return_value=True), \
             patch.object(storage, "_log_transaction"):
            result = storage.update_plan(user_id="user_x", new_plan="free")
        assert result.clerk_subscription_id is None

    def test_downgrade_preserves_stripe_customer_id(self, storage):
        # stripe_customer_id is the customer record (not the subscription); keep
        # it so a future re-subscribe can reuse the same Stripe customer.
        with patch.object(storage, "get_or_create_credits", return_value=_starter_credits()), \
             patch.object(storage, "save_credits", return_value=True), \
             patch.object(storage, "_log_transaction"):
            result = storage.update_plan(user_id="user_x", new_plan="free")
        assert result.stripe_customer_id == "cus_keep_me"


class TestTouchClerkSyncTimestamp:
    def test_uses_update_item_not_put_item(self, storage):
        # A full put_item would race with concurrent deduct_credits / promo
        # updates and overwrite them with a stale snapshot.
        storage.credits_table.update_item.reset_mock()
        storage.credits_table.put_item.reset_mock()
        storage.touch_clerk_sync_timestamp("user_x")
        storage.credits_table.update_item.assert_called_once()
        storage.credits_table.put_item.assert_not_called()
        call_kwargs = storage.credits_table.update_item.call_args.kwargs
        assert call_kwargs["Key"] == {"user_id": "user_x"}
        assert "last_clerk_sync_at" in call_kwargs["UpdateExpression"]
        assert ":ts" in call_kwargs["ExpressionAttributeValues"]


class TestMarkPendingCancellation:
    def test_uses_update_item_not_put_item(self, storage):
        # Must NOT call put_item - that would race with credit deductions.
        storage.credits_table.update_item.reset_mock()
        storage.credits_table.put_item.reset_mock()
        expires = datetime(2026, 6, 1)
        storage.mark_pending_cancellation("user_x", expires_at=expires)
        storage.credits_table.update_item.assert_called_once()
        storage.credits_table.put_item.assert_not_called()
        kwargs = storage.credits_table.update_item.call_args.kwargs
        assert kwargs["Key"] == {"user_id": "user_x"}
        assert "subscription_status" in kwargs["UpdateExpression"]
        assert "plan_expires_at" in kwargs["UpdateExpression"]
        # Must NOT touch plan or credit balances.
        assert "plan = " not in kwargs["UpdateExpression"]
        assert "credits_balance" not in kwargs["UpdateExpression"]
        assert kwargs["ExpressionAttributeValues"][":status"] == "canceled"

    def test_none_expires_at_removes_field(self, storage):
        storage.credits_table.update_item.reset_mock()
        storage.mark_pending_cancellation("user_x", expires_at=None)
        kwargs = storage.credits_table.update_item.call_args.kwargs
        assert "REMOVE plan_expires_at" in kwargs["UpdateExpression"]


class TestSetSubscriptionStatus:
    def test_uses_update_item(self, storage):
        # Atomic UpdateItem replaces the racy load+save_credits pattern used
        # for pastDue handling.
        storage.credits_table.update_item.reset_mock()
        storage.credits_table.put_item.reset_mock()
        storage.set_subscription_status("user_pd", "past_due")
        storage.credits_table.update_item.assert_called_once()
        storage.credits_table.put_item.assert_not_called()
        kwargs = storage.credits_table.update_item.call_args.kwargs
        assert kwargs["ExpressionAttributeValues"][":s"] == "past_due"


class TestResubscribeClearsExpiry:
    """Regression: when a user resubscribes, the old plan_expires_at must
    be cleared. Otherwise the subscription_expired gates block them."""

    def test_resubscribe_via_update_plan_clears_plan_expires_at(self, storage):
        from datetime import datetime as _dt, timedelta as _td
        prev_canceled = UserCredits(
            user_id="user_x",
            plan="starter",
            credits_balance=50,
            credits_monthly_allowance=50,
            subscription_status="canceled",
            plan_expires_at=_dt.utcnow() - _td(days=1),  # expired
            clerk_subscription_id="csub_old",
        )
        with patch.object(storage, "get_or_create_credits", return_value=prev_canceled), \
             patch.object(storage, "save_credits", return_value=True), \
             patch.object(storage, "_log_transaction"):
            result = storage.update_plan(
                user_id="user_x", new_plan="starter",
                clerk_subscription_id="csub_new",
            )
        assert result.plan_expires_at is None
        assert result.subscription_status == "active"

    def test_set_subscription_status_active_clears_expiry(self, storage):
        # Sync's recovery path: stored=canceled with expiry, Clerk says active
        # -> flip status to active and drop expiry atomically.
        storage.credits_table.update_item.reset_mock()
        storage.set_subscription_status("user_x", "active")
        kwargs = storage.credits_table.update_item.call_args.kwargs
        assert "REMOVE plan_expires_at" in kwargs["UpdateExpression"]
        assert kwargs["ExpressionAttributeValues"][":s"] == "active"

    def test_set_subscription_status_past_due_does_not_clear_expiry(self, storage):
        storage.credits_table.update_item.reset_mock()
        storage.set_subscription_status("user_x", "past_due")
        kwargs = storage.credits_table.update_item.call_args.kwargs
        assert "REMOVE" not in kwargs["UpdateExpression"]


class TestUpgradeStillActive:
    def test_upgrade_sets_active_and_records_new_subscription_id(self, storage):
        free_user = UserCredits(
            user_id="user_x",
            plan="free",
            credits_balance=10,
            credits_monthly_allowance=10,
        )
        with patch.object(storage, "get_or_create_credits", return_value=free_user), \
             patch.object(storage, "save_credits", return_value=True), \
             patch.object(storage, "_log_transaction"):
            result = storage.update_plan(
                user_id="user_x",
                new_plan="starter",
                clerk_subscription_id="csub_new",
                stripe_customer_id="cus_new",
            )
        assert result.plan == "starter"
        assert result.subscription_status == "active"
        assert result.clerk_subscription_id == "csub_new"
        assert result.stripe_customer_id == "cus_new"
