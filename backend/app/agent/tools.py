"""
Native LangChain tools for diagram modifications.

These tools are exposed to Claude via native tool calling, eliminating the need
for manual JSON parsing and orchestration.

NOTE: session_id is injected by the tools_node in graph.py, not by the LLM.
"""

from typing import Any, Optional, List
from langchain_core.tools import tool

from app.session.manager import session_manager
from app.models import Node, Edge, NodeMetadata, NodePosition


@tool
def add_node(
    node_id: str,
    type: str,
    label: str,
    description: str,
    technology: str,
    position: dict,
    session_id: str,  # Injected by tools_node
    inputs: Optional[List[str]] = None,
    outputs: Optional[List[str]] = None,
    notes: Optional[str] = None,
) -> dict[str, Any]:
    """
    Add a new component/node to the system architecture diagram.

    Use this tool when the user wants to introduce a new component to their system design,
    such as adding a cache layer, load balancer, database, API service, or any other
    infrastructure component. This tool creates the node but does NOT create any connections
    to other nodes - you must use add_edge separately to connect this node to others.

    IMPORTANT: Generate a unique, descriptive node_id for NEW nodes (e.g., 'redis-cache-1',
    'api-gateway-lb-1'). Do NOT use generic IDs like 'node-123'.

    Args:
        node_id: Unique identifier for the new node. Must be descriptive and unique across
                 the entire diagram (e.g., 'redis-cache-1', 'user-service-lb'). Use lowercase
                 with hyphens. This is NOT the display name - it's the internal ID.
        type: Component type category. Must be one of: cache, database, api, server,
              loadbalancer, queue, cdn, gateway, storage, service. This determines the
              visual appearance (color/icon) of the node in the diagram.
        label: Human-readable display name shown on the diagram (e.g., 'Redis Cache',
               'PostgreSQL Database', 'API Gateway Load Balancer'). This is what users see.
        description: Detailed explanation of what this component does in the system, its purpose,
                     and why it's needed. Should be 1-2 sentences.
        technology: Specific technology, product, or implementation (e.g., 'Redis 7.0',
                    'PostgreSQL 15', 'NGINX', 'AWS Application Load Balancer'). Be specific -
                    not just 'database' but 'PostgreSQL 15' or 'MongoDB 6.0'.
        position: Visual position on the diagram as {"x": float, "y": float}. Use logical positioning:
                  entry points (x: 0-200), middle tier services (x: 300-600), data layer (x: 700-1000).
                  Vertical position (y) should separate parallel components. The auto-layout will adjust
                  these, so approximate positioning is fine.
        inputs: Optional list of input descriptions (e.g., ['User requests', 'API calls']).
                Can be empty list if not applicable.
        outputs: Optional list of output descriptions (e.g., ['Cached data', 'Cache miss signals']).
                 Can be empty list if not applicable.
        notes: Optional additional implementation details, configuration notes, or caveats
               (e.g., 'Requires minimum 3 instances for HA', 'Consider sharding for >1M users')

    Returns:
        Dict with success status and message
    """
    # Get session
    session = session_manager.get_session(session_id)
    if not session:
        return {"success": False, "error": f"Session {session_id} not found"}

    # Check for duplicate node ID
    if any(n.id == node_id for n in session.diagram.nodes):
        return {"success": False, "error": f"Node with id '{node_id}' already exists"}

    # Create Node object
    node = Node(
        id=node_id,
        type=type,
        label=label,
        description=description,
        inputs=inputs or [],
        outputs=outputs or [],
        metadata=NodeMetadata(
            technology=technology,
            notes=notes
        ),
        position=NodePosition(**position)
    )

    # Add to diagram
    session.diagram.nodes.append(node)

    # Persist to storage
    session_manager.update_diagram(session_id, session.diagram)

    return {
        "success": True,
        "message": f"Added node '{label}' ({node_id}) to the diagram"
    }


@tool
def delete_node(
    node_id: str,
    session_id: str,  # Injected by tools_node
) -> dict[str, Any]:
    """
    Remove a component/node from the system architecture diagram.

    Use this tool when the user wants to remove an existing component from their system design.
    This tool automatically deletes ALL edges (connections) that are connected to this node,
    so you do NOT need to manually delete edges first.

    CRITICAL: You MUST use the EXACT node_id from the "Nodes (with exact IDs)" section in the
    diagram context. Do NOT guess or make up node IDs. If unsure about the node_id, ask the user.

    Args:
        node_id: The EXACT ID of the node to delete, as shown in the 'Nodes (with exact IDs)'
                 section. Example: if the context shows 'id: `redis-cache-1`', use exactly
                 'redis-cache-1'. All edges connected to this node will be automatically removed.

    Returns:
        Dict with success status, message, and count of removed edges
    """
    # Get session
    session = session_manager.get_session(session_id)
    if not session:
        return {"success": False, "error": f"Session {session_id} not found"}

    # Find node
    original_count = len(session.diagram.nodes)
    node_label = None
    for n in session.diagram.nodes:
        if n.id == node_id:
            node_label = n.label
            break

    session.diagram.nodes = [
        n for n in session.diagram.nodes if n.id != node_id
    ]

    if len(session.diagram.nodes) == original_count:
        return {"success": False, "error": f"Node '{node_id}' not found"}

    # Remove edges connected to this node
    edges_removed = len([
        e for e in session.diagram.edges
        if e.source == node_id or e.target == node_id
    ])
    session.diagram.edges = [
        e for e in session.diagram.edges
        if e.source != node_id and e.target != node_id
    ]

    # Persist to storage
    session_manager.update_diagram(session_id, session.diagram)

    return {
        "success": True,
        "message": f"Deleted node '{node_label or node_id}' and {edges_removed} connected edge(s)"
    }


@tool
def update_node(
    node_id: str,
    session_id: str,  # Injected by tools_node
    label: Optional[str] = None,
    description: Optional[str] = None,
    technology: Optional[str] = None,
    type: Optional[str] = None,
    notes: Optional[str] = None,
) -> dict[str, Any]:
    """
    Update properties of an existing component/node in the diagram.

    Use this tool when the user wants to modify an existing component without removing it,
    such as changing the technology stack (PostgreSQL → MongoDB), updating the display name,
    modifying the description, or changing the component type. This tool only updates the
    specific fields you provide - all other fields remain unchanged.

    CRITICAL: You MUST use the EXACT node_id from the "Nodes (with exact IDs)" section in the
    diagram context. Do NOT guess or make up node IDs. If unsure about the node_id, ask the user.

    Args:
        node_id: The EXACT ID of the node to update, as shown in the 'Nodes (with exact IDs)'
                 section. Example: if the context shows 'id: `postgres-db-1`', use exactly
                 'postgres-db-1'. This is required - you cannot update a node without knowing its ID.
        label: New human-readable display name for the component (e.g., 'MongoDB Database',
               'Redis Cache Layer'). Only provide this if the user wants to change the label.
        description: New detailed explanation of what this component does. Should be 1-2 sentences.
                     Only provide if the user wants to update the description.
        technology: New specific technology or implementation (e.g., 'MongoDB 6.0', 'Redis 7.2',
                    'AWS Application Load Balancer'). Be specific - not just 'database' but
                    'PostgreSQL 15' or 'MongoDB 6.0'. Only provide if changing technology.
        type: New component type category. Must be one of: cache, database, api, server,
              loadbalancer, queue, cdn, gateway, storage, service. This changes the visual
              appearance (color/icon) in the diagram. Only provide if changing the component type.
        notes: New additional implementation details or configuration notes. Only provide
               if adding or updating notes.

    Returns:
        Dict with success status and message listing what was updated
    """
    # Get session
    session = session_manager.get_session(session_id)
    if not session:
        return {"success": False, "error": f"Session {session_id} not found"}

    # Find node
    node_found = False
    updated_fields = []

    for i, node in enumerate(session.diagram.nodes):
        if node.id == node_id:
            # Update only the fields that were provided
            if label is not None:
                node.label = label
                updated_fields.append("label")
            if description is not None:
                node.description = description
                updated_fields.append("description")
            if type is not None:
                node.type = type
                updated_fields.append("type")
            if technology is not None:
                node.metadata.technology = technology
                updated_fields.append("technology")
            if notes is not None:
                node.metadata.notes = notes
                updated_fields.append("notes")

            session.diagram.nodes[i] = node
            node_found = True
            break

    if not node_found:
        return {"success": False, "error": f"Node '{node_id}' not found"}

    if not updated_fields:
        return {"success": False, "error": "No fields provided to update"}

    # Persist to storage
    session_manager.update_diagram(session_id, session.diagram)

    return {
        "success": True,
        "message": f"Updated node '{node_id}': {', '.join(updated_fields)}"
    }


@tool
def add_edge(
    edge_id: str,
    source: str,
    target: str,
    label: str,
    session_id: str,  # Injected by tools_node
    type: str = "default",
) -> dict[str, Any]:
    """
    Create a new connection (edge) between two existing nodes in the diagram.

    Use this tool when the user wants to establish a data flow or relationship between two components,
    such as connecting an API to a database, linking a load balancer to backend servers, or showing
    message flow from a queue to a worker. The edge represents what flows between the nodes (data,
    requests, messages, etc.). Both source and target nodes must already exist in the diagram - if they
    don't, use add_node first to create them.

    CRITICAL: You MUST use the EXACT node IDs from the "Nodes (with exact IDs)" section for source
    and target parameters. Do NOT guess or make up node IDs. If the nodes don't exist, this operation
    will fail gracefully with a warning.

    Args:
        edge_id: Unique identifier for this edge. Must be descriptive and unique across the entire
                 diagram (e.g., 'api-to-cache', 'lb-to-backend-1', 'queue-to-worker'). Use lowercase
                 with hyphens. Follow pattern: 'source-to-target' or 'source-to-target-N' for clarity.
        source: The EXACT ID of the source node where the connection starts, as shown in the
                'Nodes (with exact IDs)' section. Example: if the context shows 'id: `api-server-1`',
                use exactly 'api-server-1'. This node must already exist in the diagram.
        target: The EXACT ID of the target node where the connection ends, as shown in the
                'Nodes (with exact IDs)' section. Example: if the context shows 'id: `redis-cache-1`',
                use exactly 'redis-cache-1'. This node must already exist in the diagram.
        label: Human-readable description of WHAT flows through this connection. Be specific about
               the data/requests being transmitted, not just 'connects to'. Examples: 'User authentication
               requests', 'Cached user data', 'Database query results', 'Async job messages'. This helps
               viewers understand the system's data flow.
        type: Visual style of the edge. Use 'default' for most connections. Use 'animated' for
              real-time or streaming data flows to emphasize high-frequency communication (e.g.,
              WebSocket connections, event streams, message queues).

    Returns:
        Dict with success status and message
    """
    # Get session
    session = session_manager.get_session(session_id)
    if not session:
        return {"success": False, "error": f"Session {session_id} not found"}

    # Validate source and target nodes exist
    node_ids = {n.id for n in session.diagram.nodes}

    if source not in node_ids:
        return {"success": False, "error": f"Source node '{source}' not found"}

    if target not in node_ids:
        return {"success": False, "error": f"Target node '{target}' not found"}

    # Check for duplicate edge ID
    if any(e.id == edge_id for e in session.diagram.edges):
        return {"success": False, "error": f"Edge with id '{edge_id}' already exists"}

    # Create Edge object
    edge = Edge(
        id=edge_id,
        source=source,
        target=target,
        label=label,
        type=type
    )

    # Add to diagram
    session.diagram.edges.append(edge)

    # Persist to storage
    session_manager.update_diagram(session_id, session.diagram)

    return {
        "success": True,
        "message": f"Added edge from '{source}' to '{target}': {label}"
    }


@tool
def delete_edge(
    edge_id: str,
    session_id: str,  # Injected by tools_node
) -> dict[str, Any]:
    """
    Remove a connection (edge) between nodes in the diagram.

    Use this tool when the user wants to eliminate a data flow or relationship between components,
    such as removing a direct API-to-database connection when adding a cache layer in between,
    or deleting obsolete connections when restructuring the architecture. This tool only removes
    the connection - the nodes themselves remain in the diagram.

    CRITICAL: You MUST use the EXACT edge_id from the "Connections (with exact edge IDs)" section
    in the diagram context. Do NOT guess or make up edge IDs. If the edge doesn't exist or was
    already deleted, this operation will succeed gracefully (since the goal was to remove it anyway).

    WARNING: When adding a load balancer BEFORE a node, only delete edges going INTO that node.
    DO NOT delete edges going OUT FROM that node, or you will disconnect the graph! For example,
    if adding LB before API that connects to Database:
    - ✓ Delete: Client → API (incoming edge)
    - ✓ Add: Client → LB, LB → API
    - ✗ DO NOT delete: API → Database (outgoing edge - must be preserved!)

    Args:
        edge_id: The EXACT ID of the edge to delete, as shown in the 'Connections (with exact edge IDs)'
                 section. Example: if the context shows 'id: `api-to-db-direct`', use exactly
                 'api-to-db-direct'. If the edge doesn't exist, the operation will succeed gracefully.

    Returns:
        Dict with success status and message
    """
    # Get session
    session = session_manager.get_session(session_id)
    if not session:
        return {"success": False, "error": f"Session {session_id} not found"}

    # Find and remove edge
    original_count = len(session.diagram.edges)
    session.diagram.edges = [
        e for e in session.diagram.edges if e.id != edge_id
    ]

    if len(session.diagram.edges) == original_count:
        # Edge not found - but that's OK, the goal was to remove it anyway
        return {
            "success": True,
            "message": f"Edge '{edge_id}' not found (already deleted or never existed)"
        }

    # Persist to storage
    session_manager.update_diagram(session_id, session.diagram)

    return {
        "success": True,
        "message": f"Deleted edge '{edge_id}'"
    }


@tool
def update_design_doc_section(
    section_content: str,
    section_start_marker: str,
    session_id: str,  # Injected by tools_node
    section_end_marker: Optional[str] = None,
) -> dict[str, Any]:
    """
    Update a specific section of the design document while preserving all other sections.

    Use this tool when the user asks to modify, rewrite, or update a specific part of the
    design document. This is much safer than replacing the entire document.

    IMPORTANT: Only the specified section is modified - all other sections remain unchanged.

    Args:
        section_content: The new content for this section (markdown formatted).
                        Should NOT include the section header - just the content.
        section_start_marker: The section header that marks where this content begins.
                             Must match EXACTLY including # symbols (e.g., "## System Overview" or "**Purpose and Goals:**")
        section_end_marker: Optional marker for where the section ends.
                           If not provided, the section extends until the next header at the same level.
                           Examples: "## Architecture Diagram" or "**Target Scale:**"

    Returns:
        Dict with success status and message

    Examples:
        To update the "Purpose and Goals" subsection under "System Overview":
        - section_start_marker: "**Purpose and Goals:**"
        - section_end_marker: "**Target Scale:**"
        - section_content: "\\n\\n* Enable real-time decision-making...\\n* Deliver actionable insights..."

        To update an entire section:
        - section_start_marker: "## Data Flow"
        - section_end_marker: "## Scalability & Reliability"
        - section_content: "\\n\\n**Real-Time Path:** Data sources emit..."
    """
    # Get session
    session = session_manager.get_session(session_id)
    if not session:
        return {"success": False, "error": f"Session {session_id} not found"}

    if not session.design_doc:
        return {"success": False, "error": "No design document exists to update"}

    current_doc = session.design_doc

    # Find the section to replace
    start_idx = current_doc.find(section_start_marker)
    if start_idx == -1:
        return {
            "success": False,
            "error": f"Section marker '{section_start_marker}' not found in document"
        }

    # Find where the section ends
    if section_end_marker:
        # User specified end marker
        end_idx = current_doc.find(section_end_marker, start_idx + len(section_start_marker))
        if end_idx == -1:
            return {
                "success": False,
                "error": f"End marker '{section_end_marker}' not found after start marker"
            }
    else:
        # Find next header at same level or higher
        after_start = current_doc[start_idx + len(section_start_marker):]

        # Determine header level of start marker
        if section_start_marker.startswith("###"):
            next_header_patterns = ["###", "##"]
        elif section_start_marker.startswith("##"):
            next_header_patterns = ["##"]
        elif section_start_marker.startswith("**"):
            # For bold subsections, look for next bold subsection or major header
            next_header_patterns = ["**", "##"]
        else:
            next_header_patterns = ["##"]

        # Find the nearest matching header
        end_idx = len(current_doc)  # Default to end of document
        for pattern in next_header_patterns:
            # Look for pattern at start of line
            import re
            match = re.search(f"\n{re.escape(pattern)}", after_start)
            if match:
                potential_end = start_idx + len(section_start_marker) + match.start()
                if potential_end < end_idx:
                    end_idx = potential_end

    # Build the new document
    before_section = current_doc[:start_idx + len(section_start_marker)]
    after_section = current_doc[end_idx:]

    updated_doc = before_section + section_content + after_section

    # Update design doc in session
    success = session_manager.update_design_doc(session_id, updated_doc)

    if not success:
        return {"success": False, "error": "Failed to update design document"}

    return {
        "success": True,
        "message": f"Updated section '{section_start_marker}' ({len(section_content)} characters added)"
    }


@tool
def replace_entire_design_doc(
    updated_content: str,
    session_id: str,  # Injected by tools_node
) -> dict[str, Any]:
    """
    Replace the ENTIRE design document with new content.

    ⚠️ ⛔ CRITICAL WARNING: DO NOT USE THIS TOOL UNLESS ABSOLUTELY NECESSARY ⛔ ⚠️

    This tool OVERWRITES the entire design document, discarding all existing content.

    ONLY use this tool when the user EXPLICITLY requests:
    - "regenerate the entire document"
    - "rewrite everything from scratch"
    - "start over with the design doc"
    - "completely redo the design document"

    For ALL other edits, use update_design_doc_section instead to make surgical changes.

    DO NOT use this tool for:
    ❌ Fixing typos
    ❌ Updating a single section
    ❌ Changing technologies
    ❌ Adding or removing bullet points
    ❌ "Improving" the document
    ❌ Any edit that doesn't involve regenerating the ENTIRE document

    If you're unsure whether to use this tool, the answer is NO - use update_design_doc_section.

    Args:
        updated_content: The complete updated design document in markdown format.
                        Must include ALL sections.

    Returns:
        Dict with success status and message
    """
    # Get session
    session = session_manager.get_session(session_id)
    if not session:
        return {"success": False, "error": f"Session {session_id} not found"}

    # Update design doc in session
    success = session_manager.update_design_doc(session_id, updated_content)

    if not success:
        return {"success": False, "error": "Failed to update design document"}

    return {
        "success": True,
        "message": f"Design document completely replaced ({len(updated_content)} characters)"
    }


# Export tools as a list for binding to LLM
diagram_tools = [add_node, delete_node, update_node, add_edge, delete_edge]
design_doc_tools = [update_design_doc_section, replace_entire_design_doc]
all_tools = diagram_tools + design_doc_tools
