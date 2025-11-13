"""
Optional API key authentication middleware.

Enable by setting REQUIRE_API_KEY=true in environment variables.
"""
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
import os
from typing import Set


class APIKeyMiddleware(BaseHTTPMiddleware):
    """
    Simple API key authentication middleware.

    Checks for API key in:
    1. X-API-Key header
    2. Authorization: Bearer <key> header
    3. api_key query parameter

    Enable by setting REQUIRE_API_KEY=true and providing VALID_API_KEYS.
    """

    def __init__(self, app):
        super().__init__(app)

        # Check if authentication is enabled
        self.enabled = os.getenv("REQUIRE_API_KEY", "false").lower() == "true"

        # Load valid API keys from environment
        api_keys_str = os.getenv("VALID_API_KEYS", "")
        self.valid_keys: Set[str] = set(
            key.strip() for key in api_keys_str.split(",") if key.strip()
        )

        if self.enabled and not self.valid_keys:
            raise ValueError(
                "REQUIRE_API_KEY is enabled but no VALID_API_KEYS provided. "
                "Set VALID_API_KEYS environment variable with comma-separated keys."
            )

        # Public endpoints that don't require authentication
        self.public_paths = {"/", "/health", "/docs", "/openapi.json", "/redoc"}

    def _extract_api_key(self, request: Request) -> str | None:
        """Extract API key from request."""
        # Check X-API-Key header
        api_key = request.headers.get("X-API-Key")
        if api_key:
            return api_key

        # Check Authorization header
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            return auth_header[7:]  # Remove "Bearer " prefix

        # Check query parameter
        api_key = request.query_params.get("api_key")
        if api_key:
            return api_key

        return None

    async def dispatch(self, request: Request, call_next):
        # Skip if authentication is disabled
        if not self.enabled:
            return await call_next(request)

        # Allow public paths
        if request.url.path in self.public_paths:
            return await call_next(request)

        # Extract and validate API key
        api_key = self._extract_api_key(request)

        if not api_key:
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={
                    "error": "Authentication required",
                    "message": "API key is required. Provide it via X-API-Key header, "
                               "Authorization: Bearer header, or api_key query parameter."
                },
                headers={"WWW-Authenticate": "ApiKey"}
            )

        if api_key not in self.valid_keys:
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={
                    "error": "Invalid API key",
                    "message": "The provided API key is not valid."
                }
            )

        # API key is valid, proceed with request
        return await call_next(request)
