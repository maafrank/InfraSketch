"""Tests for public share links.

The sanitizer test is the important one: the share payload is the only place in
the app where session data crosses to unauthenticated readers, so a regression
there leaks user data rather than merely breaking a feature.
"""

from datetime import datetime, timezone

import pytest

from app.api.routes_sharing import public_share_payload
from app.models import (
    Diagram,
    Edge,
    Message,
    Node,
    NodeMetadata,
    NodePosition,
    SessionState,
)


@pytest.fixture
def fully_populated_session():
    """A session with every sensitive field set, so the allowlist is tested
    against the worst case rather than a mostly-empty object."""
    diagram = Diagram(
        nodes=[
            Node(
                id="api_1",
                type="api",
                label="API Gateway",
                description="Entry point",
                position=NodePosition(x=10, y=20),
                metadata=NodeMetadata(technology="FastAPI", notes="internal note"),
            ),
            Node(id="db_1", type="database", label="Postgres", description="Primary store"),
        ],
        edges=[Edge(id="e1", source="api_1", target="db_1", label="reads")],
    )

    return SessionState(
        session_id="sess-123",
        user_id="user_secret_clerk_id",
        diagram=diagram,
        messages=[
            Message(role="user", content="my private prompt with company details"),
            Message(role="assistant", content="private assistant reply"),
        ],
        design_doc="# Design\nPublic-facing doc.",
        name="Payments Platform",
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        shared_at=datetime(2026, 2, 1, tzinfo=timezone.utc),
        generation_prompt="the original private prompt",
        repo_url="https://github.com/acme/private-repo",
        repo_analysis={"languages": {"Python": 100}, "secrets_found": "sensitive"},
        share_token="tok_abc123",
        is_public=True,
        public_flag="1",
        allow_fork=True,
        share_view_count=42,
        diagram_revision=7,
    )


# Anything that identifies the owner, reveals their private inputs, or exposes
# account state. If a new sensitive field is added to SessionState, add it here.
FORBIDDEN_KEYS = {
    "user_id",
    "session_id",
    "messages",
    "generation_prompt",
    "repo_url",
    "repo_analysis",
    "share_token",
    "public_flag",
    "share_view_count",
    "sync_status",
    "diagram_revision",
    "review",
    "iac_artifacts",
    "model",
}


def test_public_share_payload_allowlist(fully_populated_session):
    """The public payload exposes only the allowlisted keys."""
    payload = public_share_payload(fully_populated_session)

    leaked = FORBIDDEN_KEYS & set(payload.keys())
    assert not leaked, f"Share payload leaked sensitive keys: {sorted(leaked)}"

    assert set(payload.keys()) == {
        "name",
        "diagram",
        "design_doc",
        "created_at",
        "shared_at",
        "allow_fork",
        "node_count",
        "edge_count",
    }


def test_public_share_payload_has_no_owner_identifiers_anywhere(fully_populated_session):
    """No sensitive value appears anywhere in the serialized payload.

    Key-level checks miss a value smuggled inside a nested structure, so this
    searches the whole serialized blob.
    """
    import json

    blob = json.dumps(public_share_payload(fully_populated_session))

    for secret in (
        "user_secret_clerk_id",
        "my private prompt",
        "the original private prompt",
        "private-repo",
        "secrets_found",
        "tok_abc123",
    ):
        assert secret not in blob, f"Share payload leaked {secret!r}"


def test_public_share_payload_keeps_the_useful_parts(fully_populated_session):
    """The viewer still gets everything it needs to render."""
    payload = public_share_payload(fully_populated_session)

    assert payload["name"] == "Payments Platform"
    assert payload["node_count"] == 2
    assert payload["edge_count"] == 1
    assert payload["design_doc"].startswith("# Design")
    assert payload["allow_fork"] is True

    node_ids = {n["id"] for n in payload["diagram"]["nodes"]}
    assert node_ids == {"api_1", "db_1"}


def test_public_share_payload_handles_missing_optional_fields():
    """A minimal session must not raise on the None paths."""
    session = SessionState(
        session_id="sess-min",
        user_id="user_1",
        diagram=Diagram(nodes=[], edges=[]),
    )

    payload = public_share_payload(session)

    assert payload["name"] == "Untitled Design"
    assert payload["design_doc"] is None
    assert payload["created_at"] is None
    assert payload["shared_at"] is None
    assert payload["node_count"] == 0


class TestShareTokenLifecycle:
    """Token minting and revocation on the in-memory session manager."""

    def test_share_mints_a_token_and_marks_public(self):
        from app.session.manager import SessionManager

        manager = SessionManager()
        session_id = manager.create_session(Diagram(nodes=[], edges=[]), user_id="user_1")

        token = manager.share_session(session_id)

        assert token
        session = manager.get_session(session_id)
        assert session.is_public is True
        assert session.public_flag == "1"
        assert session.share_token == token

    def test_resharing_keeps_the_same_token(self):
        """Re-sharing must not break links already handed out."""
        from app.session.manager import SessionManager

        manager = SessionManager()
        session_id = manager.create_session(Diagram(nodes=[], edges=[]), user_id="user_1")

        first = manager.share_session(session_id)
        second = manager.share_session(session_id)

        assert first == second

    def test_unshare_revokes_the_token(self):
        from app.session.manager import SessionManager

        manager = SessionManager()
        session_id = manager.create_session(Diagram(nodes=[], edges=[]), user_id="user_1")
        token = manager.share_session(session_id)

        manager.unshare_session(session_id)

        assert manager.get_session_by_share_token(token) is None
        session = manager.get_session(session_id)
        assert session.share_token is None
        assert session.is_public is False

    def test_lookup_ignores_a_session_that_is_no_longer_public(self):
        """Defense in depth: a stale index entry must not serve content."""
        from app.session.manager import SessionManager

        manager = SessionManager()
        session_id = manager.create_session(Diagram(nodes=[], edges=[]), user_id="user_1")
        token = manager.share_session(session_id)

        # Flip the flag without clearing the token, simulating a partial write.
        manager.get_session(session_id).is_public = False

        assert manager.get_session_by_share_token(token) is None
