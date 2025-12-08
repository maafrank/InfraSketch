"""
Unit tests for SessionManager in app/session/manager.py

Tests session CRUD operations using in-memory storage.
"""

import pytest
from app.models import Diagram, Node, Edge, Message, NodePosition
from app.session.manager import SessionManager


class TestSessionCreation:
    """Tests for creating sessions."""

    def test_create_session(self, fresh_session_manager, simple_diagram, test_user_id):
        """Test creating a new session."""
        session_id = fresh_session_manager.create_session(simple_diagram, test_user_id)

        assert session_id is not None
        assert len(session_id) == 36  # UUID format

        # Verify session was stored
        session = fresh_session_manager.get_session(session_id)
        assert session is not None
        assert session.user_id == test_user_id
        assert len(session.diagram.nodes) == 2

    def test_create_session_with_custom_model(self, fresh_session_manager, simple_diagram, test_user_id):
        """Test creating session with custom model."""
        session_id = fresh_session_manager.create_session(
            simple_diagram,
            test_user_id,
            model="claude-sonnet-4-5-20251001"
        )

        session = fresh_session_manager.get_session(session_id)
        assert session.model == "claude-sonnet-4-5-20251001"

    def test_create_session_has_timestamp(self, fresh_session_manager, simple_diagram, test_user_id):
        """Test that created session has a timestamp."""
        session_id = fresh_session_manager.create_session(simple_diagram, test_user_id)
        session = fresh_session_manager.get_session(session_id)

        assert session.created_at is not None

    def test_create_session_for_generation(self, fresh_session_manager, test_user_id):
        """Test creating session for async generation."""
        session_id = fresh_session_manager.create_session_for_generation(
            user_id=test_user_id,
            model="claude-haiku-4-5-20251001",
            prompt="Design a web app"
        )

        session = fresh_session_manager.get_session(session_id)
        assert session is not None
        assert session.generation_prompt == "Design a web app"
        assert session.diagram_generation_status.status == "generating"
        assert len(session.diagram.nodes) == 0  # Empty placeholder


class TestSessionRetrieval:
    """Tests for retrieving sessions."""

    def test_get_existing_session(self, session_manager_with_session):
        """Test getting an existing session."""
        manager, session_id = session_manager_with_session
        session = manager.get_session(session_id)

        assert session is not None
        assert session.session_id == session_id

    def test_get_nonexistent_session(self, fresh_session_manager):
        """Test getting a session that doesn't exist."""
        session = fresh_session_manager.get_session("nonexistent-id")
        assert session is None

    def test_get_user_sessions(self, fresh_session_manager, simple_diagram, test_user_id):
        """Test getting all sessions for a user."""
        # Create multiple sessions
        fresh_session_manager.create_session(simple_diagram, test_user_id)
        fresh_session_manager.create_session(simple_diagram, test_user_id)
        fresh_session_manager.create_session(simple_diagram, "other_user_id")

        # Get sessions for test user
        sessions = fresh_session_manager.get_user_sessions(test_user_id)
        assert len(sessions) == 2

        # All sessions should belong to test user
        for session in sessions:
            assert session.user_id == test_user_id

    def test_get_user_sessions_sorted_by_date(self, fresh_session_manager, simple_diagram, test_user_id):
        """Test that sessions are sorted newest first."""
        import time

        # Create sessions with small delays
        id1 = fresh_session_manager.create_session(simple_diagram, test_user_id)
        time.sleep(0.01)
        id2 = fresh_session_manager.create_session(simple_diagram, test_user_id)
        time.sleep(0.01)
        id3 = fresh_session_manager.create_session(simple_diagram, test_user_id)

        sessions = fresh_session_manager.get_user_sessions(test_user_id)

        # Most recent should be first
        assert sessions[0].session_id == id3
        assert sessions[2].session_id == id1


class TestSessionOwnership:
    """Tests for session ownership verification."""

    def test_verify_ownership_valid(self, session_manager_with_session, test_user_id):
        """Test ownership verification with correct user."""
        manager, session_id = session_manager_with_session
        assert manager.verify_ownership(session_id, test_user_id) is True

    def test_verify_ownership_invalid_user(self, session_manager_with_session):
        """Test ownership verification with wrong user."""
        manager, session_id = session_manager_with_session
        assert manager.verify_ownership(session_id, "wrong_user_id") is False

    def test_verify_ownership_nonexistent_session(self, fresh_session_manager, test_user_id):
        """Test ownership verification with nonexistent session."""
        assert fresh_session_manager.verify_ownership("nonexistent", test_user_id) is False


class TestDiagramUpdates:
    """Tests for updating diagrams."""

    def test_update_diagram(self, session_manager_with_session):
        """Test updating a session's diagram."""
        manager, session_id = session_manager_with_session

        # Create new diagram with additional node
        new_node = Node(
            id="new-node",
            type="cache",
            label="New Cache",
            description="A new cache node",
            position=NodePosition(x=0, y=0)
        )
        new_diagram = Diagram(nodes=[new_node], edges=[])

        result = manager.update_diagram(session_id, new_diagram)
        assert result is True

        # Verify update
        session = manager.get_session(session_id)
        assert len(session.diagram.nodes) == 1
        assert session.diagram.nodes[0].id == "new-node"

    def test_update_diagram_nonexistent_session(self, fresh_session_manager, empty_diagram):
        """Test updating diagram for nonexistent session."""
        result = fresh_session_manager.update_diagram("nonexistent", empty_diagram)
        assert result is False


class TestMessageOperations:
    """Tests for message operations."""

    def test_add_message(self, session_manager_with_session):
        """Test adding a message to session."""
        manager, session_id = session_manager_with_session

        message = Message(role="user", content="Hello")
        result = manager.add_message(session_id, message)
        assert result is True

        session = manager.get_session(session_id)
        assert len(session.messages) == 1
        assert session.messages[0].content == "Hello"

    def test_add_multiple_messages(self, session_manager_with_session):
        """Test adding multiple messages."""
        manager, session_id = session_manager_with_session

        manager.add_message(session_id, Message(role="user", content="Question"))
        manager.add_message(session_id, Message(role="assistant", content="Answer"))

        session = manager.get_session(session_id)
        assert len(session.messages) == 2
        assert session.messages[0].role == "user"
        assert session.messages[1].role == "assistant"

    def test_add_message_nonexistent_session(self, fresh_session_manager):
        """Test adding message to nonexistent session."""
        message = Message(role="user", content="Hello")
        result = fresh_session_manager.add_message("nonexistent", message)
        assert result is False


class TestDesignDocOperations:
    """Tests for design document operations."""

    def test_update_design_doc(self, session_manager_with_session):
        """Test updating design document."""
        manager, session_id = session_manager_with_session

        result = manager.update_design_doc(session_id, "# Design Doc\n\nContent here")
        assert result is True

        session = manager.get_session(session_id)
        assert session.design_doc == "# Design Doc\n\nContent here"

    def test_set_design_doc_status_generating(self, session_manager_with_session):
        """Test setting design doc status to generating."""
        manager, session_id = session_manager_with_session

        result = manager.set_design_doc_status(session_id, "generating")
        assert result is True

        status = manager.get_design_doc_status(session_id)
        assert status.status == "generating"
        assert status.started_at is not None

    def test_set_design_doc_status_completed(self, session_manager_with_session):
        """Test setting design doc status to completed."""
        manager, session_id = session_manager_with_session

        manager.set_design_doc_status(session_id, "generating")
        manager.set_design_doc_status(session_id, "completed")

        status = manager.get_design_doc_status(session_id)
        assert status.status == "completed"
        assert status.completed_at is not None

    def test_set_design_doc_status_failed(self, session_manager_with_session):
        """Test setting design doc status to failed with error."""
        manager, session_id = session_manager_with_session

        result = manager.set_design_doc_status(session_id, "failed", error="API error")
        assert result is True

        status = manager.get_design_doc_status(session_id)
        assert status.status == "failed"
        assert status.error == "API error"

    def test_get_design_doc_status_nonexistent(self, fresh_session_manager):
        """Test getting design doc status for nonexistent session."""
        status = fresh_session_manager.get_design_doc_status("nonexistent")
        assert status is None


class TestDiagramGenerationStatus:
    """Tests for diagram generation status operations."""

    def test_set_diagram_generation_status(self, session_manager_with_session):
        """Test setting diagram generation status."""
        manager, session_id = session_manager_with_session

        result = manager.set_diagram_generation_status(session_id, "completed")
        assert result is True

        status = manager.get_diagram_generation_status(session_id)
        assert status.status == "completed"

    def test_diagram_generation_status_timestamps(self, fresh_session_manager, test_user_id):
        """Test diagram generation status timestamps."""
        session_id = fresh_session_manager.create_session_for_generation(
            user_id=test_user_id,
            model="claude-haiku-4-5-20251001",
            prompt="Test prompt"
        )

        status = fresh_session_manager.get_diagram_generation_status(session_id)
        assert status.started_at is not None  # Set on creation

        fresh_session_manager.set_diagram_generation_status(session_id, "completed")
        status = fresh_session_manager.get_diagram_generation_status(session_id)
        assert status.completed_at is not None


class TestSessionNameOperations:
    """Tests for session name operations."""

    def test_update_session_name(self, session_manager_with_session):
        """Test updating session name."""
        manager, session_id = session_manager_with_session

        result = manager.update_session_name(session_id, "My Design")
        assert result is True

        session = manager.get_session(session_id)
        assert session.name == "My Design"
        assert session.name_generated is True

    def test_update_session_name_nonexistent(self, fresh_session_manager):
        """Test updating name for nonexistent session."""
        result = fresh_session_manager.update_session_name("nonexistent", "Name")
        assert result is False


class TestSessionDeletion:
    """Tests for deleting sessions."""

    def test_delete_session(self, session_manager_with_session):
        """Test deleting a session."""
        manager, session_id = session_manager_with_session

        result = manager.delete_session(session_id)
        assert result is True

        # Verify deletion
        session = manager.get_session(session_id)
        assert session is None

    def test_delete_nonexistent_session(self, fresh_session_manager):
        """Test deleting nonexistent session."""
        result = fresh_session_manager.delete_session("nonexistent")
        assert result is False


class TestModelOperations:
    """Tests for model operations."""

    def test_update_model(self, session_manager_with_session):
        """Test updating session model."""
        manager, session_id = session_manager_with_session

        result = manager.update_model(session_id, "claude-sonnet-4-5-20251001")
        assert result is True

        session = manager.get_session(session_id)
        assert session.model == "claude-sonnet-4-5-20251001"

    def test_update_model_nonexistent(self, fresh_session_manager):
        """Test updating model for nonexistent session."""
        result = fresh_session_manager.update_model("nonexistent", "claude-sonnet-4-5-20251001")
        assert result is False


class TestCurrentNodeOperations:
    """Tests for current node focus operations."""

    def test_set_current_node(self, session_manager_with_session):
        """Test setting current node focus."""
        manager, session_id = session_manager_with_session

        result = manager.set_current_node(session_id, "node-1")
        assert result is True

        session = manager.get_session(session_id)
        assert session.current_node == "node-1"

    def test_clear_current_node(self, session_manager_with_session):
        """Test clearing current node focus."""
        manager, session_id = session_manager_with_session

        manager.set_current_node(session_id, "node-1")
        manager.set_current_node(session_id, None)

        session = manager.get_session(session_id)
        assert session.current_node is None
