"""
Tests for node CRUD endpoints:
- POST /api/session/{session_id}/nodes
- DELETE /api/session/{session_id}/nodes/{node_id}
- PATCH /api/session/{session_id}/nodes/{node_id}
"""

import pytest
from fastapi.testclient import TestClient


class TestAddNode:
    """Tests for POST /api/session/{session_id}/nodes"""

    def test_add_node_returns_updated_diagram(self, client_with_session, sample_cache_node):
        """Should add node and return updated diagram."""
        client, session_id = client_with_session

        response = client.post(
            f"/api/session/{session_id}/nodes",
            json=sample_cache_node.model_dump()
        )

        assert response.status_code == 200
        diagram = response.json()
        assert len(diagram["nodes"]) == 3  # simple_diagram has 2 + new one
        node_ids = [n["id"] for n in diagram["nodes"]]
        assert sample_cache_node.id in node_ids

    def test_add_node_rejects_duplicate_id(self, client_with_session, sample_node):
        """Should reject node with duplicate ID."""
        client, session_id = client_with_session
        # sample_node is already in simple_diagram fixture

        response = client.post(
            f"/api/session/{session_id}/nodes",
            json=sample_node.model_dump()
        )

        assert response.status_code == 400
        assert "already exists" in response.json()["detail"].lower()

    def test_add_node_persists_to_session(self, client_with_session, sample_cache_node):
        """Should persist added node to session storage."""
        client, session_id = client_with_session

        response = client.post(
            f"/api/session/{session_id}/nodes",
            json=sample_cache_node.model_dump()
        )

        assert response.status_code == 200

        # Verify persistence
        from app.session.manager import session_manager
        session = session_manager.get_session(session_id)
        node_ids = [n.id for n in session.diagram.nodes]
        assert sample_cache_node.id in node_ids

    def test_add_node_returns_404_for_nonexistent_session(self, client, sample_cache_node):
        """Should return 404 for non-existent session."""
        response = client.post(
            "/api/session/nonexistent-session/nodes",
            json=sample_cache_node.model_dump()
        )

        assert response.status_code == 404


class TestDeleteNode:
    """Tests for DELETE /api/session/{session_id}/nodes/{node_id}"""

    def test_delete_node_removes_node(self, client_with_session):
        """Should remove node from diagram."""
        client, session_id = client_with_session
        node_id = "api-gateway-1"  # From sample_node in simple_diagram

        response = client.delete(f"/api/session/{session_id}/nodes/{node_id}")

        assert response.status_code == 200
        diagram = response.json()
        node_ids = [n["id"] for n in diagram["nodes"]]
        assert node_id not in node_ids

    def test_delete_node_removes_connected_edges(self, client_with_session):
        """Should remove edges connected to deleted node."""
        client, session_id = client_with_session
        node_id = "api-gateway-1"  # Source of edge in simple_diagram

        response = client.delete(f"/api/session/{session_id}/nodes/{node_id}")

        assert response.status_code == 200
        diagram = response.json()
        # Edge edge-api-to-db connects api-gateway-1 to postgres-db-1
        edge_sources = [e["source"] for e in diagram["edges"]]
        edge_targets = [e["target"] for e in diagram["edges"]]
        assert node_id not in edge_sources
        assert node_id not in edge_targets

    def test_delete_node_cascades_group_children(self, client):
        """Should delete group and all children when deleting a group node."""
        from app.session.manager import session_manager
        from app.models import Node, NodePosition, Diagram

        # Create a session with a group
        child1 = Node(id="child-1", type="api", label="Child 1", description="First child", position=NodePosition(x=0, y=0))
        child2 = Node(id="child-2", type="api", label="Child 2", description="Second child", position=NodePosition(x=100, y=0))
        group = Node(
            id="parent-group",
            type="group",
            label="Parent Group",
            description="A group",
            is_group=True,
            is_collapsed=True,
            child_ids=["child-1", "child-2"],
            position=NodePosition(x=50, y=50)
        )
        child1.parent_id = "parent-group"
        child2.parent_id = "parent-group"

        diagram = Diagram(nodes=[child1, child2, group], edges=[])
        session_id = session_manager.create_session(diagram, user_id="local-dev-user")

        response = client.delete(f"/api/session/{session_id}/nodes/parent-group")

        assert response.status_code == 200
        result_diagram = response.json()
        # All nodes should be deleted (group + 2 children)
        assert len(result_diagram["nodes"]) == 0

    def test_delete_node_returns_404_for_nonexistent(self, client_with_session):
        """Should return 404 for non-existent node."""
        client, session_id = client_with_session

        response = client.delete(f"/api/session/{session_id}/nodes/nonexistent-node")

        assert response.status_code == 404


class TestUpdateNode:
    """Tests for PATCH /api/session/{session_id}/nodes/{node_id}"""

    def test_update_node_modifies_properties(self, client_with_session):
        """Should update node properties."""
        client, session_id = client_with_session
        node_id = "api-gateway-1"

        updated_node = {
            "id": node_id,
            "type": "gateway",
            "label": "Updated API Gateway",
            "description": "Updated description",
            "inputs": [],
            "outputs": [],
            "position": {"x": 100, "y": 200}
        }

        response = client.patch(
            f"/api/session/{session_id}/nodes/{node_id}",
            json=updated_node
        )

        assert response.status_code == 200
        diagram = response.json()
        updated = next(n for n in diagram["nodes"] if n["id"] == node_id)
        assert updated["label"] == "Updated API Gateway"
        assert updated["description"] == "Updated description"

    def test_update_node_rejects_id_mismatch(self, client_with_session):
        """Should reject when body ID doesn't match URL parameter."""
        client, session_id = client_with_session

        updated_node = {
            "id": "different-id",
            "type": "gateway",
            "label": "Gateway",
            "description": "Desc",
            "inputs": [],
            "outputs": [],
            "position": {"x": 0, "y": 0}
        }

        response = client.patch(
            f"/api/session/{session_id}/nodes/api-gateway-1",
            json=updated_node
        )

        assert response.status_code == 400
        assert "must match" in response.json()["detail"].lower()

    def test_update_node_returns_404_for_nonexistent(self, client_with_session):
        """Should return 404 for non-existent node."""
        client, session_id = client_with_session

        updated_node = {
            "id": "nonexistent-node",
            "type": "api",
            "label": "Test",
            "description": "Test",
            "inputs": [],
            "outputs": [],
            "position": {"x": 0, "y": 0}
        }

        response = client.patch(
            f"/api/session/{session_id}/nodes/nonexistent-node",
            json=updated_node
        )

        assert response.status_code == 404

    def test_update_node_persists_changes(self, client_with_session):
        """Should persist updated node to session storage."""
        client, session_id = client_with_session
        node_id = "api-gateway-1"
        new_label = "Persisted Gateway"

        updated_node = {
            "id": node_id,
            "type": "gateway",
            "label": new_label,
            "description": "Persisted description",
            "inputs": [],
            "outputs": [],
            "position": {"x": 100, "y": 200}
        }

        response = client.patch(
            f"/api/session/{session_id}/nodes/{node_id}",
            json=updated_node
        )

        assert response.status_code == 200

        # Verify persistence
        from app.session.manager import session_manager
        session = session_manager.get_session(session_id)
        node = next(n for n in session.diagram.nodes if n.id == node_id)
        assert node.label == new_label


class TestUpdateNodePositions:
    """Tests for PATCH /api/session/{session_id}/nodes/positions"""

    def test_saves_positions_and_sets_manual_layout(self, client_with_session):
        """Should persist coordinates and flip manual_layout so the canvas stops auto-laying out."""
        client, session_id = client_with_session

        response = client.patch(
            f"/api/session/{session_id}/nodes/positions",
            json={"positions": [
                {"id": "api-gateway-1", "x": 42.5, "y": -17.0},
                {"id": "postgres-db-1", "x": 300, "y": 500},
            ]}
        )

        assert response.status_code == 200
        diagram = response.json()
        assert diagram["manual_layout"] is True

        by_id = {n["id"]: n for n in diagram["nodes"]}
        assert by_id["api-gateway-1"]["position"] == {"x": 42.5, "y": -17.0}
        assert by_id["postgres-db-1"]["position"] == {"x": 300.0, "y": 500.0}

    def test_persists_to_session(self, client_with_session):
        """Positions must survive in session storage, not just the response."""
        client, session_id = client_with_session

        response = client.patch(
            f"/api/session/{session_id}/nodes/positions",
            json={"positions": [{"id": "api-gateway-1", "x": 11, "y": 22}]}
        )
        assert response.status_code == 200

        from app.session.manager import session_manager
        session = session_manager.get_session(session_id)
        node = next(n for n in session.diagram.nodes if n.id == "api-gateway-1")
        assert node.position.x == 11
        assert node.position.y == 22
        assert session.diagram.manual_layout is True

    def test_route_is_not_shadowed_by_node_id_route(self, client_with_session):
        """
        Regression: PATCH /nodes/{node_id} is declared in the same router, so
        "positions" must not be matched as a node ID.
        """
        client, session_id = client_with_session

        response = client.patch(
            f"/api/session/{session_id}/nodes/positions",
            json={"positions": [{"id": "api-gateway-1", "x": 1, "y": 2}]}
        )

        # The node_id route would reject this body with a 400/422, never a 200.
        assert response.status_code == 200

    def test_skips_unknown_node_ids(self, client_with_session):
        """A node deleted concurrently should be skipped, not fail the whole save."""
        client, session_id = client_with_session

        response = client.patch(
            f"/api/session/{session_id}/nodes/positions",
            json={"positions": [
                {"id": "api-gateway-1", "x": 5, "y": 6},
                {"id": "deleted-by-another-tab", "x": 9, "y": 9},
            ]}
        )

        assert response.status_code == 200
        diagram = response.json()
        node_ids = [n["id"] for n in diagram["nodes"]]
        assert "deleted-by-another-tab" not in node_ids
        by_id = {n["id"]: n for n in diagram["nodes"]}
        assert by_id["api-gateway-1"]["position"] == {"x": 5.0, "y": 6.0}

    def test_returns_404_when_no_ids_match(self, client_with_session):
        """All-unknown payload means the client is out of sync entirely."""
        client, session_id = client_with_session

        response = client.patch(
            f"/api/session/{session_id}/nodes/positions",
            json={"positions": [{"id": "nope", "x": 1, "y": 1}]}
        )

        assert response.status_code == 404

    def test_rejects_empty_positions_list(self, client_with_session):
        """An empty save is a client bug, not a no-op worth a DynamoDB write."""
        client, session_id = client_with_session

        response = client.patch(
            f"/api/session/{session_id}/nodes/positions",
            json={"positions": []}
        )

        assert response.status_code == 422

    def test_returns_404_for_nonexistent_session(self, client):
        """Should return 404 for non-existent session."""
        response = client.patch(
            "/api/session/nonexistent-session/nodes/positions",
            json={"positions": [{"id": "api-gateway-1", "x": 1, "y": 1}]}
        )

        assert response.status_code == 404

    def test_manual_layout_survives_adding_a_node(self, client_with_session, sample_cache_node):
        """
        Regression: every diagram mutation path must mutate the existing Diagram
        rather than rebuild one, or manual_layout would silently reset to False
        and the user's arrangement would be discarded on the next render.
        """
        client, session_id = client_with_session

        client.patch(
            f"/api/session/{session_id}/nodes/positions",
            json={"positions": [{"id": "api-gateway-1", "x": 700, "y": 900}]}
        )

        response = client.post(
            f"/api/session/{session_id}/nodes",
            json=sample_cache_node.model_dump()
        )

        assert response.status_code == 200
        diagram = response.json()
        assert diagram["manual_layout"] is True
        by_id = {n["id"]: n for n in diagram["nodes"]}
        assert by_id["api-gateway-1"]["position"] == {"x": 700.0, "y": 900.0}
        # The new node keeps whatever position it was created with. A node added
        # by a chat tool has none, so it lands on the server-side (0, 0) default,
        # which the canvas reads as "never placed" and auto-positions.
        assert by_id[sample_cache_node.id]["position"] == {
            "x": sample_cache_node.position.x,
            "y": sample_cache_node.position.y,
        }

    def test_manual_layout_survives_deleting_a_node(self, client_with_session):
        """Deleting a node must not reset the saved layout for the survivors."""
        client, session_id = client_with_session

        client.patch(
            f"/api/session/{session_id}/nodes/positions",
            json={"positions": [{"id": "api-gateway-1", "x": 700, "y": 900}]}
        )

        response = client.delete(f"/api/session/{session_id}/nodes/postgres-db-1")

        assert response.status_code == 200
        diagram = response.json()
        assert diagram["manual_layout"] is True
        by_id = {n["id"]: n for n in diagram["nodes"]}
        assert by_id["api-gateway-1"]["position"] == {"x": 700.0, "y": 900.0}
