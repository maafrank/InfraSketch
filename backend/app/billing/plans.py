"""
Shared Clerk plan ID mapping.

Both the webhook handler and the Clerk Backend API client convert raw Clerk
plan IDs into our internal plan names. Lives in its own module to avoid a
circular import between routes_billing and the Clerk client.
"""

import logging

logger = logging.getLogger(__name__)


CLERK_PLAN_ID_MAP = {
    # Clerk's default plan. Every user gets a subscription to it at signup, so
    # omitting it made subscription.created raise UnknownClerkPlanError on every
    # new user and 500 the webhook (which Clerk then retried ~7x each).
    "cplan_37a40Ja1JwQMw78ZUiNu8H9miEX": "free",
    "cplan_3ASdFvizPo0JbVeethbsS7UfLjp": "starter",
    "cplan_37cOR2Mjs1jWOjaJfUGTX0U1Jf4": "pro",
    "cplan_37cOpDf5Cm7GGUl2K8lUarQf7Bp": "enterprise",
}


class UnknownClerkPlanError(Exception):
    """Raised when a non-empty Clerk plan_id cannot be mapped to a known plan."""

    def __init__(self, plan_id: str):
        super().__init__(f"Unknown Clerk plan_id: {plan_id!r}")
        self.plan_id = plan_id


def extract_plan_id_from_item(item: dict) -> str:
    """
    Try every field Clerk might use to identify the plan on a subscription_item,
    in priority order: top-level plan_id, then nested plan.id, then nested
    plan.slug. The fuzzy matcher in get_plan_from_clerk_id resolves slug names
    like "starter" / "pro" correctly. Returns "" if nothing useful is present.

    Used by both the Clerk API client (parsing /billing/subscription responses)
    and the webhook handler (parsing subscription.* event payloads) so both
    paths handle the same shape variants.
    """
    if not isinstance(item, dict):
        return ""
    plan_id = item.get("plan_id") or ""
    if plan_id:
        return plan_id
    nested = item.get("plan") or {}
    if not isinstance(nested, dict):
        return ""
    return nested.get("id") or nested.get("slug") or ""


def get_plan_from_clerk_id(plan_id: str, raise_on_unknown: bool = False) -> str:
    """
    Map a raw Clerk plan ID to our internal plan name.

    Empty / missing plan_id always returns "free" silently (this is how Clerk
    indicates "no subscription"). A non-empty plan_id that doesn't match the
    map nor any fuzzy alias logs a WARNING and either returns "free" or, if
    raise_on_unknown is True, raises UnknownClerkPlanError so the caller can
    fail loudly (e.g. return 500 from a webhook to trigger Clerk retry).
    """
    if not plan_id:
        return "free"

    if plan_id in CLERK_PLAN_ID_MAP:
        return CLERK_PLAN_ID_MAP[plan_id]

    plan_id_lower = plan_id.lower()
    # Checked before the paid slugs: extract_plan_id_from_item can hand us a
    # bare slug ("free") rather than a cplan_ ID, and the default plan must
    # resolve without raising.
    if "free" in plan_id_lower:
        return "free"
    if "starter" in plan_id_lower:
        return "starter"
    if "pro" in plan_id_lower:
        return "pro"
    if "enterprise" in plan_id_lower:
        return "enterprise"

    logger.warning("Unknown Clerk plan_id %r; defaulting to free", plan_id)
    if raise_on_unknown:
        raise UnknownClerkPlanError(plan_id)
    return "free"
