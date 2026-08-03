"""
Tests for GitHub API authentication and rate-limit handling.

Unauthenticated, GitHub allows 60 requests/hour per IP. Every Lambda invocation
shares an egress IP, so an unauthenticated analyzer burns a quota shared by all
users. These tests pin the token plumbing and the rate-limit detection that
tells us when it has run out.
"""

import pytest
from unittest.mock import MagicMock, patch

from app.github.analyzer import GitHubAnalyzer, GitHubRateLimitError
from app.utils.secrets import get_github_token


def _response(status_code: int, headers: dict = None) -> MagicMock:
    """Minimal httpx.Response stand-in for _check_rate_limit."""
    response = MagicMock()
    response.status_code = status_code
    response.headers = headers or {}
    return response


@pytest.fixture(autouse=True)
def clear_token_cache():
    """get_github_token is lru_cached, so each test needs a clean slate."""
    get_github_token.cache_clear()
    yield
    get_github_token.cache_clear()


class TestGetGitHubToken:
    """Tests for app.utils.secrets.get_github_token"""

    def test_returns_none_when_not_configured(self):
        """Missing token must not raise: analysis still works unauthenticated."""
        with patch("app.utils.secrets.get_secret", side_effect=ValueError("not found")):
            assert get_github_token() is None

    def test_returns_token_when_configured(self):
        with patch("app.utils.secrets.get_secret", return_value="ghp_realtoken"):
            assert get_github_token() == "ghp_realtoken"

    def test_strips_whitespace(self):
        """A trailing newline from Secrets Manager would corrupt the auth header."""
        with patch("app.utils.secrets.get_secret", return_value="  ghp_realtoken\n"):
            assert get_github_token() == "ghp_realtoken"

    def test_treats_blank_token_as_missing(self):
        with patch("app.utils.secrets.get_secret", return_value="   "):
            assert get_github_token() is None

    def test_is_cached(self):
        """Read once per warm container, not once per API call."""
        with patch("app.utils.secrets.get_secret", return_value="ghp_realtoken") as mock_secret:
            get_github_token()
            get_github_token()
            assert mock_secret.call_count == 1


class TestAnalyzerAuthHeaders:
    """Tests for GitHubAnalyzer._get_headers"""

    def test_includes_authorization_when_token_present(self):
        analyzer = GitHubAnalyzer(access_token="ghp_realtoken")
        assert analyzer._get_headers()["Authorization"] == "Bearer ghp_realtoken"

    def test_omits_authorization_when_no_token(self):
        analyzer = GitHubAnalyzer()
        assert "Authorization" not in analyzer._get_headers()


class TestBadTokenFallback:
    """A misconfigured server-side credential must not break user analyses.

    Regression: the infrasketch/github-token secret was once created holding the
    literal placeholder "ghp_xxx". GitHub answers 401 Bad credentials, which
    raise_for_status turned into a hard failure, so repo analysis broke entirely
    rather than degrading to the unauthenticated rate it had before the token
    existed.
    """

    def test_401_drops_the_token_and_retries(self):
        analyzer = GitHubAnalyzer(access_token="ghp_bad")
        analyzer._client = MagicMock()
        analyzer._client.get.side_effect = [_response(401), _response(200)]

        result = analyzer._get("https://api.github.com/repos/o/r")

        assert result.status_code == 200
        assert analyzer.access_token is None, "bad token must be dropped"
        assert analyzer._client.get.call_count == 2

    def test_retry_is_sent_without_an_authorization_header(self):
        analyzer = GitHubAnalyzer(access_token="ghp_bad")
        analyzer._client = MagicMock()
        analyzer._client.get.side_effect = [_response(401), _response(200)]

        analyzer._get("https://api.github.com/repos/o/r")

        retry_headers = analyzer._client.get.call_args_list[1].kwargs["headers"]
        assert "Authorization" not in retry_headers

    def test_401_without_a_token_does_not_retry(self):
        """Nothing to drop, so a genuine 401 must surface rather than loop."""
        analyzer = GitHubAnalyzer()
        analyzer._client = MagicMock()
        analyzer._client.get.return_value = _response(401)

        result = analyzer._get("https://api.github.com/repos/o/r")

        assert result.status_code == 401
        assert analyzer._client.get.call_count == 1

    def test_a_working_token_is_kept(self):
        analyzer = GitHubAnalyzer(access_token="ghp_good")
        analyzer._client = MagicMock()
        analyzer._client.get.return_value = _response(200)

        analyzer._get("https://api.github.com/repos/o/r")

        assert analyzer.access_token == "ghp_good"
        assert analyzer._client.get.call_count == 1

    def test_rate_limit_still_raises_through_get(self):
        """The fallback must not swallow rate-limit detection."""
        analyzer = GitHubAnalyzer(access_token="ghp_good")
        analyzer._client = MagicMock()
        analyzer._client.get.return_value = _response(403, {"X-RateLimit-Remaining": "0"})

        with pytest.raises(GitHubRateLimitError):
            analyzer._get("https://api.github.com/repos/o/r")


class TestRateLimitDetection:
    """Tests for GitHubAnalyzer._check_rate_limit"""

    def test_raises_on_403_with_no_remaining(self):
        """GitHub's primary rate limit: 403 plus X-RateLimit-Remaining: 0."""
        analyzer = GitHubAnalyzer()
        with pytest.raises(GitHubRateLimitError) as exc:
            analyzer._check_rate_limit(_response(403, {
                "X-RateLimit-Remaining": "0",
                "X-RateLimit-Reset": "1700000000",
                "X-RateLimit-Limit": "60",
            }))
        assert exc.value.reset_time == 1700000000

    def test_raises_on_429(self):
        """Secondary (abuse) limits come back as 429 with quota still remaining."""
        analyzer = GitHubAnalyzer()
        with pytest.raises(GitHubRateLimitError):
            analyzer._check_rate_limit(_response(429, {"X-RateLimit-Remaining": "42"}))

    def test_ignores_403_with_quota_remaining(self):
        """A 403 with quota left is a permissions problem, not a rate limit."""
        analyzer = GitHubAnalyzer()
        analyzer._check_rate_limit(_response(403, {"X-RateLimit-Remaining": "58"}))

    def test_ignores_success(self):
        analyzer = GitHubAnalyzer()
        analyzer._check_rate_limit(_response(200))

    def test_tolerates_unparseable_reset_header(self):
        analyzer = GitHubAnalyzer()
        with pytest.raises(GitHubRateLimitError) as exc:
            analyzer._check_rate_limit(_response(429, {"X-RateLimit-Reset": "not-a-number"}))
        assert exc.value.reset_time == 0

    def test_error_message_records_whether_authenticated(self):
        """Ops needs to tell 'no token configured' apart from 'token exhausted'."""
        analyzer = GitHubAnalyzer(access_token="ghp_realtoken")
        with pytest.raises(GitHubRateLimitError) as exc:
            analyzer._check_rate_limit(_response(429, {"X-RateLimit-Limit": "5000"}))
        assert "authenticated=True" in str(exc.value)
