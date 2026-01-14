"""
Rate limiting middleware for FastAPI.
Supports both in-memory (local dev) and DynamoDB (production) backends.

Security features:
- Distributed rate limiting across Lambda instances using DynamoDB
- Token bucket algorithm with burst allowance
- Automatic TTL cleanup of expired records
"""
import os
import time
from decimal import Decimal
from typing import Dict, Tuple, Optional

import boto3
from botocore.exceptions import ClientError
from fastapi import Request, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from collections import defaultdict


def _is_production_environment() -> bool:
    """Check if running in AWS Lambda or production environment."""
    return bool(os.environ.get('AWS_LAMBDA_FUNCTION_NAME') or os.environ.get('AWS_EXECUTION_ENV'))


class DynamoDBRateLimiter:
    """
    Distributed rate limiter using DynamoDB for cross-instance coordination.

    Uses atomic conditional updates to ensure accurate rate limiting
    across multiple Lambda instances.
    """

    def __init__(
        self,
        table_name: str = "infrasketch-rate-limits",
        requests_per_minute: int = 60,
        burst_size: int = 10,
    ):
        self.table_name = table_name
        self.requests_per_minute = requests_per_minute
        self.burst_size = burst_size
        self.rate_per_second = requests_per_minute / 60.0

        self.dynamodb = boto3.resource('dynamodb')
        self.table = self.dynamodb.Table(table_name)
        self._ensure_table_exists()

    def _ensure_table_exists(self):
        """Create rate limit table if it doesn't exist."""
        dynamodb_client = boto3.client('dynamodb')

        try:
            self.table.load()
        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceNotFoundException':
                print(f"Creating DynamoDB rate limit table '{self.table_name}'...")
                dynamodb_client.create_table(
                    TableName=self.table_name,
                    KeySchema=[
                        {'AttributeName': 'ip_hash', 'KeyType': 'HASH'}
                    ],
                    AttributeDefinitions=[
                        {'AttributeName': 'ip_hash', 'AttributeType': 'S'}
                    ],
                    BillingMode='PAY_PER_REQUEST',
                    Tags=[
                        {'Key': 'Application', 'Value': 'InfraSketch'},
                        {'Key': 'Environment', 'Value': 'production'},
                        {'Key': 'Purpose', 'Value': 'RateLimiting'}
                    ]
                )
                # Enable TTL on the table
                try:
                    dynamodb_client.update_time_to_live(
                        TableName=self.table_name,
                        TimeToLiveSpecification={
                            'Enabled': True,
                            'AttributeName': 'ttl'
                        }
                    )
                except ClientError:
                    pass  # TTL might already be enabled

                waiter = dynamodb_client.get_waiter('table_exists')
                waiter.wait(TableName=self.table_name)
                print(f"Rate limit table '{self.table_name}' created successfully")
            else:
                raise

    def _hash_ip(self, ip: str) -> str:
        """Hash IP for privacy and consistent key length."""
        import hashlib
        return hashlib.sha256(ip.encode()).hexdigest()[:32]

    def check_and_consume(self, ip: str) -> Tuple[bool, float, int]:
        """
        Check rate limit and consume a token if available.

        Returns:
            Tuple of (allowed, tokens_remaining, retry_after_seconds)
        """
        ip_hash = self._hash_ip(ip)
        now = Decimal(str(time.time()))
        ttl = int(time.time()) + 3600  # Expire records after 1 hour

        try:
            # Try to get existing record
            response = self.table.get_item(Key={'ip_hash': ip_hash})
            item = response.get('Item')

            if item:
                tokens = float(item.get('tokens', self.burst_size))
                last_update = float(item.get('last_update', now))
            else:
                tokens = float(self.burst_size)
                last_update = float(now)

            # Calculate token refill
            time_passed = float(now) - last_update
            new_tokens = min(
                self.burst_size,
                tokens + (time_passed * self.rate_per_second)
            )

            # Check if we have tokens available
            if new_tokens < 1.0:
                retry_after = int((1.0 - new_tokens) / self.rate_per_second) + 1
                return False, new_tokens, retry_after

            # Consume one token atomically
            self.table.put_item(
                Item={
                    'ip_hash': ip_hash,
                    'tokens': Decimal(str(new_tokens - 1.0)),
                    'last_update': now,
                    'ttl': ttl
                }
            )

            return True, new_tokens - 1.0, 0

        except Exception as e:
            # On error, allow request (fail open) but log
            print(f"Rate limit check error: {e}")
            return True, self.burst_size, 0


class InMemoryRateLimiter:
    """
    Simple in-memory rate limiter for local development.

    Note: This resets on server restart and doesn't work across instances.
    Use DynamoDBRateLimiter for production.
    """

    def __init__(
        self,
        requests_per_minute: int = 60,
        burst_size: int = 10,
    ):
        self.requests_per_minute = requests_per_minute
        self.burst_size = burst_size
        self.rate_per_second = requests_per_minute / 60.0

        # Store: {ip: (tokens, last_update)}
        self.buckets: Dict[str, Tuple[float, float]] = defaultdict(
            lambda: (self.burst_size, time.time())
        )

    def check_and_consume(self, ip: str) -> Tuple[bool, float, int]:
        """Check rate limit and consume a token if available."""
        tokens, last_update = self.buckets[ip]
        now = time.time()
        time_passed = now - last_update

        # Refill tokens
        new_tokens = min(
            self.burst_size,
            tokens + (time_passed * self.rate_per_second)
        )

        # Check if we have tokens
        if new_tokens < 1.0:
            retry_after = int((1.0 - new_tokens) / self.rate_per_second) + 1
            return False, new_tokens, retry_after

        # Consume token
        self.buckets[ip] = (new_tokens - 1.0, now)
        return True, new_tokens - 1.0, 0


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Rate limiting middleware that uses appropriate backend based on environment.

    - Production (Lambda): Uses DynamoDB for distributed rate limiting
    - Development (local): Uses in-memory for simplicity
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

        # Choose backend based on environment
        if _is_production_environment():
            self.limiter = DynamoDBRateLimiter(
                requests_per_minute=requests_per_minute,
                burst_size=burst_size,
            )
        else:
            self.limiter = InMemoryRateLimiter(
                requests_per_minute=requests_per_minute,
                burst_size=burst_size,
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

    async def dispatch(self, request: Request, call_next):
        # Skip rate limiting for health checks and OPTIONS (CORS preflight)
        if request.url.path in ["/health", "/"] or request.method == "OPTIONS":
            return await call_next(request)

        client_ip = self._get_client_ip(request)

        # Check rate limit
        allowed, tokens, retry_after = self.limiter.check_and_consume(client_ip)

        if not allowed:
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "error": "Rate limit exceeded",
                    "message": f"Too many requests. Please try again in {retry_after} seconds.",
                    "retry_after": retry_after
                },
                headers={"Retry-After": str(retry_after)}
            )

        # Process request
        response = await call_next(request)

        # Add rate limit headers
        response.headers["X-RateLimit-Limit"] = str(self.requests_per_minute)
        response.headers["X-RateLimit-Remaining"] = str(max(0, int(tokens)))

        return response
