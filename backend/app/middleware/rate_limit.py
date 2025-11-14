"""
Rate limiting middleware for FastAPI.
Implements a simple in-memory token bucket algorithm.
"""
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from collections import defaultdict
from datetime import datetime, timedelta
import time
from typing import Dict, Tuple


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Simple in-memory rate limiter using token bucket algorithm.

    Note: This is in-memory only and will reset on server restart.
    For production with multiple instances, consider Redis-based rate limiting.
    """

    def __init__(
        self,
        app,
        requests_per_minute: int = 60,
        burst_size: int = 10,
    ):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.burst_size = burst_size
        self.rate_per_second = requests_per_minute / 60.0

        # Store: {ip: (tokens, last_update)}
        self.buckets: Dict[str, Tuple[float, float]] = defaultdict(
            lambda: (self.burst_size, time.time())
        )

    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP, considering proxies."""
        # Check for CloudFront/API Gateway headers
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()

        # Check for standard proxy headers
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip

        # Fallback to direct connection
        if request.client:
            return request.client.host

        return "unknown"

    def _refill_bucket(self, ip: str) -> Tuple[float, float]:
        """Refill tokens based on time passed."""
        tokens, last_update = self.buckets[ip]
        now = time.time()
        time_passed = now - last_update

        # Add tokens based on rate
        new_tokens = min(
            self.burst_size,
            tokens + (time_passed * self.rate_per_second)
        )

        return new_tokens, now

    async def dispatch(self, request: Request, call_next):
        # Skip rate limiting for health checks and OPTIONS (CORS preflight)
        if request.url.path in ["/health", "/"] or request.method == "OPTIONS":
            return await call_next(request)

        client_ip = self._get_client_ip(request)

        # Refill bucket
        tokens, now = self._refill_bucket(client_ip)

        # Check if we have tokens
        if tokens < 1.0:
            # Calculate retry after time
            retry_after = int((1.0 - tokens) / self.rate_per_second) + 1

            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "error": "Rate limit exceeded",
                    "message": f"Too many requests. Please try again in {retry_after} seconds.",
                    "retry_after": retry_after
                },
                headers={"Retry-After": str(retry_after)}
            )

        # Consume one token
        self.buckets[client_ip] = (tokens - 1.0, now)

        # Process request
        response = await call_next(request)

        # Add rate limit headers
        response.headers["X-RateLimit-Limit"] = str(self.requests_per_minute)
        response.headers["X-RateLimit-Remaining"] = str(int(tokens - 1))

        return response
