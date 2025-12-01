"""
Post-processing utilities for automatic diagram grouping.

Handles:
1. Validation of Claude-generated groups
2. Fallback heuristic grouping by logical layer if no groups provided
3. Edge redirection for group structures
"""

from typing import List, Dict, Set, Tuple, Optional
from app.models import Node, Edge, Diagram, NodeMetadata, NodePosition
import uuid


# Define logical layers for grouping
LAYER_DEFINITIONS = {
    "data": {
        "types": {"database", "cache"},
        "label": "Data Layer",
        "description": "Data persistence and caching components",
    },
    "api": {
        "types": {"api", "server", "service"},
        "label": "Services Layer",
        "description": "Application and API services",
    },
    "processing": {
        "types": {"queue", "worker"},
        "label": "Processing Layer",
        "description": "Async processing and message queues",
    },
    "infrastructure": {
        "types": {"loadbalancer", "cdn", "gateway", "storage"},
        "label": "Infrastructure Layer",
        "description": "Infrastructure and networking components",
    },
}


def validate_group_structure(diagram: Diagram) -> Diagram:
    """
    Validate and fix group relationships in diagram.

    Fixes:
    - child_ids that reference non-existent nodes
    - parent_id that references non-existent groups
    - Groups with less than 2 children (dissolves them)
    - Circular parent references
    """
    node_ids = {n.id for n in diagram.nodes}
    group_ids = {n.id for n in diagram.nodes if n.is_group}

    nodes_to_keep = []
    for node in diagram.nodes:
        # Fix parent_id references
        if node.parent_id and node.parent_id not in group_ids:
            node.parent_id = None

        # Fix child_ids references
        if node.is_group:
            node.child_ids = [cid for cid in node.child_ids if cid in node_ids]
            # Dissolve groups with <2 children
            if len(node.child_ids) < 2:
                # Clear parent_id from any children that referenced this group
                for other_node in diagram.nodes:
                    if other_node.parent_id == node.id:
                        other_node.parent_id = None
                # Don't add this invalid group to the output
                continue

        nodes_to_keep.append(node)

    diagram.nodes = nodes_to_keep
    return diagram


def apply_heuristic_grouping(diagram: Diagram, max_visible_nodes: int = 6) -> Diagram:
    """
    Apply heuristic grouping to flat diagrams when Claude doesn't group.

    Strategy:
    1. If node count <= max_visible_nodes, no grouping needed
    2. If diagram already has groups, skip
    3. Group nodes by logical layer (data, api, processing, infrastructure)
    4. Only create layer group if it would contain 2+ nodes
    """
    # Skip if already has groups
    has_groups = any(n.is_group for n in diagram.nodes)
    if has_groups:
        print(f"Diagram already has groups, skipping heuristic grouping")
        return diagram

    # Skip if small enough
    if len(diagram.nodes) <= max_visible_nodes:
        print(f"Diagram has {len(diagram.nodes)} nodes (≤{max_visible_nodes}), skipping grouping")
        return diagram

    print(f"Applying heuristic grouping to {len(diagram.nodes)} nodes")

    # Categorize nodes by layer
    layer_nodes: Dict[str, List[Node]] = {layer: [] for layer in LAYER_DEFINITIONS}
    ungrouped_nodes: List[Node] = []

    for node in diagram.nodes:
        placed = False
        for layer_name, layer_def in LAYER_DEFINITIONS.items():
            if node.type in layer_def["types"]:
                layer_nodes[layer_name].append(node)
                placed = True
                break
        if not placed:
            ungrouped_nodes.append(node)

    # Create groups for layers with 2+ nodes
    groups_created: List[Tuple[Node, List[str]]] = []
    for layer_name, nodes in layer_nodes.items():
        if len(nodes) >= 2:
            layer_def = LAYER_DEFINITIONS[layer_name]
            group_node, child_ids = _create_layer_group(nodes, layer_name, layer_def)
            groups_created.append((group_node, child_ids))
            print(f"  Created group '{group_node.label}' with {len(child_ids)} nodes")

    if not groups_created:
        print(f"No layers had 2+ nodes, skipping grouping")
        return diagram

    # Add groups to diagram and update children
    for group_node, child_ids in groups_created:
        diagram.nodes.append(group_node)
        # Update children to reference parent
        for node in diagram.nodes:
            if node.id in child_ids:
                node.parent_id = group_node.id

    # Redirect external edges to groups
    diagram = _redirect_edges_to_groups(diagram)

    visible_count = len([n for n in diagram.nodes if not n.parent_id])
    print(f"Post-grouping: {visible_count} visible nodes (was {len(diagram.nodes) - len(groups_created)})")

    return diagram


def _create_layer_group(
    nodes: List[Node],
    layer_name: str,
    layer_def: dict,
) -> Tuple[Node, List[str]]:
    """Create a group node from nodes in a logical layer."""
    child_ids = [n.id for n in nodes]
    group_id = f"group-{layer_name}-{uuid.uuid4().hex[:6]}"

    # Calculate average position
    avg_x = sum(n.position.x for n in nodes) / len(nodes)
    avg_y = sum(n.position.y for n in nodes) / len(nodes)

    # Collect unique types for color blending
    child_types = list(set(n.type for n in nodes))

    # Use the most common type for the group's type (for color)
    type_counts = {}
    for n in nodes:
        type_counts[n.type] = type_counts.get(n.type, 0) + 1
    most_common_type = max(type_counts, key=type_counts.get)

    group_node = Node(
        id=group_id,
        type=most_common_type,  # Use most common child type for color
        label=f"{layer_def['label']} ({len(nodes)})",
        description=layer_def["description"],
        inputs=[],
        outputs=[],
        metadata=NodeMetadata(
            technology=None,
            notes=f"Auto-grouped {len(nodes)} components",
            child_types=child_types,
        ),
        position=NodePosition(x=avg_x, y=avg_y),
        is_group=True,
        is_collapsed=True,  # Start collapsed for cleaner view
        child_ids=child_ids,
        parent_id=None,
    )

    return (group_node, child_ids)


def _redirect_edges_to_groups(diagram: Diagram) -> Diagram:
    """
    Redirect edges to/from grouped nodes to their parent group.

    For external edges (one endpoint outside group):
    - Replace child node with parent group in edge
    - Deduplicate resulting edges
    - Keep internal edges (both endpoints in same group)
    """
    # Build child-to-parent map
    child_to_parent: Dict[str, str] = {}
    for node in diagram.nodes:
        if node.parent_id:
            child_to_parent[node.id] = node.parent_id

    # Get all group child sets for internal edge detection
    group_children: Dict[str, Set[str]] = {}
    for node in diagram.nodes:
        if node.is_group:
            group_children[node.id] = set(node.child_ids)

    new_edges: List[Edge] = []
    seen_edges: Set[str] = set()

    for edge in diagram.edges:
        source = edge.source
        target = edge.target

        # Check if this is an internal edge (both in same group)
        source_parent = child_to_parent.get(source)
        target_parent = child_to_parent.get(target)

        if source_parent and target_parent and source_parent == target_parent:
            # Internal edge - keep as-is (will be hidden when collapsed)
            new_edges.append(edge)
            continue

        # Redirect to parent group if applicable
        redirected_source = child_to_parent.get(source, source)
        redirected_target = child_to_parent.get(target, target)

        # Skip self-loops after redirection
        if redirected_source == redirected_target:
            continue

        # Deduplicate edges with same source/target
        edge_key = f"{redirected_source}->{redirected_target}"
        if edge_key in seen_edges:
            continue
        seen_edges.add(edge_key)

        # Create redirected edge
        new_edge = Edge(
            id=f"{redirected_source}-to-{redirected_target}",
            source=redirected_source,
            target=redirected_target,
            label=edge.label,
            type=edge.type,
        )
        new_edges.append(new_edge)

    diagram.edges = new_edges
    return diagram


def ensure_groups_collapsed(diagram: Diagram) -> Diagram:
    """Ensure all groups start in collapsed state."""
    for node in diagram.nodes:
        if node.is_group:
            node.is_collapsed = True
    return diagram


def process_diagram_groups(diagram: Diagram, max_visible_nodes: int = 6) -> Diagram:
    """
    Main entry point for group processing.

    Applies validation, heuristic grouping (if needed), and ensures groups are collapsed.
    """
    print(f"\n=== GROUP PROCESSING ===")
    print(f"Input: {len(diagram.nodes)} nodes, {len(diagram.edges)} edges")

    # 1. Validate any Claude-generated groups
    diagram = validate_group_structure(diagram)

    # 2. Apply heuristic grouping if Claude didn't group
    diagram = apply_heuristic_grouping(diagram, max_visible_nodes)

    # 3. Ensure groups start collapsed
    diagram = ensure_groups_collapsed(diagram)

    visible_nodes = [n for n in diagram.nodes if not n.parent_id]
    group_nodes = [n for n in diagram.nodes if n.is_group]
    print(f"Output: {len(visible_nodes)} visible nodes, {len(group_nodes)} groups")
    print(f"========================\n")

    return diagram
