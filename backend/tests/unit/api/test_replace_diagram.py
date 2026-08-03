"""Tests for PUT /session/{id}/diagram, the endpoint that backs undo/redo.

Unlike the incremental mutation endpoints, this one accepts an arbitrary
client-supplied diagram, so its referential-integrity validation is the only
thing standing between a buggy client and a diagram the canvas and the agent
both choke on.
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models import Diagram, Edge, Node
from app.session.manager import session_manager


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def session_id():
    diagram = Diagram(
        nodes=[
            Node(id="a", type="api", label="A", description="a"),
            Node(id="b", type="database", label="B", description="b"),
        ],
        edges=[Edge(id="e1", source="a", target="b")],
    )
    return session_manager.create_session(diagram, user_id="local-dev-user")


def _payload(nodes, edges, manual_layout=False):
    return {
        "nodes": [n.model_dump() for n in nodes],
        "edges": [e.model_dump() for e in edges],
        "manual_layout": manual_layout,
    }


def test_replaces_the_diagram(client, session_id):
    nodes = [Node(id="x", type="cache", label="X", description="x")]
    response = client.put(f"/api/session/{session_id}/diagram", json=_payload(nodes, []))

    assert response.status_code == 200
    assert [n["id"] for n in response.json()["nodes"]] == ["x"]
    assert session_manager.get_session(session_id).diagram.nodes[0].id == "x"


def test_restores_a_group_and_its_children(client, session_id):
    """The case undo exists for: deleting a group cascades to its children."""
    nodes = [
        Node(id="g1", type="group", label="Group", description="g", is_group=True,
             child_ids=["c1", "c2"]),
        Node(id="c1", type="api", label="C1", description="c1", parent_id="g1"),
        Node(id="c2", type="database", label="C2", description="c2", parent_id="g1"),
    ]
    response = client.put(f"/api/session/{session_id}/diagram", json=_payload(nodes, []))

    assert response.status_code == 200
    restored = session_manager.get_session(session_id).diagram
    assert {n.id for n in restored.nodes} == {"g1", "c1", "c2"}
    assert restored.nodes[0].child_ids == ["c1", "c2"]


def test_preserves_manual_layout_flag(client, session_id):
    nodes = [Node(id="x", type="cache", label="X", description="x")]
    response = client.put(
        f"/api/session/{session_id}/diagram",
        json=_payload(nodes, [], manual_layout=True),
    )

    assert response.status_code == 200
    assert response.json()["manual_layout"] is True


def test_rejects_edge_with_unknown_source(client, session_id):
    nodes = [Node(id="a", type="api", label="A", description="a")]
    edges = [Edge(id="e1", source="ghost", target="a")]

    response = client.put(f"/api/session/{session_id}/diagram", json=_payload(nodes, edges))

    assert response.status_code == 400
    assert "unknown source" in response.json()["detail"]


def test_rejects_edge_with_unknown_target(client, session_id):
    nodes = [Node(id="a", type="api", label="A", description="a")]
    edges = [Edge(id="e1", source="a", target="ghost")]

    response = client.put(f"/api/session/{session_id}/diagram", json=_payload(nodes, edges))

    assert response.status_code == 400
    assert "unknown target" in response.json()["detail"]


def test_rejects_unknown_parent_id(client, session_id):
    nodes = [Node(id="a", type="api", label="A", description="a", parent_id="ghost")]

    response = client.put(f"/api/session/{session_id}/diagram", json=_payload(nodes, []))

    assert response.status_code == 400
    assert "unknown parent" in response.json()["detail"]


def test_rejects_unknown_child_id(client, session_id):
    nodes = [
        Node(id="g1", type="group", label="G", description="g", is_group=True,
             child_ids=["ghost"]),
    ]

    response = client.put(f"/api/session/{session_id}/diagram", json=_payload(nodes, []))

    assert response.status_code == 400
    assert "unknown child" in response.json()["detail"]


def test_rejects_duplicate_node_ids(client, session_id):
    nodes = [
        Node(id="dup", type="api", label="A", description="a"),
        Node(id="dup", type="cache", label="B", description="b"),
    ]

    response = client.put(f"/api/session/{session_id}/diagram", json=_payload(nodes, []))

    assert response.status_code == 400
    assert "duplicate node" in response.json()["detail"].lower()


def test_rejects_duplicate_edge_ids(client, session_id):
    nodes = [
        Node(id="a", type="api", label="A", description="a"),
        Node(id="b", type="database", label="B", description="b"),
    ]
    edges = [Edge(id="dup", source="a", target="b"), Edge(id="dup", source="b", target="a")]

    response = client.put(f"/api/session/{session_id}/diagram", json=_payload(nodes, edges))

    assert response.status_code == 400
    assert "duplicate edge" in response.json()["detail"].lower()


def test_a_rejected_payload_leaves_the_diagram_untouched(client, session_id):
    """Validation must run before the write, not after."""
    before = session_manager.get_session(session_id).diagram.model_dump()

    nodes = [Node(id="a", type="api", label="A", description="a")]
    edges = [Edge(id="e1", source="a", target="ghost")]
    client.put(f"/api/session/{session_id}/diagram", json=_payload(nodes, edges))

    assert session_manager.get_session(session_id).diagram.model_dump() == before


def test_accepts_an_empty_diagram(client, session_id):
    """Undoing back to a blank canvas is legitimate."""
    response = client.put(f"/api/session/{session_id}/diagram", json=_payload([], []))

    assert response.status_code == 200
    assert response.json()["nodes"] == []


def test_404_for_unknown_session(client):
    nodes = [Node(id="a", type="api", label="A", description="a")]
    response = client.put("/api/session/does-not-exist/diagram", json=_payload(nodes, []))

    assert response.status_code == 404
