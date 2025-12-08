"""
Tests for rate limiting middleware.
"""

import pytest
import time
from fastapi.testclient import TestClient


class TestTokenBucketAlgorithm:
    """Tests for the token bucket rate limiting algorithm."""

    def test_rate_limit_allows_requests_under_limit(self, rate_limit_client):
        """Should allow requests when under the rate limit."""
        # rate_limit_app has burst_size=2, so first 2 requests should succeed
        response1 = rate_limit_client.get("/test")
        response2 = rate_limit_client.get("/test")

        assert response1.status_code == 200
        assert response2.status_code == 200

    def test_rate_limit_blocks_after_exhaustion(self, rate_limit_client):
        """Should return 429 when rate limit is exhausted."""
        # Exhaust the burst (2 requests)
        rate_limit_client.get("/test")
        rate_limit_client.get("/test")

        # Third request should be blocked
        response = rate_limit_client.get("/test")

        assert response.status_code == 429
        data = response.json()
        assert "rate limit" in data["error"].lower()

    def test_rate_limit_includes_retry_after_header(self, rate_limit_client):
        """Should include Retry-After header when rate limited."""
        # Exhaust the burst
        rate_limit_client.get("/test")
        rate_limit_client.get("/test")

        # Get rate limited response
        response = rate_limit_client.get("/test")

        assert response.status_code == 429
        assert "Retry-After" in response.headers
        retry_after = int(response.headers["Retry-After"])
        assert retry_after > 0

    def test_rate_limit_refills_over_time(self, rate_limit_client):
        """Should refill tokens over time allowing new requests."""
        # Exhaust the burst
        rate_limit_client.get("/test")
        rate_limit_client.get("/test")

        # Should be blocked
        response = rate_limit_client.get("/test")
        assert response.status_code == 429

        # Wait for token refill (rate is 10/min = 1 token per 6 seconds)
        # Wait enough time for at least 1 token
        time.sleep(7)

        # Should work again
        response = rate_limit_client.get("/test")
        assert response.status_code == 200

    def test_rate_limit_respects_burst_size(self, rate_limit_client):
        """Should allow burst_size requests immediately."""
        # rate_limit_app has burst_size=2
        responses = [rate_limit_client.get("/test") for _ in range(2)]

        # All should succeed
        assert all(r.status_code == 200 for r in responses)

        # Next one should fail
        response = rate_limit_client.get("/test")
        assert response.status_code == 429

    def test_rate_limit_includes_limit_headers(self, rate_limit_client):
        """Should include rate limit headers in response."""
        response = rate_limit_client.get("/test")

        assert response.status_code == 200
        assert "X-RateLimit-Limit" in response.headers
        assert "X-RateLimit-Remaining" in response.headers


class TestIPHandling:
    """Tests for IP address handling in rate limiting."""

    def test_rate_limit_uses_x_forwarded_for(self, rate_limit_client):
        """Should use X-Forwarded-For header for IP identification."""
        # Make requests from different "IPs"
        ip1_headers = {"X-Forwarded-For": "1.2.3.4"}
        ip2_headers = {"X-Forwarded-For": "5.6.7.8"}

        # Exhaust rate limit for IP1
        rate_limit_client.get("/test", headers=ip1_headers)
        rate_limit_client.get("/test", headers=ip1_headers)
        response_ip1 = rate_limit_client.get("/test", headers=ip1_headers)

        # IP1 should be blocked
        assert response_ip1.status_code == 429

        # IP2 should still work (separate bucket)
        response_ip2 = rate_limit_client.get("/test", headers=ip2_headers)
        assert response_ip2.status_code == 200

    def test_rate_limit_uses_x_real_ip(self, rate_limit_client):
        """Should use X-Real-IP header when X-Forwarded-For is not present."""
        ip1_headers = {"X-Real-IP": "10.0.0.1"}
        ip2_headers = {"X-Real-IP": "10.0.0.2"}

        # Exhaust rate limit for IP1
        rate_limit_client.get("/test", headers=ip1_headers)
        rate_limit_client.get("/test", headers=ip1_headers)
        response_ip1 = rate_limit_client.get("/test", headers=ip1_headers)

        assert response_ip1.status_code == 429

        # IP2 should work
        response_ip2 = rate_limit_client.get("/test", headers=ip2_headers)
        assert response_ip2.status_code == 200

    def test_rate_limit_tracks_separate_buckets_per_ip(self, rate_limit_client):
        """Should maintain separate rate limit buckets for each IP."""
        ips = ["1.1.1.1", "2.2.2.2", "3.3.3.3"]

        # Each IP should get its own burst allowance
        for ip in ips:
            headers = {"X-Forwarded-For": ip}
            response1 = rate_limit_client.get("/test", headers=headers)
            response2 = rate_limit_client.get("/test", headers=headers)

            assert response1.status_code == 200
            assert response2.status_code == 200


class TestEndpointExclusions:
    """Tests for endpoints excluded from rate limiting."""

    def test_rate_limit_skips_health_endpoint(self, rate_limit_client):
        """Should not rate limit /health endpoint."""
        # Make many requests to /health
        responses = [rate_limit_client.get("/health") for _ in range(10)]

        # All should succeed (no rate limiting)
        assert all(r.status_code == 200 for r in responses)

    def test_rate_limit_skips_root_endpoint(self, rate_limit_client):
        """Should not rate limit / endpoint."""
        # Make many requests to /
        responses = [rate_limit_client.get("/") for _ in range(10)]

        # All should succeed
        assert all(r.status_code == 200 for r in responses)

    def test_rate_limit_skips_options_requests(self, rate_limit_client):
        """Should not rate limit OPTIONS requests (CORS preflight)."""
        # Make many OPTIONS requests
        responses = [rate_limit_client.options("/test") for _ in range(10)]

        # All should succeed (might be 405 if not explicitly handled, but not 429)
        assert all(r.status_code != 429 for r in responses)
