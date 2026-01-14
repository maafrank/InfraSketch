"""
Clerk JWT Authentication Middleware

This middleware validates Clerk-issued JWT tokens on every request.
It fetches Clerk's public keys (JWKS), validates the token signature,
and extracts the user_id from the validated token.

Flow:
1. Extract JWT from Authorization header
2. Fetch Clerk's public keys (cached for 15 minutes)
3. Validate token signature and claims
4. Attach user_id to request.state for use in routes
5. Return 401 if token is missing/invalid

Security Notes:
- DISABLE_CLERK_AUTH is blocked in Lambda/production environments
- Error messages are generic to avoid leaking JWT internals
- JWKS cache uses asyncio.Lock for thread safety
"""

import os
import asyncio
import jwt
import requests
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from app.utils.logger import log_event, EventType


# Security: Prevent auth bypass in production
def _is_production_environment() -> bool:
    """Check if running in AWS Lambda or production environment."""
    return bool(os.environ.get('AWS_LAMBDA_FUNCTION_NAME') or os.environ.get('AWS_EXECUTION_ENV'))


def _get_cors_headers(request: Request) -> dict:
    """
    Get CORS headers based on request origin.

    This is needed because when middleware returns early (before call_next),
    the CORS middleware doesn't get a chance to add headers to the response.
    """
    origin = request.headers.get("origin", "")
    # Only return CORS headers for allowed origins
    allowed_origins = [
        "https://dr6smezctn6x0.cloudfront.net",
        "https://infrasketch.net",
        "https://www.infrasketch.net",
    ]
    # Add localhost for development
    for port in range(5173, 5191):
        allowed_origins.append(f"http://localhost:{port}")
        allowed_origins.append(f"http://127.0.0.1:{port}")

    if origin in allowed_origins:
        return {
            "Access-Control-Allow-Origin": origin,
            "Access-Control-Allow-Credentials": "true",
        }
    return {}


# Clerk domain extracted from publishable key
# Production: pk_live_Y2xlcmsuaW5mcmFza2V0Y2gubmV0JA decodes to "clerk.infrasketch.net$"
# Development: pk_test_YmlnLWdpYmJvbi02MS5jbGVyay5hY2NvdW50cy5kZXYk decodes to "big-gibbon-61.clerk.accounts.dev$"
CLERK_DOMAIN = os.getenv("CLERK_DOMAIN", "clerk.infrasketch.net")
JWKS_URL = f"https://{CLERK_DOMAIN}/.well-known/jwks.json"

# Cache for Clerk's public keys (JWKS)
_jwks_cache: Optional[Dict[str, Any]] = None
_jwks_cache_expiry: Optional[datetime] = None
_jwks_cache_lock: asyncio.Lock = asyncio.Lock()
JWKS_CACHE_TTL = timedelta(minutes=15)  # Refresh keys every 15 minutes (security best practice)


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
        "/api/badges/",  # Badge images (public, no auth required)
    ]

    async def dispatch(self, request: Request, call_next):
        """
        Process each request and validate JWT token.
        """
        # Check if Clerk auth is disabled (for local development ONLY)
        # SECURITY: This bypass is blocked in production/Lambda environments
        if os.getenv("DISABLE_CLERK_AUTH", "false").lower() == "true":
            if _is_production_environment():
                # Log critical security warning and reject the bypass attempt
                log_event(
                    EventType.API_ERROR,
                    metadata={
                        "error": "CRITICAL: DISABLE_CLERK_AUTH attempted in production - blocked",
                        "path": request.url.path,
                        "method": request.method
                    }
                )
                # Do NOT bypass auth in production, continue with normal validation
            else:
                # Local development only - set a dummy user_id
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
                content={"detail": "Missing or invalid Authorization header"},
                headers=_get_cors_headers(request)
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
                content={"detail": e.detail},
                headers=_get_cors_headers(request)
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
                content={"detail": "Internal authentication error"},
                headers=_get_cors_headers(request)
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

        # Get JWKS (Clerk's public keys) with thread-safe locking
        async with _jwks_cache_lock:
            if _jwks_cache is None or _jwks_cache_expiry is None or datetime.now() > _jwks_cache_expiry:
                # Fetch fresh JWKS
                try:
                    response = requests.get(JWKS_URL, timeout=5)
                    response.raise_for_status()
                    _jwks_cache = response.json()
                    _jwks_cache_expiry = datetime.now() + JWKS_CACHE_TTL
                except Exception as e:
                    # Log detailed error internally, return generic message
                    log_event(
                        EventType.API_ERROR,
                        metadata={"error": f"JWKS fetch failed: {str(e)}"}
                    )
                    raise HTTPException(
                        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                        detail="Authentication service temporarily unavailable"
                    )

        # Decode token header to get key ID (kid)
        try:
            unverified_header = jwt.get_unverified_header(token)
            kid = unverified_header.get("kid")
            if not kid:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid or expired authentication token"
                )
        except jwt.exceptions.DecodeError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired authentication token"
            )
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired authentication token"
            )

        # Find the matching public key
        public_key = None
        for key in _jwks_cache.get("keys", []):
            if key.get("kid") == kid:
                # Convert JWK to PEM format for PyJWT
                public_key = jwt.algorithms.RSAAlgorithm.from_jwk(key)
                break

        if not public_key:
            # Key not found - could be rotated, try refreshing cache once
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired authentication token"
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
                    detail="Invalid or expired authentication token"
                )

            return user_id

        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired authentication token"
            )
        except jwt.InvalidTokenError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired authentication token"
            )
