"""
Tests for subscription endpoints:
- POST /api/subscribe
- GET /api/subscription/status
- POST /api/unsubscribe
- GET /api/unsubscribe/{token}
- GET /api/resubscribe/{token}
"""

import pytest
from fastapi.testclient import TestClient


class TestSubscribe:
    """Tests for POST /api/subscribe"""

    def test_subscribe_creates_subscriber(self, client, mock_subscriber_storage):
        """Should create a new subscriber."""
        response = client.post(
            "/api/subscribe",
            json={"email": "newuser@example.com"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["subscribed"] is True
        assert "email" in data

    def test_subscribe_calls_storage(self, client, mock_subscriber_storage):
        """Should call storage to create subscriber."""
        email = "test@example.com"

        response = client.post(
            "/api/subscribe",
            json={"email": email}
        )

        assert response.status_code == 200
        mock_subscriber_storage.create_subscriber.assert_called_once()


class TestSubscriptionStatus:
    """Tests for GET /api/subscription/status"""

    def test_subscription_status_returns_subscribed(self, client, mock_subscriber_storage):
        """Should return subscribed=True for subscribed user."""
        response = client.get("/api/subscription/status")

        assert response.status_code == 200
        data = response.json()
        assert data["subscribed"] is True
        assert "email" in data

    def test_subscription_status_returns_not_subscribed(self, client, mock_subscriber_storage):
        """Should return subscribed=False for non-subscriber."""
        # Mock storage to return None (no subscriber)
        mock_subscriber_storage.get_subscriber.return_value = None

        response = client.get("/api/subscription/status")

        assert response.status_code == 200
        data = response.json()
        assert data["subscribed"] is False


class TestUnsubscribe:
    """Tests for POST /api/unsubscribe"""

    def test_unsubscribe_removes_subscription(self, client, mock_subscriber_storage):
        """Should unsubscribe the user."""
        response = client.post("/api/unsubscribe")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        mock_subscriber_storage.unsubscribe.assert_called_once()

    def test_unsubscribe_returns_404_for_nonexistent(self, client, mock_subscriber_storage):
        """Should return 404 for non-subscriber."""
        mock_subscriber_storage.unsubscribe.return_value = False

        response = client.post("/api/unsubscribe")

        assert response.status_code == 404


class TestUnsubscribeViaToken:
    """Tests for GET /api/unsubscribe/{token}"""

    def test_unsubscribe_via_token_returns_html(self, client, mock_subscriber_storage):
        """Should return HTML confirmation page."""
        response = client.get("/api/unsubscribe/test-token-abc123")

        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        assert "unsubscribed" in response.text.lower()

    def test_unsubscribe_via_token_returns_404_invalid(self, client, mock_subscriber_storage):
        """Should return 404 HTML for invalid token."""
        mock_subscriber_storage.get_subscriber_by_token.return_value = None

        response = client.get("/api/unsubscribe/invalid-token")

        assert response.status_code == 404
        assert "text/html" in response.headers["content-type"]
        assert "invalid" in response.text.lower()


class TestResubscribeViaToken:
    """Tests for GET /api/resubscribe/{token}"""

    def test_resubscribe_via_token_returns_html(self, client, mock_subscriber_storage):
        """Should return HTML confirmation page."""
        response = client.get("/api/resubscribe/test-token-abc123")

        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        assert "re-subscribed" in response.text.lower()

    def test_resubscribe_via_token_returns_404_invalid(self, client, mock_subscriber_storage):
        """Should return 404 HTML for invalid token."""
        mock_subscriber_storage.get_subscriber_by_token.return_value = None

        response = client.get("/api/resubscribe/invalid-token")

        assert response.status_code == 404
        assert "text/html" in response.headers["content-type"]
