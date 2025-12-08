"""
Tests for group/merge endpoints:
- POST /api/session/{session_id}/groups
- PATCH /api/session/{session_id}/groups/{group_id}/collapse
- DELETE /api/session/{session_id}/groups/{group_id}
"""

import pytest
from fastapi.testclient import TestClient


class TestCreateGroup:
    """Tests for POST /api/session/{session_id}/groups"""

    def test_create_group_merges_nodes(self, client_with_session):
        """Should create a group node containing specified nodes."""
        client, session_id = client_with_session
        # simple_diagram has api-gateway-1 and postgres-db-1

        response = client.post(
            f"/api/session/{session_id}/groups?generate_ai_description=false",
            json={"child_node_ids": ["api-gateway-1", "postgres-db-1"]}
        )

        assert response.status_code == 200
        data = response.json()
        assert "group_id" in data
        assert "diagram" in data

        # Verify group was created
        group_node = next(
            (n for n in data["diagram"]["nodes"] if n["id"] == data["group_id"]),
            None
        )
        assert group_node is not None
        assert group_node["is_group"] is True
        assert set(group_node["child_ids"]) == {"api-gateway-1", "postgres-db-1"}

    def test_create_group_requires_minimum_2_nodes(self, client_with_session):
        """Should reject group with less than 2 nodes."""
        client, session_id = client_with_session

        response = client.post(
            f"/api/session/{session_id}/groups?generate_ai_description=false",
            json={"child_node_ids": ["api-gateway-1"]}
        )

        assert response.status_code == 400
        assert "2 nodes" in response.json()["detail"].lower()

    def test_create_group_validates_nodes_exist(self, client_with_session):
        """Should reject if any node doesn't exist."""
        client, session_id = client_with_session

        response = client.post(
            f"/api/session/{session_id}/groups?generate_ai_description=false",
            json={"child_node_ids": ["api-gateway-1", "nonexistent-node"]}
        )

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_create_group_prevents_nested_groups(self, client):
        """Should reject nodes that already belong to a group."""
        from app.session.manager import session_manager
        from app.models import Node, NodePosition, Diagram

        # Create nodes where one already has a parent
        node1 = Node(
            id="node-1",
            type="api",
            label="Node 1",
            description="First",
            parent_id="existing-group",
            position=NodePosition(x=0, y=0)
        )
        node2 = Node(
            id="node-2",
            type="api",
            label="Node 2",
            description="Second",
            position=NodePosition(x=100, y=0)
        )

        session_id = session_manager.create_session(
            Diagram(nodes=[node1, node2], edges=[]),
            user_id="local-dev-user"
        )

        response = client.post(
            f"/api/session/{session_id}/groups?generate_ai_description=false",
            json={"child_node_ids": ["node-1", "node-2"]}
        )

        assert response.status_code == 400
        assert "already belongs" in response.json()["detail"].lower()

    def test_create_group_sets_parent_id_on_children(self, client_with_session):
        """Should set parent_id on child nodes."""
        client, session_id = client_with_session

        response = client.post(
            f"/api/session/{session_id}/groups?generate_ai_description=false",
            json={"child_node_ids": ["api-gateway-1", "postgres-db-1"]}
        )

        assert response.status_code == 200
        group_id = response.json()["group_id"]
        diagram = response.json()["diagram"]

        # Check that children have parent_id set
        for node in diagram["nodes"]:
            if node["id"] in ["api-gateway-1", "postgres-db-1"]:
                assert node["parent_id"] == group_id

    def test_create_group_starts_collapsed(self, client_with_session):
        """Should create group in collapsed state by default."""
        client, session_id = client_with_session

        response = client.post(
            f"/api/session/{session_id}/groups?generate_ai_description=false",
            json={"child_node_ids": ["api-gateway-1", "postgres-db-1"]}
        )

        assert response.status_code == 200
        group_id = response.json()["group_id"]
        diagram = response.json()["diagram"]

        group_node = next(n for n in diagram["nodes"] if n["id"] == group_id)
        assert group_node["is_collapsed"] is True

    def test_create_group_adds_to_existing_group(self, client):
        """Should add nodes to existing group when one node is already a group."""
        from app.session.manager import session_manager
        from app.models import Node, NodePosition, Diagram

        # Create nodes including an existing group
        child1 = Node(id="child-1", type="api", label="Child 1", description="First", position=NodePosition(x=0, y=0))
        existing_group = Node(
            id="existing-group",
            type="group",
            label="Existing Group",
            description="A group",
            is_group=True,
            is_collapsed=True,
            child_ids=["child-1"],
            position=NodePosition(x=50, y=50)
        )
        child1.parent_id = "existing-group"
        new_node = Node(id="new-node", type="database", label="New Node", description="New", position=NodePosition(x=100, y=0))

        session_id = session_manager.create_session(
            Diagram(nodes=[child1, existing_group, new_node], edges=[]),
            user_id="local-dev-user"
        )

        response = client.post(
            f"/api/session/{session_id}/groups?generate_ai_description=false",
            json={"child_node_ids": ["existing-group", "new-node"]}
        )

        assert response.status_code == 200
        data = response.json()
        # Should return the existing group ID, not create a new one
        assert data["group_id"] == "existing-group"

        # Verify new-node was added to the existing group
        group_node = next(n for n in data["diagram"]["nodes"] if n["id"] == "existing-group")
        assert "new-node" in group_node["child_ids"]


class TestToggleCollapse:
    """Tests for PATCH /api/session/{session_id}/groups/{group_id}/collapse"""

    def test_toggle_collapse_changes_state(self, client):
        """Should toggle is_collapsed state."""
        from app.session.manager import session_manager
        from app.models import Node, NodePosition, Diagram

        # Create a collapsed group
        group = Node(
            id="test-group",
            type="group",
            label="Test Group",
            description="A group",
            is_group=True,
            is_collapsed=True,
            child_ids=[],
            position=NodePosition(x=0, y=0)
        )

        session_id = session_manager.create_session(
            Diagram(nodes=[group], edges=[]),
            user_id="local-dev-user"
        )

        # Toggle (collapsed -> expanded)
        response = client.patch(f"/api/session/{session_id}/groups/test-group/collapse")

        assert response.status_code == 200
        diagram = response.json()
        group_node = next(n for n in diagram["nodes"] if n["id"] == "test-group")
        assert group_node["is_collapsed"] is False

        # Toggle again (expanded -> collapsed)
        response = client.patch(f"/api/session/{session_id}/groups/test-group/collapse")

        assert response.status_code == 200
        diagram = response.json()
        group_node = next(n for n in diagram["nodes"] if n["id"] == "test-group")
        assert group_node["is_collapsed"] is True

    def test_toggle_collapse_returns_404_for_nonexistent(self, client_with_session):
        """Should return 404 for non-existent group."""
        client, session_id = client_with_session

        response = client.patch(f"/api/session/{session_id}/groups/nonexistent-group/collapse")

        assert response.status_code == 404

    def test_toggle_collapse_rejects_non_group(self, client_with_session):
        """Should reject toggle on non-group node."""
        client, session_id = client_with_session
        # api-gateway-1 is not a group node

        response = client.patch(f"/api/session/{session_id}/groups/api-gateway-1/collapse")

        assert response.status_code == 400
        assert "not a group" in response.json()["detail"].lower()


class TestUngroupNodes:
    """Tests for DELETE /api/session/{session_id}/groups/{group_id}"""

    def test_ungroup_dissolves_group(self, client):
        """Should remove the group node."""
        from app.session.manager import session_manager
        from app.models import Node, NodePosition, Diagram

        child = Node(id="child-1", type="api", label="Child", description="A child", parent_id="test-group", position=NodePosition(x=0, y=0))
        group = Node(
            id="test-group",
            type="group",
            label="Test Group",
            description="A group",
            is_group=True,
            is_collapsed=True,
            child_ids=["child-1"],
            position=NodePosition(x=50, y=50)
        )

        session_id = session_manager.create_session(
            Diagram(nodes=[child, group], edges=[]),
            user_id="local-dev-user"
        )

        response = client.delete(f"/api/session/{session_id}/groups/test-group")

        assert response.status_code == 200
        diagram = response.json()
        node_ids = [n["id"] for n in diagram["nodes"]]
        assert "test-group" not in node_ids

    def test_ungroup_clears_parent_id_on_children(self, client):
        """Should clear parent_id on former child nodes."""
        from app.session.manager import session_manager
        from app.models import Node, NodePosition, Diagram

        child1 = Node(id="child-1", type="api", label="Child 1", description="First", parent_id="test-group", position=NodePosition(x=0, y=0))
        child2 = Node(id="child-2", type="api", label="Child 2", description="Second", parent_id="test-group", position=NodePosition(x=100, y=0))
        group = Node(
            id="test-group",
            type="group",
            label="Test Group",
            description="A group",
            is_group=True,
            is_collapsed=True,
            child_ids=["child-1", "child-2"],
            position=NodePosition(x=50, y=50)
        )

        session_id = session_manager.create_session(
            Diagram(nodes=[child1, child2, group], edges=[]),
            user_id="local-dev-user"
        )

        response = client.delete(f"/api/session/{session_id}/groups/test-group")

        assert response.status_code == 200
        diagram = response.json()

        for node in diagram["nodes"]:
            if node["id"] in ["child-1", "child-2"]:
                assert node["parent_id"] is None

    def test_ungroup_removes_group_edges(self, client):
        """Should remove edges connected to the group node."""
        from app.session.manager import session_manager
        from app.models import Node, Edge, NodePosition, Diagram

        outside_node = Node(id="outside", type="api", label="Outside", description="Outside node", position=NodePosition(x=200, y=0))
        group = Node(
            id="test-group",
            type="group",
            label="Test Group",
            description="A group",
            is_group=True,
            child_ids=[],
            position=NodePosition(x=50, y=50)
        )
        edge_to_group = Edge(id="edge-to-group", source="outside", target="test-group", label="Connection")

        session_id = session_manager.create_session(
            Diagram(nodes=[outside_node, group], edges=[edge_to_group]),
            user_id="local-dev-user"
        )

        response = client.delete(f"/api/session/{session_id}/groups/test-group")

        assert response.status_code == 200
        diagram = response.json()
        edge_ids = [e["id"] for e in diagram["edges"]]
        assert "edge-to-group" not in edge_ids

    def test_ungroup_returns_404_for_nonexistent(self, client_with_session):
        """Should return 404 for non-existent group."""
        client, session_id = client_with_session

        response = client.delete(f"/api/session/{session_id}/groups/nonexistent-group")

        assert response.status_code == 404

    def test_ungroup_rejects_non_group(self, client_with_session):
        """Should reject ungroup on non-group node."""
        client, session_id = client_with_session

        response = client.delete(f"/api/session/{session_id}/groups/api-gateway-1")

        assert response.status_code == 400
        assert "not a group" in response.json()["detail"].lower()
