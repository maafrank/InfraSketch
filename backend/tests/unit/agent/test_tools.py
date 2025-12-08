"""
Unit tests for agent tools in app/agent/tools.py

Tests each tool function in isolation with a mocked session manager.
"""

import pytest
from unittest.mock import patch, MagicMock

from app.models import Node, Edge, Diagram, SessionState, NodePosition, NodeMetadata
from app.agent.tools import (
    add_node, delete_node, update_node,
    add_edge, delete_edge,
    update_design_doc_section, replace_entire_design_doc
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def mock_session_with_diagram(test_user_id):
    """Create a mock session with a simple diagram."""
    diagram = Diagram(
        nodes=[
            Node(
                id="api-server-1",
                type="api",
                label="API Server",
                description="Handles API requests",
                position=NodePosition(x=100, y=100),
                metadata=NodeMetadata(technology="FastAPI")
            ),
            Node(
                id="postgres-db-1",
                type="database",
                label="PostgreSQL",
                description="Primary database",
                position=NodePosition(x=300, y=100),
                metadata=NodeMetadata(technology="PostgreSQL 15")
            )
        ],
        edges=[
            Edge(
                id="api-to-db",
                source="api-server-1",
                target="postgres-db-1",
                label="SQL queries"
            )
        ]
    )
    return SessionState(
        session_id="test-session-123",
        user_id=test_user_id,
        diagram=diagram,
        messages=[]
    )


@pytest.fixture
def mock_session_with_design_doc(mock_session_with_diagram):
    """Session with a design document."""
    mock_session_with_diagram.design_doc = """# System Design

## System Overview

This is the overview section.

## Architecture

This is the architecture section.

## Conclusion

This is the conclusion.
"""
    return mock_session_with_diagram


@pytest.fixture
def mock_session_with_group(test_user_id):
    """Create a mock session with a group node."""
    diagram = Diagram(
        nodes=[
            Node(
                id="backend-group",
                type="group",
                label="Backend Services",
                description="Group of backend services",
                is_group=True,
                is_collapsed=False,
                child_ids=["service-1", "service-2"],
                position=NodePosition(x=200, y=200)
            ),
            Node(
                id="service-1",
                type="service",
                label="Service 1",
                description="First service",
                parent_id="backend-group",
                position=NodePosition(x=100, y=100)
            ),
            Node(
                id="service-2",
                type="service",
                label="Service 2",
                description="Second service",
                parent_id="backend-group",
                position=NodePosition(x=300, y=100)
            )
        ],
        edges=[
            Edge(id="edge-1", source="service-1", target="service-2", label="calls")
        ]
    )
    return SessionState(
        session_id="test-session-group",
        user_id=test_user_id,
        diagram=diagram,
        messages=[]
    )


# ============================================================================
# add_node Tests
# ============================================================================

class TestAddNode:
    """Tests for add_node tool."""

    def test_add_node_success(self, mock_session_with_diagram):
        """Test successfully adding a new node."""
        with patch("app.agent.tools.session_manager") as mock_manager:
            mock_manager.get_session.return_value = mock_session_with_diagram
            mock_manager.update_diagram.return_value = True

            result = add_node.invoke({
                "node_id": "redis-cache-1",
                "type": "cache",
                "label": "Redis Cache",
                "description": "In-memory cache for session data",
                "technology": "Redis 7.0",
                "position": {"x": 200, "y": 200},
                "session_id": "test-session-123"
            })

            assert result["success"] is True
            assert "redis-cache-1" in result["message"]

            # Verify node was added to diagram
            assert len(mock_session_with_diagram.diagram.nodes) == 3

    def test_add_node_duplicate_id(self, mock_session_with_diagram):
        """Test adding node with existing ID fails."""
        with patch("app.agent.tools.session_manager") as mock_manager:
            mock_manager.get_session.return_value = mock_session_with_diagram

            result = add_node.invoke({
                "node_id": "api-server-1",  # Already exists
                "type": "api",
                "label": "Another API",
                "description": "Test",
                "technology": "Flask",
                "position": {"x": 0, "y": 0},
                "session_id": "test-session-123"
            })

            assert result["success"] is False
            assert "already exists" in result["error"]

    def test_add_node_session_not_found(self):
        """Test adding node to nonexistent session."""
        with patch("app.agent.tools.session_manager") as mock_manager:
            mock_manager.get_session.return_value = None

            result = add_node.invoke({
                "node_id": "new-node",
                "type": "api",
                "label": "New Node",
                "description": "Test",
                "technology": "Test",
                "position": {"x": 0, "y": 0},
                "session_id": "nonexistent"
            })

            assert result["success"] is False
            assert "not found" in result["error"]

    def test_add_node_with_optional_fields(self, mock_session_with_diagram):
        """Test adding node with all optional fields."""
        with patch("app.agent.tools.session_manager") as mock_manager:
            mock_manager.get_session.return_value = mock_session_with_diagram
            mock_manager.update_diagram.return_value = True

            result = add_node.invoke({
                "node_id": "queue-1",
                "type": "queue",
                "label": "Message Queue",
                "description": "Async message processing",
                "technology": "RabbitMQ",
                "position": {"x": 400, "y": 100},
                "session_id": "test-session-123",
                "inputs": ["API requests"],
                "outputs": ["Worker jobs"],
                "notes": "Requires 3 nodes for HA"
            })

            assert result["success"] is True

            # Check the added node has optional fields
            added_node = mock_session_with_diagram.diagram.nodes[-1]
            assert added_node.inputs == ["API requests"]
            assert added_node.outputs == ["Worker jobs"]
            assert added_node.metadata.notes == "Requires 3 nodes for HA"


# ============================================================================
# delete_node Tests
# ============================================================================

class TestDeleteNode:
    """Tests for delete_node tool."""

    def test_delete_node_success(self, mock_session_with_diagram):
        """Test successfully deleting a node."""
        with patch("app.agent.tools.session_manager") as mock_manager:
            mock_manager.get_session.return_value = mock_session_with_diagram
            mock_manager.update_diagram.return_value = True

            result = delete_node.invoke({
                "node_id": "api-server-1",
                "session_id": "test-session-123"
            })

            assert result["success"] is True
            assert len(mock_session_with_diagram.diagram.nodes) == 1
            # Edge should also be deleted (connected to api-server-1)
            assert len(mock_session_with_diagram.diagram.edges) == 0

    def test_delete_node_not_found(self, mock_session_with_diagram):
        """Test deleting nonexistent node."""
        with patch("app.agent.tools.session_manager") as mock_manager:
            mock_manager.get_session.return_value = mock_session_with_diagram

            result = delete_node.invoke({
                "node_id": "nonexistent-node",
                "session_id": "test-session-123"
            })

            assert result["success"] is False
            assert "not found" in result["error"]

    def test_delete_group_node_cascades(self, mock_session_with_group):
        """Test deleting group node also deletes children."""
        with patch("app.agent.tools.session_manager") as mock_manager:
            mock_manager.get_session.return_value = mock_session_with_group
            mock_manager.update_diagram.return_value = True

            result = delete_node.invoke({
                "node_id": "backend-group",
                "session_id": "test-session-group"
            })

            assert result["success"] is True
            assert "child node(s)" in result["message"]
            # All nodes should be deleted (group + 2 children)
            assert len(mock_session_with_group.diagram.nodes) == 0
            # Edges connected to children should also be deleted
            assert len(mock_session_with_group.diagram.edges) == 0


# ============================================================================
# update_node Tests
# ============================================================================

class TestUpdateNode:
    """Tests for update_node tool."""

    def test_update_node_label(self, mock_session_with_diagram):
        """Test updating node label."""
        with patch("app.agent.tools.session_manager") as mock_manager:
            mock_manager.get_session.return_value = mock_session_with_diagram
            mock_manager.update_diagram.return_value = True

            result = update_node.invoke({
                "node_id": "api-server-1",
                "session_id": "test-session-123",
                "label": "Updated API Server"
            })

            assert result["success"] is True
            assert "label" in result["message"]

            # Verify update
            updated_node = next(n for n in mock_session_with_diagram.diagram.nodes if n.id == "api-server-1")
            assert updated_node.label == "Updated API Server"

    def test_update_node_multiple_fields(self, mock_session_with_diagram):
        """Test updating multiple fields at once."""
        with patch("app.agent.tools.session_manager") as mock_manager:
            mock_manager.get_session.return_value = mock_session_with_diagram
            mock_manager.update_diagram.return_value = True

            result = update_node.invoke({
                "node_id": "postgres-db-1",
                "session_id": "test-session-123",
                "label": "MongoDB",
                "technology": "MongoDB 6.0",
                "type": "database",
                "description": "NoSQL document database"
            })

            assert result["success"] is True

            updated_node = next(n for n in mock_session_with_diagram.diagram.nodes if n.id == "postgres-db-1")
            assert updated_node.label == "MongoDB"
            assert updated_node.metadata.technology == "MongoDB 6.0"

    def test_update_node_not_found(self, mock_session_with_diagram):
        """Test updating nonexistent node."""
        with patch("app.agent.tools.session_manager") as mock_manager:
            mock_manager.get_session.return_value = mock_session_with_diagram

            result = update_node.invoke({
                "node_id": "nonexistent",
                "session_id": "test-session-123",
                "label": "New Label"
            })

            assert result["success"] is False
            assert "not found" in result["error"]

    def test_update_node_no_fields(self, mock_session_with_diagram):
        """Test updating with no fields provided."""
        with patch("app.agent.tools.session_manager") as mock_manager:
            mock_manager.get_session.return_value = mock_session_with_diagram

            result = update_node.invoke({
                "node_id": "api-server-1",
                "session_id": "test-session-123"
            })

            assert result["success"] is False
            assert "No fields" in result["error"]


# ============================================================================
# add_edge Tests
# ============================================================================

class TestAddEdge:
    """Tests for add_edge tool."""

    def test_add_edge_success(self, mock_session_with_diagram):
        """Test successfully adding an edge."""
        # First add a third node to connect
        mock_session_with_diagram.diagram.nodes.append(
            Node(
                id="redis-cache-1",
                type="cache",
                label="Redis",
                description="Cache",
                position=NodePosition(x=200, y=200)
            )
        )

        with patch("app.agent.tools.session_manager") as mock_manager:
            mock_manager.get_session.return_value = mock_session_with_diagram
            mock_manager.update_diagram.return_value = True

            result = add_edge.invoke({
                "edge_id": "api-to-cache",
                "source": "api-server-1",
                "target": "redis-cache-1",
                "label": "Cache lookups",
                "session_id": "test-session-123"
            })

            assert result["success"] is True
            assert len(mock_session_with_diagram.diagram.edges) == 2

    def test_add_edge_source_not_found(self, mock_session_with_diagram):
        """Test adding edge with nonexistent source."""
        with patch("app.agent.tools.session_manager") as mock_manager:
            mock_manager.get_session.return_value = mock_session_with_diagram

            result = add_edge.invoke({
                "edge_id": "bad-edge",
                "source": "nonexistent-node",
                "target": "postgres-db-1",
                "label": "Test",
                "session_id": "test-session-123"
            })

            assert result["success"] is False
            assert "Source node" in result["error"]

    def test_add_edge_target_not_found(self, mock_session_with_diagram):
        """Test adding edge with nonexistent target."""
        with patch("app.agent.tools.session_manager") as mock_manager:
            mock_manager.get_session.return_value = mock_session_with_diagram

            result = add_edge.invoke({
                "edge_id": "bad-edge",
                "source": "api-server-1",
                "target": "nonexistent-node",
                "label": "Test",
                "session_id": "test-session-123"
            })

            assert result["success"] is False
            assert "Target node" in result["error"]

    def test_add_edge_duplicate_id(self, mock_session_with_diagram):
        """Test adding edge with existing ID."""
        with patch("app.agent.tools.session_manager") as mock_manager:
            mock_manager.get_session.return_value = mock_session_with_diagram

            result = add_edge.invoke({
                "edge_id": "api-to-db",  # Already exists
                "source": "api-server-1",
                "target": "postgres-db-1",
                "label": "Duplicate",
                "session_id": "test-session-123"
            })

            assert result["success"] is False
            assert "already exists" in result["error"]

    def test_add_edge_animated_type(self, mock_session_with_diagram):
        """Test adding animated edge."""
        mock_session_with_diagram.diagram.nodes.append(
            Node(
                id="queue-1",
                type="queue",
                label="Queue",
                description="Message queue",
                position=NodePosition(x=200, y=200)
            )
        )

        with patch("app.agent.tools.session_manager") as mock_manager:
            mock_manager.get_session.return_value = mock_session_with_diagram
            mock_manager.update_diagram.return_value = True

            result = add_edge.invoke({
                "edge_id": "api-to-queue",
                "source": "api-server-1",
                "target": "queue-1",
                "label": "Async messages",
                "type": "animated",
                "session_id": "test-session-123"
            })

            assert result["success"] is True

            added_edge = mock_session_with_diagram.diagram.edges[-1]
            assert added_edge.type == "animated"


# ============================================================================
# delete_edge Tests
# ============================================================================

class TestDeleteEdge:
    """Tests for delete_edge tool."""

    def test_delete_edge_success(self, mock_session_with_diagram):
        """Test successfully deleting an edge."""
        with patch("app.agent.tools.session_manager") as mock_manager:
            mock_manager.get_session.return_value = mock_session_with_diagram
            mock_manager.update_diagram.return_value = True

            result = delete_edge.invoke({
                "edge_id": "api-to-db",
                "session_id": "test-session-123"
            })

            assert result["success"] is True
            assert len(mock_session_with_diagram.diagram.edges) == 0

    def test_delete_edge_not_found_succeeds(self, mock_session_with_diagram):
        """Test deleting nonexistent edge succeeds gracefully."""
        with patch("app.agent.tools.session_manager") as mock_manager:
            mock_manager.get_session.return_value = mock_session_with_diagram

            result = delete_edge.invoke({
                "edge_id": "nonexistent-edge",
                "session_id": "test-session-123"
            })

            # Should succeed because goal was to remove it
            assert result["success"] is True
            assert "not found" in result["message"]


# ============================================================================
# update_design_doc_section Tests
# ============================================================================

class TestUpdateDesignDocSection:
    """Tests for update_design_doc_section tool."""

    def test_update_section_success(self, mock_session_with_design_doc):
        """Test successfully updating a section."""
        with patch("app.agent.tools.session_manager") as mock_manager:
            mock_manager.get_session.return_value = mock_session_with_design_doc
            mock_manager.update_design_doc.return_value = True

            result = update_design_doc_section.invoke({
                "section_start_marker": "## System Overview",
                "section_end_marker": "## Architecture",
                "section_content": "\n\nThis is the updated overview section.\n\n",
                "session_id": "test-session-123"
            })

            assert result["success"] is True

    def test_update_section_marker_not_found(self, mock_session_with_design_doc):
        """Test updating with nonexistent marker."""
        with patch("app.agent.tools.session_manager") as mock_manager:
            mock_manager.get_session.return_value = mock_session_with_design_doc

            result = update_design_doc_section.invoke({
                "section_start_marker": "## Nonexistent Section",
                "section_content": "New content",
                "session_id": "test-session-123"
            })

            assert result["success"] is False
            assert "not found" in result["error"]

    def test_update_section_no_design_doc(self, mock_session_with_diagram):
        """Test updating when no design doc exists."""
        with patch("app.agent.tools.session_manager") as mock_manager:
            mock_manager.get_session.return_value = mock_session_with_diagram

            result = update_design_doc_section.invoke({
                "section_start_marker": "## Overview",
                "section_content": "Content",
                "session_id": "test-session-123"
            })

            assert result["success"] is False
            assert "No design document" in result["error"]


# ============================================================================
# replace_entire_design_doc Tests
# ============================================================================

class TestReplaceEntireDesignDoc:
    """Tests for replace_entire_design_doc tool."""

    def test_replace_design_doc_success(self, mock_session_with_design_doc):
        """Test successfully replacing entire design doc."""
        with patch("app.agent.tools.session_manager") as mock_manager:
            mock_manager.get_session.return_value = mock_session_with_design_doc
            mock_manager.update_design_doc.return_value = True

            result = replace_entire_design_doc.invoke({
                "updated_content": "# New Design Document\n\nCompletely new content.",
                "session_id": "test-session-123"
            })

            assert result["success"] is True
            mock_manager.update_design_doc.assert_called_once()

    def test_replace_design_doc_session_not_found(self):
        """Test replacing doc for nonexistent session."""
        with patch("app.agent.tools.session_manager") as mock_manager:
            mock_manager.get_session.return_value = None

            result = replace_entire_design_doc.invoke({
                "updated_content": "New content",
                "session_id": "nonexistent"
            })

            assert result["success"] is False
            assert "not found" in result["error"]
