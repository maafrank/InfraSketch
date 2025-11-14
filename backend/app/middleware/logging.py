"""
Middleware for automatic request/response logging.
Tracks all API calls with timing and user information.
"""

import time
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
from typing import Callable
from app.utils.logger import log_api_request


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware to log all API requests with timing and metadata"""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip logging for health check to reduce noise
        if request.url.path in ["/health", "/", "/favicon.ico"]:
            return await call_next(request)

        start_time = time.time()

        # Extract user IP (handle proxy headers)
        user_ip = (
            request.headers.get("X-Forwarded-For", "").split(",")[0].strip()
            or request.headers.get("X-Real-IP")
            or request.client.host if request.client else None
        )

        # Process request
        try:
            response = await call_next(request)
            duration_ms = (time.time() - start_time) * 1000

            # Extract session_id from request if present
            session_id = None
            if hasattr(request.state, "session_id"):
                session_id = request.state.session_id

            # Log the request
            log_api_request(
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
                duration_ms=duration_ms,
                user_ip=user_ip,
                session_id=session_id,
            )

            return response

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000

            # Log error
            log_api_request(
                method=request.method,
                path=request.url.path,
                status_code=500,
                duration_ms=duration_ms,
                user_ip=user_ip,
            )

            raise e
