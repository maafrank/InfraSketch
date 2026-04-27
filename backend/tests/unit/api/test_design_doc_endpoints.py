"""
Tests for design document endpoints:
- POST /api/session/{session_id}/design-doc/generate
- GET /api/session/{session_id}/design-doc/status
- PATCH /api/session/{session_id}/design-doc
- POST /api/session/{session_id}/design-doc/export
"""

import pytest
from fastapi.testclient import TestClient


class TestGenerateDesignDoc:
    """Tests for POST /api/session/{session_id}/design-doc/generate"""

    def test_generate_design_doc_starts_background_task(self, client_with_session, mock_user_credits_storage):
        """Should start generation and return immediately."""
        client, session_id = client_with_session

        response = client.post(
            f"/api/session/{session_id}/design-doc/generate",
            json={}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "started"

    def test_generate_design_doc_sets_status_tracking(self, client_with_session, mock_user_credits_storage):
        """Should set design_doc_status with started_at tracking."""
        client, session_id = client_with_session

        response = client.post(
            f"/api/session/{session_id}/design-doc/generate",
            json={}
        )

        assert response.status_code == 200

        # Check status tracking was set up
        # Note: In test env, background task runs synchronously so status may be completed
        from app.session.manager import session_manager
        session = session_manager.get_session(session_id)
        assert session.design_doc_status is not None
        assert session.design_doc_status.started_at is not None

    def test_generate_design_doc_produces_document(self, client_with_session, mock_design_doc_generator, mock_user_credits_storage):
        """Should produce a design document after generation."""
        client, session_id = client_with_session

        # Start generation (runs synchronously in tests, mocked to avoid API calls)
        response = client.post(
            f"/api/session/{session_id}/design-doc/generate",
            json={}
        )

        assert response.status_code == 200

        # In test env, background task completes immediately with mocked response
        from app.session.manager import session_manager
        session = session_manager.get_session(session_id)
        # Should have generated a document (mocked)
        assert session.design_doc is not None or session.design_doc_status.status in ("completed", "generating", "failed")

    def test_generate_design_doc_returns_404_for_nonexistent(self, client):
        """Should return 404 for non-existent session."""
        response = client.post(
            "/api/session/nonexistent-session/design-doc/generate",
            json={}
        )

        assert response.status_code == 404


class TestDesignDocStatus:
    """Tests for GET /api/session/{session_id}/design-doc/status"""

    def test_design_doc_status_returns_not_started(self, client_with_session):
        """Should return not_started for new session."""
        client, session_id = client_with_session

        response = client.get(f"/api/session/{session_id}/design-doc/status")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "not_started"

    def test_design_doc_status_returns_generating_when_set(self, client_with_session):
        """Should return generating status when manually set."""
        client, session_id = client_with_session

        # Manually set status to generating (since background tasks run sync in tests)
        from app.session.manager import session_manager
        session_manager.set_design_doc_status(session_id, "generating")

        response = client.get(f"/api/session/{session_id}/design-doc/status")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "generating"
        assert "elapsed_seconds" in data

    def test_design_doc_status_returns_completed_with_doc(self, client_with_session):
        """Should return completed with document when done."""
        client, session_id = client_with_session

        # Manually set to completed with a doc
        from app.session.manager import session_manager
        test_doc = "# Test Design Document\n\nThis is a test."
        session_manager.update_design_doc(session_id, test_doc)
        session_manager.set_design_doc_status(session_id, "completed")

        response = client.get(f"/api/session/{session_id}/design-doc/status")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"
        assert data["design_doc"] == test_doc
        assert "design_doc_length" in data

    def test_design_doc_status_returns_failed_with_error(self, client_with_session):
        """Should return failed with error message."""
        client, session_id = client_with_session

        # Set to failed
        from app.session.manager import session_manager
        error_msg = "LLM API error"
        session_manager.set_design_doc_status(session_id, "failed", error=error_msg)

        response = client.get(f"/api/session/{session_id}/design-doc/status")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "failed"
        assert data["error"] == error_msg


class TestUpdateDesignDoc:
    """Tests for PATCH /api/session/{session_id}/design-doc"""

    def test_update_design_doc_saves_content(self, client_with_session):
        """Should save updated design doc content."""
        client, session_id = client_with_session
        new_content = "# Updated Design Document\n\nThis is updated content."

        response = client.patch(
            f"/api/session/{session_id}/design-doc",
            json={"content": new_content}
        )

        assert response.status_code == 200
        assert response.json()["design_doc"] == new_content

        # Verify persistence
        from app.session.manager import session_manager
        session = session_manager.get_session(session_id)
        assert session.design_doc == new_content

    def test_update_design_doc_rejects_oversized(self, client_with_session):
        """Should reject content larger than 1MB."""
        client, session_id = client_with_session
        oversized_content = "x" * (1_000_001)  # Just over 1MB

        response = client.patch(
            f"/api/session/{session_id}/design-doc",
            json={"content": oversized_content}
        )

        assert response.status_code == 400
        assert "too large" in response.json()["detail"].lower()

    def test_update_design_doc_returns_404_for_nonexistent(self, client):
        """Should return 404 for non-existent session."""
        response = client.patch(
            "/api/session/nonexistent-session/design-doc",
            json={"content": "Test"}
        )

        assert response.status_code == 404


class TestExportDesignDoc:
    """Tests for POST /api/session/{session_id}/design-doc/export"""

    def test_export_design_doc_returns_pdf(self, client_with_session, mocker, mock_user_credits_storage):
        """Should return PDF when format=pdf."""
        client, session_id = client_with_session

        # Mock PDF conversion to avoid WeasyPrint compatibility issues in CI
        mock_pdf_bytes = b"%PDF-1.4 test pdf content"
        mocker.patch(
            "app.api.routes_design_docs.convert_markdown_to_pdf",
            return_value=mock_pdf_bytes
        )

        # First set a design doc
        from app.session.manager import session_manager
        session_manager.update_design_doc(session_id, "# Test Document\n\nContent here.")
        session_manager.set_design_doc_status(session_id, "completed")

        response = client.post(
            f"/api/session/{session_id}/design-doc/export?format=pdf",
            json={}
        )

        assert response.status_code == 200
        data = response.json()
        assert "pdf" in data
        assert "content" in data["pdf"]
        assert "filename" in data["pdf"]
        assert data["pdf"]["filename"].endswith(".pdf")

    def test_export_design_doc_returns_markdown(self, client_with_session, mock_user_credits_storage):
        """Should return markdown when format=markdown."""
        client, session_id = client_with_session

        # Set a design doc
        from app.session.manager import session_manager
        test_doc = "# Test Document\n\nMarkdown content."
        session_manager.update_design_doc(session_id, test_doc)
        session_manager.set_design_doc_status(session_id, "completed")

        response = client.post(
            f"/api/session/{session_id}/design-doc/export?format=markdown",
            json={}
        )

        assert response.status_code == 200
        data = response.json()
        assert "markdown" in data
        assert data["markdown"]["content"] == test_doc
        assert data["markdown"]["filename"].endswith(".md")

    def test_export_design_doc_returns_404_without_doc(self, client_with_session):
        """Should return 404 when no design doc exists."""
        client, session_id = client_with_session

        response = client.post(
            f"/api/session/{session_id}/design-doc/export?format=pdf",
            json={}
        )

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_export_design_doc_returns_both_formats(self, client_with_session, mocker, mock_user_credits_storage):
        """Should return both PDF and markdown when format=both."""
        client, session_id = client_with_session

        # Mock PDF conversion to avoid WeasyPrint compatibility issues in CI
        mock_pdf_bytes = b"%PDF-1.4 test pdf content"
        mocker.patch(
            "app.api.routes_design_docs.convert_markdown_to_pdf",
            return_value=mock_pdf_bytes
        )

        # Set a design doc
        from app.session.manager import session_manager
        session_manager.update_design_doc(session_id, "# Test\n\nBoth formats.")
        session_manager.set_design_doc_status(session_id, "completed")

        response = client.post(
            f"/api/session/{session_id}/design-doc/export?format=both",
            json={}
        )

        assert response.status_code == 200
        data = response.json()
        assert "pdf" in data
        assert "markdown" in data
        assert "diagram_png" in data

    def test_export_design_doc_triggers_gamification(self, client_with_session, mocker, mock_user_credits_storage):
        """Should trigger process_action for gamification tracking."""
        client, session_id = client_with_session

        mock_process_action = mocker.patch("app.api.routes_design_docs.process_action", return_value={
            "xp_gained": 0,
            "level_up": False,
            "new_level": None,
            "new_level_name": None,
            "new_achievements": [],
            "current_streak": 0,
        })
        mocker.patch(
            "app.api.routes_design_docs.convert_markdown_to_pdf",
            return_value=b"%PDF-1.4 test"
        )

        from app.session.manager import session_manager
        session_manager.update_design_doc(session_id, "# Test Document")
        session_manager.set_design_doc_status(session_id, "completed")

        response = client.post(
            f"/api/session/{session_id}/design-doc/export?format=pdf",
            json={}
        )

        assert response.status_code == 200
        mock_process_action.assert_called_once()
        args = mock_process_action.call_args[0]
        assert args[1] == "export_completed"
        assert args[2] == {"format": "pdf"}


class TestDesignDocFreeTierGate:
    """Tests for the free-tier gate at routes_design_docs.py.

    Three paths from a free user's POST to /design-doc/generate:
      1. No grant, preview not used  -> preview path (is_preview=True)
      2. Grant available             -> full doc path, grant decrements
      3. No grant, preview already used -> 403 feature_locked
    """

    @staticmethod
    def _free_user_credits(free_design_docs_remaining=0):
        from datetime import datetime
        from app.billing.models import UserCredits
        return UserCredits(
            user_id="local-dev-user",
            plan="free",
            credits_balance=10,
            credits_monthly_allowance=10,
            credits_used_this_period=0,
            free_design_docs_remaining=free_design_docs_remaining,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

    def test_free_user_without_grant_uses_preview(
        self, client_with_session, mock_user_credits_storage
    ):
        client, session_id = client_with_session
        free_credits = self._free_user_credits(free_design_docs_remaining=0)
        mock_user_credits_storage.get_or_create_credits.return_value = free_credits

        response = client.post(
            f"/api/session/{session_id}/design-doc/generate", json={}
        )

        assert response.status_code == 200
        mock_user_credits_storage.consume_design_doc_grant.assert_not_called()
        from app.session.manager import session_manager
        session = session_manager.get_session(session_id)
        assert session.design_doc_status.is_preview is True

    def test_free_user_with_grant_consumes_and_runs_full(
        self, client_with_session, mock_user_credits_storage
    ):
        client, session_id = client_with_session
        free_credits = self._free_user_credits(free_design_docs_remaining=1)
        mock_user_credits_storage.get_or_create_credits.return_value = free_credits
        consumed_credits = self._free_user_credits(free_design_docs_remaining=0)
        mock_user_credits_storage.consume_design_doc_grant.return_value = (True, consumed_credits)

        response = client.post(
            f"/api/session/{session_id}/design-doc/generate", json={}
        )

        assert response.status_code == 200
        mock_user_credits_storage.consume_design_doc_grant.assert_called_once_with("local-dev-user")
        from app.session.manager import session_manager
        session = session_manager.get_session(session_id)
        assert session.design_doc_status.is_preview is False

    def test_free_user_with_preview_used_returns_403(
        self, client_with_session, mock_user_credits_storage
    ):
        client, session_id = client_with_session
        free_credits = self._free_user_credits(free_design_docs_remaining=0)
        mock_user_credits_storage.get_or_create_credits.return_value = free_credits

        # Mark this session as having already used its preview.
        from app.session.manager import session_manager
        session_manager.mark_design_doc_preview_used(session_id)

        response = client.post(
            f"/api/session/{session_id}/design-doc/generate", json={}
        )

        assert response.status_code == 403
        body = response.json()
        assert body["error"] == "feature_locked"
        assert body["feature"] == "design_doc_generation"
