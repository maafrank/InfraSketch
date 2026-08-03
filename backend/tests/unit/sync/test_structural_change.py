"""Position-only diagram edits must not schedule a design-doc sync.

Dragging nodes now writes to the backend on every drag-stop. Each sync run costs
the user 2 credits and an LLM call, so a diagram tidy-up session would be
expensive (and would rewrite the doc for no reason) if _is_structural_change
treated a move as a change.
"""

import pytest

from app.models import Diagram, Edge, Node, NodeMetadata, NodePosition
from app.sync.engine import _is_structural_change


def _node(node_id: str, x: float = 0, y: float = 0, label: str = "API", **kwargs) -> Node:
    return Node(
        id=node_id,
        type="api",
        label=label,
        description="Handles requests",
        inputs=["client"],
        outputs=["db"],
        metadata=NodeMetadata(technology="FastAPI", notes="none"),
        position=NodePosition(x=x, y=y),
        **kwargs,
    )


class TestPositionOnlyChanges:

    def test_moving_a_node_is_not_structural(self):
        old = Diagram(nodes=[_node("api-1", x=0, y=0)], edges=[])
        new = Diagram(nodes=[_node("api-1", x=940, y=-320)], edges=[])

        assert _is_structural_change(old, new) is False

    def test_moving_every_node_is_not_structural(self):
        """The canvas sends the whole visible set on each drag-stop."""
        old = Diagram(
            nodes=[_node("api-1"), _node("db-1", label="DB"), _node("cache-1", label="Cache")],
            edges=[Edge(id="e1", source="api-1", target="db-1", label="reads")],
        )
        new = Diagram(
            nodes=[
                _node("api-1", x=100, y=100),
                _node("db-1", x=200, y=400, label="DB"),
                _node("cache-1", x=-50, y=250, label="Cache"),
            ],
            edges=[Edge(id="e1", source="api-1", target="db-1", label="reads")],
        )

        assert _is_structural_change(old, new) is False

    def test_setting_manual_layout_is_not_structural(self):
        """The flag is presentation state, not architecture."""
        old = Diagram(nodes=[_node("api-1")], edges=[], manual_layout=False)
        new = Diagram(nodes=[_node("api-1", x=10, y=10)], edges=[], manual_layout=True)

        assert _is_structural_change(old, new) is False


class TestRealChangesStillSync:
    """Guard against the position exemption swallowing genuine edits."""

    def test_relabelling_a_node_is_structural(self):
        old = Diagram(nodes=[_node("api-1", label="API")], edges=[])
        new = Diagram(nodes=[_node("api-1", x=500, y=500, label="Public API")], edges=[])

        assert _is_structural_change(old, new) is True

    def test_adding_a_node_is_structural(self):
        old = Diagram(nodes=[_node("api-1")], edges=[])
        new = Diagram(nodes=[_node("api-1", x=500, y=500), _node("db-1", label="DB")], edges=[])

        assert _is_structural_change(old, new) is True

    def test_adding_an_edge_is_structural(self):
        old = Diagram(nodes=[_node("api-1"), _node("db-1", label="DB")], edges=[])
        new = Diagram(
            nodes=[_node("api-1", x=1, y=1), _node("db-1", x=2, y=2, label="DB")],
            edges=[Edge(id="e1", source="api-1", target="db-1", label="reads")],
        )

        assert _is_structural_change(old, new) is True

    def test_first_diagram_is_structural(self):
        assert _is_structural_change(None, Diagram(nodes=[_node("api-1")], edges=[])) is True
