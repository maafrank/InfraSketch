"""
Tests for chat endpoint:
- POST /api/chat
"""

import pytest
from fastapi.testclient import TestClient


class TestChatEndpoint:
    """Tests for POST /api/chat"""

    def test_chat_returns_response(self, client_with_session, mock_agent_graph):
        """Happy path: Chat returns response from agent."""
        client, session_id = client_with_session

        response = client.post(
            "/api/chat",
            json={
                "session_id": session_id,
                "message": "Add a load balancer to the system"
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert "response" in data
        assert len(data["response"]) > 0

    def test_chat_returns_404_for_nonexistent_session(self, client, mock_agent_graph):
        """Should return 404 for non-existent session."""
        response = client.post(
            "/api/chat",
            json={
                "session_id": "nonexistent-session-xyz",
                "message": "Hello"
            }
        )

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_chat_adds_messages_to_session(self, client_with_session, mock_agent_graph):
        """Should add user and assistant messages to session."""
        client, session_id = client_with_session
        user_message = "Add a Redis cache for session storage"

        response = client.post(
            "/api/chat",
            json={
                "session_id": session_id,
                "message": user_message
            }
        )

        assert response.status_code == 200

        # Verify messages were added
        from app.session.manager import session_manager
        session = session_manager.get_session(session_id)

        assert len(session.messages) >= 2  # At least user + assistant
        # Check user message was added
        user_msgs = [m for m in session.messages if m.role == "user"]
        assert any(m.content == user_message for m in user_msgs)

    def test_chat_handles_node_id_focus(self, client_with_session, mock_agent_graph):
        """Should handle node_id parameter for focused conversations."""
        client, session_id = client_with_session
        node_id = "api-gateway-1"  # From sample_node fixture

        response = client.post(
            "/api/chat",
            json={
                "session_id": session_id,
                "message": "What does this component do?",
                "node_id": node_id
            }
        )

        assert response.status_code == 200

        # Verify current_node was set
        from app.session.manager import session_manager
        session = session_manager.get_session(session_id)
        assert session.current_node == node_id

    def test_chat_uses_session_model_by_default(self, client_with_session, mock_agent_graph):
        """Should use the session's model when none specified."""
        client, session_id = client_with_session

        # Set a specific model on the session
        from app.session.manager import session_manager
        session_manager.update_model(session_id, "claude-sonnet-4-5")

        response = client.post(
            "/api/chat",
            json={
                "session_id": session_id,
                "message": "Analyze this architecture"
            }
        )

        assert response.status_code == 200

        # Verify agent was called with session model
        mock_agent_graph.invoke.assert_called_once()
        call_args = mock_agent_graph.invoke.call_args[0][0]
        assert call_args["model"] == "claude-sonnet-4-5"

    def test_chat_updates_model_when_specified(self, client_with_session, mock_agent_graph):
        """Should update session model when model parameter is provided."""
        client, session_id = client_with_session
        new_model = "claude-sonnet-4-5"

        response = client.post(
            "/api/chat",
            json={
                "session_id": session_id,
                "message": "Use a better model for this",
                "model": new_model
            }
        )

        assert response.status_code == 200

        # Verify model was updated in session
        from app.session.manager import session_manager
        session = session_manager.get_session(session_id)
        assert session.model == new_model

    def test_chat_invokes_agent_graph(self, client_with_session, mock_agent_graph):
        """Should invoke agent graph with correct parameters."""
        client, session_id = client_with_session
        message = "Add a database"

        response = client.post(
            "/api/chat",
            json={
                "session_id": session_id,
                "message": message
            }
        )

        assert response.status_code == 200
        mock_agent_graph.invoke.assert_called_once()

        # Check invoke was called with messages containing our message
        call_args = mock_agent_graph.invoke.call_args[0][0]
        assert "messages" in call_args
        assert "session_id" in call_args
        assert call_args["session_id"] == session_id

    def test_chat_returns_updated_diagram_when_changed(self, client_with_session, mock_agent_graph, sample_node):
        """Should return diagram when tools modify it."""
        client, session_id = client_with_session

        # Simulate agent modifying the diagram by updating session before response
        from app.session.manager import session_manager
        from app.models import Diagram

        # Get current session and add a node to simulate tool modification
        session = session_manager.get_session(session_id)
        new_diagram = Diagram(
            nodes=session.diagram.nodes + [sample_node],
            edges=session.diagram.edges
        )

        # Mock the agent to also trigger diagram update
        def invoke_with_diagram_update(state):
            session_manager.update_diagram(session_id, new_diagram)
            from langchain_core.messages import AIMessage
            return {
                "messages": [AIMessage(content="Added a new node")],
                "diagram": None,
                "design_doc": None,
            }

        mock_agent_graph.invoke.side_effect = invoke_with_diagram_update

        response = client.post(
            "/api/chat",
            json={
                "session_id": session_id,
                "message": "Add a new component"
            }
        )

        assert response.status_code == 200
        data = response.json()
        # Diagram should be included when it changed
        assert data.get("diagram") is not None

    def test_chat_returns_null_diagram_when_unchanged(self, client_with_session, mock_agent_graph):
        """Should return null diagram when no changes were made."""
        client, session_id = client_with_session

        response = client.post(
            "/api/chat",
            json={
                "session_id": session_id,
                "message": "Just a question, no changes needed"
            }
        )

        assert response.status_code == 200
        data = response.json()
        # Diagram should be null when unchanged
        assert data.get("diagram") is None
