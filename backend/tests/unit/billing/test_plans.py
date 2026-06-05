"""Tests for backend/app/billing/plans.py."""

import logging
import pytest

from app.billing.plans import (
    CLERK_PLAN_ID_MAP,
    UnknownClerkPlanError,
    get_plan_from_clerk_id,
)


class TestKnownPlans:
    @pytest.mark.parametrize("plan_id,expected", list(CLERK_PLAN_ID_MAP.items()))
    def test_exact_mapping(self, plan_id, expected):
        assert get_plan_from_clerk_id(plan_id) == expected


class TestFuzzyMatch:
    @pytest.mark.parametrize("plan_id,expected", [
        ("cplan_xyz_starter_abc", "starter"),
        ("cplan_STARTER_2", "starter"),
        ("cplan_pro_v3", "pro"),
        ("cplan_enterprise_eu", "enterprise"),
    ])
    def test_fuzzy_match(self, plan_id, expected):
        assert get_plan_from_clerk_id(plan_id) == expected


class TestEmptyInput:
    def test_empty_string_returns_free_silently(self, caplog):
        with caplog.at_level(logging.WARNING, logger="app.billing.plans"):
            assert get_plan_from_clerk_id("") == "free"
        assert caplog.text == ""

    def test_empty_string_with_raise_does_not_raise(self):
        assert get_plan_from_clerk_id("", raise_on_unknown=True) == "free"


class TestUnknownPlan:
    def test_unknown_returns_free_with_warning(self, caplog):
        with caplog.at_level(logging.WARNING, logger="app.billing.plans"):
            assert get_plan_from_clerk_id("cplan_neverseen") == "free"
        assert "cplan_neverseen" in caplog.text
        assert "defaulting to free" in caplog.text

    def test_unknown_with_raise_on_unknown_raises(self):
        with pytest.raises(UnknownClerkPlanError) as exc_info:
            get_plan_from_clerk_id("cplan_neverseen", raise_on_unknown=True)
        assert exc_info.value.plan_id == "cplan_neverseen"
