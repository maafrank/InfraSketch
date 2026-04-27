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
