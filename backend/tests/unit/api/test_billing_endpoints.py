"""Tests for the billing-related endpoints flagged as gaps in the cleanup audit:

- POST /api/promo/redeem
- POST /api/promo/validate
- POST /api/webhooks/clerk-billing  (signature verification + a couple of event types)

We don't exercise every Clerk event variant - just enough to catch the
high-blast-radius regressions (signature failure, user.created credit init).
"""

import json
import sys
from unittest.mock import MagicMock, patch

import pytest


# The clerk-billing webhook does an inline `from svix.webhooks import ...`
# inside the handler. svix isn't a hard test dependency, so install a stub
# in sys.modules so the import succeeds. Tests that exercise the verification
# branch override Webhook.verify directly.
class _StubVerificationError(Exception):
    pass


class _StubWebhook:
    def __init__(self, secret):
        self.secret = secret

    def verify(self, body, headers):
        # Default: behave like a real verifier and reject anything unsigned.
        raise _StubVerificationError("missing svix headers")


_svix_stub = MagicMock()
_svix_stub.webhooks.Webhook = _StubWebhook
_svix_stub.webhooks.WebhookVerificationError = _StubVerificationError
sys.modules.setdefault("svix", _svix_stub)
sys.modules.setdefault("svix.webhooks", _svix_stub.webhooks)


class TestPromoRedeem:
    """POST /api/promo/redeem"""

    def test_invalid_code_returns_400(self, client, mock_user_credits_storage):
        with patch("app.api.routes_billing.redeem_promo_code") as mock_redeem:
            mock_redeem.return_value = (False, "Code not found", 0, 0)
            response = client.post("/api/promo/redeem", json={"code": "DOESNTEXIST"})

        assert response.status_code == 400
        assert response.json()["detail"] == "Code not found"

    def test_successful_redeem_returns_credits(self, client, mock_user_credits_storage):
        with patch("app.api.routes_billing.redeem_promo_code") as mock_redeem:
            mock_redeem.return_value = (True, None, 100, 0)
            response = client.post("/api/promo/redeem", json={"code": "WELCOME100"})

        assert response.status_code == 200
        body = response.json()
        assert body["success"] is True
        assert body["credits_granted"] == 100
        assert body["design_docs_granted"] == 0
        assert body["new_balance"] == 10000  # from mock_user_credits_storage default
        assert "100 credits" in body["message"]
        mock_redeem.assert_called_once_with("WELCOME100", "local-dev-user")

    def test_freedesign_redeem_grants_design_doc(self, client, mock_user_credits_storage):
        # Simulate FREEDESIGN: zero credits granted, one design-doc grant.
        mock_user_credits_storage.get_credits.return_value.free_design_docs_remaining = 1
        with patch("app.api.routes_billing.redeem_promo_code") as mock_redeem:
            mock_redeem.return_value = (True, None, 0, 1)
            response = client.post("/api/promo/redeem", json={"code": "FREEDESIGN"})

        assert response.status_code == 200
        body = response.json()
        assert body["success"] is True
        assert body["credits_granted"] == 0
        assert body["design_docs_granted"] == 1
        assert body["free_design_docs_remaining"] == 1
        assert "free design doc" in body["message"]
        mock_redeem.assert_called_once_with("FREEDESIGN", "local-dev-user")


class TestPromoValidate:
    """POST /api/promo/validate"""

    def test_invalid_code_returns_invalid(self, client):
        with patch("app.api.routes_billing.validate_promo_code") as mock_validate:
            mock_validate.return_value = (False, "Code expired")
            response = client.post("/api/promo/validate", json={"code": "OLD"})

        assert response.status_code == 200
        body = response.json()
        assert body["valid"] is False
        assert body["error"] == "Code expired"

    def test_valid_code_returns_credits_amount(self, client):
        with patch("app.api.routes_billing.validate_promo_code") as mock_validate, \
             patch("app.api.routes_billing.get_promo_code_info") as mock_info:
            mock_validate.return_value = (True, None)
            mock_info.return_value = {"credits": 250, "grants_design_doc": 0}
            response = client.post("/api/promo/validate", json={"code": "GOOD"})

        assert response.status_code == 200
        body = response.json()
        assert body["valid"] is True
        assert body["credits"] == 250
        assert body["design_docs_granted"] == 0

    def test_valid_freedesign_returns_grant_metadata(self, client):
        with patch("app.api.routes_billing.validate_promo_code") as mock_validate, \
             patch("app.api.routes_billing.get_promo_code_info") as mock_info:
            mock_validate.return_value = (True, None)
            mock_info.return_value = {"credits": 0, "grants_design_doc": 1}
            response = client.post("/api/promo/validate", json={"code": "FREEDESIGN"})

        assert response.status_code == 200
        body = response.json()
        assert body["valid"] is True
        assert body["credits"] == 0
        assert body["design_docs_granted"] == 1


class TestClerkBillingWebhook:
    """POST /api/webhooks/clerk-billing - signature handling + key event types.

    The endpoint configures a Webhook(secret) verifier when CLERK_BILLING_WEBHOOK_SECRET
    is set. Tests force the unset path (dev mode, no signature check) to
    exercise event routing without setting up real svix signing.
    """

    def test_user_created_initializes_credits(self, client, mock_user_credits_storage, monkeypatch):
        monkeypatch.delenv("CLERK_BILLING_WEBHOOK_SECRET", raising=False)
        payload = {"type": "user.created", "data": {"id": "user_test_42"}}
        response = client.post(
            "/api/webhooks/clerk-billing",
            content=json.dumps(payload),
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code == 200
        mock_user_credits_storage.get_or_create_credits.assert_called_with("user_test_42")

    def test_subscription_created_updates_plan(self, client, mock_user_credits_storage, monkeypatch):
        monkeypatch.delenv("CLERK_BILLING_WEBHOOK_SECRET", raising=False)
        payload = {
            "type": "subscription.created",
            "data": {
                "id": "sub_xyz",
                "plan_id": "cplan_starter",
                "stripe_customer_id": "cus_123",
                "payer": {"user_id": "user_test_99"},
            },
        }
        response = client.post(
            "/api/webhooks/clerk-billing",
            content=json.dumps(payload),
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code == 200
        # update_plan should be called for this user
        assert mock_user_credits_storage.update_plan.called
        call_kwargs = mock_user_credits_storage.update_plan.call_args.kwargs
        assert call_kwargs["user_id"] == "user_test_99"

    def test_invalid_signature_returns_401(self, client, monkeypatch):
        # When the secret IS set, an unsigned body must be rejected.
        monkeypatch.setenv("CLERK_BILLING_WEBHOOK_SECRET", "whsec_test_secret")
        payload = {"type": "user.created", "data": {"id": "u"}}
        response = client.post(
            "/api/webhooks/clerk-billing",
            content=json.dumps(payload),
            headers={"Content-Type": "application/json"},
        )
        # svix verification will fail because no svix-id/svix-timestamp/svix-signature
        # headers were sent.
        assert response.status_code == 401
        assert response.json()["detail"] == "Invalid webhook signature"

    def test_subscription_created_extracts_nested_plan_id(self, client, mock_user_credits_storage, monkeypatch):
        # This is the bug class that broke mattafrank's account: the top-level
        # data.plan_id is empty, and the real plan_id lives in subscription_items.
        monkeypatch.delenv("CLERK_BILLING_WEBHOOK_SECRET", raising=False)
        payload = {
            "type": "subscription.created",
            "data": {
                "id": "csub_nested",
                "plan_id": "",  # the bug-trigger
                "payer": {"user_id": "user_nested"},
                "subscription_items": [
                    {
                        "status": "active",
                        "plan_id": "cplan_3ASdFvizPo0JbVeethbsS7UfLjp",
                    }
                ],
            },
        }
        response = client.post(
            "/api/webhooks/clerk-billing",
            content=json.dumps(payload),
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code == 200
        assert mock_user_credits_storage.update_plan.called
        kwargs = mock_user_credits_storage.update_plan.call_args.kwargs
        assert kwargs["user_id"] == "user_nested"
        assert kwargs["new_plan"] == "starter"

    def test_subscription_created_resolves_nested_plan_slug(self, client, mock_user_credits_storage, monkeypatch):
        # Webhook must accept the same nested shapes the Clerk API client
        # handles. If Clerk sends an item with only nested plan.slug, the
        # webhook used to return missing_plan_id and never sync the user.
        monkeypatch.delenv("CLERK_BILLING_WEBHOOK_SECRET", raising=False)
        payload = {
            "type": "subscription.created",
            "data": {
                "id": "csub_slug_webhook",
                "payer": {"user_id": "user_slug_webhook"},
                "subscription_items": [
                    {"status": "active", "plan": {"slug": "starter"}}
                ],
            },
        }
        response = client.post(
            "/api/webhooks/clerk-billing",
            content=json.dumps(payload),
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code == 200
        kwargs = mock_user_credits_storage.update_plan.call_args.kwargs
        assert kwargs["user_id"] == "user_slug_webhook"
        assert kwargs["new_plan"] == "starter"

    def test_subscription_created_empty_plan_id_returns_500(self, client, mock_user_credits_storage, monkeypatch):
        # Malformed payload (no subscription_items, no top-level plan_id) must
        # NOT silently flow through to update_plan(new_plan="free"), which
        # would mark a paying account as canceled.
        monkeypatch.delenv("CLERK_BILLING_WEBHOOK_SECRET", raising=False)
        payload = {
            "type": "subscription.created",
            "data": {
                "id": "csub_empty",
                "plan_id": "",
                "payer": {"user_id": "user_empty"},
                "subscription_items": [],
            },
        }
        response = client.post(
            "/api/webhooks/clerk-billing",
            content=json.dumps(payload),
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code == 500
        assert "missing_plan_id" in response.text
        mock_user_credits_storage.update_plan.assert_not_called()

    def test_subscription_updated_empty_plan_id_returns_500(self, client, mock_user_credits_storage, monkeypatch):
        # Same protection on the update path - active subscription with a
        # shape-changed payload must not become a stealth cancellation.
        monkeypatch.delenv("CLERK_BILLING_WEBHOOK_SECRET", raising=False)
        payload = {
            "type": "subscription.updated",
            "data": {
                "id": "csub_upd",
                "payer": {"user_id": "user_upd"},
                "subscription_items": [{"status": "active"}],  # plan_id missing
            },
        }
        response = client.post(
            "/api/webhooks/clerk-billing",
            content=json.dumps(payload),
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code == 500
        assert "missing_plan_id" in response.text
        mock_user_credits_storage.update_plan.assert_not_called()

    def test_subscription_created_unknown_plan_id_returns_500(self, client, mock_user_credits_storage, monkeypatch):
        # Unknown plan_id during create/activate must NOT silently store free.
        # Returning 500 forces Clerk to retry the webhook.
        monkeypatch.delenv("CLERK_BILLING_WEBHOOK_SECRET", raising=False)
        payload = {
            "type": "subscription.created",
            "data": {
                "id": "csub_bad",
                "plan_id": "cplan_neverseen",
                "payer": {"user_id": "user_bad"},
            },
        }
        response = client.post(
            "/api/webhooks/clerk-billing",
            content=json.dumps(payload),
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code == 500
        assert "unknown_plan_id" in response.text
        mock_user_credits_storage.update_plan.assert_not_called()

    def test_subscription_updated_canceled_marks_pending_not_downgrade(self, client, mock_user_credits_storage, monkeypatch):
        # Per Clerk billing semantics, status=canceled means user opted out
        # but retains entitlement until period_end. We mark canceled, keep
        # the plan; a later subscription.ended (or periodic sync) flips to
        # free at the actual expiry.
        monkeypatch.delenv("CLERK_BILLING_WEBHOOK_SECRET", raising=False)
        payload = {
            "type": "subscription.updated",
            "data": {
                "id": "csub_cancel_update",
                "status": "canceled",
                "payer": {"user_id": "user_canceled"},
                "subscription_items": [
                    {"status": "canceled", "period_end": 1780591212670,
                     "plan_id": "cplan_3ASdFvizPo0JbVeethbsS7UfLjp"}
                ],
            },
        }
        response = client.post(
            "/api/webhooks/clerk-billing",
            content=json.dumps(payload),
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code == 200
        mock_user_credits_storage.update_plan.assert_not_called()
        mock_user_credits_storage.mark_pending_cancellation.assert_called_once()
        kwargs = mock_user_credits_storage.mark_pending_cancellation.call_args.kwargs
        assert kwargs["user_id"] == "user_canceled"
        assert kwargs["expires_at"] is not None

    def test_subscription_updated_past_due_marks_past_due_keeps_plan(self, client, mock_user_credits_storage, monkeypatch):
        # past_due must NOT be routed to the canceled-by-items branch (which
        # treats it as canceled-with-grace and keeps service on). It must
        # mark stored status past_due so gates block.
        monkeypatch.delenv("CLERK_BILLING_WEBHOOK_SECRET", raising=False)
        payload = {
            "type": "subscription.updated",
            "data": {
                "id": "csub_pd_top",
                "status": "past_due",
                "payer": {"user_id": "user_pd_via_updated"},
                "subscription_items": [
                    {"status": "canceled", "plan_id": "cplan_3ASdFvizPo0JbVeethbsS7UfLjp"}
                ],
            },
        }
        response = client.post(
            "/api/webhooks/clerk-billing",
            content=json.dumps(payload),
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code == 200
        mock_user_credits_storage.set_subscription_status.assert_called_once_with(
            "user_pd_via_updated", "past_due"
        )
        mock_user_credits_storage.update_plan.assert_not_called()
        mock_user_credits_storage.mark_pending_cancellation.assert_not_called()

    def test_subscription_updated_ended_status_downgrades(self, client, mock_user_credits_storage, monkeypatch):
        # status=ended IS authoritative - entitlement is over now.
        monkeypatch.delenv("CLERK_BILLING_WEBHOOK_SECRET", raising=False)
        payload = {
            "type": "subscription.updated",
            "data": {
                "id": "csub_ended",
                "status": "ended",
                "payer": {"user_id": "user_ended"},
                "subscription_items": [],
            },
        }
        response = client.post(
            "/api/webhooks/clerk-billing",
            content=json.dumps(payload),
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code == 200
        mock_user_credits_storage.update_plan.assert_called_once()
        assert mock_user_credits_storage.update_plan.call_args.kwargs["new_plan"] == "free"

    def test_subscription_updated_no_active_items_marks_canceled(self, client, mock_user_credits_storage, monkeypatch):
        # When items are all canceled but top-level status is missing, treat
        # as canceled-with-grace (NOT immediate downgrade). The subsequent
        # subscription.ended event will handle the actual downgrade.
        monkeypatch.delenv("CLERK_BILLING_WEBHOOK_SECRET", raising=False)
        payload = {
            "type": "subscription.updated",
            "data": {
                "id": "csub_all_inactive",
                "payer": {"user_id": "user_all_inactive"},
                "subscription_items": [
                    {"status": "canceled", "period_end": 1780591212670,
                     "plan_id": "cplan_3ASdFvizPo0JbVeethbsS7UfLjp"}
                ],
            },
        }
        response = client.post(
            "/api/webhooks/clerk-billing",
            content=json.dumps(payload),
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code == 200
        mock_user_credits_storage.update_plan.assert_not_called()
        mock_user_credits_storage.mark_pending_cancellation.assert_called_once()

    def test_subscription_updated_all_items_ended_downgrades(self, client, mock_user_credits_storage, monkeypatch):
        # Regression: previously bundled with canceled in all_items_terminal,
        # which kept the paid plan. ended/expired means entitlement is OVER -
        # must downgrade, not mark pending cancellation.
        monkeypatch.delenv("CLERK_BILLING_WEBHOOK_SECRET", raising=False)
        payload = {
            "type": "subscription.updated",
            "data": {
                "id": "csub_all_ended",
                "payer": {"user_id": "user_all_ended"},
                "subscription_items": [
                    {"status": "ended", "plan_id": "cplan_3ASdFvizPo0JbVeethbsS7UfLjp"}
                ],
            },
        }
        response = client.post(
            "/api/webhooks/clerk-billing",
            content=json.dumps(payload),
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code == 200
        mock_user_credits_storage.update_plan.assert_called_once()
        assert mock_user_credits_storage.update_plan.call_args.kwargs["new_plan"] == "free"
        mock_user_credits_storage.mark_pending_cancellation.assert_not_called()

    def test_subscription_updated_all_items_expired_downgrades(self, client, mock_user_credits_storage, monkeypatch):
        monkeypatch.delenv("CLERK_BILLING_WEBHOOK_SECRET", raising=False)
        payload = {
            "type": "subscription.updated",
            "data": {
                "id": "csub_all_expired",
                "payer": {"user_id": "user_all_expired"},
                "subscription_items": [
                    {"status": "expired", "plan_id": "cplan_3ASdFvizPo0JbVeethbsS7UfLjp"}
                ],
            },
        }
        response = client.post(
            "/api/webhooks/clerk-billing",
            content=json.dumps(payload),
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code == 200
        assert mock_user_credits_storage.update_plan.call_args.kwargs["new_plan"] == "free"

    def test_subscription_updated_mixed_canceled_and_ended_downgrades(self, client, mock_user_credits_storage, monkeypatch):
        # If any non-active item is ended/expired, entitlement is over for
        # that part of the subscription. With no compensating active item,
        # downgrade rather than mark pending.
        monkeypatch.delenv("CLERK_BILLING_WEBHOOK_SECRET", raising=False)
        payload = {
            "type": "subscription.updated",
            "data": {
                "id": "csub_mixed",
                "payer": {"user_id": "user_mixed"},
                "subscription_items": [
                    {"status": "canceled", "plan_id": "cplan_3ASdFvizPo0JbVeethbsS7UfLjp"},
                    {"status": "ended", "plan_id": "cplan_3ASdFvizPo0JbVeethbsS7UfLjp"},
                ],
            },
        }
        response = client.post(
            "/api/webhooks/clerk-billing",
            content=json.dumps(payload),
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code == 200
        assert mock_user_credits_storage.update_plan.call_args.kwargs["new_plan"] == "free"
        mock_user_credits_storage.mark_pending_cancellation.assert_not_called()

    def test_subscription_updated_statusless_items_apply_plan_not_cancel(self, client, mock_user_credits_storage, monkeypatch):
        # Regression: a payload with subscription_items[] that lack an explicit
        # status but DO carry a plan_id used to be mis-routed as cancellation
        # (because no item had status=="active"). Statusless items are
        # ambiguous - the extraction helper accepts them as usable plan data,
        # so the webhook handler must too.
        monkeypatch.delenv("CLERK_BILLING_WEBHOOK_SECRET", raising=False)
        payload = {
            "type": "subscription.updated",
            "data": {
                "id": "csub_statusless",
                "payer": {"user_id": "user_statusless"},
                "subscription_items": [
                    {"plan_id": "cplan_3ASdFvizPo0JbVeethbsS7UfLjp"}
                ],
            },
        }
        response = client.post(
            "/api/webhooks/clerk-billing",
            content=json.dumps(payload),
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code == 200
        mock_user_credits_storage.mark_pending_cancellation.assert_not_called()
        mock_user_credits_storage.update_plan.assert_called_once()
        assert mock_user_credits_storage.update_plan.call_args.kwargs["new_plan"] == "starter"

    def test_subscription_item_created_resolves_nested_plan_slug(self, client, mock_user_credits_storage, monkeypatch):
        # subscriptionItem.* events ARE the item (not wrapped). Must use the
        # shared extractor so plan.id / plan.slug variants still sync.
        monkeypatch.delenv("CLERK_BILLING_WEBHOOK_SECRET", raising=False)
        payload = {
            "type": "subscriptionItem.created",
            "data": {
                "subscription_id": "csub_item_slug",
                "payer": {"user_id": "user_item_slug"},
                "plan": {"slug": "starter"},
            },
        }
        response = client.post(
            "/api/webhooks/clerk-billing",
            content=json.dumps(payload),
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code == 200
        kwargs = mock_user_credits_storage.update_plan.call_args.kwargs
        assert kwargs["user_id"] == "user_item_slug"
        assert kwargs["new_plan"] == "starter"

    def test_subscription_item_canceled_marks_pending_with_period_end(self, client, mock_user_credits_storage, monkeypatch):
        # subscriptionItem.canceled means "user opted out, entitlement until
        # period_end". We mark canceled and keep the plan. A later
        # subscriptionItem.ended (or periodic sync) flips to free.
        monkeypatch.delenv("CLERK_BILLING_WEBHOOK_SECRET", raising=False)
        payload = {
            "type": "subscriptionItem.canceled",
            "data": {
                "subscription_id": "csub_cancel",
                "period_end": 1780591212670,
                "payer": {"user_id": "user_cancel"},
            },
        }
        response = client.post(
            "/api/webhooks/clerk-billing",
            content=json.dumps(payload),
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code == 200
        mock_user_credits_storage.update_plan.assert_not_called()
        mock_user_credits_storage.mark_pending_cancellation.assert_called_once()
        kwargs = mock_user_credits_storage.mark_pending_cancellation.call_args.kwargs
        assert kwargs["user_id"] == "user_cancel"
        assert kwargs["expires_at"] is not None
        assert kwargs["clerk_subscription_id"] == "csub_cancel"

    def test_subscription_item_ended_downgrades(self, client, mock_user_credits_storage, monkeypatch):
        # subscriptionItem.ended IS the authoritative entitlement end.
        monkeypatch.delenv("CLERK_BILLING_WEBHOOK_SECRET", raising=False)
        payload = {
            "type": "subscriptionItem.ended",
            "data": {
                "subscription_id": "csub_ended_item",
                "payer": {"user_id": "user_ended_item"},
            },
        }
        response = client.post(
            "/api/webhooks/clerk-billing",
            content=json.dumps(payload),
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code == 200
        mock_user_credits_storage.update_plan.assert_called_once()
        assert mock_user_credits_storage.update_plan.call_args.kwargs["new_plan"] == "free"

    def test_subscription_ended_downgrades(self, client, mock_user_credits_storage, monkeypatch):
        monkeypatch.delenv("CLERK_BILLING_WEBHOOK_SECRET", raising=False)
        payload = {
            "type": "subscription.ended",
            "data": {
                "id": "csub_sub_ended",
                "payer": {"user_id": "user_sub_ended"},
            },
        }
        response = client.post(
            "/api/webhooks/clerk-billing",
            content=json.dumps(payload),
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code == 200
        mock_user_credits_storage.update_plan.assert_called_once()
        assert mock_user_credits_storage.update_plan.call_args.kwargs["new_plan"] == "free"

    def test_subscription_item_past_due_sets_status(self, client, mock_user_credits_storage, monkeypatch):
        monkeypatch.delenv("CLERK_BILLING_WEBHOOK_SECRET", raising=False)
        payload = {
            "type": "subscriptionItem.pastDue",
            "data": {"payer": {"user_id": "user_pd"}},
        }
        response = client.post(
            "/api/webhooks/clerk-billing",
            content=json.dumps(payload),
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code == 200
        mock_user_credits_storage.set_subscription_status.assert_called_once_with("user_pd", "past_due")

    def test_subscription_past_due_uses_atomic_set_status(self, client, mock_user_credits_storage, monkeypatch):
        # Was previously a racy load+save; now an atomic UpdateItem.
        monkeypatch.delenv("CLERK_BILLING_WEBHOOK_SECRET", raising=False)
        payload = {
            "type": "subscription.pastDue",
            "data": {"id": "csub_pd", "payer": {"user_id": "user_pd_top"}},
        }
        response = client.post(
            "/api/webhooks/clerk-billing",
            content=json.dumps(payload),
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code == 200
        mock_user_credits_storage.set_subscription_status.assert_called_once_with("user_pd_top", "past_due")
        mock_user_credits_storage.save_credits.assert_not_called()


class TestUserCreditsSelfHealing:
    """GET /api/user/credits triggers Clerk sync for free-tier users.

    The conftest fixture stubs out sync_user_from_clerk to a transparent
    pass-through for unrelated tests. These tests want the real sync to run,
    so they re-patch the route's binding back to the real function.
    """

    @staticmethod
    def _restore_real_sync(mocker):
        from app.billing.sync import sync_user_from_clerk as real_sync
        mocker.patch("app.api.routes_billing.sync_user_from_clerk", side_effect=real_sync)

    def test_free_user_with_active_starter_subscription_is_healed(self, client, mock_user_credits_storage, mocker):
        from datetime import datetime
        from app.billing.clerk_client import ClerkSubscription
        from app.billing.models import UserCredits

        self._restore_real_sync(mocker)

        free_credits = UserCredits(
            user_id="local-dev-user",
            plan="free",
            credits_balance=10,
            credits_monthly_allowance=10,
            last_clerk_sync_at=None,
        )
        starter_credits = UserCredits(
            user_id="local-dev-user",
            plan="starter",
            credits_balance=50,
            credits_monthly_allowance=50,
        )
        mock_user_credits_storage.get_or_create_credits.return_value = free_credits
        mock_user_credits_storage.update_plan.return_value = starter_credits
        # Sync re-fetches the freshest row after update_plan via get_credits.
        mock_user_credits_storage.get_credits.return_value = starter_credits

        with patch("app.billing.sync.get_clerk_client") as mock_get_client:
            mock_client = MagicMock()
            mock_client.get_user_subscription.return_value = ClerkSubscription(
                plan="starter",
                subscription_id="csub_heal",
                plan_id="cplan_3ASdFvizPo0JbVeethbsS7UfLjp",
                status="active",
                has_active_item=True,
            )
            mock_get_client.return_value = mock_client
            response = client.get("/api/user/credits")

        assert response.status_code == 200
        body = response.json()
        assert body["plan"] == "starter"
        mock_user_credits_storage.update_plan.assert_called_once()

    def test_paid_user_throttled_skips_clerk_lookup(self, client, mock_user_credits_storage):
        # Paid users are now ALSO checked periodically (24h interval). Within
        # the throttle window, Clerk isn't called.
        from datetime import datetime
        from app.billing.models import UserCredits

        paid_user_recent = UserCredits(
            user_id="local-dev-user",
            plan="pro",
            credits_balance=10000,
            credits_monthly_allowance=500,
            last_clerk_sync_at=datetime.utcnow(),  # just synced
        )
        mock_user_credits_storage.get_or_create_credits.return_value = paid_user_recent
        mock_user_credits_storage.get_credits.return_value = paid_user_recent

        with patch("app.billing.sync.get_clerk_client") as mock_get_client:
            response = client.get("/api/user/credits")
            mock_get_client.return_value.get_user_subscription.assert_not_called()
        assert response.status_code == 200
        assert response.json()["plan"] == "pro"


class TestAdminSyncPlan:
    """POST /api/admin/user/{id}/sync-plan"""

    def test_non_admin_gets_403(self, client, mock_user_credits_storage, monkeypatch):
        monkeypatch.setenv("ADMIN_USER_IDS", "user_someone_else")
        response = client.post("/api/admin/user/user_target/sync-plan")
        assert response.status_code == 403

    def test_admin_sync_returns_502_when_clerk_fails(self, client, mock_user_credits_storage, monkeypatch, mocker):
        # Support must see a clear failure, not a misleading 200 with unchanged credits.
        from app.billing.sync import sync_user_from_clerk as real_sync
        mocker.patch("app.api.routes_billing.sync_user_from_clerk", side_effect=real_sync)
        monkeypatch.setenv("ADMIN_USER_IDS", "local-dev-user")
        with patch("app.billing.sync.get_clerk_client",
                   side_effect=ValueError("Could not retrieve secret 'infrasketch/clerk-secret-key'")):
            response = client.post("/api/admin/user/user_target/sync-plan")
        assert response.status_code == 502
        assert "Clerk sync failed" in response.json()["detail"]
        mock_user_credits_storage.update_plan.assert_not_called()

    def test_admin_force_syncs(self, client, mock_user_credits_storage, monkeypatch, mocker):
        from app.billing.clerk_client import ClerkSubscription
        from app.billing.models import UserCredits
        from app.billing.sync import sync_user_from_clerk as real_sync
        mocker.patch("app.api.routes_billing.sync_user_from_clerk", side_effect=real_sync)

        # dev auth bypass user is "local-dev-user"; promote it to admin.
        monkeypatch.setenv("ADMIN_USER_IDS", "local-dev-user")

        target_credits = UserCredits(
            user_id="user_target", plan="free", credits_balance=10,
            credits_monthly_allowance=10,
        )
        healed = UserCredits(
            user_id="user_target", plan="starter", credits_balance=50,
            credits_monthly_allowance=50, subscription_status="active",
        )
        mock_user_credits_storage.get_or_create_credits.return_value = target_credits
        mock_user_credits_storage.update_plan.return_value = healed
        mock_user_credits_storage.get_credits.return_value = healed

        with patch("app.billing.sync.get_clerk_client") as mock_get_client:
            mock_get_client.return_value.get_user_subscription.return_value = ClerkSubscription(
                plan="starter", subscription_id="csub_a", plan_id="cplan_starter",
                status="active", has_active_item=True,
            )
            response = client.post("/api/admin/user/user_target/sync-plan")

        assert response.status_code == 200
        body = response.json()
        assert body["user_id"] == "user_target"
        assert body["plan"] == "starter"
        mock_user_credits_storage.update_plan.assert_called_once()


class TestWebhookInvalidatesClerkCache:
    """Every billing webhook with a user_id must drop that user's per-process
    Clerk client cache. Regression: a free user's 404 was cached, then they
    paid, then a service gate read the stale 404 and downgraded them.
    """

    def test_webhook_invalidates_cache_for_user(self, client, mock_user_credits_storage, monkeypatch, mocker):
        monkeypatch.delenv("CLERK_BILLING_WEBHOOK_SECRET", raising=False)
        spy = mocker.patch("app.api.routes_billing.invalidate_clerk_cache_for_user")
        payload = {
            "type": "subscription.created",
            "data": {
                "id": "csub_new",
                "payer": {"user_id": "user_just_paid"},
                "subscription_items": [
                    {"status": "active", "plan_id": "cplan_3ASdFvizPo0JbVeethbsS7UfLjp"}
                ],
            },
        }
        response = client.post(
            "/api/webhooks/clerk-billing",
            content=json.dumps(payload),
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code == 200
        spy.assert_called_once_with("user_just_paid")

    def test_webhook_without_user_id_skips_invalidation(self, client, mock_user_credits_storage, monkeypatch, mocker):
        monkeypatch.delenv("CLERK_BILLING_WEBHOOK_SECRET", raising=False)
        spy = mocker.patch("app.api.routes_billing.invalidate_clerk_cache_for_user")
        # Malformed payload with no user_id - the invalidate helper is
        # called but its no-op branch (empty user_id) handles it.
        payload = {"type": "subscription.created", "data": {}}
        client.post(
            "/api/webhooks/clerk-billing",
            content=json.dumps(payload),
            headers={"Content-Type": "application/json"},
        )
        spy.assert_called_once_with(None)


class TestPastDueGates:
    """past_due users must NOT be able to consume credits or generate paid
    features. Setting subscription_status="past_due" via webhook alone is
    not enough - the service gates must enforce it.
    """

    def test_check_and_deduct_credits_returns_402_for_past_due(self, mock_user_credits_storage, mocker):
        from app.api._helpers import check_and_deduct_credits
        from app.billing.models import UserCredits
        from fastapi import HTTPException
        import asyncio

        past_due = UserCredits(
            user_id="user_pd", plan="starter", credits_balance=40,
            credits_monthly_allowance=50, subscription_status="past_due",
        )
        # The conftest sync stub returns whatever get_or_create_credits returns.
        mock_user_credits_storage.get_or_create_credits.return_value = past_due

        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(check_and_deduct_credits(user_id="user_pd", action="chat_message"))
        assert exc_info.value.status_code == 402
        assert exc_info.value.detail["error"] == "subscription_past_due"
        mock_user_credits_storage.deduct_credits.assert_not_called()

    def test_design_doc_gate_returns_402_for_past_due(self, client_with_session, mock_user_credits_storage):
        from app.billing.models import UserCredits
        client, session_id = client_with_session
        past_due = UserCredits(
            user_id="local-dev-user", plan="starter", credits_balance=40,
            credits_monthly_allowance=50, subscription_status="past_due",
        )
        mock_user_credits_storage.get_or_create_credits.return_value = past_due

        response = client.post(f"/api/session/{session_id}/design-doc/generate", json={})
        assert response.status_code == 402
        assert response.json()["error"] == "subscription_past_due"

    def test_user_is_paid_returns_false_for_past_due(self, mocker):
        from app.billing.models import UserCredits
        past_due = UserCredits(
            user_id="user_pd", plan="starter", credits_balance=40,
            credits_monthly_allowance=50, subscription_status="past_due",
        )
        mocker.patch("app.sync.engine.sync_user_from_clerk", return_value=past_due)
        from app.sync.engine import _user_is_paid
        assert _user_is_paid("user_pd") is False

    def test_check_and_deduct_credits_returns_402_for_expired_plan(self, mock_user_credits_storage, mocker):
        # Defense in depth: even if Clerk sync silently fails, gates fail
        # closed when stored plan_expires_at is past.
        from datetime import datetime, timedelta
        from app.api._helpers import check_and_deduct_credits
        from app.billing.models import UserCredits
        from fastapi import HTTPException
        import asyncio

        expired = UserCredits(
            user_id="user_exp", plan="starter", credits_balance=40,
            credits_monthly_allowance=50, subscription_status="canceled",
            plan_expires_at=datetime.utcnow() - timedelta(hours=1),
        )
        mock_user_credits_storage.get_or_create_credits.return_value = expired

        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(check_and_deduct_credits(user_id="user_exp", action="chat_message"))
        assert exc_info.value.status_code == 402
        assert exc_info.value.detail["error"] == "subscription_expired"
        mock_user_credits_storage.deduct_credits.assert_not_called()

    def test_user_is_paid_returns_false_for_expired_plan(self, mocker):
        from datetime import datetime, timedelta
        from app.billing.models import UserCredits
        expired = UserCredits(
            user_id="user_exp", plan="starter", credits_balance=40,
            credits_monthly_allowance=50, subscription_status="canceled",
            plan_expires_at=datetime.utcnow() - timedelta(hours=1),
        )
        mocker.patch("app.sync.engine.sync_user_from_clerk", return_value=expired)
        from app.sync.engine import _user_is_paid
        assert _user_is_paid("user_exp") is False

    def test_active_paid_user_still_passes_all_gates(self, mock_user_credits_storage, mocker):
        # Sanity: past_due gating doesn't accidentally block legitimate paid users.
        from app.api._helpers import check_and_deduct_credits
        from app.billing.models import UserCredits
        import asyncio

        active = UserCredits(
            user_id="user_ok", plan="starter", credits_balance=50,
            credits_monthly_allowance=50, subscription_status="active",
        )
        mock_user_credits_storage.get_or_create_credits.return_value = active
        mock_user_credits_storage.deduct_credits.return_value = (True, active)

        cost = asyncio.run(check_and_deduct_credits(user_id="user_ok", action="chat_message"))
        assert cost > 0
        mock_user_credits_storage.deduct_credits.assert_called_once()


class TestSubscriptionItemUpdatedStatusRouting:
    """subscriptionItem.updated with status=canceled/ended must NOT call
    update_plan with the still-populated plan_id - that would re-enable
    service for a non-active item.
    """

    def test_updated_with_status_ended_downgrades(self, client, mock_user_credits_storage, monkeypatch):
        monkeypatch.delenv("CLERK_BILLING_WEBHOOK_SECRET", raising=False)
        payload = {
            "type": "subscriptionItem.updated",
            "data": {
                "subscription_id": "csub_x",
                "status": "ended",
                "plan_id": "cplan_3ASdFvizPo0JbVeethbsS7UfLjp",
                "payer": {"user_id": "user_ended_item_update"},
            },
        }
        response = client.post(
            "/api/webhooks/clerk-billing",
            content=json.dumps(payload),
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code == 200
        mock_user_credits_storage.update_plan.assert_called_once()
        assert mock_user_credits_storage.update_plan.call_args.kwargs["new_plan"] == "free"

    def test_updated_with_status_canceled_marks_pending(self, client, mock_user_credits_storage, monkeypatch):
        monkeypatch.delenv("CLERK_BILLING_WEBHOOK_SECRET", raising=False)
        payload = {
            "type": "subscriptionItem.updated",
            "data": {
                "subscription_id": "csub_y",
                "status": "canceled",
                "plan_id": "cplan_3ASdFvizPo0JbVeethbsS7UfLjp",
                "period_end": 1780591212670,
                "payer": {"user_id": "user_canceled_item_update"},
            },
        }
        response = client.post(
            "/api/webhooks/clerk-billing",
            content=json.dumps(payload),
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code == 200
        mock_user_credits_storage.update_plan.assert_not_called()
        mock_user_credits_storage.mark_pending_cancellation.assert_called_once()

    def test_updated_with_status_canceled_applies_grace_fallback_when_period_end_missing(self, client, mock_user_credits_storage, monkeypatch):
        # Regression: subscriptionItem.updated with status=canceled and no
        # period_end used to write plan_expires_at=None, leaving the user
        # canceled-with-no-expiry forever (gates passing because plan was
        # still paid).
        monkeypatch.delenv("CLERK_BILLING_WEBHOOK_SECRET", raising=False)
        payload = {
            "type": "subscriptionItem.updated",
            "data": {
                "subscription_id": "csub_no_period_end",
                "status": "canceled",
                "plan_id": "cplan_3ASdFvizPo0JbVeethbsS7UfLjp",
                "payer": {"user_id": "user_canceled_no_period_end"},
                # no period_end
            },
        }
        response = client.post(
            "/api/webhooks/clerk-billing",
            content=json.dumps(payload),
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code == 200
        mock_user_credits_storage.mark_pending_cancellation.assert_called_once()
        kwargs = mock_user_credits_storage.mark_pending_cancellation.call_args.kwargs
        # Must have a definite expiry, not None.
        assert kwargs["expires_at"] is not None

    def test_updated_with_status_past_due_marks_past_due_not_plan(self, client, mock_user_credits_storage, monkeypatch):
        # Regression: subscriptionItem.updated with status=past_due and a
        # plan_id used to fall through to update_plan and re-enable service.
        monkeypatch.delenv("CLERK_BILLING_WEBHOOK_SECRET", raising=False)
        payload = {
            "type": "subscriptionItem.updated",
            "data": {
                "subscription_id": "csub_pd_item",
                "status": "past_due",
                "plan_id": "cplan_3ASdFvizPo0JbVeethbsS7UfLjp",
                "payer": {"user_id": "user_pd_item_update"},
            },
        }
        response = client.post(
            "/api/webhooks/clerk-billing",
            content=json.dumps(payload),
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code == 200
        mock_user_credits_storage.update_plan.assert_not_called()
        mock_user_credits_storage.set_subscription_status.assert_called_once_with(
            "user_pd_item_update", "past_due"
        )

    def test_updated_with_status_active_still_applies_plan(self, client, mock_user_credits_storage, monkeypatch):
        # Regression guard: the new branching must not break the legitimate
        # path - active item with a plan_id should still update_plan.
        monkeypatch.delenv("CLERK_BILLING_WEBHOOK_SECRET", raising=False)
        payload = {
            "type": "subscriptionItem.updated",
            "data": {
                "subscription_id": "csub_z",
                "status": "active",
                "plan_id": "cplan_3ASdFvizPo0JbVeethbsS7UfLjp",
                "payer": {"user_id": "user_active_item_update"},
            },
        }
        response = client.post(
            "/api/webhooks/clerk-billing",
            content=json.dumps(payload),
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code == 200
        kwargs = mock_user_credits_storage.update_plan.call_args.kwargs
        assert kwargs["new_plan"] == "starter"


class TestGateSyncWiring:
    """Service gates must self-heal a paid user with a missed webhook before
    denying entitlement. Regression for finding: a paying user who never hit
    /user/credits first would be blocked from design docs / overcharged for
    chat because the gate read stored DynamoDB directly.
    """

    def test_check_and_deduct_credits_syncs_before_charging(self, mock_user_credits_storage, mocker):
        # The conftest patches sync to a transparent pass-through. Replace
        # it with an explicit spy so we can assert it's called BEFORE deduct.
        spy = MagicMock(side_effect=lambda user_id, force=False, gate_check=False: mock_user_credits_storage.get_or_create_credits(user_id))
        mocker.patch("app.api._helpers.sync_user_from_clerk", spy)

        from app.api._helpers import check_and_deduct_credits
        import asyncio
        asyncio.run(check_and_deduct_credits(user_id="user_x", action="chat_message"))

        # Gates must pass gate_check=True to use the tighter 1h throttle.
        spy.assert_called_once_with("user_x", gate_check=True)
        # deduct_credits must run AFTER sync, not before.
        deduct_call_order = mock_user_credits_storage.method_calls.index(
            [c for c in mock_user_credits_storage.method_calls if c[0] == "deduct_credits"][0]
        )
        # get_or_create_credits (called by sync stub) must precede deduct_credits.
        goc_indexes = [i for i, c in enumerate(mock_user_credits_storage.method_calls) if c[0] == "get_or_create_credits"]
        assert any(i < deduct_call_order for i in goc_indexes)

    def test_design_doc_gate_syncs_before_paid_plan_check(self, client_with_session, mock_user_credits_storage, mocker):
        # Wire a spy in place of the transparent stub so we can verify the
        # gate calls sync before reading user_credits.plan.
        from app.billing.models import UserCredits
        free_credits = UserCredits(
            user_id="local-dev-user", plan="free", credits_balance=10,
            credits_monthly_allowance=10,
        )
        mock_user_credits_storage.get_or_create_credits.return_value = free_credits
        spy = MagicMock(side_effect=lambda user_id, force=False, gate_check=False: mock_user_credits_storage.get_or_create_credits(user_id))
        mocker.patch("app.api.routes_design_docs.sync_user_from_clerk", spy)

        client, session_id = client_with_session
        response = client.post(f"/api/session/{session_id}/design-doc/generate", json={})

        assert response.status_code in (200, 403)  # 200 preview or 403 if used
        spy.assert_called_once_with("local-dev-user", gate_check=True)

    def test_auto_sync_eligibility_routes_through_sync(self, mocker):
        # _user_is_paid is the auto-sync gate. Must call sync_user_from_clerk
        # before reading plan, otherwise a paying user whose webhook missed
        # won't get auto-sync.
        from app.billing.models import UserCredits
        starter_credits = UserCredits(
            user_id="user_x", plan="starter", credits_balance=50,
            credits_monthly_allowance=50,
        )
        spy = MagicMock(return_value=starter_credits)
        mocker.patch("app.sync.engine.sync_user_from_clerk", spy)

        from app.sync.engine import _user_is_paid
        assert _user_is_paid("user_x") is True
        spy.assert_called_once_with("user_x", gate_check=True)


class TestAnalyzeRepoEndpoint:
    """POST /api/analyze-repo

    The body of _analyze_repo_background pulls in GitHub + Claude, neither of
    which we want to hit in tests. Just check the synchronous-path:
    invalid URL -> 400, valid URL -> session created and 202 returned.
    """

    def test_invalid_repo_url_returns_400(self, client, mock_user_credits_storage):
        from app.github.analyzer import GitHubAnalyzer

        with patch.object(GitHubAnalyzer, "parse_github_url", side_effect=ValueError("bad url")):
            response = client.post(
                "/api/analyze-repo",
                json={"repo_url": "not-a-url"},
            )
        assert response.status_code == 400
        assert "bad url" in response.json()["detail"]

    def test_valid_repo_url_creates_session(self, client, mock_user_credits_storage):
        from app.github.analyzer import GitHubAnalyzer

        with patch.object(GitHubAnalyzer, "parse_github_url", return_value=("acme", "widgets")), \
             patch.object(GitHubAnalyzer, "close"), \
             patch("app.api.routes_diagrams.session_manager.create_session_for_repo_analysis",
                   return_value="session-repo-123") as mock_create:
            response = client.post(
                "/api/analyze-repo",
                json={"repo_url": "https://github.com/acme/widgets"},
            )

        assert response.status_code == 200
        body = response.json()
        assert body["session_id"] == "session-repo-123"
        assert body["status"] in ("fetching", "analyzing", "generating", "queued", "in_progress")
        mock_create.assert_called_once()
