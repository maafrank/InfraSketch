"""
Tests for Clerk authentication middleware.

Note: These tests must temporarily disable DISABLE_CLERK_AUTH to test real auth flow.
"""

import pytest
import os
import time
from unittest.mock import patch, MagicMock
from fastapi import FastAPI
from fastapi.testclient import TestClient
from contextlib import contextmanager


@contextmanager
def clerk_auth_enabled():
    """Context manager to temporarily enable Clerk auth for testing."""
    original = os.environ.get("DISABLE_CLERK_AUTH")
    if "DISABLE_CLERK_AUTH" in os.environ:
        del os.environ["DISABLE_CLERK_AUTH"]

    # Clear cached state in middleware module
    import app.middleware.clerk_auth as clerk_module
    clerk_module._jwks_cache = None
    clerk_module._jwks_cache_expiry = None

    try:
        yield
    finally:
        if original is not None:
            os.environ["DISABLE_CLERK_AUTH"] = original
        # Restore cache clearing
        clerk_module._jwks_cache = None
        clerk_module._jwks_cache_expiry = None


class TestTokenValidation:
    """Tests for JWT token validation."""

    def test_clerk_auth_accepts_valid_token(self, clerk_auth_test_keys, valid_clerk_token):
        """Should accept a valid JWT token and allow request."""
        with clerk_auth_enabled():
            from app.middleware.clerk_auth import ClerkAuthMiddleware

            # Create test app with Clerk auth
            app = FastAPI()
            app.add_middleware(ClerkAuthMiddleware)

            @app.get("/api/test")
            def test_endpoint():
                return {"status": "ok"}

            # Mock the JWKS fetch
            with patch("app.middleware.clerk_auth.requests.get") as mock_get:
                mock_response = MagicMock()
                mock_response.json.return_value = clerk_auth_test_keys["jwks"]
                mock_response.raise_for_status.return_value = None
                mock_get.return_value = mock_response

                client = TestClient(app)
                response = client.get(
                    "/api/test",
                    headers={"Authorization": f"Bearer {valid_clerk_token}"}
                )

                assert response.status_code == 200

    def test_clerk_auth_extracts_user_id(self, clerk_auth_test_keys, valid_clerk_token):
        """Should extract user_id from token and attach to request state."""
        with clerk_auth_enabled():
            from app.middleware.clerk_auth import ClerkAuthMiddleware
            from fastapi import Request

            app = FastAPI()
            app.add_middleware(ClerkAuthMiddleware)

            captured_user_id = None

            @app.get("/api/test")
            def test_endpoint(request: Request):
                nonlocal captured_user_id
                captured_user_id = request.state.user_id
                return {"user_id": captured_user_id}

            with patch("app.middleware.clerk_auth.requests.get") as mock_get:
                mock_response = MagicMock()
                mock_response.json.return_value = clerk_auth_test_keys["jwks"]
                mock_response.raise_for_status.return_value = None
                mock_get.return_value = mock_response

                client = TestClient(app)
                response = client.get(
                    "/api/test",
                    headers={"Authorization": f"Bearer {valid_clerk_token}"}
                )

                assert response.status_code == 200
                assert captured_user_id == "user_test_clerk_123"

    def test_clerk_auth_rejects_missing_auth_header(self):
        """Should return 401 when Authorization header is missing."""
        with clerk_auth_enabled():
            from app.middleware.clerk_auth import ClerkAuthMiddleware

            app = FastAPI()
            app.add_middleware(ClerkAuthMiddleware)

            @app.get("/api/test")
            def test_endpoint():
                return {"status": "ok"}

            client = TestClient(app)
            response = client.get("/api/test")

            assert response.status_code == 401
            assert "authorization" in response.json()["detail"].lower()

    def test_clerk_auth_rejects_malformed_header(self):
        """Should return 401 for malformed Authorization header."""
        with clerk_auth_enabled():
            from app.middleware.clerk_auth import ClerkAuthMiddleware

            app = FastAPI()
            app.add_middleware(ClerkAuthMiddleware)

            @app.get("/api/test")
            def test_endpoint():
                return {"status": "ok"}

            client = TestClient(app)

            # Test without "Bearer " prefix
            response = client.get(
                "/api/test",
                headers={"Authorization": "invalid-token"}
            )

            assert response.status_code == 401

    def test_clerk_auth_rejects_expired_token(self, clerk_auth_test_keys, expired_clerk_token):
        """Should return 401 for expired JWT token."""
        with clerk_auth_enabled():
            from app.middleware.clerk_auth import ClerkAuthMiddleware

            app = FastAPI()
            app.add_middleware(ClerkAuthMiddleware)

            @app.get("/api/test")
            def test_endpoint():
                return {"status": "ok"}

            with patch("app.middleware.clerk_auth.requests.get") as mock_get:
                mock_response = MagicMock()
                mock_response.json.return_value = clerk_auth_test_keys["jwks"]
                mock_response.raise_for_status.return_value = None
                mock_get.return_value = mock_response

                client = TestClient(app)
                response = client.get(
                    "/api/test",
                    headers={"Authorization": f"Bearer {expired_clerk_token}"}
                )

                assert response.status_code == 401
                assert "expired" in response.json()["detail"].lower()

    def test_clerk_auth_rejects_invalid_signature(self, clerk_auth_test_keys):
        """Should return 401 for token with invalid signature."""
        with clerk_auth_enabled():
            from app.middleware.clerk_auth import ClerkAuthMiddleware
            import jwt
            from cryptography.hazmat.primitives.asymmetric import rsa
            from cryptography.hazmat.backends import default_backend

            app = FastAPI()
            app.add_middleware(ClerkAuthMiddleware)

            @app.get("/api/test")
            def test_endpoint():
                return {"status": "ok"}

            # Create token signed with DIFFERENT key
            wrong_key = rsa.generate_private_key(
                public_exponent=65537,
                key_size=2048,
                backend=default_backend()
            )

            now = int(time.time())
            token = jwt.encode(
                {"sub": "user_123", "iss": "https://clerk.infrasketch.net", "iat": now, "exp": now + 3600},
                wrong_key,
                algorithm="RS256",
                headers={"kid": clerk_auth_test_keys["kid"]}
            )

            with patch("app.middleware.clerk_auth.requests.get") as mock_get:
                mock_response = MagicMock()
                mock_response.json.return_value = clerk_auth_test_keys["jwks"]
                mock_response.raise_for_status.return_value = None
                mock_get.return_value = mock_response

                client = TestClient(app)
                response = client.get(
                    "/api/test",
                    headers={"Authorization": f"Bearer {token}"}
                )

                assert response.status_code == 401

    def test_clerk_auth_rejects_unknown_kid(self, clerk_auth_test_keys):
        """Should return 401 when token kid doesn't match any JWKS key."""
        with clerk_auth_enabled():
            from app.middleware.clerk_auth import ClerkAuthMiddleware
            import jwt

            app = FastAPI()
            app.add_middleware(ClerkAuthMiddleware)

            @app.get("/api/test")
            def test_endpoint():
                return {"status": "ok"}

            # Create token with unknown kid
            now = int(time.time())
            token = jwt.encode(
                {"sub": "user_123", "iss": "https://clerk.infrasketch.net", "iat": now, "exp": now + 3600},
                clerk_auth_test_keys["private_key"],
                algorithm="RS256",
                headers={"kid": "unknown-kid-xyz"}
            )

            with patch("app.middleware.clerk_auth.requests.get") as mock_get:
                mock_response = MagicMock()
                mock_response.json.return_value = clerk_auth_test_keys["jwks"]
                mock_response.raise_for_status.return_value = None
                mock_get.return_value = mock_response

                client = TestClient(app)
                response = client.get(
                    "/api/test",
                    headers={"Authorization": f"Bearer {token}"}
                )

                assert response.status_code == 401
                assert "kid" in response.json()["detail"].lower()

    def test_clerk_auth_handles_jwks_fetch_failure(self):
        """Should return 503 when JWKS fetch fails."""
        with clerk_auth_enabled():
            from app.middleware.clerk_auth import ClerkAuthMiddleware

            app = FastAPI()
            app.add_middleware(ClerkAuthMiddleware)

            @app.get("/api/test")
            def test_endpoint():
                return {"status": "ok"}

            with patch("app.middleware.clerk_auth.requests.get") as mock_get:
                mock_get.side_effect = Exception("Network error")

                client = TestClient(app)
                response = client.get(
                    "/api/test",
                    headers={"Authorization": "Bearer some-token"}
                )

                assert response.status_code == 503


class TestJWKSCaching:
    """Tests for JWKS caching behavior."""

    def test_clerk_auth_caches_jwks(self, clerk_auth_test_keys, valid_clerk_token):
        """Should cache JWKS and not fetch on every request."""
        with clerk_auth_enabled():
            from app.middleware.clerk_auth import ClerkAuthMiddleware

            app = FastAPI()
            app.add_middleware(ClerkAuthMiddleware)

            @app.get("/api/test")
            def test_endpoint():
                return {"status": "ok"}

            with patch("app.middleware.clerk_auth.requests.get") as mock_get:
                mock_response = MagicMock()
                mock_response.json.return_value = clerk_auth_test_keys["jwks"]
                mock_response.raise_for_status.return_value = None
                mock_get.return_value = mock_response

                client = TestClient(app)

                # Make multiple requests
                client.get("/api/test", headers={"Authorization": f"Bearer {valid_clerk_token}"})
                client.get("/api/test", headers={"Authorization": f"Bearer {valid_clerk_token}"})
                client.get("/api/test", headers={"Authorization": f"Bearer {valid_clerk_token}"})

                # Should only fetch JWKS once (cached)
                assert mock_get.call_count == 1


class TestPublicEndpoints:
    """Tests for endpoints excluded from authentication."""

    def test_clerk_auth_skips_health_endpoint(self):
        """Should not require auth for /health endpoint."""
        from app.middleware.clerk_auth import ClerkAuthMiddleware

        app = FastAPI()
        app.add_middleware(ClerkAuthMiddleware)

        @app.get("/health")
        def health():
            return {"status": "healthy"}

        client = TestClient(app)
        response = client.get("/health")

        assert response.status_code == 200

    def test_clerk_auth_skips_docs_endpoint(self):
        """Should not require auth for /docs endpoint."""
        from app.middleware.clerk_auth import ClerkAuthMiddleware

        app = FastAPI()
        app.add_middleware(ClerkAuthMiddleware)

        client = TestClient(app)
        response = client.get("/docs")

        # Docs endpoint returns 200 or redirects
        assert response.status_code in [200, 307]

    def test_clerk_auth_skips_unsubscribe_paths(self):
        """Should not require auth for unsubscribe paths."""
        from app.middleware.clerk_auth import ClerkAuthMiddleware

        app = FastAPI()
        app.add_middleware(ClerkAuthMiddleware)

        @app.get("/api/unsubscribe/{token}")
        def unsubscribe(token: str):
            return {"token": token}

        client = TestClient(app)
        response = client.get("/api/unsubscribe/some-token")

        assert response.status_code == 200

    def test_clerk_auth_skips_options_requests(self):
        """Should not require auth for OPTIONS requests (CORS preflight)."""
        from app.middleware.clerk_auth import ClerkAuthMiddleware

        app = FastAPI()
        app.add_middleware(ClerkAuthMiddleware)

        @app.get("/api/test")
        def test_endpoint():
            return {"status": "ok"}

        client = TestClient(app)
        response = client.options("/api/test")

        # Should not be 401 (might be 405 if no explicit OPTIONS handler)
        assert response.status_code != 401


class TestDevelopmentMode:
    """Tests for development mode with auth disabled."""

    def test_clerk_auth_disabled_sets_dummy_user(self):
        """Should set dummy user_id when DISABLE_CLERK_AUTH=true."""
        from app.middleware.clerk_auth import ClerkAuthMiddleware
        from fastapi import Request

        # Temporarily set env var
        original = os.environ.get("DISABLE_CLERK_AUTH")
        os.environ["DISABLE_CLERK_AUTH"] = "true"

        try:
            app = FastAPI()
            app.add_middleware(ClerkAuthMiddleware)

            captured_user_id = None

            @app.get("/api/test")
            def test_endpoint(request: Request):
                nonlocal captured_user_id
                captured_user_id = request.state.user_id
                return {"user_id": captured_user_id}

            client = TestClient(app)
            response = client.get("/api/test")

            assert response.status_code == 200
            assert captured_user_id == "local-dev-user"
        finally:
            # Restore original
            if original is not None:
                os.environ["DISABLE_CLERK_AUTH"] = original
            elif "DISABLE_CLERK_AUTH" in os.environ:
                del os.environ["DISABLE_CLERK_AUTH"]
