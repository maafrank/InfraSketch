"""
Tool executor for agent-driven diagram modifications.

Executes tool invocations by calling the session manager's methods.
"""

from typing import List, Dict, Any
from app.agent.tools import (
    ToolInvocation,
    AddNodeTool,
    DeleteNodeTool,
    UpdateNodeTool,
    AddEdgeTool,
    DeleteEdgeTool,
)
from app.models import Node, Edge, NodeMetadata, NodePosition, Diagram
from app.session.manager import session_manager


class ToolExecutionError(Exception):
    """Raised when a tool execution fails."""
    pass


class ToolExecutor:
    """
    Executes tools returned by the AI agent.

    This class provides a clean interface between the agent's tool invocations
    and the session manager's CRUD operations.
    """

    def __init__(self, session_id: str):
        self.session_id = session_id
        self.session = session_manager.get_session(session_id)
        if not self.session:
            raise ToolExecutionError(f"Session {session_id} not found")

    def execute_tools(self, tool_invocation: ToolInvocation) -> Diagram:
        """
        Execute all tools in the invocation sequentially.

        Args:
            tool_invocation: ToolInvocation object with list of tools

        Returns:
            Updated Diagram object

        Raises:
            ToolExecutionError: If any tool execution fails
        """
        results = []

        for i, tool in enumerate(tool_invocation.tools):
            try:
                print(f"\n=== Executing Tool {i+1}/{len(tool_invocation.tools)} ===")
                print(f"Action: {tool.action}")

                if tool.action == "add_node":
                    result = self._execute_add_node(tool)
                elif tool.action == "delete_node":
                    result = self._execute_delete_node(tool)
                elif tool.action == "update_node":
                    result = self._execute_update_node(tool)
                elif tool.action == "add_edge":
                    result = self._execute_add_edge(tool)
                elif tool.action == "delete_edge":
                    result = self._execute_delete_edge(tool)
                else:
                    raise ToolExecutionError(f"Unknown action: {tool.action}")

                results.append(result)
                print(f"✓ Tool executed successfully")

            except Exception as e:
                error_msg = f"Failed to execute tool {i+1} ({tool.action}): {str(e)}"
                print(f"✗ {error_msg}")
                raise ToolExecutionError(error_msg) from e

        print(f"\n=== All {len(tool_invocation.tools)} tools executed successfully ===")

        # Return the final diagram state
        updated_session = session_manager.get_session(self.session_id)
        return updated_session.diagram

    def _execute_add_node(self, tool: AddNodeTool) -> None:
        """Execute add_node tool."""
        # Check for duplicate node ID
        if any(n.id == tool.node_id for n in self.session.diagram.nodes):
            raise ToolExecutionError(f"Node with id '{tool.node_id}' already exists")

        # Create Node object
        node = Node(
            id=tool.node_id,
            type=tool.type,
            label=tool.label,
            description=tool.description,
            inputs=tool.inputs,
            outputs=tool.outputs,
            metadata=NodeMetadata(
                technology=tool.technology,
                notes=tool.notes
            ),
            position=NodePosition(**tool.position)
        )

        # Add to diagram
        self.session.diagram.nodes.append(node)

        # Persist to storage (important for DynamoDB in production)
        session_manager.update_diagram(self.session_id, self.session.diagram)

        print(f"  Added node: {tool.label} ({tool.type})")

    def _execute_delete_node(self, tool: DeleteNodeTool) -> None:
        """Execute delete_node tool."""
        # Find node
        original_count = len(self.session.diagram.nodes)
        self.session.diagram.nodes = [
            n for n in self.session.diagram.nodes if n.id != tool.node_id
        ]

        if len(self.session.diagram.nodes) == original_count:
            raise ToolExecutionError(f"Node '{tool.node_id}' not found")

        # Remove edges connected to this node
        edges_removed = len([
            e for e in self.session.diagram.edges
            if e.source == tool.node_id or e.target == tool.node_id
        ])
        self.session.diagram.edges = [
            e for e in self.session.diagram.edges
            if e.source != tool.node_id and e.target != tool.node_id
        ]

        # Persist to storage
        session_manager.update_diagram(self.session_id, self.session.diagram)

        print(f"  Deleted node: {tool.node_id} (removed {edges_removed} connected edges)")

    def _execute_update_node(self, tool: UpdateNodeTool) -> None:
        """Execute update_node tool."""
        # Find node
        node_found = False
        for i, node in enumerate(self.session.diagram.nodes):
            if node.id == tool.node_id:
                # Update only the fields that were provided
                if tool.label is not None:
                    node.label = tool.label
                if tool.description is not None:
                    node.description = tool.description
                if tool.type is not None:
                    node.type = tool.type
                if tool.technology is not None:
                    node.metadata.technology = tool.technology
                if tool.notes is not None:
                    node.metadata.notes = tool.notes

                self.session.diagram.nodes[i] = node
                node_found = True
                print(f"  Updated node: {node.label}")
                break

        if not node_found:
            raise ToolExecutionError(f"Node '{tool.node_id}' not found")

        # Persist to storage
        session_manager.update_diagram(self.session_id, self.session.diagram)

    def _execute_add_edge(self, tool: AddEdgeTool) -> None:
        """Execute add_edge tool."""
        # Validate source and target nodes exist
        node_ids = {n.id for n in self.session.diagram.nodes}

        if tool.source not in node_ids:
            # Source node doesn't exist - skip this edge gracefully
            print(f"  ⚠️  Source node '{tool.source}' not found - skipping edge creation")
            return

        if tool.target not in node_ids:
            # Target node doesn't exist - skip this edge gracefully
            print(f"  ⚠️  Target node '{tool.target}' not found - skipping edge creation")
            return

        # Check for duplicate edge ID
        if any(e.id == tool.edge_id for e in self.session.diagram.edges):
            print(f"  ⚠️  Edge with id '{tool.edge_id}' already exists - skipping")
            return

        # Create Edge object
        edge = Edge(
            id=tool.edge_id,
            source=tool.source,
            target=tool.target,
            label=tool.label,
            type=tool.type
        )

        # Add to diagram
        self.session.diagram.edges.append(edge)

        # Persist to storage
        session_manager.update_diagram(self.session_id, self.session.diagram)

        print(f"  Added edge: {tool.source} → {tool.target} ({tool.label})")

    def _execute_delete_edge(self, tool: DeleteEdgeTool) -> None:
        """Execute delete_edge tool."""
        # Find and remove edge
        original_count = len(self.session.diagram.edges)
        self.session.diagram.edges = [
            e for e in self.session.diagram.edges if e.id != tool.edge_id
        ]

        if len(self.session.diagram.edges) == original_count:
            # Edge not found - but that's OK, the goal was to remove it anyway
            print(f"  ⚠️  Edge '{tool.edge_id}' not found (already deleted or never existed)")
            return  # Don't raise error, just skip

        # Persist to storage
        session_manager.update_diagram(self.session_id, self.session.diagram)

        print(f"  Deleted edge: {tool.edge_id}")


def execute_tool_invocation(session_id: str, tool_invocation: ToolInvocation) -> Diagram:
    """
    Convenience function to execute a tool invocation.

    Args:
        session_id: Session ID
        tool_invocation: ToolInvocation object

    Returns:
        Updated Diagram

    Raises:
        ToolExecutionError: If execution fails
    """
    executor = ToolExecutor(session_id)
    return executor.execute_tools(tool_invocation)
