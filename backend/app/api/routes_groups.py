"""Node-grouping endpoints (create, collapse-toggle, ungroup)."""

import base64
import json
import logging
import time

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request
from fastapi.encoders import jsonable_encoder
from fastapi.responses import HTMLResponse, JSONResponse, Response
from pydantic import BaseModel
from typing import Optional

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from app.agent.doc_generator import generate_design_document, generate_design_document_preview
from app.agent.graph import agent_graph, generate_suggestions, process_diagram_groups
from app.agent.name_generator import generate_session_name
from app.api.deps import verify_session_access
from app.api._helpers import (
    check_and_deduct_credits,
    generate_system_overview,
    _should_generate_session_name,
    _generate_session_name_from_content,
)
from app.billing.credit_costs import DESIGN_DOC_PLANS, calculate_cost
from app.billing.promo_codes import get_promo_code_info, redeem_promo_code, validate_promo_code
from app.billing.storage import get_user_credits_storage
from app.config.models import DEFAULT_MODEL
from app.gamification.achievements import (
    ACHIEVEMENT_DEFINITIONS,
    ACHIEVEMENTS_BY_ID,
    get_achievement_progress,
)
from app.gamification.engine import process_action
from app.gamification.storage import get_gamification_storage
from app.gamification.streaks import check_streak_expired
from app.gamification.xp import get_level_progress
from app.github.analyzer import (
    GitHubAnalyzer,
    GitHubRateLimitError,
    RepoAccessDeniedError,
    RepoNotFoundError,
)
from app.github.prompts import format_repo_analysis_prompt
from app.models import (
    AnalyzeRepoRequest,
    AnalyzeRepoResponse,
    ChatRequest,
    ChatResponse,
    CreateGroupRequest,
    CreateGroupResponse,
    Diagram,
    Edge,
    GenerateRequest,
    GenerateResponse,
    Message,
    Node,
    NodeMetadata,
    NodePosition,
    SessionState,
)
from app.session.manager import session_manager
from app.subscription.models import SubscribeRequest, SubscriptionStatus
from app.subscription.storage import get_subscriber_storage
from app.user.models import UserPreferences
from app.user.storage import get_user_preferences_storage
from app.utils.badge_generator import get_monthly_visitors_badge_svg
from app.utils.diagram_export import convert_markdown_to_pdf, generate_diagram_png
from app.utils.logger import (
    EventType,
    log_chat_interaction,
    log_design_doc_generation,
    log_diagram_generation,
    log_error,
    log_event,
    log_export,
)
from app.utils.secrets import get_anthropic_api_key

logger = logging.getLogger(__name__)
router = APIRouter()


def generate_group_description_ai(child_nodes: list[Node], model: str = DEFAULT_MODEL) -> dict:
    """
    Generate AI-powered description for a group of nodes.

    Args:
        child_nodes: List of nodes being grouped together
        model: Claude model to use for generation

    Returns:
        Dictionary with generated label, description, and optional metadata
    """
    try:
        # Create Claude LLM instance
        api_key = get_anthropic_api_key()
        llm = ChatAnthropic(
            model=model,
            api_key=api_key,
            temperature=0.7,
            max_tokens=500,  # Small response needed
        )

        # Format child nodes information
        nodes_info = []
        for node in child_nodes:
            node_info = f"- **{node.label}** ({node.type})"
            if node.description:
                node_info += f": {node.description}"
            if node.metadata and node.metadata.technology:
                node_info += f" [Technology: {node.metadata.technology}]"
            nodes_info.append(node_info)

        nodes_context = "\n".join(nodes_info)

        # Create prompt for AI generation
        prompt = f"""You are analyzing a group of {len(child_nodes)} infrastructure components that have been merged together into a collapsible group.

**Nodes in this group:**
{nodes_context}

Generate a concise, technical description for this group. Return ONLY a valid JSON object with these fields:

{{
  "label": "3-5 word descriptive name for the group",
  "description": "1-2 sentence explanation of what this group does or represents",
  "technology": "Optional: overall technology category if applicable (e.g., 'Microservices', 'Data Layer', 'Authentication Stack')",
  "notes": "Optional: brief architectural insight or pattern"
}}

Make the label concise and professional (e.g., "User Authentication Service", "Data Processing Pipeline", "Frontend Assets").
Make the description technical and specific to what these components accomplish together.

Return ONLY the JSON, no markdown code blocks or extra text."""

        messages = [
            SystemMessage(content="You are an expert system architect who creates concise, technical descriptions for infrastructure components."),
            HumanMessage(content=prompt)
        ]

        logger.info(f"\n=== GENERATING AI GROUP DESCRIPTION ===")
        logger.info(f"Child nodes: {len(child_nodes)}")
        logger.info(f"Node types: {[n.type for n in child_nodes]}")

        response = llm.invoke(messages)

        logger.info(f"AI Response: {response.content[:200]}...")

        # Parse JSON response
        # Clean up markdown code blocks if present
        content = response.content.strip()
        if content.startswith("```json"):
            content = content[7:]  # Remove ```json
        if content.startswith("```"):
            content = content[3:]  # Remove ```
        if content.endswith("```"):
            content = content[:-3]  # Remove trailing ```
        content = content.strip()

        result = json.loads(content)

        logger.info(f"Parsed result: label='{result.get('label')}', description length={len(result.get('description', ''))}")
        logger.info(f"=====================================\n")

        return result

    except Exception as e:
        logger.exception(f"✗ Error generating AI description: {e}")
        logger.info(f"  Falling back to default description")
        # Return None to signal fallback to default logic
        return None


@router.post("/session/{session_id}/groups", response_model=CreateGroupResponse)
async def create_node_group(
    session_id: str,
    request: CreateGroupRequest,
    http_request: Request,
    generate_ai_description: bool = True
):
    """
    Create a collapsible group from multiple nodes (drag-to-merge feature).

    This merges the specified nodes into a parent group node that inherits all
    their connections. The group starts collapsed by default.

    Args:
        session_id: The session ID
        request: Contains child_node_ids to merge
        generate_ai_description: If True, use AI to generate smart descriptions (default: True)

    Returns:
        Updated diagram with new group node
    """
    user_id = getattr(http_request.state, "user_id", None)
    session = verify_session_access(session_id, user_id, http_request)

    child_node_ids = request.child_node_ids

    # Validate: need at least 2 nodes to group
    if len(child_node_ids) < 2:
        raise HTTPException(status_code=400, detail="Need at least 2 nodes to create a group")

    # Validate: all child nodes exist
    existing_node_ids = {n.id for n in session.diagram.nodes}
    for node_id in child_node_ids:
        if node_id not in existing_node_ids:
            raise HTTPException(status_code=404, detail=f"Node '{node_id}' not found")

    # Get child nodes
    child_nodes = [n for n in session.diagram.nodes if n.id in child_node_ids]

    # Validate: prevent nested groups - check if any node already has a parent
    for node in child_nodes:
        if node.parent_id:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot group node '{node.id}' because it already belongs to group '{node.parent_id}'. "
                       "Remove it from its current group first."
            )

    # Check if any of the nodes is already a group
    existing_group = None
    non_group_nodes = []
    for node in child_nodes:
        if node.is_group:
            existing_group = node
        else:
            non_group_nodes.append(node)

    if existing_group:
        # Add non-group nodes to the existing group
        group_id = existing_group.id

        # Update existing group's child_ids
        for node_id in [n.id for n in non_group_nodes]:
            if node_id not in existing_group.child_ids:
                existing_group.child_ids.append(node_id)

        # Get all child nodes (existing + new) to recalculate type
        all_children = [n for n in session.diagram.nodes if n.id in existing_group.child_ids]
        child_types = [n.type for n in all_children]

        # Try AI generation if enabled
        ai_result = None
        if generate_ai_description:
            ai_result = generate_group_description_ai(all_children, session.model)

        if ai_result:
            # Use AI-generated description
            existing_group.label = ai_result.get("label", existing_group.label)
            existing_group.description = ai_result.get("description", existing_group.description)
            if ai_result.get("technology"):
                existing_group.metadata.technology = ai_result["technology"]
            if ai_result.get("notes"):
                existing_group.metadata.notes = ai_result["notes"]
        else:
            # Fallback to default logic
            # Recalculate group type
            if len(set(child_types)) == 1:
                # All same type - use that type
                existing_group.type = child_types[0]
                existing_group.label = f"Group ({len(existing_group.child_ids)} {child_types[0]}s)"
            else:
                # Mixed types - use generic "group"
                existing_group.type = "group"
                existing_group.label = f"Group ({len(existing_group.child_ids)} nodes)"

            existing_group.description = f"Collapsible group containing {len(existing_group.child_ids)} nodes"

        # Set parent_id on newly added children
        for node in session.diagram.nodes:
            if node.id in [n.id for n in non_group_nodes]:
                node.parent_id = group_id

        # Update child_types metadata for color blending
        existing_group.metadata.child_types = child_types

        # Inherit edges from newly added nodes
        new_node_ids = set([n.id for n in non_group_nodes])
        new_edges = []
        edges_to_remove = []

        for edge in session.diagram.edges:
            # Skip if this is an internal edge within the group
            all_child_ids = set(existing_group.child_ids)
            is_internal = edge.source in all_child_ids and edge.target in all_child_ids
            if is_internal:
                continue

            # Redirect edges from newly added nodes
            if edge.source in new_node_ids:
                # Outgoing edge from a newly added child - redirect from group
                edges_to_remove.append(edge.id)
                new_edge_id = f"{group_id}-to-{edge.target}"
                if not any(e.id == new_edge_id for e in session.diagram.edges) and not any(e.id == new_edge_id for e in new_edges):
                    new_edges.append(Edge(
                        id=new_edge_id,
                        source=group_id,
                        target=edge.target,
                        label=edge.label,
                        type=edge.type
                    ))
            elif edge.target in new_node_ids:
                # Incoming edge to a newly added child - redirect to group
                edges_to_remove.append(edge.id)
                new_edge_id = f"{edge.source}-to-{group_id}"
                if not any(e.id == new_edge_id for e in session.diagram.edges) and not any(e.id == new_edge_id for e in new_edges):
                    new_edges.append(Edge(
                        id=new_edge_id,
                        source=edge.source,
                        target=group_id,
                        label=edge.label,
                        type=edge.type
                    ))

        # Remove old edges and add new ones
        session.diagram.edges = [e for e in session.diagram.edges if e.id not in edges_to_remove]
        session.diagram.edges.extend(new_edges)

        # Persist to storage
        session_manager.update_diagram(session_id, session.diagram)

        # Log event
        user_ip = http_request.client.host if http_request.client else None
        log_event(
            EventType.NODE_UPDATED,
            session_id=session_id,
            user_ip=user_ip,
            metadata={"node_id": group_id, "action": "add_to_group", "added_count": len(non_group_nodes)},
        )

        return CreateGroupResponse(diagram=session.diagram, group_id=group_id)

    # No existing group - create a new one
    import uuid

    group_id = f"group-{uuid.uuid4().hex[:8]}"

    # Determine group type: if all children have the same type, use that; otherwise use "group"
    child_types = [n.type for n in child_nodes]
    if len(set(child_types)) == 1:
        # All same type - use that type
        group_type = child_types[0]
        default_label = f"Group ({len(child_nodes)} {group_type}s)"
    else:
        # Mixed types - use generic "group"
        group_type = "group"
        default_label = f"Group ({len(child_nodes)} nodes)"

    default_description = f"Collapsible group containing {len(child_nodes)} nodes"

    # Try AI generation if enabled
    ai_result = None
    if generate_ai_description:
        ai_result = generate_group_description_ai(child_nodes, session.model)

    # Use AI results or defaults
    if ai_result:
        group_label = ai_result.get("label", default_label)
        group_description = ai_result.get("description", default_description)
        group_metadata = NodeMetadata(
            technology=ai_result.get("technology"),
            notes=ai_result.get("notes")
        )
    else:
        group_label = default_label
        group_description = default_description
        group_metadata = NodeMetadata()

    # Store child types for frontend color blending
    group_metadata.child_types = child_types

    # Calculate average position of children
    avg_x = sum(n.position.x for n in child_nodes) / len(child_nodes)
    avg_y = sum(n.position.y for n in child_nodes) / len(child_nodes)

    # Create group node
    group_node = Node(
        id=group_id,
        type=group_type,
        label=group_label,
        description=group_description,
        inputs=[],
        outputs=[],
        metadata=group_metadata,
        position=NodePosition(x=avg_x, y=avg_y),
        is_group=True,
        is_collapsed=True,  # Start collapsed
        child_ids=child_node_ids,
        parent_id=None
    )

    # Update child nodes to reference parent
    for node in session.diagram.nodes:
        if node.id in child_node_ids:
            node.parent_id = group_id

    # Add group node to diagram
    session.diagram.nodes.append(group_node)

    # Note: We keep all original edges intact. The frontend dynamically re-routes
    # edges through collapsed groups during rendering (DiagramCanvas.jsx).
    # This ensures edges are preserved when groups are expanded.

    # Persist to storage
    session_manager.update_diagram(session_id, session.diagram)

    # Log event
    user_ip = http_request.client.host if http_request.client else None
    log_event(
        EventType.NODE_ADDED,
        session_id=session_id,
        user_ip=user_ip,
        metadata={"node_id": group_id, "node_type": "group", "child_count": len(child_nodes)},
    )

    # Gamification: track group creation
    gamification_result = process_action(user_id, "group_created")

    return CreateGroupResponse(diagram=session.diagram, group_id=group_id, gamification=gamification_result)


@router.patch("/session/{session_id}/groups/{group_id}/collapse", response_model=Diagram)
async def toggle_group_collapse(
    session_id: str,
    group_id: str,
    http_request: Request
):
    """
    Toggle the collapse state of a group node.

    When collapsed: children are hidden, edges route through parent
    When expanded: children are shown, parent is hidden
    """
    user_id = getattr(http_request.state, "user_id", None)
    session = verify_session_access(session_id, user_id, http_request)

    # Find group node
    group_node = None
    for node in session.diagram.nodes:
        if node.id == group_id:
            group_node = node
            break

    if not group_node:
        raise HTTPException(status_code=404, detail=f"Group '{group_id}' not found")

    if not group_node.is_group:
        raise HTTPException(status_code=400, detail=f"Node '{group_id}' is not a group")

    # Toggle collapse state
    group_node.is_collapsed = not group_node.is_collapsed

    # Persist to storage
    session_manager.update_diagram(session_id, session.diagram)

    # Log event
    user_ip = http_request.client.host if http_request.client else None
    log_event(
        EventType.NODE_UPDATED,
        session_id=session_id,
        user_ip=user_ip,
        metadata={"node_id": group_id, "is_collapsed": group_node.is_collapsed},
    )

    # Gamification: track group collapse (only when collapsing, not expanding)
    gamification_result = None
    if group_node.is_collapsed:
        gamification_result = process_action(user_id, "group_collapsed")

    content = jsonable_encoder(session.diagram)
    if gamification_result:
        content["gamification"] = gamification_result
    return JSONResponse(content=content)


@router.delete("/session/{session_id}/groups/{group_id}", response_model=Diagram)
async def ungroup_nodes(
    session_id: str,
    group_id: str,
    http_request: Request
):
    """
    Dissolve a group and restore individual nodes.

    Removes the parent group node and clears parent_id from all children.
    """
    user_id = getattr(http_request.state, "user_id", None)
    session = verify_session_access(session_id, user_id, http_request)

    # Find group node
    group_node = None
    for node in session.diagram.nodes:
        if node.id == group_id:
            group_node = node
            break

    if not group_node:
        raise HTTPException(status_code=404, detail=f"Group '{group_id}' not found")

    if not group_node.is_group:
        raise HTTPException(status_code=400, detail=f"Node '{group_id}' is not a group")

    # Clear parent_id from all children
    for node in session.diagram.nodes:
        if node.parent_id == group_id:
            node.parent_id = None

    # Remove group node
    session.diagram.nodes = [n for n in session.diagram.nodes if n.id != group_id]

    # Remove edges connected to the group node
    session.diagram.edges = [
        e for e in session.diagram.edges
        if e.source != group_id and e.target != group_id
    ]

    # Persist to storage
    session_manager.update_diagram(session_id, session.diagram)

    # Log event
    user_ip = http_request.client.host if http_request.client else None
    log_event(
        EventType.NODE_DELETED,
        session_id=session_id,
        user_ip=user_ip,
        metadata={"node_id": group_id, "node_type": "group"},
    )

    return session.diagram
