"""
Tests for diagram generation endpoints:
- POST /api/generate
- GET /api/session/{session_id}/diagram/status
"""

import pytest
from fastapi.testclient import TestClient


class TestGenerateEndpoint:
    """Tests for POST /api/generate"""

    def test_generate_returns_session_id_and_generating_status(self, client, mock_user_credits_storage):
        """Happy path: Generate returns session_id and generating status immediately."""
        response = client.post(
            "/api/generate",
            json={"prompt": "Create a simple web application architecture"}
        )

        assert response.status_code == 200
        data = response.json()
        assert "session_id" in data
        assert data["status"] == "generating"
        assert len(data["session_id"]) > 0

    def test_generate_uses_default_model_when_not_specified(self, client, mock_user_credits_storage):
        """Should use claude-haiku-4-5 when no model specified."""
        response = client.post(
            "/api/generate",
            json={"prompt": "Create a basic API"}
        )

        assert response.status_code == 200
        data = response.json()
        session_id = data["session_id"]

        # Check session was created with default model
        from app.session.manager import session_manager
        session = session_manager.get_session(session_id)
        assert session is not None
        assert session.model == "claude-haiku-4-5"

    def test_generate_uses_specified_model(self, client, mock_user_credits_storage):
        """Should use the model specified in the request."""
        response = client.post(
            "/api/generate",
            json={
                "prompt": "Create a complex microservices architecture",
                "model": "claude-sonnet-4-5"
            }
        )

        assert response.status_code == 200
        data = response.json()
        session_id = data["session_id"]

        # Check session was created with specified model
        from app.session.manager import session_manager
        session = session_manager.get_session(session_id)
        assert session is not None
        assert session.model == "claude-sonnet-4-5"

    def test_generate_creates_session_with_prompt_stored(self, client, mock_user_credits_storage):
        """Should create session with generation_prompt stored for background task."""
        prompt = "Create a database schema"
        response = client.post(
            "/api/generate",
            json={"prompt": prompt}
        )

        assert response.status_code == 200
        session_id = response.json()["session_id"]

        from app.session.manager import session_manager
        session = session_manager.get_session(session_id)
        assert session is not None
        # Note: In test env, background task runs synchronously so status may be completed
        # But we can verify the prompt was stored and status tracking was set up
        assert session.diagram_generation_status is not None
        assert session.diagram_generation_status.started_at is not None

    def test_generate_stores_prompt_in_session(self, client, mock_user_credits_storage):
        """Should store the prompt in session for background task."""
        prompt = "Design a real-time chat system"
        response = client.post(
            "/api/generate",
            json={"prompt": prompt}
        )

        assert response.status_code == 200
        session_id = response.json()["session_id"]

        from app.session.manager import session_manager
        session = session_manager.get_session(session_id)
        assert session.generation_prompt == prompt


class TestDiagramStatusEndpoint:
    """Tests for GET /api/session/{session_id}/diagram/status"""

    def test_diagram_status_returns_generating_while_pending(self, client):
        """Should return generating status when diagram is still being generated."""
        # Create a session with generating status
        from app.session.manager import session_manager
        from app.models import Diagram

        session_id = session_manager.create_session_for_generation(
            user_id="local-dev-user",
            model="claude-haiku-4-5",
            prompt="Test prompt"
        )

        response = client.get(f"/api/session/{session_id}/diagram/status")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "generating"
        assert "elapsed_seconds" in data
        assert data["error"] is None

    def test_diagram_status_returns_completed_with_diagram(self, client, simple_diagram):
        """Should return completed status with diagram when generation is done."""
        from app.session.manager import session_manager

        # Create a completed session
        session_id = session_manager.create_session(simple_diagram, user_id="local-dev-user")
        session_manager.set_diagram_generation_status(session_id, "completed")

        response = client.get(f"/api/session/{session_id}/diagram/status")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"
        assert "diagram" in data
        assert data["diagram"]["nodes"] is not None
        assert data["diagram"]["edges"] is not None

    def test_diagram_status_returns_failed_with_error(self, client):
        """Should return failed status with error message."""
        from app.session.manager import session_manager
        from app.models import Diagram

        # Create a session
        session_id = session_manager.create_session(
            Diagram(nodes=[], edges=[]),
            user_id="local-dev-user"
        )
        # Mark as failed
        error_msg = "LLM API rate limit exceeded"
        session_manager.set_diagram_generation_status(session_id, "failed", error=error_msg)

        response = client.get(f"/api/session/{session_id}/diagram/status")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "failed"
        assert data["error"] == error_msg

    def test_diagram_status_includes_elapsed_time(self, client):
        """Should include elapsed_seconds when still generating."""
        from app.session.manager import session_manager
        import time

        session_id = session_manager.create_session_for_generation(
            user_id="local-dev-user",
            model="claude-haiku-4-5",
            prompt="Test prompt"
        )

        # Small delay to ensure elapsed time > 0
        time.sleep(0.1)

        response = client.get(f"/api/session/{session_id}/diagram/status")

        assert response.status_code == 200
        data = response.json()
        assert "elapsed_seconds" in data
        assert data["elapsed_seconds"] >= 0.1

    def test_diagram_status_returns_404_for_nonexistent_session(self, client):
        """Should return 404 for non-existent session."""
        response = client.get("/api/session/nonexistent-session-id/diagram/status")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_diagram_status_includes_duration_when_completed(self, client, simple_diagram):
        """Should include duration_seconds when generation is completed."""
        from app.session.manager import session_manager
        import time

        # Create session for generation (sets started_at)
        session_id = session_manager.create_session_for_generation(
            user_id="local-dev-user",
            model="claude-haiku-4-5",
            prompt="Test prompt"
        )

        # Small delay
        time.sleep(0.1)

        # Update diagram and mark completed
        session_manager.update_diagram(session_id, simple_diagram)
        session_manager.set_diagram_generation_status(session_id, "completed")

        response = client.get(f"/api/session/{session_id}/diagram/status")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"
        assert "duration_seconds" in data
        assert data["duration_seconds"] >= 0.1
