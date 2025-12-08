"""
Tests for edge CRUD endpoints:
- POST /api/session/{session_id}/edges
- DELETE /api/session/{session_id}/edges/{edge_id}
"""

import pytest
from fastapi.testclient import TestClient


class TestAddEdge:
    """Tests for POST /api/session/{session_id}/edges"""

    def test_add_edge_returns_updated_diagram(self, client_with_session):
        """Should add edge and return updated diagram."""
        client, session_id = client_with_session

        # Add edge between existing nodes
        new_edge = {
            "id": "new-edge-1",
            "source": "api-gateway-1",
            "target": "postgres-db-1",
            "label": "New connection",
            "type": "animated"
        }

        response = client.post(
            f"/api/session/{session_id}/edges",
            json=new_edge
        )

        assert response.status_code == 200
        diagram = response.json()
        edge_ids = [e["id"] for e in diagram["edges"]]
        assert "new-edge-1" in edge_ids

    def test_add_edge_validates_source_exists(self, client_with_session):
        """Should reject edge with non-existent source node."""
        client, session_id = client_with_session

        new_edge = {
            "id": "invalid-edge",
            "source": "nonexistent-source",
            "target": "postgres-db-1",
            "label": "Invalid edge",
            "type": "default"
        }

        response = client.post(
            f"/api/session/{session_id}/edges",
            json=new_edge
        )

        assert response.status_code == 400
        assert "source" in response.json()["detail"].lower()
        assert "not exist" in response.json()["detail"].lower()

    def test_add_edge_validates_target_exists(self, client_with_session):
        """Should reject edge with non-existent target node."""
        client, session_id = client_with_session

        new_edge = {
            "id": "invalid-edge",
            "source": "api-gateway-1",
            "target": "nonexistent-target",
            "label": "Invalid edge",
            "type": "default"
        }

        response = client.post(
            f"/api/session/{session_id}/edges",
            json=new_edge
        )

        assert response.status_code == 400
        assert "target" in response.json()["detail"].lower()
        assert "not exist" in response.json()["detail"].lower()

    def test_add_edge_rejects_duplicate_id(self, client_with_session):
        """Should reject edge with duplicate ID."""
        client, session_id = client_with_session

        # sample_edge with id "edge-api-to-db" is already in simple_diagram
        duplicate_edge = {
            "id": "edge-api-to-db",
            "source": "api-gateway-1",
            "target": "postgres-db-1",
            "label": "Duplicate edge",
            "type": "default"
        }

        response = client.post(
            f"/api/session/{session_id}/edges",
            json=duplicate_edge
        )

        assert response.status_code == 400
        assert "already exists" in response.json()["detail"].lower()

    def test_add_edge_persists_to_session(self, client_with_session):
        """Should persist added edge to session storage."""
        client, session_id = client_with_session

        new_edge = {
            "id": "persisted-edge",
            "source": "api-gateway-1",
            "target": "postgres-db-1",
            "label": "Persisted",
            "type": "default"
        }

        response = client.post(
            f"/api/session/{session_id}/edges",
            json=new_edge
        )

        assert response.status_code == 200

        # Verify persistence
        from app.session.manager import session_manager
        session = session_manager.get_session(session_id)
        edge_ids = [e.id for e in session.diagram.edges]
        assert "persisted-edge" in edge_ids


class TestDeleteEdge:
    """Tests for DELETE /api/session/{session_id}/edges/{edge_id}"""

    def test_delete_edge_removes_edge(self, client_with_session):
        """Should remove edge from diagram."""
        client, session_id = client_with_session
        edge_id = "edge-api-to-db"  # From simple_diagram

        response = client.delete(f"/api/session/{session_id}/edges/{edge_id}")

        assert response.status_code == 200
        diagram = response.json()
        edge_ids = [e["id"] for e in diagram["edges"]]
        assert edge_id not in edge_ids

    def test_delete_edge_returns_404_for_nonexistent(self, client_with_session):
        """Should return 404 for non-existent edge."""
        client, session_id = client_with_session

        response = client.delete(f"/api/session/{session_id}/edges/nonexistent-edge")

        assert response.status_code == 404

    def test_delete_edge_persists_removal(self, client_with_session):
        """Should persist edge removal to session storage."""
        client, session_id = client_with_session
        edge_id = "edge-api-to-db"

        response = client.delete(f"/api/session/{session_id}/edges/{edge_id}")

        assert response.status_code == 200

        # Verify persistence
        from app.session.manager import session_manager
        session = session_manager.get_session(session_id)
        edge_ids = [e.id for e in session.diagram.edges]
        assert edge_id not in edge_ids
