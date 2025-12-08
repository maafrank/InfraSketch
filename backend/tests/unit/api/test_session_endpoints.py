"""
Tests for session management endpoints:
- GET /api/session/{session_id}
- POST /api/session/create-blank
- PATCH /api/session/{session_id}/name
- DELETE /api/session/{session_id}
- GET /api/user/sessions
"""

import pytest
from fastapi.testclient import TestClient


class TestGetSession:
    """Tests for GET /api/session/{session_id}"""

    def test_get_session_returns_session_state(self, client_with_session):
        """Should return full session state for owned session."""
        client, session_id = client_with_session

        response = client.get(f"/api/session/{session_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["session_id"] == session_id
        assert "diagram" in data
        assert "messages" in data
        assert "model" in data

    def test_get_session_returns_404_for_nonexistent(self, client):
        """Should return 404 for non-existent session."""
        response = client.get("/api/session/nonexistent-session-xyz")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_get_session_includes_diagram_data(self, client_with_session):
        """Should include nodes and edges in diagram."""
        client, session_id = client_with_session

        response = client.get(f"/api/session/{session_id}")

        assert response.status_code == 200
        diagram = response.json()["diagram"]
        assert "nodes" in diagram
        assert "edges" in diagram
        # simple_diagram fixture has 2 nodes and 1 edge
        assert len(diagram["nodes"]) == 2
        assert len(diagram["edges"]) == 1


class TestCreateBlankSession:
    """Tests for POST /api/session/create-blank"""

    def test_create_blank_session_returns_empty_diagram(self, client):
        """Should create session with empty diagram."""
        response = client.post("/api/session/create-blank")

        assert response.status_code == 200
        data = response.json()
        assert "session_id" in data
        assert "diagram" in data
        assert data["diagram"]["nodes"] == []
        assert data["diagram"]["edges"] == []

    def test_create_blank_session_sets_default_name(self, client):
        """Should set 'Untitled Design' as default name."""
        response = client.post("/api/session/create-blank")

        assert response.status_code == 200
        session_id = response.json()["session_id"]

        # Verify in session manager
        from app.session.manager import session_manager
        session = session_manager.get_session(session_id)
        assert session.name == "Untitled Design"

    def test_create_blank_session_assigns_user_id(self, client):
        """Should assign user_id from auth context."""
        response = client.post("/api/session/create-blank")

        assert response.status_code == 200
        session_id = response.json()["session_id"]

        from app.session.manager import session_manager
        session = session_manager.get_session(session_id)
        # In test mode, user_id is "local-dev-user"
        assert session.user_id == "local-dev-user"


class TestRenameSession:
    """Tests for PATCH /api/session/{session_id}/name"""

    def test_rename_session_updates_name(self, client_with_session):
        """Should update session name."""
        client, session_id = client_with_session
        new_name = "My Awesome Architecture"

        response = client.patch(
            f"/api/session/{session_id}/name",
            json={"name": new_name}
        )

        assert response.status_code == 200
        assert response.json()["success"] is True
        assert response.json()["name"] == new_name

        # Verify in session manager
        from app.session.manager import session_manager
        session = session_manager.get_session(session_id)
        assert session.name == new_name

    def test_rename_session_rejects_empty_name(self, client_with_session):
        """Should reject empty name with 400."""
        client, session_id = client_with_session

        response = client.patch(
            f"/api/session/{session_id}/name",
            json={"name": ""}
        )

        assert response.status_code == 400
        assert "empty" in response.json()["detail"].lower()

    def test_rename_session_rejects_whitespace_only_name(self, client_with_session):
        """Should reject whitespace-only name with 400."""
        client, session_id = client_with_session

        response = client.patch(
            f"/api/session/{session_id}/name",
            json={"name": "   "}
        )

        assert response.status_code == 400

    def test_rename_session_returns_404_for_nonexistent(self, client):
        """Should return 404 for non-existent session."""
        response = client.patch(
            "/api/session/nonexistent-xyz/name",
            json={"name": "New Name"}
        )

        assert response.status_code == 404


class TestDeleteSession:
    """Tests for DELETE /api/session/{session_id}"""

    def test_delete_session_removes_session(self, client_with_session):
        """Should delete the session."""
        client, session_id = client_with_session

        response = client.delete(f"/api/session/{session_id}")

        assert response.status_code == 200
        assert response.json()["success"] is True

        # Verify session is gone
        from app.session.manager import session_manager
        assert session_manager.get_session(session_id) is None

    def test_delete_session_returns_404_for_nonexistent(self, client):
        """Should return 404 for non-existent session."""
        response = client.delete("/api/session/nonexistent-session-abc")

        assert response.status_code == 404

    def test_delete_session_returns_success_message(self, client_with_session):
        """Should return success message."""
        client, session_id = client_with_session

        response = client.delete(f"/api/session/{session_id}")

        assert response.status_code == 200
        assert "deleted" in response.json()["message"].lower()


class TestGetUserSessions:
    """Tests for GET /api/user/sessions"""

    def test_get_user_sessions_returns_list(self, client):
        """Should return list of user's sessions."""
        # Create a few sessions first
        from app.session.manager import session_manager
        from app.models import Diagram

        session_manager.create_session(
            Diagram(nodes=[], edges=[]),
            user_id="local-dev-user"
        )
        session_manager.create_session(
            Diagram(nodes=[], edges=[]),
            user_id="local-dev-user"
        )

        response = client.get("/api/user/sessions")

        assert response.status_code == 200
        data = response.json()
        assert "sessions" in data
        assert "total" in data
        assert data["total"] >= 2
        assert len(data["sessions"]) >= 2

    def test_get_user_sessions_includes_metadata(self, client_with_session):
        """Should include session metadata in response."""
        client, session_id = client_with_session

        response = client.get("/api/user/sessions")

        assert response.status_code == 200
        sessions = response.json()["sessions"]

        # Find our session
        our_session = next((s for s in sessions if s["session_id"] == session_id), None)
        assert our_session is not None
        assert "node_count" in our_session
        assert "edge_count" in our_session
        assert "message_count" in our_session
        assert "model" in our_session
        assert "name" in our_session

    def test_get_user_sessions_only_returns_owned_sessions(self, client):
        """Should only return sessions owned by the authenticated user."""
        from app.session.manager import session_manager
        from app.models import Diagram

        # Create session for current user
        my_session_id = session_manager.create_session(
            Diagram(nodes=[], edges=[]),
            user_id="local-dev-user"
        )
        # Create session for different user
        other_session_id = session_manager.create_session(
            Diagram(nodes=[], edges=[]),
            user_id="different-user-xyz"
        )

        response = client.get("/api/user/sessions")

        assert response.status_code == 200
        session_ids = [s["session_id"] for s in response.json()["sessions"]]

        assert my_session_id in session_ids
        assert other_session_id not in session_ids

    def test_get_user_sessions_returns_empty_for_new_user(self, client):
        """Should return empty list for user with no sessions."""
        # Clear all sessions for the test user
        from app.session.manager import session_manager
        session_manager.sessions = {}

        response = client.get("/api/user/sessions")

        assert response.status_code == 200
        data = response.json()
        assert data["sessions"] == []
        assert data["total"] == 0
