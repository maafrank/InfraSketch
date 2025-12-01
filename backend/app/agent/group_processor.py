"""
Post-processing utilities for automatic diagram grouping.

Handles:
1. AI-powered semantic grouping by business domain (primary)
2. Fallback heuristic grouping by logical layer
3. Validation of group structures

NOTE: Original edges are preserved. The frontend handles dynamic edge
redirection based on group collapse state. This ensures edges remain
visible when groups are expanded.
"""

import json
import uuid
from typing import List, Dict, Set, Tuple, Optional

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage

from app.models import Node, Edge, Diagram, NodeMetadata, NodePosition
from app.utils.secrets import get_anthropic_api_key


# Prompt for AI semantic grouping
SEMANTIC_GROUPING_PROMPT = """You are analyzing a system architecture diagram to identify logical business domains for grouping.

**Nodes in the diagram:**
{nodes_context}

**Connections between nodes:**
{edges_context}

Your task: Identify clusters of nodes that work together for a specific BUSINESS FUNCTION.

**Grouping Rules:**
1. Group by PURPOSE/FEATURE, not just technical type (don't just put all databases together)
2. Each group should have 2-5 nodes that collaborate on a specific feature/domain
3. Name groups after business domains: "Payment Processing", "User Authentication", "Order Fulfillment", etc.
4. Entry points (load balancers, API gateways, CDNs, clients, web browsers) should remain UNGROUPED for visibility
5. Groups need at least 2 related nodes - don't create single-node groups
6. Don't group unrelated nodes just to reduce count
7. Consider data flow: nodes that exchange data often should be grouped together
8. Aim for 4-6 groups total for a complex system

**Output:** Return ONLY valid JSON (no markdown, no explanation):
{{
  "groups": [
    {{
      "name": "Payment Processing",
      "description": "Handles payment validation, processing, and confirmation",
      "node_ids": ["payment-api", "payment-db", "stripe-webhook"]
    }}
  ],
  "ungrouped_node_ids": ["load-balancer", "api-gateway"]
}}
"""


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


# =============================================================================
# AI Semantic Grouping Functions
# =============================================================================

def _format_nodes_for_grouping(nodes: List[Node]) -> str:
    """Format nodes for the AI grouping prompt with relevant context."""
    lines = []
    for node in nodes:
        tech = node.metadata.technology if node.metadata and node.metadata.technology else "N/A"
        lines.append(
            f"- {node.id}: {node.label} (type: {node.type}) - {node.description} [Tech: {tech}]"
        )
    return "\n".join(lines)


def _format_edges_for_grouping(edges: List[Edge], nodes: List[Node]) -> str:
    """Format edges showing data flow between nodes."""
    node_labels = {n.id: n.label for n in nodes}
    lines = []
    for edge in edges:
        src_label = node_labels.get(edge.source, edge.source)
        tgt_label = node_labels.get(edge.target, edge.target)
        label = f" ({edge.label})" if edge.label else ""
        lines.append(f"- {src_label} -> {tgt_label}{label}")
    return "\n".join(lines)


def _parse_grouping_response(content: str) -> dict:
    """Parse Claude's JSON response, handling markdown code blocks."""
    content = content.strip()
    if content.startswith("```json"):
        content = content[7:]
    if content.startswith("```"):
        content = content[3:]
    if content.endswith("```"):
        content = content[:-3]
    return json.loads(content.strip())


def _validate_group_suggestions(groups: list, diagram: Diagram) -> List[dict]:
    """
    Validate AI group suggestions against actual diagram.

    - Filters out non-existent node IDs
    - Ensures each group has at least 2 valid nodes
    - Prevents nodes from being in multiple groups
    """
    valid_node_ids = {n.id for n in diagram.nodes}
    validated = []
    used_node_ids: Set[str] = set()

    for group in groups:
        node_ids = group.get("node_ids", [])
        # Filter to only existing nodes that haven't been used
        available_ids = [
            nid for nid in node_ids
            if nid in valid_node_ids and nid not in used_node_ids
        ]
        # Skip if less than 2 valid nodes
        if len(available_ids) < 2:
            continue

        used_node_ids.update(available_ids)
        validated.append({
            "name": group.get("name", "Group"),
            "description": group.get("description", ""),
            "node_ids": available_ids,
        })

    return validated


def suggest_semantic_groups(diagram: Diagram, model: str = "claude-haiku-4-5") -> Optional[List[dict]]:
    """
    Use AI to analyze diagram and suggest semantic business domain groupings.

    Args:
        diagram: The flat diagram to analyze
        model: Claude model to use

    Returns:
        List of validated group suggestions, or None if AI fails/suggests nothing
    """
    # Skip small diagrams
    if len(diagram.nodes) < 7:
        print(f"Diagram has {len(diagram.nodes)} nodes (<7), skipping AI grouping")
        return None

    try:
        api_key = get_anthropic_api_key()
        llm = ChatAnthropic(
            model=model,
            api_key=api_key,
            temperature=0.3,  # Lower temp for more consistent grouping
            max_tokens=2000,
        )

        # Format context for AI
        nodes_context = _format_nodes_for_grouping(diagram.nodes)
        edges_context = _format_edges_for_grouping(diagram.edges, diagram.nodes)

        prompt = SEMANTIC_GROUPING_PROMPT.format(
            nodes_context=nodes_context,
            edges_context=edges_context
        )

        print(f"Calling AI for semantic grouping analysis...")

        # Call Claude
        response = llm.invoke([
            SystemMessage(content="You are an expert system architect analyzing component relationships."),
            HumanMessage(content=prompt)
        ])

        print(f"AI grouping response received ({len(response.content)} chars)")

        # Parse JSON response
        result = _parse_grouping_response(response.content)

        # Validate groups
        groups = result.get("groups", [])
        valid_groups = _validate_group_suggestions(groups, diagram)

        if valid_groups:
            print(f"AI suggested {len(valid_groups)} valid groups")
            return valid_groups
        else:
            print(f"AI returned no valid groups")
            return None

    except json.JSONDecodeError as e:
        print(f"AI semantic grouping failed - JSON parse error: {e}")
        return None
    except Exception as e:
        print(f"AI semantic grouping failed: {e}")
        return None


def apply_ai_suggested_groups(diagram: Diagram, ai_groups: List[dict]) -> Diagram:
    """
    Apply AI-suggested groupings to the diagram.

    Creates group nodes, sets parent_id on children, and redirects edges.
    """
    for group_info in ai_groups:
        node_ids = group_info["node_ids"]
        child_nodes = [n for n in diagram.nodes if n.id in node_ids]

        if len(child_nodes) < 2:
            continue

        # Determine dominant type for coloring
        type_counts: Dict[str, int] = {}
        for n in child_nodes:
            type_counts[n.type] = type_counts.get(n.type, 0) + 1
        dominant_type = max(type_counts, key=type_counts.get)

        # Calculate average position
        avg_x = sum(n.position.x for n in child_nodes) / len(child_nodes)
        avg_y = sum(n.position.y for n in child_nodes) / len(child_nodes)

        # Create group node
        group_id = f"group-{uuid.uuid4().hex[:6]}"
        group_name = group_info["name"]
        group_node = Node(
            id=group_id,
            type=dominant_type,
            label=f"{group_name} ({len(child_nodes)})",
            description=group_info.get("description", f"Group containing {len(child_nodes)} components"),
            inputs=[],
            outputs=[],
            metadata=NodeMetadata(
                technology=None,
                notes="AI-suggested semantic grouping",
                child_types=list(set(n.type for n in child_nodes)),
            ),
            position=NodePosition(x=avg_x, y=avg_y),
            is_group=True,
            is_collapsed=True,
            child_ids=node_ids,
            parent_id=None,
        )

        diagram.nodes.append(group_node)

        # Update children to reference parent
        for node in diagram.nodes:
            if node.id in node_ids:
                node.parent_id = group_id

        print(f"  Created semantic group '{group_node.label}' with nodes: {node_ids}")

    # NOTE: Original edges are preserved - frontend handles dynamic redirection
    # based on collapse state. This ensures edges are visible when groups expand.

    return diagram


# =============================================================================
# Validation and Heuristic Grouping Functions
# =============================================================================

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

    # NOTE: Original edges are preserved - frontend handles dynamic redirection
    # based on collapse state. This ensures edges are visible when groups expand.

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


def ensure_groups_collapsed(diagram: Diagram) -> Diagram:
    """Ensure all groups start in collapsed state."""
    for node in diagram.nodes:
        if node.is_group:
            node.is_collapsed = True
    return diagram


def process_diagram_groups(
    diagram: Diagram,
    max_visible_nodes: int = 6,
    model: str = "claude-haiku-4-5"
) -> Diagram:
    """
    Main entry point for group processing.

    Uses AI-first approach for semantic grouping, falls back to heuristic layer-based grouping.

    Args:
        diagram: The diagram to process
        max_visible_nodes: Threshold below which no grouping is applied
        model: Claude model to use for AI grouping
    """
    print(f"\n=== GROUP PROCESSING ===")
    print(f"Input: {len(diagram.nodes)} nodes, {len(diagram.edges)} edges")

    # 1. Validate any existing groups
    diagram = validate_group_structure(diagram)

    # 2. Skip if already has valid groups
    has_groups = any(n.is_group for n in diagram.nodes)
    if has_groups:
        print(f"Diagram already has groups, skipping auto-grouping")
        diagram = ensure_groups_collapsed(diagram)
        visible_nodes = [n for n in diagram.nodes if not n.parent_id]
        group_nodes = [n for n in diagram.nodes if n.is_group]
        print(f"Output: {len(visible_nodes)} visible nodes, {len(group_nodes)} groups")
        print(f"========================\n")
        return diagram

    # 3. Skip if small enough
    if len(diagram.nodes) <= max_visible_nodes:
        print(f"Diagram has {len(diagram.nodes)} nodes (≤{max_visible_nodes}), skipping grouping")
        print(f"========================\n")
        return diagram

    # 4. Try AI-based semantic grouping (primary approach)
    print(f"Attempting AI semantic grouping for {len(diagram.nodes)} nodes...")
    ai_groups = suggest_semantic_groups(diagram, model)

    if ai_groups:
        print(f"AI suggested {len(ai_groups)} semantic groups, applying...")
        diagram = apply_ai_suggested_groups(diagram, ai_groups)
    else:
        # 5. Fall back to heuristic layer-based grouping
        print(f"AI grouping returned no results, falling back to heuristic layer-based grouping")
        diagram = apply_heuristic_grouping(diagram, max_visible_nodes)

    # 6. Ensure groups start collapsed
    diagram = ensure_groups_collapsed(diagram)

    visible_nodes = [n for n in diagram.nodes if not n.parent_id]
    group_nodes = [n for n in diagram.nodes if n.is_group]
    print(f"Output: {len(visible_nodes)} visible nodes, {len(group_nodes)} groups")
    print(f"========================\n")

    return diagram
