"""
Clerk Backend API client.

Used by the self-healing sync path on GET /user/credits and by the admin
sync endpoint / CLI script. The only call we make today is "what is this
user's current subscription plan", which we use to repair DynamoDB rows
when a webhook missed or stored the wrong plan.

Reference endpoint (verified live 2026-05-17):
    GET https://api.clerk.com/v1/users/{user_id}/billing/subscription
    -> 200 {object: commerce_subscription, status, subscription_items: [...]}
    -> 404 if the user has no subscription
"""

import logging
import time
from datetime import datetime, timezone
from typing import Optional

import httpx
from pydantic import BaseModel
from typing import Literal

from app.billing.plans import (
    UnknownClerkPlanError,
    extract_plan_id_from_item,
    get_plan_from_clerk_id,
)
from app.utils.secrets import get_clerk_secret_key

logger = logging.getLogger(__name__)


CLERK_API_BASE = "https://api.clerk.com/v1"
HTTP_TIMEOUT_SECONDS = 3.0
CACHE_TTL_SECONDS = 60


class ClerkAPIError(Exception):
    """Raised when the Clerk Backend API call fails (network, auth, 5xx)."""


def parse_clerk_timestamp(value) -> Optional[datetime]:
    """
    Normalize Clerk's timestamp shapes to NAIVE UTC datetimes. Live API uses
    int milliseconds (e.g. 1780591212670). Some events may use int seconds
    or ISO strings (potentially with tz info).

    Always returns naive UTC because the rest of this module compares against
    datetime.utcnow() (naive). Returning tz-aware datetimes here would crash
    `_period_end_passed` with "can't compare offset-naive and offset-aware".
    Returns None for None/0/unparseable input.
    """
    if value is None or value == 0:
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        # Heuristic: anything past year 5000 in seconds is almost certainly ms.
        # 1e12 seconds == year 33658; 1e12 ms == year 2001 - so threshold splits cleanly.
        try:
            if value > 1e12:
                return datetime.utcfromtimestamp(value / 1000)
            return datetime.utcfromtimestamp(value)
        except (ValueError, OSError, OverflowError):
            return None
    if isinstance(value, str):
        try:
            dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
        # Convert to UTC then drop tzinfo so comparisons against utcnow() work.
        if dt.tzinfo is not None:
            dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
        return dt
    return None


class ClerkSubscription(BaseModel):
    plan: Literal["free", "starter", "pro", "enterprise"] = "free"
    subscription_id: Optional[str] = None
    plan_id: Optional[str] = None
    status: Optional[str] = None
    stripe_customer_id: Optional[str] = None
    # Derived fields for entitlement decisions.
    has_active_item: bool = False        # True iff at least one subscription_item has status="active"
    not_found: bool = False              # True iff Clerk returned 404 (no subscription record at all)
    period_end: Optional[datetime] = None    # End of current paid billing period (from active item if any, else first item)
    canceled_at: Optional[datetime] = None   # Non-None if user opted out; entitlement continues until period_end


class ClerkClient:
    def __init__(self, secret_key: str, base_url: str = CLERK_API_BASE):
        self._secret_key = secret_key
        self._base_url = base_url.rstrip("/")
        self._client = httpx.Client(
            timeout=HTTP_TIMEOUT_SECONDS,
            headers={"Authorization": f"Bearer {secret_key}"},
        )
        # user_id -> (expires_at_epoch, ClerkSubscription)
        self._cache: dict[str, tuple[float, ClerkSubscription]] = {}

    def _cache_get(self, user_id: str) -> Optional[ClerkSubscription]:
        entry = self._cache.get(user_id)
        if not entry:
            return None
        expires_at, sub = entry
        if time.time() >= expires_at:
            self._cache.pop(user_id, None)
            return None
        return sub

    def _cache_set(self, user_id: str, sub: ClerkSubscription) -> None:
        self._cache[user_id] = (time.time() + CACHE_TTL_SECONDS, sub)

    def invalidate(self, user_id: str) -> None:
        """Drop the cached entry for this user. Called from billing webhook
        handlers on every mutation so subsequent same-container reads see
        fresh Clerk state instead of the pre-mutation snapshot. Cross-
        container staleness is bounded by CACHE_TTL_SECONDS (60s)."""
        self._cache.pop(user_id, None)

    def get_user_subscription(self, user_id: str) -> ClerkSubscription:
        cached = self._cache_get(user_id)
        if cached is not None:
            return cached

        url = f"{self._base_url}/users/{user_id}/billing/subscription"
        try:
            response = self._client.get(url)
        except httpx.RequestError as e:
            raise ClerkAPIError(f"Clerk API request failed: {e}") from e

        if response.status_code == 404:
            # 404 means the user has no Clerk subscription record at all (either
            # never subscribed, or the subscription was hard-deleted). For a
            # stored-paid user this is authoritative: their entitlement is gone.
            # not_found=True lets the sync layer distinguish this from "active
            # subscription with no items".
            #
            # DELIBERATELY NOT CACHED: a 404 flips to "exists" the moment a
            # user completes Clerk checkout. Caching it would let a stale 404
            # downgrade a just-paid user back to free on the next gate call.
            return ClerkSubscription(plan="free", not_found=True)
        if response.status_code == 401 or response.status_code == 403:
            raise ClerkAPIError(f"Clerk API auth failed ({response.status_code}): {response.text[:200]}")
        if response.status_code >= 500:
            raise ClerkAPIError(f"Clerk API server error ({response.status_code}): {response.text[:200]}")
        if response.status_code != 200:
            raise ClerkAPIError(f"Clerk API unexpected status {response.status_code}: {response.text[:200]}")

        try:
            body = response.json()
        except ValueError as e:
            raise ClerkAPIError(f"Clerk API returned non-JSON: {e}") from e

        sub = self._parse_subscription(body)
        self._cache_set(user_id, sub)
        return sub

    def lookup_user_id_by_email(self, email: str) -> Optional[str]:
        """Used by the CLI to resolve an email address to a Clerk user_id.

        Clerk's GET /v1/users returns either a bare JSON array (legacy) or
        a paginated envelope {"data": [...], "total_count": ...} depending on
        API version. Accept both rather than crashing with KeyError on the
        envelope shape.
        """
        url = f"{self._base_url}/users"
        try:
            response = self._client.get(url, params={"email_address": email})
        except httpx.RequestError as e:
            raise ClerkAPIError(f"Clerk API request failed: {e}") from e
        if response.status_code != 200:
            raise ClerkAPIError(f"Clerk API status {response.status_code} for email lookup")
        body = response.json()
        if isinstance(body, dict):
            users = body.get("data") or []
        elif isinstance(body, list):
            users = body
        else:
            raise ClerkAPIError(f"Clerk API unexpected user-list shape: {type(body).__name__}")
        if not users:
            return None
        first = users[0]
        if not isinstance(first, dict):
            raise ClerkAPIError(f"Clerk API user entry not a dict: {type(first).__name__}")
        return first.get("id")

    @staticmethod
    def _parse_subscription(body: dict) -> ClerkSubscription:
        """
        Extract entitlement state from a /billing/subscription payload.

        Shape (observed): top-level subscription has status + subscription_items[].
        Each item has plan_id + nested plan with id/slug, plus optional
        canceled_at and period_end timestamps.

        Returns a ClerkSubscription with derived fields:
          - has_active_item: True iff any item has status=="active"
          - plan: paid plan slug if has_active_item, else "free"
          - period_end, canceled_at: from the active item (else first item)
          - status: top-level subscription status (active/canceled/ended/...)

        "free" returned for no active item is NOT itself a downgrade signal.
        The sync layer interprets it together with status + period_end to
        decide canceled-with-grace vs ended.

        Raises UnknownClerkPlanError if there IS an active item but no
        extractable plan identity (schema shift / corrupt payload) - silent
        free here would recreate the original downgrade-real-paying-user bug.
        """
        items = body.get("subscription_items") or []
        top_status = (body.get("status") or "").lower()
        # Treat a statusless item as active when the top-level subscription
        # itself is active/trialing AND the item carries a plan identity.
        # Clerk omits item.status in some payload variants; without this
        # fallback, sync would see no active item and a paying user whose
        # webhook was missed would stay blocked. Mirrors the webhook handler
        # which also accepts statusless items as plan data.
        top_indicates_entitled = top_status in {"active", "trialing"}

        active_item: Optional[dict] = None
        for item in items:
            if not isinstance(item, dict):
                continue
            item_status = (item.get("status") or "").lower()
            if item_status == "active":
                active_item = item
                break
            if (not item_status
                and top_indicates_entitled
                and extract_plan_id_from_item(item)):
                active_item = item
                break

        # Pull canceled_at / period_end from the active item if present,
        # otherwise from the first item (so a canceled-not-yet-ended subscription
        # still surfaces its period_end after the item status changes).
        metadata_item = active_item
        if metadata_item is None and items:
            first = items[0]
            if isinstance(first, dict):
                metadata_item = first

        period_end = parse_clerk_timestamp(metadata_item.get("period_end")) if metadata_item else None
        canceled_at = parse_clerk_timestamp(metadata_item.get("canceled_at")) if metadata_item else None

        common = dict(
            subscription_id=body.get("id"),
            status=body.get("status"),
            stripe_customer_id=body.get("stripe_customer_id"),
            period_end=period_end,
            canceled_at=canceled_at,
        )

        if active_item is None:
            return ClerkSubscription(
                plan="free",
                plan_id=None,
                has_active_item=False,
                **common,
            )

        plan_id = extract_plan_id_from_item(active_item)
        if not plan_id:
            raise UnknownClerkPlanError("<missing-from-active-item>")
        plan = get_plan_from_clerk_id(plan_id, raise_on_unknown=True)

        return ClerkSubscription(
            plan=plan,
            plan_id=plan_id,
            has_active_item=True,
            **common,
        )


_client_singleton: Optional[ClerkClient] = None


def get_clerk_client() -> ClerkClient:
    global _client_singleton
    if _client_singleton is None:
        secret = get_clerk_secret_key()
        _client_singleton = ClerkClient(secret_key=secret)
    return _client_singleton


def invalidate_clerk_cache_for_user(user_id: str) -> None:
    """Module-level helper used by webhook handlers. No-op if the singleton
    hasn't been created yet (e.g. webhook fires before any user-facing read).
    """
    if _client_singleton is not None and user_id:
        _client_singleton.invalidate(user_id)


def reset_clerk_client_for_tests() -> None:
    """Test helper to clear the module-level singleton between tests."""
    global _client_singleton
    _client_singleton = None
