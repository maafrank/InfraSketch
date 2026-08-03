"""Tests for the lazy monthly credit reset in UserCreditsStorage.

Clerk emits no renewal webhook for the $0 default plan, so free users were
granted their allowance once at signup and never again despite the pricing page
promising it monthly. get_or_create_credits now refills on read when a cycle
has elapsed.
"""

from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

from app.billing.models import UserCredits
from app.billing.storage import CREDIT_RESET_INTERVAL, UserCreditsStorage


@pytest.fixture
def storage():
    with patch("app.billing.storage.boto3.resource") as mock_resource, \
         patch("app.billing.storage.boto3.client") as mock_client:
        mock_resource.return_value.Table.return_value = MagicMock()
        mock_client.return_value.describe_table.return_value = {"Table": {"TableStatus": "ACTIVE"}}
        s = UserCreditsStorage()
    return s


def _credits(**overrides) -> UserCredits:
    base = dict(
        user_id="user_x",
        plan="free",
        credits_balance=0,
        credits_monthly_allowance=10,
        credits_used_this_period=10,
        plan_started_at=datetime.utcnow() - timedelta(days=200),
    )
    base.update(overrides)
    return UserCredits(**base)


class TestLazyMonthlyReset:
    def test_stale_free_user_is_refilled(self, storage):
        """The 187-user case: signed up months ago, never reset, stuck at 0."""
        credits = _credits(last_credit_reset_at=None)
        with patch.object(storage, "get_credits", return_value=credits), \
             patch.object(storage, "save_credits", return_value=True), \
             patch.object(storage, "_log_transaction") as log:
            result = storage.get_or_create_credits("user_x")

        assert result.credits_balance == 10
        assert result.credits_used_this_period == 0
        assert result.last_credit_reset_at is not None
        log.assert_called_once()
        assert log.call_args.kwargs["txn_type"] == "reset"
        assert log.call_args.kwargs["action"] == "monthly_reset_lazy"

    def test_recent_reset_is_not_refilled(self, storage):
        """A user mid-cycle keeps their spent balance."""
        credits = _credits(
            credits_balance=3,
            last_credit_reset_at=datetime.utcnow() - timedelta(days=2),
        )
        with patch.object(storage, "get_credits", return_value=credits), \
             patch.object(storage, "save_credits") as save, \
             patch.object(storage, "_log_transaction") as log:
            result = storage.get_or_create_credits("user_x")

        assert result.credits_balance == 3
        assert result.credits_used_this_period == 10
        save.assert_not_called()
        log.assert_not_called()

    def test_boundary_just_past_interval_refills(self, storage):
        credits = _credits(
            last_credit_reset_at=datetime.utcnow() - CREDIT_RESET_INTERVAL - timedelta(minutes=1),
        )
        with patch.object(storage, "get_credits", return_value=credits), \
             patch.object(storage, "save_credits", return_value=True), \
             patch.object(storage, "_log_transaction"):
            result = storage.get_or_create_credits("user_x")

        assert result.credits_balance == 10

    def test_reset_never_reduces_a_larger_balance(self, storage):
        """Promo/admin credits above the allowance survive a reset."""
        credits = _credits(credits_balance=500, last_credit_reset_at=None)
        with patch.object(storage, "get_credits", return_value=credits), \
             patch.object(storage, "save_credits", return_value=True), \
             patch.object(storage, "_log_transaction"):
            result = storage.get_or_create_credits("user_x")

        assert result.credits_balance == 500

    def test_paid_plan_also_refills_when_webhook_missed(self, storage):
        credits = _credits(
            plan="pro",
            credits_balance=0,
            credits_monthly_allowance=300,
            last_credit_reset_at=datetime.utcnow() - timedelta(days=45),
        )
        with patch.object(storage, "get_credits", return_value=credits), \
             patch.object(storage, "save_credits", return_value=True), \
             patch.object(storage, "_log_transaction"):
            result = storage.get_or_create_credits("user_x")

        assert result.credits_balance == 300

    def test_failed_save_rolls_back_in_memory_balance(self, storage):
        """Callers must not spend credits that were never persisted."""
        credits = _credits(last_credit_reset_at=None)
        with patch.object(storage, "get_credits", return_value=credits), \
             patch.object(storage, "save_credits", return_value=False), \
             patch.object(storage, "_log_transaction") as log:
            result = storage.get_or_create_credits("user_x")

        assert result.credits_balance == 0
        log.assert_not_called()

    def test_new_user_is_stamped_and_not_double_granted(self, storage):
        with patch.object(storage, "get_credits", return_value=None), \
             patch.object(storage, "save_credits", return_value=True), \
             patch.object(storage, "_log_transaction") as log:
            result = storage.get_or_create_credits("user_new")

        assert result.credits_balance == 10
        assert result.last_credit_reset_at is not None
        assert log.call_count == 1
        assert log.call_args.kwargs["action"] == "initial_signup"

    def test_missing_anchor_is_stamped_without_refill(self, storage):
        # created_at is non-nullable on the model, so this state is only
        # reachable defensively (e.g. a malformed stored row). model_construct
        # bypasses validation to exercise that branch.
        credits = UserCredits.model_construct(
            user_id="user_x",
            plan="free",
            credits_balance=4,
            credits_monthly_allowance=10,
            credits_used_this_period=6,
            last_credit_reset_at=None,
            plan_started_at=None,
            created_at=None,
        )
        with patch.object(storage, "get_credits", return_value=credits), \
             patch.object(storage, "save_credits", return_value=True), \
             patch.object(storage, "_log_transaction") as log:
            result = storage.get_or_create_credits("user_x")

        assert result.credits_balance == 4
        assert result.last_credit_reset_at is not None
        log.assert_not_called()
