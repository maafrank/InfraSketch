"""Tests for backend/app/billing/clerk_client.py."""

from unittest.mock import MagicMock, patch

import httpx
import pytest

from app.billing.clerk_client import (
    ClerkAPIError,
    ClerkClient,
    ClerkSubscription,
    parse_clerk_timestamp,
    reset_clerk_client_for_tests,
)
from app.billing.plans import UnknownClerkPlanError


class TestParseClerkTimestamp:
    def test_none_and_zero(self):
        assert parse_clerk_timestamp(None) is None
        assert parse_clerk_timestamp(0) is None

    def test_ms_epoch(self):
        # 1780591212670 ms ~= 2026-05-04
        dt = parse_clerk_timestamp(1780591212670)
        assert dt is not None
        assert dt.year == 2026

    def test_seconds_epoch(self):
        # 1780591212 s ~= 2026-05-04
        dt = parse_clerk_timestamp(1780591212)
        assert dt is not None
        assert dt.year == 2026

    def test_iso_string(self):
        dt = parse_clerk_timestamp("2026-05-04T12:00:00Z")
        assert dt is not None
        assert dt.year == 2026 and dt.month == 5 and dt.day == 4

    def test_iso_string_returns_naive_utc(self):
        # Bug regression: tz-aware results crashed `_period_end_passed` with
        # "can't compare offset-naive and offset-aware".
        dt = parse_clerk_timestamp("2026-05-04T12:00:00Z")
        assert dt.tzinfo is None

    def test_iso_string_with_offset_normalizes_to_naive_utc(self):
        # "2026-05-04T07:00:00-05:00" == "2026-05-04T12:00:00Z"
        dt = parse_clerk_timestamp("2026-05-04T07:00:00-05:00")
        assert dt.tzinfo is None
        assert dt.hour == 12

    def test_unparseable_returns_none(self):
        assert parse_clerk_timestamp("not a date") is None
        assert parse_clerk_timestamp({"weird": "shape"}) is None
        assert parse_clerk_timestamp(True) is None


def _mock_response(status_code: int, json_body: dict | None = None, text: str = "") -> MagicMock:
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = status_code
    resp.json.return_value = json_body if json_body is not None else {}
    if json_body is None:
        resp.json.side_effect = ValueError("no JSON")
    resp.text = text or (str(json_body) if json_body else "")
    return resp


@pytest.fixture
def client():
    reset_clerk_client_for_tests()
    yield ClerkClient(secret_key="sk_test_fake")
    reset_clerk_client_for_tests()


class TestGetUserSubscription:
    def test_active_starter_subscription(self, client):
        body = {
            "id": "csub_abc",
            "status": "active",
            "stripe_customer_id": "cus_x",
            "subscription_items": [
                {
                    "id": "csub_item_1",
                    "status": "active",
                    "plan_id": "cplan_3ASdFvizPo0JbVeethbsS7UfLjp",
                    "plan": {"id": "cplan_3ASdFvizPo0JbVeethbsS7UfLjp", "slug": "starter"},
                }
            ],
        }
        with patch.object(client._client, "get", return_value=_mock_response(200, body)) as mock_get:
            sub = client.get_user_subscription("user_x")
        assert sub == ClerkSubscription(
            plan="starter",
            subscription_id="csub_abc",
            plan_id="cplan_3ASdFvizPo0JbVeethbsS7UfLjp",
            status="active",
            stripe_customer_id="cus_x",
            has_active_item=True,
        )
        mock_get.assert_called_once()

    def test_no_subscription_404(self, client):
        with patch.object(client._client, "get", return_value=_mock_response(404, {})):
            sub = client.get_user_subscription("user_y")
        assert sub.plan == "free"
        assert sub.subscription_id is None
        # 404 must set not_found so sync can authoritatively downgrade a paid
        # stored user. Without this, we'd ambiguously leave them paid.
        assert sub.not_found is True
        assert sub.has_active_item is False

    def test_404_is_not_cached(self, client):
        # Regression: caching 404 lets a stale "no subscription" response
        # downgrade a user who just completed Clerk checkout. Every call
        # must re-hit Clerk after a 404.
        with patch.object(client._client, "get", return_value=_mock_response(404, {})) as mock_get:
            client.get_user_subscription("user_404")
            client.get_user_subscription("user_404")
            client.get_user_subscription("user_404")
        assert mock_get.call_count == 3

    def test_active_subscription_is_cached(self, client):
        # Sanity: caching still works for the common case (active subscription).
        body = {
            "id": "csub_ok",
            "status": "active",
            "subscription_items": [{"status": "active", "plan_id": "cplan_3ASdFvizPo0JbVeethbsS7UfLjp"}],
        }
        with patch.object(client._client, "get", return_value=_mock_response(200, body)) as mock_get:
            client.get_user_subscription("user_active")
            client.get_user_subscription("user_active")
        assert mock_get.call_count == 1

    def test_invalidate_drops_cached_entry(self, client):
        body = {
            "id": "csub_invalidate",
            "status": "active",
            "subscription_items": [{"status": "active", "plan_id": "cplan_3ASdFvizPo0JbVeethbsS7UfLjp"}],
        }
        with patch.object(client._client, "get", return_value=_mock_response(200, body)) as mock_get:
            client.get_user_subscription("user_inv")
            client.invalidate("user_inv")
            client.get_user_subscription("user_inv")
        assert mock_get.call_count == 2

    def test_invalidate_unknown_user_is_noop(self, client):
        # Doesn't crash on a user that was never cached.
        client.invalidate("user_never_seen")

    def test_active_subscription_surfaces_period_end_and_canceled_at(self, client):
        # period_end is in ms epoch (matches live Clerk API).
        body = {
            "id": "csub_dates",
            "status": "active",
            "subscription_items": [
                {
                    "status": "active",
                    "plan_id": "cplan_3ASdFvizPo0JbVeethbsS7UfLjp",
                    "period_end": 1780591212670,
                    "canceled_at": 1779000000000,
                }
            ],
        }
        with patch.object(client._client, "get", return_value=_mock_response(200, body)):
            sub = client.get_user_subscription("user_dates")
        assert sub.plan == "starter"
        assert sub.has_active_item is True
        assert sub.period_end is not None
        assert sub.period_end.year == 2026
        assert sub.canceled_at is not None

    def test_canceled_subscription_no_active_item_surfaces_period_end(self, client):
        # User canceled and the item flipped to canceled status, but period_end
        # is still in the future - sync layer needs this to keep entitlement.
        body = {
            "id": "csub_canceled_grace",
            "status": "canceled",
            "subscription_items": [
                {
                    "status": "canceled",
                    "plan_id": "cplan_3ASdFvizPo0JbVeethbsS7UfLjp",
                    "period_end": 1780591212670,
                    "canceled_at": 1779000000000,
                }
            ],
        }
        with patch.object(client._client, "get", return_value=_mock_response(200, body)):
            sub = client.get_user_subscription("user_canceled_grace")
        assert sub.plan == "free"  # no active item
        assert sub.has_active_item is False
        assert sub.status == "canceled"
        assert sub.period_end is not None
        assert sub.canceled_at is not None

    def test_no_active_items_returns_free(self, client):
        body = {"id": "csub_inactive", "status": "canceled", "subscription_items": []}
        with patch.object(client._client, "get", return_value=_mock_response(200, body)):
            sub = client.get_user_subscription("user_z")
        assert sub.plan == "free"

    def test_active_item_with_no_plan_identity_raises(self, client):
        # Schema shift / corrupt payload: active item but plan_id and nested
        # plan.id/slug are all missing. Returning "free" here would recreate
        # the original bug (downgrade a real paying user via the self-heal
        # path). Raise so non-force fails open and force=True surfaces it.
        body = {
            "id": "csub_no_plan",
            "status": "active",
            "subscription_items": [{"status": "active"}],
        }
        with patch.object(client._client, "get", return_value=_mock_response(200, body)):
            with pytest.raises(UnknownClerkPlanError):
                client.get_user_subscription("user_no_plan")

    def test_active_unknown_plan_id_raises(self, client):
        # An active subscription with an unknown plan_id must not silently map
        # to "free" - that would let a forced admin sync downgrade a real paid
        # subscriber the moment a new Clerk plan_id ships.
        body = {
            "id": "csub_unknown",
            "status": "active",
            "subscription_items": [
                {"status": "active", "plan_id": "cplan_neverseen"}
            ],
        }
        with patch.object(client._client, "get", return_value=_mock_response(200, body)):
            with pytest.raises(UnknownClerkPlanError) as exc_info:
                client.get_user_subscription("user_u")
        assert exc_info.value.plan_id == "cplan_neverseen"

    def test_active_subscription_resolves_via_nested_plan_slug(self, client):
        # If a payload omits plan_id at the item level and the nested plan.id,
        # but exposes plan.slug, the fuzzy mapper should still recognize it.
        # Without this, self-healing would treat a paid subscriber as free.
        body = {
            "id": "csub_slug",
            "status": "active",
            "subscription_items": [
                {"status": "active", "plan": {"slug": "starter"}}
            ],
        }
        with patch.object(client._client, "get", return_value=_mock_response(200, body)):
            sub = client.get_user_subscription("user_slug")
        assert sub.plan == "starter"
        assert sub.plan_id == "starter"

    def test_statusless_item_treated_active_when_top_level_active(self, client):
        # Regression: Clerk sometimes omits item.status in payloads where the
        # top-level subscription is clearly active. The webhook handler
        # accepts statusless items as plan data; self-heal must too, or a
        # paying user with a missed webhook stays blocked.
        body = {
            "id": "csub_statusless",
            "status": "active",
            "subscription_items": [
                {"plan_id": "cplan_3ASdFvizPo0JbVeethbsS7UfLjp"}  # no status
            ],
        }
        with patch.object(client._client, "get", return_value=_mock_response(200, body)):
            sub = client.get_user_subscription("user_statusless")
        assert sub.plan == "starter"
        assert sub.has_active_item is True

    def test_statusless_item_treated_active_when_top_level_trialing(self, client):
        body = {
            "id": "csub_trialing_statusless",
            "status": "trialing",
            "subscription_items": [
                {"plan": {"slug": "starter"}}  # statusless + nested slug
            ],
        }
        with patch.object(client._client, "get", return_value=_mock_response(200, body)):
            sub = client.get_user_subscription("user_trial")
        assert sub.plan == "starter"
        assert sub.has_active_item is True

    def test_statusless_item_not_active_when_top_level_canceled(self, client):
        # Conservative: top-level NOT active/trialing -> statusless items
        # don't get the active-fallback treatment. Prevents re-enabling
        # service for a canceled subscription whose items lack status.
        body = {
            "id": "csub_canceled_statusless",
            "status": "canceled",
            "subscription_items": [
                {"plan_id": "cplan_3ASdFvizPo0JbVeethbsS7UfLjp"}
            ],
        }
        with patch.object(client._client, "get", return_value=_mock_response(200, body)):
            sub = client.get_user_subscription("user_cs")
        assert sub.plan == "free"
        assert sub.has_active_item is False

    def test_active_subscription_resolves_via_nested_plan_id(self, client):
        body = {
            "id": "csub_nested",
            "status": "active",
            "subscription_items": [
                {"status": "active", "plan": {"id": "cplan_3ASdFvizPo0JbVeethbsS7UfLjp"}}
            ],
        }
        with patch.object(client._client, "get", return_value=_mock_response(200, body)):
            sub = client.get_user_subscription("user_nested_id")
        assert sub.plan == "starter"

    def test_canceled_item_with_known_plan_id_returns_free(self, client):
        # Prior bug: a canceled subscription_item with a KNOWN starter plan_id
        # fell through the fallback and was reported as plan="starter". That
        # would let /user/credits re-upgrade a free user from a stale
        # subscription and block admin force-sync from repairing stale paid
        # users. Now: no active item -> free, regardless of canceled items'
        # plan_ids.
        body = {
            "id": "csub_canceled_starter",
            "status": "canceled",
            "subscription_items": [
                {
                    "status": "canceled",
                    "plan_id": "cplan_3ASdFvizPo0JbVeethbsS7UfLjp",
                }
            ],
        }
        with patch.object(client._client, "get", return_value=_mock_response(200, body)):
            sub = client.get_user_subscription("user_canceled_starter")
        assert sub.plan == "free"
        assert sub.plan_id is None
        # The top-level Clerk status is still surfaced so the storage layer
        # can record the correct subscription_status.
        assert sub.status == "canceled"

    def test_mixed_items_only_active_one_counts(self, client):
        # If Clerk returns one active + one canceled item with different plans,
        # the active one wins. (Today this is moot since we don't have multi-
        # plan subscriptions, but the test pins the contract.)
        body = {
            "id": "csub_mixed",
            "status": "active",
            "subscription_items": [
                {"status": "canceled", "plan": {"slug": "pro"}},
                {"status": "active", "plan_id": "cplan_3ASdFvizPo0JbVeethbsS7UfLjp"},
            ],
        }
        with patch.object(client._client, "get", return_value=_mock_response(200, body)):
            sub = client.get_user_subscription("user_mixed")
        assert sub.plan == "starter"

    def test_canceled_unknown_plan_id_returns_free(self, client):
        # A canceled / inactive item with unknown plan_id is fine to map to
        # free - we're downgrading regardless.
        body = {
            "id": "csub_canceled",
            "status": "canceled",
            "subscription_items": [
                {"status": "canceled", "plan_id": "cplan_neverseen"}
            ],
        }
        with patch.object(client._client, "get", return_value=_mock_response(200, body)):
            sub = client.get_user_subscription("user_c")
        assert sub.plan == "free"

    def test_401_raises_clerk_api_error(self, client):
        with patch.object(client._client, "get", return_value=_mock_response(401, text="auth fail")):
            with pytest.raises(ClerkAPIError) as exc_info:
                client.get_user_subscription("user_a")
        assert "401" in str(exc_info.value)

    def test_500_raises_clerk_api_error(self, client):
        with patch.object(client._client, "get", return_value=_mock_response(503, text="boom")):
            with pytest.raises(ClerkAPIError):
                client.get_user_subscription("user_b")

    def test_network_error_raises(self, client):
        with patch.object(client._client, "get", side_effect=httpx.ConnectError("dns")):
            with pytest.raises(ClerkAPIError):
                client.get_user_subscription("user_c")

    def test_cache_hits_within_ttl(self, client):
        body = {"id": "csub_cached", "status": "active", "subscription_items": [
            {"status": "active", "plan_id": "cplan_3ASdFvizPo0JbVeethbsS7UfLjp"}
        ]}
        with patch.object(client._client, "get", return_value=_mock_response(200, body)) as mock_get:
            client.get_user_subscription("user_cache")
            client.get_user_subscription("user_cache")
        assert mock_get.call_count == 1


class TestLookupUserIdByEmail:
    def test_email_resolves_to_user_id_legacy_bare_list(self, client):
        with patch.object(client._client, "get", return_value=_mock_response(200, [{"id": "user_77"}])):
            uid = client.lookup_user_id_by_email("a@b.c")
        assert uid == "user_77"

    def test_email_resolves_to_user_id_paginated_envelope(self, client):
        # Clerk's current API returns {"data": [...], "total_count": N}.
        # The CLI must work against both shapes.
        envelope = {"data": [{"id": "user_88"}, {"id": "user_other"}], "total_count": 2}
        with patch.object(client._client, "get", return_value=_mock_response(200, envelope)):
            uid = client.lookup_user_id_by_email("a@b.c")
        assert uid == "user_88"

    def test_no_users_returns_none_bare_list(self, client):
        with patch.object(client._client, "get", return_value=_mock_response(200, [])):
            assert client.lookup_user_id_by_email("a@b.c") is None

    def test_no_users_returns_none_paginated(self, client):
        with patch.object(client._client, "get", return_value=_mock_response(200, {"data": [], "total_count": 0})):
            assert client.lookup_user_id_by_email("a@b.c") is None

    def test_unexpected_shape_raises(self, client):
        # A bare string / number response would silently break users[0] before.
        with patch.object(client._client, "get", return_value=_mock_response(200, "unexpected")):
            with pytest.raises(ClerkAPIError, match="user-list shape"):
                client.lookup_user_id_by_email("a@b.c")

    def test_non_200_raises(self, client):
        with patch.object(client._client, "get", return_value=_mock_response(500, text="err")):
            with pytest.raises(ClerkAPIError):
                client.lookup_user_id_by_email("a@b.c")
