"""
Unit tests for Pydantic models in app/models.py

Tests model validation, defaults, and serialization.
"""

import pytest
from pydantic import ValidationError
from app.models import (
    Node, Edge, Diagram, Message, SessionState,
    NodePosition, NodeMetadata, DesignDocStatus, DiagramGenerationStatus,
    GenerateRequest, ChatRequest, CreateGroupRequest
)


class TestNodePosition:
    """Tests for NodePosition model."""

    def test_valid_position(self):
        pos = NodePosition(x=100.5, y=200.0)
        assert pos.x == 100.5
        assert pos.y == 200.0

    def test_negative_position(self):
        """Negative positions should be valid."""
        pos = NodePosition(x=-50, y=-100)
        assert pos.x == -50
        assert pos.y == -100

    def test_integer_coercion(self):
        """Integers should be coerced to floats."""
        pos = NodePosition(x=100, y=200)
        assert isinstance(pos.x, float)


class TestNodeMetadata:
    """Tests for NodeMetadata model."""

    def test_empty_metadata(self):
        meta = NodeMetadata()
        assert meta.technology is None
        assert meta.notes is None
        assert meta.child_types is None

    def test_full_metadata(self):
        meta = NodeMetadata(
            technology="PostgreSQL",
            notes="Primary database",
            child_types=["database", "cache"]
        )
        assert meta.technology == "PostgreSQL"
        assert meta.notes == "Primary database"
        assert meta.child_types == ["database", "cache"]


class TestNode:
    """Tests for Node model."""

    def test_minimal_node(self):
        """Test node with only required fields."""
        node = Node(
            id="test-1",
            type="server",
            label="Test Server",
            description="A test server"
        )
        assert node.id == "test-1"
        assert node.inputs == []
        assert node.outputs == []
        assert node.is_group is False
        assert node.is_collapsed is False
        assert node.child_ids == []

    def test_full_node(self, sample_node):
        """Test node from fixture has all fields."""
        assert sample_node.id == "api-gateway-1"
        assert sample_node.type == "gateway"
        assert sample_node.metadata.technology == "AWS API Gateway"
        assert sample_node.position.x == 100

    def test_group_node(self, sample_group_node):
        """Test group node properties."""
        assert sample_group_node.is_group is True
        assert sample_group_node.is_collapsed is False
        assert len(sample_group_node.child_ids) == 2

    def test_node_missing_required_fields(self):
        """Test that missing required fields raise ValidationError."""
        with pytest.raises(ValidationError):
            Node(id="test")  # Missing type, label, description


class TestEdge:
    """Tests for Edge model."""

    def test_minimal_edge(self):
        """Test edge with only required fields."""
        edge = Edge(
            id="edge-1",
            source="node-a",
            target="node-b"
        )
        assert edge.label is None
        assert edge.type == "default"

    def test_animated_edge(self, sample_animated_edge):
        """Test animated edge type."""
        assert sample_animated_edge.type == "animated"

    def test_edge_with_label(self, sample_edge):
        """Test edge with label."""
        assert sample_edge.label == "SQL queries"

    def test_invalid_edge_type(self):
        """Test that invalid edge type raises ValidationError."""
        with pytest.raises(ValidationError):
            Edge(
                id="edge-1",
                source="a",
                target="b",
                type="invalid"  # Not "default" or "animated"
            )


class TestDiagram:
    """Tests for Diagram model."""

    def test_empty_diagram(self, empty_diagram):
        """Test empty diagram."""
        assert len(empty_diagram.nodes) == 0
        assert len(empty_diagram.edges) == 0

    def test_simple_diagram(self, simple_diagram):
        """Test diagram from fixture."""
        assert len(simple_diagram.nodes) == 2
        assert len(simple_diagram.edges) == 1

    def test_diagram_serialization(self, simple_diagram):
        """Test diagram can be serialized to dict."""
        data = simple_diagram.model_dump()
        assert "nodes" in data
        assert "edges" in data
        assert len(data["nodes"]) == 2


class TestMessage:
    """Tests for Message model."""

    def test_user_message(self, sample_user_message):
        """Test user message."""
        assert sample_user_message.role == "user"
        assert "load balancer" in sample_user_message.content

    def test_assistant_message(self, sample_assistant_message):
        """Test assistant message."""
        assert sample_assistant_message.role == "assistant"

    def test_invalid_role(self):
        """Test that invalid role raises ValidationError."""
        with pytest.raises(ValidationError):
            Message(role="system", content="test")  # Only "user" or "assistant"


class TestDesignDocStatus:
    """Tests for DesignDocStatus model."""

    def test_default_status(self):
        """Test default status is not_started."""
        status = DesignDocStatus()
        assert status.status == "not_started"
        assert status.error is None
        assert status.started_at is None
        assert status.completed_at is None

    def test_generating_status(self):
        """Test generating status with timestamp."""
        status = DesignDocStatus(
            status="generating",
            started_at=1234567890.0
        )
        assert status.status == "generating"
        assert status.started_at == 1234567890.0

    def test_failed_status(self):
        """Test failed status with error."""
        status = DesignDocStatus(
            status="failed",
            error="API timeout"
        )
        assert status.status == "failed"
        assert status.error == "API timeout"

    def test_invalid_status(self):
        """Test that invalid status raises ValidationError."""
        with pytest.raises(ValidationError):
            DesignDocStatus(status="invalid")


class TestDiagramGenerationStatus:
    """Tests for DiagramGenerationStatus model."""

    def test_default_status(self):
        """Test default status is not_started."""
        status = DiagramGenerationStatus()
        assert status.status == "not_started"

    def test_completed_status(self):
        """Test completed status with timestamps."""
        status = DiagramGenerationStatus(
            status="completed",
            started_at=1000.0,
            completed_at=1060.0
        )
        assert status.status == "completed"
        assert status.completed_at - status.started_at == 60.0


class TestSessionState:
    """Tests for SessionState model."""

    def test_sample_session(self, sample_session):
        """Test session from fixture."""
        assert sample_session.session_id == "session-test-abc123"
        assert sample_session.user_id == "user_test_123456"
        assert len(sample_session.diagram.nodes) == 2

    def test_session_with_messages(self, session_with_messages):
        """Test session with conversation history."""
        assert len(session_with_messages.messages) == 2

    def test_session_with_design_doc(self, session_with_design_doc):
        """Test session with design document."""
        assert session_with_design_doc.design_doc is not None
        assert session_with_design_doc.design_doc_status.status == "completed"

    def test_default_model(self, empty_diagram, test_user_id):
        """Test default model is set."""
        session = SessionState(
            session_id="test",
            user_id=test_user_id,
            diagram=empty_diagram
        )
        assert session.model == "claude-haiku-4-5-20251001"


class TestRequestModels:
    """Tests for API request models."""

    def test_generate_request(self):
        """Test GenerateRequest model."""
        req = GenerateRequest(prompt="Design a web app")
        assert req.prompt == "Design a web app"
        assert req.model is None  # Optional

    def test_generate_request_with_model(self):
        """Test GenerateRequest with custom model."""
        req = GenerateRequest(
            prompt="Design a web app",
            model="claude-sonnet-4-5-20251001"
        )
        assert req.model == "claude-sonnet-4-5-20251001"

    def test_chat_request(self):
        """Test ChatRequest model."""
        req = ChatRequest(
            session_id="abc123",
            message="Add caching"
        )
        assert req.node_id is None

    def test_chat_request_with_node(self):
        """Test ChatRequest with node focus."""
        req = ChatRequest(
            session_id="abc123",
            message="Update this node",
            node_id="node-1"
        )
        assert req.node_id == "node-1"

    def test_create_group_request(self):
        """Test CreateGroupRequest model."""
        req = CreateGroupRequest(
            child_node_ids=["node-1", "node-2", "node-3"]
        )
        assert len(req.child_node_ids) == 3
