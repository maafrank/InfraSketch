"""Tests for the plan entitlement gates in app.api._helpers.

Two features were advertised on the pricing page but never enforced:
"Power model access" (Pro) and "Design document export" (Starter). Free users
could use both.
"""

from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

from app.api._helpers import enforce_export_access, resolve_model_for_plan
from app.billing.models import UserCredits
from app.config.models import HAIKU, OPUS, SONNET


def _storage_returning(plan: str):
    storage = MagicMock()
    storage.get_or_create_credits.return_value = UserCredits(user_id="user_x", plan=plan)
    return storage


class TestResolveModelForPlan:
    @pytest.mark.parametrize("model", [SONNET, OPUS])
    def test_free_user_is_downgraded_to_speed(self, model):
        with patch("app.api._helpers.get_user_credits_storage", return_value=_storage_returning("free")):
            assert resolve_model_for_plan("user_x", model) == HAIKU

    @pytest.mark.parametrize("plan", ["pro", "enterprise"])
    @pytest.mark.parametrize("model", [SONNET, OPUS])
    def test_entitled_plans_keep_premium_model(self, plan, model):
        with patch("app.api._helpers.get_user_credits_storage", return_value=_storage_returning(plan)):
            assert resolve_model_for_plan("user_x", model) == model

    def test_starter_is_not_entitled_to_premium(self):
        """Starter buys credits and export, not Power model access."""
        with patch("app.api._helpers.get_user_credits_storage", return_value=_storage_returning("starter")):
            assert resolve_model_for_plan("user_x", SONNET) == HAIKU

    def test_speed_model_is_never_gated(self):
        with patch("app.api._helpers.get_user_credits_storage") as storage:
            assert resolve_model_for_plan("user_x", HAIKU) == HAIKU
            storage.assert_not_called()

    def test_no_model_falls_back_to_default_without_a_plan_lookup(self):
        with patch("app.api._helpers.get_user_credits_storage") as storage:
            assert resolve_model_for_plan("user_x", None) == HAIKU
            storage.assert_not_called()

    def test_anonymous_caller_is_unrestricted(self):
        """Local dev with auth disabled has no user_id."""
        with patch("app.api._helpers.get_user_credits_storage") as storage:
            assert resolve_model_for_plan(None, OPUS) == OPUS
            storage.assert_not_called()

    def test_storage_failure_fails_open(self):
        """A storage blip must not downgrade a paying customer mid-request."""
        with patch("app.api._helpers.get_user_credits_storage", side_effect=RuntimeError("dynamo down")):
            assert resolve_model_for_plan("user_x", OPUS) == OPUS


class TestEnforceExportAccess:
    @pytest.mark.parametrize("plan", ["starter", "pro", "enterprise"])
    def test_paid_plans_may_export(self, plan):
        with patch("app.api._helpers.get_user_credits_storage", return_value=_storage_returning(plan)):
            enforce_export_access("user_x")  # does not raise

    def test_free_plan_is_blocked_with_feature_locked(self):
        with patch("app.api._helpers.get_user_credits_storage", return_value=_storage_returning("free")):
            with pytest.raises(HTTPException) as exc:
                enforce_export_access("user_x")

        assert exc.value.status_code == 403
        assert exc.value.detail["error"] == "feature_locked"
        assert exc.value.detail["feature"] == "design_doc_export"
        assert exc.value.detail["required_plan"] == "starter"

    def test_anonymous_caller_is_unrestricted(self):
        with patch("app.api._helpers.get_user_credits_storage") as storage:
            enforce_export_access(None)
            storage.assert_not_called()

    def test_storage_failure_fails_open(self):
        with patch("app.api._helpers.get_user_credits_storage", side_effect=RuntimeError("dynamo down")):
            enforce_export_access("user_x")  # does not raise
