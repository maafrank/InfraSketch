"""
Clerk JWT Authentication Middleware

This middleware validates Clerk-issued JWT tokens on every request.
It fetches Clerk's public keys (JWKS), validates the token signature,
and extracts the user_id from the validated token.

Flow:
1. Extract JWT from Authorization header
2. Fetch Clerk's public keys (cached for 1 hour)
3. Validate token signature and claims
4. Attach user_id to request.state for use in routes
5. Return 401 if token is missing/invalid
"""

import os
import jwt
import requests
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from app.utils.logger import log_event, EventType


# Clerk domain extracted from publishable key
# Production: pk_live_Y2xlcmsuaW5mcmFza2V0Y2gubmV0JA decodes to "clerk.infrasketch.net$"
# Development: pk_test_YmlnLWdpYmJvbi02MS5jbGVyay5hY2NvdW50cy5kZXYk decodes to "big-gibbon-61.clerk.accounts.dev$"
CLERK_DOMAIN = os.getenv("CLERK_DOMAIN", "clerk.infrasketch.net")
JWKS_URL = f"https://{CLERK_DOMAIN}/.well-known/jwks.json"

# Cache for Clerk's public keys (JWKS)
_jwks_cache: Optional[Dict[str, Any]] = None
_jwks_cache_expiry: Optional[datetime] = None
JWKS_CACHE_TTL = timedelta(hours=1)  # Refresh keys every hour


class ClerkAuthMiddleware(BaseHTTPMiddleware):
    """
    Middleware to validate Clerk JWT tokens on all requests.

    Exempts public endpoints like /health, /, /docs from authentication.
    Can be disabled via DISABLE_CLERK_AUTH=true environment variable.
    """

    # Endpoints that don't require authentication
    PUBLIC_PATHS = {
        "/",
        "/health",
        "/docs",
        "/openapi.json",
        "/redoc",
    }

    # Path prefixes that don't require authentication
    PUBLIC_PATH_PREFIXES = [
        "/api/unsubscribe/",  # Email unsubscribe links (token-based auth)
        "/api/resubscribe/",  # Email re-subscribe links (token-based auth)
        "/api/webhooks/",  # Webhook endpoints (use signature verification instead)
    ]

    async def dispatch(self, request: Request, call_next):
        """
        Process each request and validate JWT token.
        """
        # Check if Clerk auth is disabled (for local development)
        if os.getenv("DISABLE_CLERK_AUTH", "false").lower() == "true":
            # Set a dummy user_id for local development
            request.state.user_id = "local-dev-user"
            return await call_next(request)

        # Skip auth for public endpoints
        if request.url.path in self.PUBLIC_PATHS:
            return await call_next(request)

        # Skip auth for public path prefixes (like unsubscribe links)
        for prefix in self.PUBLIC_PATH_PREFIXES:
            if request.url.path.startswith(prefix):
                return await call_next(request)

        # Skip auth for CORS preflight requests (OPTIONS method)
        if request.method == "OPTIONS":
            return await call_next(request)

        # Extract JWT from Authorization header
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            log_event(
                EventType.API_ERROR,
                metadata={
                    "error": "Missing or invalid Authorization header",
                    "path": request.url.path,
                    "method": request.method
                }
            )
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "Missing or invalid Authorization header"}
            )

        token = auth_header.replace("Bearer ", "")

        # Validate token and extract user_id
        try:
            user_id = await self.validate_clerk_token(token)
            # Attach user_id to request state for use in routes
            request.state.user_id = user_id
        except HTTPException as e:
            log_event(
                EventType.API_ERROR,
                metadata={
                    "error": f"Token validation failed: {e.detail}",
                    "path": request.url.path,
                    "method": request.method
                }
            )
            return JSONResponse(
                status_code=e.status_code,
                content={"detail": e.detail}
            )
        except Exception as e:
            log_event(
                EventType.API_ERROR,
                metadata={
                    "error": f"Unexpected auth error: {str(e)}",
                    "path": request.url.path,
                    "method": request.method
                }
            )
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={"detail": "Internal authentication error"}
            )

        # Continue to the route handler
        response = await call_next(request)
        return response

    async def validate_clerk_token(self, token: str) -> str:
        """
        Validate Clerk JWT token and return user_id.

        Args:
            token: JWT token string

        Returns:
            user_id: Clerk user ID (subject claim)

        Raises:
            HTTPException: If token is invalid
        """
        global _jwks_cache, _jwks_cache_expiry

        # Get JWKS (Clerk's public keys)
        if _jwks_cache is None or _jwks_cache_expiry is None or datetime.now() > _jwks_cache_expiry:
            # Fetch fresh JWKS
            try:
                response = requests.get(JWKS_URL, timeout=5)
                response.raise_for_status()
                _jwks_cache = response.json()
                _jwks_cache_expiry = datetime.now() + JWKS_CACHE_TTL
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail=f"Failed to fetch Clerk public keys: {str(e)}"
                )

        # Decode token header to get key ID (kid)
        try:
            unverified_header = jwt.get_unverified_header(token)
            kid = unverified_header.get("kid")
            if not kid:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token missing key ID (kid)"
                )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid token format: {str(e)}"
            )

        # Find the matching public key
        public_key = None
        for key in _jwks_cache.get("keys", []):
            if key.get("kid") == kid:
                # Convert JWK to PEM format for PyJWT
                public_key = jwt.algorithms.RSAAlgorithm.from_jwk(key)
                break

        if not public_key:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token key ID (kid) not found in Clerk JWKS"
            )

        # Validate token signature and claims
        try:
            payload = jwt.decode(
                token,
                public_key,
                algorithms=["RS256"],
                # Verify issuer matches Clerk domain
                issuer=f"https://{CLERK_DOMAIN}",
                # Skip audience verification (Clerk tokens don't always include aud)
                options={"verify_aud": False}
            )

            # Extract user_id from subject claim
            user_id = payload.get("sub")
            if not user_id:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token missing subject (user_id)"
                )

            return user_id

        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired"
            )
        except jwt.InvalidTokenError as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid token: {str(e)}"
            )
