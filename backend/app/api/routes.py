from fastapi import APIRouter, HTTPException, Request, BackgroundTasks
from fastapi.responses import Response, JSONResponse
from pydantic import BaseModel
from typing import Optional
from langchain_core.messages import HumanMessage, AIMessage
from app.models import (
    GenerateRequest,
    GenerateResponse,
    ChatRequest,
    ChatResponse,
    SessionState,
    Diagram,
    Message,
    Node,
    Edge,
    CreateGroupRequest,
    CreateGroupResponse,
)
from app.session.manager import session_manager
from app.agent.graph import agent_graph
from app.agent.doc_generator import generate_design_document
from app.agent.name_generator import generate_session_name
from app.utils.diagram_export import generate_diagram_png, convert_markdown_to_pdf
from app.utils.logger import (
    log_diagram_generation,
    log_chat_interaction,
    log_export,
    log_event,
    log_error,
    EventType,
)
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage
from app.utils.secrets import get_anthropic_api_key
import json
import base64
import time

router = APIRouter()


def generate_system_overview(diagram: Diagram) -> str:
    """
    Generate a formatted system overview message from a diagram.
    This is what the user sees in chat after diagram generation.

    Args:
        diagram: The generated diagram

    Returns:
        Formatted markdown system overview message
    """
    node_count = len(diagram.nodes)
    node_types = sorted(set(node.type for node in diagram.nodes))

    overview = f"""## System Overview
I've generated a system architecture with {node_count} components.

**Component Types**
{chr(10).join(f"- {node_type}" for node_type in node_types)}

**What's Next?**
- Click any node to focus the conversation on that component
- Ask questions about the overall system design
- Request changes to add, remove, or modify components

Feel free to explore the diagram and ask me anything!"""

    return overview


def verify_session_access(session_id: str, user_id: str, http_request: Request) -> SessionState:
    """
    Helper function to verify user has access to a session.

    Args:
        session_id: Session ID to check
        user_id: User ID from authenticated request
        http_request: FastAPI Request object

    Returns:
        SessionState if user has access

    Raises:
        HTTPException: 401 if not authenticated, 404 if session not found, 403 if no access
    """
    if not user_id:
        raise HTTPException(status_code=401, detail="User authentication required")

    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if not session_manager.verify_ownership(session_id, user_id):
        raise HTTPException(status_code=403, detail="You don't have permission to access this session")

    return session


def generate_group_description_ai(child_nodes: list[Node], model: str = "claude-haiku-4-5-20251001") -> dict:
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

        print(f"\n=== GENERATING AI GROUP DESCRIPTION ===")
        print(f"Child nodes: {len(child_nodes)}")
        print(f"Node types: {[n.type for n in child_nodes]}")

        response = llm.invoke(messages)

        print(f"AI Response: {response.content[:200]}...")

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

        print(f"Parsed result: label='{result.get('label')}', description length={len(result.get('description', ''))}")
        print(f"=====================================\n")

        return result

    except Exception as e:
        print(f"✗ Error generating AI description: {e}")
        print(f"  Falling back to default description")
        # Return None to signal fallback to default logic
        return None


class ExportRequest(BaseModel):
    diagram_image: str | None = None  # Base64 encoded PNG from frontend


def _should_generate_session_name(session) -> bool:
    """Check if session needs a name generated."""
    # Skip if already generated
    if session.name_generated:
        return False

    # Skip if name is set to something other than None or "Untitled Design"
    if session.name and session.name != "Untitled Design":
        return False

    return True


def _generate_session_name_from_content(session_id: str, model: str):
    """
    Background task to generate session name from session content.
    Uses first message or node descriptions if no messages exist.
    """
    import os

    try:
        session = session_manager.get_session(session_id)
        if not session:
            print(f"Session {session_id} not found for name generation")
            return

        # Skip if already generated
        if not _should_generate_session_name(session):
            print(f"Session {session_id} already has a name: {session.name}")
            return

        print(f"\n=== BACKGROUND: GENERATE SESSION NAME ===")
        print(f"Session ID: {session_id}")

        # Build prompt from session content
        # Priority: 1) First user message, 2) Node descriptions
        prompt = None

        if session.messages:
            # Find first user message
            for msg in session.messages:
                if msg.role == "user":
                    prompt = msg.content
                    print(f"Using first user message: {prompt[:100]}...")
                    break

        if not prompt and session.diagram and session.diagram.nodes:
            # Use node descriptions/labels
            node_descriptions = [f"{node.label}: {node.description}" for node in session.diagram.nodes[:5]]
            prompt = "System with: " + ", ".join(node_descriptions)
            print(f"Using node descriptions: {prompt[:100]}...")

        if not prompt:
            print("No content available for name generation, skipping")
            return

        # Get API key from environment or secrets
        from app.utils.secrets import get_anthropic_api_key
        api_key = get_anthropic_api_key()

        # Generate name using LLM
        import asyncio
        name = asyncio.run(generate_session_name(prompt, api_key, model))

        # Update session using proper method
        session_manager.update_session_name(session_id, name)

        print(f"Generated name: {name}")
        print(f"=========================================\n")

    except Exception as e:
        import traceback
        print(f"Error generating session name: {e}")
        print(traceback.format_exc())
        # Set fallback name so we don't retry
        try:
            session_manager.update_session_name(session_id, "Untitled Design")
        except:
            pass


def _generate_session_name_background(session_id: str, prompt: str, model: str):
    """Background task to generate session name from initial prompt (used by /generate endpoint)."""
    import os

    try:
        session = session_manager.get_session(session_id)
        if not session:
            print(f"Session {session_id} not found for name generation")
            return

        # Skip if already generated
        if not _should_generate_session_name(session):
            print(f"Session {session_id} already has a name: {session.name}")
            return

        print(f"\n=== BACKGROUND: GENERATE SESSION NAME ===")
        print(f"Session ID: {session_id}")
        print(f"Prompt: {prompt[:100]}...")

        # Get API key from environment or secrets
        from app.utils.secrets import get_anthropic_api_key
        api_key = get_anthropic_api_key()

        # Generate name using LLM
        import asyncio
        name = asyncio.run(generate_session_name(prompt, api_key, model))

        # Update session using proper method
        session_manager.update_session_name(session_id, name)

        print(f"Generated name: {name}")
        print(f"=========================================\n")

    except Exception as e:
        import traceback
        print(f"Error generating session name: {e}")
        print(traceback.format_exc())
        # Set fallback name so we don't retry
        try:
            session_manager.update_session_name(session_id, "Untitled Design")
        except:
            pass


@router.post("/generate", response_model=GenerateResponse)
async def generate_diagram(request: GenerateRequest, http_request: Request, background_tasks: BackgroundTasks):
    """Generate initial system diagram from user prompt."""
    start_time = time.time()
    user_ip = http_request.client.host if http_request.client else None

    # Extract user_id from request state (set by Clerk middleware)
    user_id = getattr(http_request.state, "user_id", None)
    if not user_id:
        raise HTTPException(status_code=401, detail="User authentication required")

    try:
        # Use specified model or default to Haiku (alias auto-updates to latest)
        model = request.model or "claude-haiku-4-5"

        # Run agent with message-based state
        result = agent_graph.invoke({
            "messages": [HumanMessage(content=request.prompt)],
            "diagram": None,
            "session_id": "",  # Will be created after
            "model": model,
        })

        # Extract diagram from result
        diagram = result["diagram"]

        # Create session with user_id
        session_id = session_manager.create_session(diagram, user_id=user_id, model=model)

        # Add messages to session (user + formatted assistant overview)
        session_manager.add_message(
            session_id,
            Message(role="user", content=request.prompt)
        )
        # Generate and store formatted system overview instead of raw JSON
        system_overview = generate_system_overview(diagram)
        session_manager.add_message(
            session_id,
            Message(role="assistant", content=system_overview)
        )

        # Generate session name in background
        background_tasks.add_task(_generate_session_name_background, session_id, request.prompt, model)

        # Log diagram generation event
        duration_ms = (time.time() - start_time) * 1000
        log_diagram_generation(
            session_id=session_id,
            node_count=len(diagram.nodes),
            edge_count=len(diagram.edges),
            prompt_length=len(request.prompt),
            duration_ms=duration_ms,
            user_ip=user_ip,
        )

        return GenerateResponse(
            session_id=session_id,
            diagram=diagram
        )

    except Exception as e:
        log_error(
            error_type="diagram_generation_failed",
            error_message=str(e),
            user_ip=user_ip,
        )
        raise HTTPException(status_code=500, detail=f"Failed to generate diagram: {str(e)}")


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest, http_request: Request, background_tasks: BackgroundTasks):
    """Continue conversation about diagram/node."""
    start_time = time.time()
    user_ip = http_request.client.host if http_request.client else None

    # Extract user_id from request state (set by Clerk middleware)
    user_id = getattr(http_request.state, "user_id", None)
    if not user_id:
        raise HTTPException(status_code=401, detail="User authentication required")

    try:
        # Get session
        session = session_manager.get_session(request.session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        # Verify ownership
        if not session_manager.verify_ownership(request.session_id, user_id):
            raise HTTPException(status_code=403, detail="You don't have permission to access this session")

        # Check if this is the first message and name hasn't been generated
        is_first_message = len(session.messages) == 0
        needs_name = is_first_message and _should_generate_session_name(session)

        # Update current node if provided
        if request.node_id:
            session_manager.set_current_node(request.session_id, request.node_id)

        # Convert Pydantic messages to LangChain messages
        langchain_messages = []
        for msg in session.messages:
            if msg.role == "user":
                langchain_messages.append(HumanMessage(content=msg.content))
            else:
                langchain_messages.append(AIMessage(content=msg.content))

        # Add current user message
        langchain_messages.append(HumanMessage(content=request.message))

        # Store diagram/doc state before agent call for comparison
        # Make a serializable copy for comparison (model_dump then reconstruct)
        old_diagram_dict = session.diagram.model_dump()
        old_design_doc = session.design_doc

        # Use model from request if provided, otherwise use session's model
        model_to_use = request.model if request.model else session.model

        # Update session model if changed
        if request.model and request.model != session.model:
            session_manager.update_model(request.session_id, request.model)

        # Run agent with message-based state
        result = agent_graph.invoke({
            "messages": langchain_messages,
            "diagram": session.diagram,
            "design_doc": session.design_doc,
            "node_id": request.node_id,
            "session_id": request.session_id,
            "model": model_to_use,
        })

        # Add user message to session
        session_manager.add_message(
            request.session_id,
            Message(role="user", content=request.message)
        )

        # Extract assistant response from last message
        response_text = ""
        if result.get("messages"):
            last_msg = result["messages"][-1]
            if isinstance(last_msg, AIMessage):
                response_text = last_msg.content

        # Check if diagram was updated by reloading from session storage
        # This is critical for production (DynamoDB) where tools update the session
        # directly, but the agent state may not reflect those changes
        response_diagram = None
        diagram_updated = False

        # Reload session to get any updates made by tools
        updated_session = session_manager.get_session(request.session_id)
        new_diagram_dict = updated_session.diagram.model_dump()

        if new_diagram_dict != old_diagram_dict:
            response_diagram = updated_session.diagram
            diagram_updated = True
            print(f"✓ Diagram updated: {len(updated_session.diagram.nodes)} nodes, {len(updated_session.diagram.edges)} edges")

        # Check if design doc was updated (reload from session like diagram)
        response_design_doc = None
        if updated_session.design_doc and updated_session.design_doc != old_design_doc:
            response_design_doc = updated_session.design_doc
            print(f"✓ Design doc updated via chat ({len(response_design_doc)} chars)")

        # Add assistant response to session
        session_manager.add_message(
            request.session_id,
            Message(role="assistant", content=response_text)
        )

        # Log chat interaction
        duration_ms = (time.time() - start_time) * 1000
        log_chat_interaction(
            session_id=request.session_id,
            message_length=len(request.message),
            node_id=request.node_id,
            diagram_updated=diagram_updated,
            duration_ms=duration_ms,
            user_ip=user_ip,
        )

        # Generate session name in background if this was the first message
        if needs_name:
            background_tasks.add_task(_generate_session_name_from_content, request.session_id, session.model)

        return ChatResponse(
            response=response_text,
            diagram=response_diagram,
            design_doc=response_design_doc
        )

    except HTTPException:
        raise
    except Exception as e:
        log_error(
            error_type="chat_failed",
            error_message=str(e),
            session_id=request.session_id,
            user_ip=user_ip,
        )
        raise HTTPException(status_code=500, detail=f"Chat failed: {str(e)}")


@router.get("/session/{session_id}", response_model=SessionState)
async def get_session(session_id: str, http_request: Request):
    """Retrieve current session state."""
    # Extract user_id from request state (set by Clerk middleware)
    user_id = getattr(http_request.state, "user_id", None)
    if not user_id:
        raise HTTPException(status_code=401, detail="User authentication required")

    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Verify ownership
    if not session_manager.verify_ownership(session_id, user_id):
        raise HTTPException(status_code=403, detail="You don't have permission to access this session")

    return session


@router.patch("/session/{session_id}/name")
async def rename_session(session_id: str, request: dict, http_request: Request):
    """Rename a session."""
    user_id = getattr(http_request.state, "user_id", None)
    if not user_id:
        raise HTTPException(status_code=401, detail="User authentication required")

    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if not session_manager.verify_ownership(session_id, user_id):
        raise HTTPException(status_code=403, detail="You don't have permission to modify this session")

    new_name = request.get("name", "").strip()
    if not new_name:
        raise HTTPException(status_code=400, detail="Session name cannot be empty")

    # Update session name using the proper method
    success = session_manager.update_session_name(session_id, new_name)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to update session name")

    return {"success": True, "name": new_name}


@router.delete("/session/{session_id}")
async def delete_session(session_id: str, http_request: Request):
    """Delete a session."""
    user_id = getattr(http_request.state, "user_id", None)
    if not user_id:
        raise HTTPException(status_code=401, detail="User authentication required")

    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if not session_manager.verify_ownership(session_id, user_id):
        raise HTTPException(status_code=403, detail="You don't have permission to delete this session")

    # Delete the session
    session_manager.delete_session(session_id)

    # Log event
    user_ip = http_request.client.host if http_request.client else None
    log_event(
        EventType.API_REQUEST,
        session_id=session_id,
        user_ip=user_ip,
        metadata={"action": "delete_session"},
    )

    return {"success": True, "message": "Session deleted successfully"}


@router.post("/session/create-blank")
async def create_blank_session(http_request: Request):
    """Create a new blank session with empty diagram."""
    user_id = getattr(http_request.state, "user_id", None)
    if not user_id:
        raise HTTPException(status_code=401, detail="User authentication required")

    # Create empty diagram
    empty_diagram = Diagram(nodes=[], edges=[])

    # Create session with default model
    session_id = session_manager.create_session(
        empty_diagram,
        user_id=user_id,
        model="claude-haiku-4-5"
    )

    # Set a default name
    session_manager.update_session_name(session_id, "Untitled Design")

    # Log event
    user_ip = http_request.client.host if http_request.client else None
    log_event(
        EventType.API_REQUEST,
        session_id=session_id,
        user_ip=user_ip,
        metadata={"action": "create_blank_session"},
    )

    return {
        "session_id": session_id,
        "diagram": empty_diagram
    }


@router.post("/session/{session_id}/nodes", response_model=Diagram)
async def add_node(session_id: str, node: Node, http_request: Request, background_tasks: BackgroundTasks):
    """Add a new node to the diagram."""
    # Extract user_id and verify ownership
    user_id = getattr(http_request.state, "user_id", None)
    if not user_id:
        raise HTTPException(status_code=401, detail="User authentication required")

    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if not session_manager.verify_ownership(session_id, user_id):
        raise HTTPException(status_code=403, detail="You don't have permission to modify this session")

    # Check for duplicate node ID
    if any(n.id == node.id for n in session.diagram.nodes):
        raise HTTPException(status_code=400, detail=f"Node with id '{node.id}' already exists")

    # Check current node count before adding
    nodes_before = len(session.diagram.nodes)

    # Add node to diagram
    session.diagram.nodes.append(node)

    # Persist to storage (critical for DynamoDB in production)
    session_manager.update_diagram(session_id, session.diagram)

    # Check if we just added the 5th node and name hasn't been generated
    nodes_after = len(session.diagram.nodes)
    if nodes_after == 5 and _should_generate_session_name(session):
        background_tasks.add_task(_generate_session_name_from_content, session_id, session.model)

    # Log event
    user_ip = http_request.client.host if http_request.client else None
    log_event(
        EventType.NODE_ADDED,
        session_id=session_id,
        user_ip=user_ip,
        metadata={"node_id": node.id, "node_type": node.type},
    )

    return session.diagram


@router.delete("/session/{session_id}/nodes/{node_id}", response_model=Diagram)
async def delete_node(session_id: str, node_id: str, http_request: Request):
    """Delete a node and its connected edges from the diagram.

    If the node is a group, all child nodes are also deleted (cascade delete).
    """
    user_id = getattr(http_request.state, "user_id", None)
    session = verify_session_access(session_id, user_id, http_request)

    # Find the node to delete
    node_to_delete = next((n for n in session.diagram.nodes if n.id == node_id), None)
    if not node_to_delete:
        raise HTTPException(status_code=404, detail=f"Node '{node_id}' not found")

    # Collect all node IDs to delete (group + children if applicable)
    nodes_to_delete = [node_id]
    if node_to_delete.is_group and node_to_delete.child_ids:
        nodes_to_delete.extend(node_to_delete.child_ids)

    # Remove all nodes (group and children)
    original_count = len(session.diagram.nodes)
    session.diagram.nodes = [n for n in session.diagram.nodes if n.id not in nodes_to_delete]

    # Remove edges connected to any deleted node
    edges_removed = len([
        e for e in session.diagram.edges
        if e.source in nodes_to_delete or e.target in nodes_to_delete
    ])
    session.diagram.edges = [
        e for e in session.diagram.edges
        if e.source not in nodes_to_delete and e.target not in nodes_to_delete
    ]

    # Persist to storage (critical for DynamoDB in production)
    session_manager.update_diagram(session_id, session.diagram)

    # Log event
    user_ip = http_request.client.host if http_request.client else None
    log_event(
        EventType.NODE_DELETED,
        session_id=session_id,
        user_ip=user_ip,
        metadata={
            "node_id": node_id,
            "is_group": node_to_delete.is_group,
            "child_nodes_deleted": len(nodes_to_delete) - 1,
            "edges_removed": edges_removed
        },
    )

    return session.diagram


@router.patch("/session/{session_id}/nodes/{node_id}", response_model=Diagram)
async def update_node(session_id: str, node_id: str, updated_node: Node, http_request: Request):
    """Update an existing node's properties."""
    user_id = getattr(http_request.state, "user_id", None)
    session = verify_session_access(session_id, user_id, http_request)

    # Ensure IDs match
    if updated_node.id != node_id:
        raise HTTPException(status_code=400, detail="Node ID in body must match URL parameter")

    # Find and update node
    node_found = False
    for i, node in enumerate(session.diagram.nodes):
        if node.id == node_id:
            session.diagram.nodes[i] = updated_node
            node_found = True
            break

    if not node_found:
        raise HTTPException(status_code=404, detail=f"Node '{node_id}' not found")

    # Persist to storage (critical for DynamoDB in production)
    session_manager.update_diagram(session_id, session.diagram)

    return session.diagram


@router.post("/session/{session_id}/edges", response_model=Diagram)
async def add_edge(session_id: str, edge: Edge, http_request: Request):
    """Add a new edge to the diagram."""
    user_id = getattr(http_request.state, "user_id", None)
    session = verify_session_access(session_id, user_id, http_request)

    # Validate source and target nodes exist
    node_ids = {n.id for n in session.diagram.nodes}
    if edge.source not in node_ids:
        raise HTTPException(status_code=400, detail=f"Source node '{edge.source}' does not exist")
    if edge.target not in node_ids:
        raise HTTPException(status_code=400, detail=f"Target node '{edge.target}' does not exist")

    # Check for duplicate edge ID
    if any(e.id == edge.id for e in session.diagram.edges):
        raise HTTPException(status_code=400, detail=f"Edge with id '{edge.id}' already exists")

    # Add edge to diagram
    session.diagram.edges.append(edge)

    # Persist to storage (critical for DynamoDB in production)
    session_manager.update_diagram(session_id, session.diagram)

    return session.diagram


@router.delete("/session/{session_id}/edges/{edge_id}", response_model=Diagram)
async def delete_edge(session_id: str, edge_id: str, http_request: Request):
    """Delete an edge from the diagram."""
    user_id = getattr(http_request.state, "user_id", None)
    session = verify_session_access(session_id, user_id, http_request)

    # Find and remove edge
    original_count = len(session.diagram.edges)
    session.diagram.edges = [e for e in session.diagram.edges if e.id != edge_id]

    if len(session.diagram.edges) == original_count:
        raise HTTPException(status_code=404, detail=f"Edge '{edge_id}' not found")

    # Persist to storage (critical for DynamoDB in production)
    session_manager.update_diagram(session_id, session.diagram)

    return session.diagram


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
    from app.models import NodePosition, NodeMetadata

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

    # Inherit edges: redirect external edges to/from children through the group node
    child_node_ids_set = set(child_node_ids)
    new_edges = []
    edges_to_remove = []

    for edge in session.diagram.edges:
        is_internal = edge.source in child_node_ids_set and edge.target in child_node_ids_set

        if is_internal:
            # Internal edge between children - keep as is (will be hidden when collapsed)
            continue

        # External edge - redirect through group
        if edge.source in child_node_ids_set:
            # Outgoing edge from a child - redirect from group
            edges_to_remove.append(edge.id)
            new_edge_id = f"{group_id}-to-{edge.target}"
            # Check if this edge already exists (avoid duplicates)
            if not any(e.id == new_edge_id for e in session.diagram.edges) and not any(e.id == new_edge_id for e in new_edges):
                new_edges.append(Edge(
                    id=new_edge_id,
                    source=group_id,
                    target=edge.target,
                    label=edge.label,
                    type=edge.type
                ))
        elif edge.target in child_node_ids_set:
            # Incoming edge to a child - redirect to group
            edges_to_remove.append(edge.id)
            new_edge_id = f"{edge.source}-to-{group_id}"
            # Check if this edge already exists (avoid duplicates)
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
        EventType.NODE_ADDED,
        session_id=session_id,
        user_ip=user_ip,
        metadata={"node_id": group_id, "node_type": "group", "child_count": len(child_nodes)},
    )

    return CreateGroupResponse(diagram=session.diagram, group_id=group_id)


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

    return session.diagram


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


class GenerateDescriptionResponse(BaseModel):
    """Response model for AI-generated node description."""
    label: str
    description: str
    technology: Optional[str] = None
    notes: Optional[str] = None
    diagram: Diagram  # Updated diagram with new description


@router.post("/session/{session_id}/nodes/{node_id}/generate-description", response_model=GenerateDescriptionResponse)
async def generate_node_description(
    session_id: str,
    node_id: str,
    http_request: Request
):
    """
    Generate AI-powered description for a group node.

    This endpoint regenerates the label, description, and metadata for an existing
    group node based on its child nodes using AI.

    Args:
        session_id: The session ID
        node_id: The group node ID to regenerate description for

    Returns:
        Updated node description and full diagram
    """
    user_id = getattr(http_request.state, "user_id", None)
    session = verify_session_access(session_id, user_id, http_request)

    # Find the node
    target_node = None
    for node in session.diagram.nodes:
        if node.id == node_id:
            target_node = node
            break

    if not target_node:
        raise HTTPException(status_code=404, detail=f"Node '{node_id}' not found")

    if not target_node.is_group:
        raise HTTPException(status_code=400, detail=f"Node '{node_id}' is not a group. AI description generation is only available for group nodes.")

    # Get child nodes
    child_nodes = [n for n in session.diagram.nodes if n.id in target_node.child_ids]

    if not child_nodes:
        raise HTTPException(status_code=400, detail=f"Group '{node_id}' has no child nodes")

    # Generate AI description
    ai_result = generate_group_description_ai(child_nodes, session.model)

    if not ai_result:
        raise HTTPException(status_code=500, detail="Failed to generate AI description. Please try again.")

    # Update node with AI-generated content
    target_node.label = ai_result.get("label", target_node.label)
    target_node.description = ai_result.get("description", target_node.description)
    if ai_result.get("technology"):
        target_node.metadata.technology = ai_result["technology"]
    if ai_result.get("notes"):
        target_node.metadata.notes = ai_result["notes"]

    # Persist to storage
    session_manager.update_diagram(session_id, session.diagram)

    # Log event
    user_ip = http_request.client.host if http_request.client else None
    log_event(
        EventType.NODE_UPDATED,
        session_id=session_id,
        user_ip=user_ip,
        metadata={"node_id": node_id, "action": "ai_description_generated"},
    )

    return GenerateDescriptionResponse(
        label=target_node.label,
        description=target_node.description,
        technology=target_node.metadata.technology,
        notes=target_node.metadata.notes,
        diagram=session.diagram
    )


@router.post("/session/{session_id}/export/design-doc")
async def export_design_doc(session_id: str, request: ExportRequest, format: str = "pdf", http_request: Request = None):
    """
    Generate and export a comprehensive design document.

    Args:
        session_id: The session ID
        request: Request body with optional diagram_image
        format: Export format - 'markdown', 'pdf', or 'both' (default: 'pdf')

    Returns:
        JSON with base64 encoded files
    """
    start_time = time.time()
    user_ip = http_request.client.host if http_request and http_request.client else None
    user_id = getattr(http_request.state, "user_id", None) if http_request else None

    try:
        # Verify access
        session = verify_session_access(session_id, user_id, http_request)

        # Get conversation history
        conversation_history = [
            {"role": msg.role, "content": msg.content}
            for msg in session.messages
        ]

        print(f"\n=== EXPORT DESIGN DOC ===")
        print(f"Session ID: {session_id}")
        print(f"Format requested: {format}")
        print(f"Nodes: {len(session.diagram.nodes)}")
        print(f"Edges: {len(session.diagram.edges)}")
        print(f"Has custom diagram image: {request.diagram_image is not None}")

        # Generate markdown document using LLM with session's model
        markdown_content = generate_design_document(
            session.diagram.model_dump(),
            conversation_history,
            session.model
        )

        # Use provided diagram image or generate one
        if request.diagram_image:
            # Use the screenshot from frontend
            diagram_png = base64.b64decode(request.diagram_image)
            print("Using frontend screenshot for diagram")
        else:
            # Fallback to generated diagram
            diagram_png = generate_diagram_png(session.diagram.model_dump())
            print("Generated diagram using Pillow")

        result = {}

        # Return markdown if requested
        if format in ["markdown", "both"]:
            result["markdown"] = {
                "content": markdown_content,
                "filename": "design_document.md"
            }
            # Only include diagram PNG for "both" format, not for "markdown" alone
            if format == "both":
                result["diagram_png"] = {
                    "content": base64.b64encode(diagram_png).decode('utf-8'),
                    "filename": "diagram.png"
                }

        # Return PDF if requested
        if format in ["pdf", "both"]:
            pdf_bytes = convert_markdown_to_pdf(markdown_content, diagram_png)
            result["pdf"] = {
                "content": base64.b64encode(pdf_bytes).decode('utf-8'),
                "filename": "design_document.pdf"
            }

        print(f"Generated documents successfully")
        print(f"========================\n")

        # Log export event
        duration_ms = (time.time() - start_time) * 1000
        log_export(
            session_id=session_id,
            format=format,
            duration_ms=duration_ms,
            user_ip=user_ip,
            success=True,
        )

        return JSONResponse(content=result)

    except ImportError as e:
        import traceback
        traceback.print_exc()
        duration_ms = (time.time() - start_time) * 1000
        log_export(
            session_id=session_id,
            format=format,
            duration_ms=duration_ms,
            user_ip=user_ip,
            success=False,
        )
        raise HTTPException(
            status_code=500,
            detail=f"PDF generation dependencies not installed: {str(e)}"
        )
    except Exception as e:
        import traceback
        print(f"Error generating design doc: {str(e)}")
        traceback.print_exc()
        duration_ms = (time.time() - start_time) * 1000
        log_export(
            session_id=session_id,
            format=format,
            duration_ms=duration_ms,
            user_ip=user_ip,
            success=False,
        )
        raise HTTPException(status_code=500, detail=f"Failed to generate design document: {str(e)}")


def _generate_design_doc_background(session_id: str, user_ip: str):
    """Background task to generate design document."""
    start_time = time.time()

    try:
        # Get session
        session = session_manager.get_session(session_id)
        if not session:
            print(f"Session {session_id} not found in background task")
            return

        # Get conversation history
        conversation_history = [
            {"role": msg.role, "content": msg.content}
            for msg in session.messages
        ]

        print(f"\n=== BACKGROUND: GENERATE DESIGN DOC ===")
        print(f"Session ID: {session_id}")
        print(f"Nodes: {len(session.diagram.nodes)}")
        print(f"Edges: {len(session.diagram.edges)}")

        # Generate markdown document using LLM with session's model
        markdown_content = generate_design_document(
            session.diagram.model_dump(),
            conversation_history,
            session.model
        )

        # Store in session state
        session_manager.update_design_doc(session_id, markdown_content)
        session_manager.set_design_doc_status(session_id, "completed")

        print(f"Generated and stored design doc ({len(markdown_content)} chars)")
        print(f"========================================\n")

        # Log event
        duration_ms = (time.time() - start_time) * 1000
        log_event(
            EventType.EXPORT_DESIGN_DOC,
            session_id=session_id,
            user_ip=user_ip,
            metadata={"format": "generate", "duration_ms": duration_ms, "success": True},
        )

    except Exception as e:
        import traceback
        print(f"Error generating design doc in background: {str(e)}")
        traceback.print_exc()

        # Mark as failed
        session_manager.set_design_doc_status(session_id, "failed", error=str(e))

        duration_ms = (time.time() - start_time) * 1000
        log_event(
            EventType.EXPORT_DESIGN_DOC,
            session_id=session_id,
            user_ip=user_ip,
            metadata={"format": "generate", "duration_ms": duration_ms, "success": False, "error": str(e)},
        )


@router.post("/session/{session_id}/design-doc/generate")
async def generate_design_doc(session_id: str, request: ExportRequest, background_tasks: BackgroundTasks, http_request: Request):
    """
    Start design document generation.

    In local development: Uses background tasks for true async operation.
    In AWS Lambda: Runs synchronously but sets status immediately for polling compatibility.

    Args:
        session_id: The session ID
        request: Request body with optional diagram_image
        background_tasks: FastAPI background tasks

    Returns:
        JSON with status: "started"
    """
    import os
    user_ip = http_request.client.host if http_request.client else None
    user_id = getattr(http_request.state, "user_id", None)

    try:
        # Verify access
        session = verify_session_access(session_id, user_id, http_request)

        # Check if already generating
        if session.design_doc_status.status == "generating":
            return JSONResponse(content={
                "status": "already_generating",
                "message": "Design document generation already in progress"
            })

        # Set status to generating
        session_manager.set_design_doc_status(session_id, "generating")

        # Check if running in Lambda (AWS_LAMBDA_FUNCTION_NAME env var is set)
        is_lambda = os.environ.get('AWS_LAMBDA_FUNCTION_NAME') is not None

        if is_lambda:
            # In Lambda: Use async invocation to avoid API Gateway 30s timeout
            # API Gateway has a 30s timeout, but generation takes 30-150s
            # Solution: Invoke Lambda asynchronously for the actual generation
            import boto3
            import json as json_lib

            print(f"Lambda environment detected - triggering async invocation for session {session_id}")

            try:
                lambda_client = boto3.client('lambda')
                function_name = os.environ.get('AWS_LAMBDA_FUNCTION_NAME')

                # Invoke this same Lambda function asynchronously with a special event
                # that will trigger the generation without going through API Gateway
                payload = {
                    "async_task": "generate_design_doc",
                    "session_id": session_id,
                    "user_ip": user_ip
                }

                lambda_client.invoke(
                    FunctionName=function_name,
                    InvocationType='Event',  # Async invocation
                    Payload=json_lib.dumps(payload)
                )

                print(f"Async Lambda invocation triggered for session {session_id}")
            except Exception as e:
                print(f"Failed to trigger async invocation: {e}")
                # Fall back to inline execution (will timeout after 30s but generation continues)
                background_tasks.add_task(_generate_design_doc_background, session_id, user_ip)
        else:
            # Local development: Use true background tasks (non-blocking)
            print(f"Local environment - starting background generation for session {session_id}")
            background_tasks.add_task(_generate_design_doc_background, session_id, user_ip)

        return JSONResponse(content={
            "status": "started",
            "message": "Design document generation started"
        })

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        print(f"Error starting design doc generation: {str(e)}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to start design document generation: {str(e)}")


@router.get("/session/{session_id}/design-doc/status")
async def get_design_doc_status(session_id: str, http_request: Request):
    """
    Get the current status of design document generation.

    Args:
        session_id: The session ID

    Returns:
        JSON with status information
    """
    user_id = getattr(http_request.state, "user_id", None)
    session = verify_session_access(session_id, user_id, http_request)

    status = session.design_doc_status

    response = {
        "status": status.status,
        "error": status.error,
        "started_at": status.started_at,
        "completed_at": status.completed_at,
    }

    # Include the document if completed
    if status.status == "completed" and session.design_doc:
        response["design_doc"] = session.design_doc
        response["design_doc_length"] = len(session.design_doc)

    # Calculate duration if applicable
    if status.started_at:
        if status.completed_at:
            response["duration_seconds"] = status.completed_at - status.started_at
        else:
            # Still generating
            response["elapsed_seconds"] = time.time() - status.started_at

    return JSONResponse(content=response)


class DesignDocUpdateRequest(BaseModel):
    content: str


@router.patch("/session/{session_id}/design-doc")
async def update_design_doc(session_id: str, request: DesignDocUpdateRequest, http_request: Request):
    """
    Update design document content in session state.

    Args:
        session_id: The session ID
        request: Request body with updated content

    Returns:
        JSON with updated design_doc content
    """
    user_ip = http_request.client.host if http_request.client else None
    user_id = getattr(http_request.state, "user_id", None)

    try:
        # Verify access
        session = verify_session_access(session_id, user_id, http_request)

        # Validate content size (limit to 1MB)
        if len(request.content) > 1_000_000:
            raise HTTPException(status_code=400, detail="Design doc content too large (max 1MB)")

        # Update session state
        session_manager.update_design_doc(session_id, request.content)

        print(f"Updated design doc for session {session_id} ({len(request.content)} chars)")

        # Log event
        log_event(
            EventType.EXPORT_DESIGN_DOC,
            session_id=session_id,
            user_ip=user_ip,
            metadata={"action": "update", "content_length": len(request.content)},
        )

        return JSONResponse(content={"design_doc": request.content})

    except HTTPException:
        raise
    except Exception as e:
        log_error(
            error_type="design_doc_update_failed",
            error_message=str(e),
            session_id=session_id,
            user_ip=user_ip,
        )
        raise HTTPException(status_code=500, detail=f"Failed to update design document: {str(e)}")


@router.post("/session/{session_id}/design-doc/export")
async def export_design_doc_from_session(session_id: str, request: ExportRequest, format: str = "pdf", http_request: Request = None):
    """
    Export design document from session state (uses stored content, not regenerated).

    Args:
        session_id: The session ID
        request: Request body with optional diagram_image
        format: Export format - 'markdown', 'pdf', or 'both' (default: 'pdf')

    Returns:
        JSON with base64 encoded files
    """
    start_time = time.time()
    user_ip = http_request.client.host if http_request and http_request.client else None
    user_id = getattr(http_request.state, "user_id", None) if http_request else None

    try:
        # Verify access
        session = verify_session_access(session_id, user_id, http_request)

        # Check if design doc exists
        if not session.design_doc:
            raise HTTPException(status_code=404, detail="Design document not found. Generate one first.")

        print(f"\n=== EXPORT DESIGN DOC FROM SESSION ===")
        print(f"Session ID: {session_id}")
        print(f"Format requested: {format}")
        print(f"Design doc length: {len(session.design_doc)} chars")
        print(f"Has custom diagram image: {request.diagram_image is not None}")

        markdown_content = session.design_doc

        # Use provided diagram image or generate one
        if request.diagram_image:
            # Use the screenshot from frontend
            diagram_png = base64.b64decode(request.diagram_image)
            print("Using frontend screenshot for diagram")
        else:
            # Fallback to generated diagram
            diagram_png = generate_diagram_png(session.diagram.model_dump())
            print("Generated diagram using Pillow")

        result = {}

        # Return markdown if requested
        if format in ["markdown", "both"]:
            result["markdown"] = {
                "content": markdown_content,
                "filename": "design_document.md"
            }
            # Only include diagram PNG for "both" format, not for "markdown" alone
            if format == "both":
                result["diagram_png"] = {
                    "content": base64.b64encode(diagram_png).decode('utf-8'),
                    "filename": "diagram.png"
                }

        # Return PDF if requested
        if format in ["pdf", "both"]:
            pdf_bytes = convert_markdown_to_pdf(markdown_content, diagram_png)
            result["pdf"] = {
                "content": base64.b64encode(pdf_bytes).decode('utf-8'),
                "filename": "design_document.pdf"
            }

        print(f"Exported documents successfully")
        print(f"======================================\n")

        # Log export event
        duration_ms = (time.time() - start_time) * 1000
        log_export(
            session_id=session_id,
            format=format,
            duration_ms=duration_ms,
            user_ip=user_ip,
            success=True,
        )

        return JSONResponse(content=result)

    except HTTPException:
        raise
    except ImportError as e:
        import traceback
        traceback.print_exc()
        duration_ms = (time.time() - start_time) * 1000
        log_export(
            session_id=session_id,
            format=format,
            duration_ms=duration_ms,
            user_ip=user_ip,
            success=False,
        )
        raise HTTPException(
            status_code=500,
            detail=f"PDF generation dependencies not installed: {str(e)}"
        )
    except Exception as e:
        import traceback
        print(f"Error exporting design doc: {str(e)}")
        traceback.print_exc()
        duration_ms = (time.time() - start_time) * 1000
        log_export(
            session_id=session_id,
            format=format,
            duration_ms=duration_ms,
            user_ip=user_ip,
            success=False,
        )
        raise HTTPException(status_code=500, detail=f"Failed to export design document: {str(e)}")


@router.get("/user/sessions")
async def get_user_sessions(http_request: Request):
    """
    Get all sessions belonging to the authenticated user.

    Returns:
        List of sessions with metadata, sorted by most recent first
    """
    user_id = getattr(http_request.state, "user_id", None)
    if not user_id:
        raise HTTPException(status_code=401, detail="User authentication required")

    try:
        # Get all sessions for this user
        sessions = session_manager.get_user_sessions(user_id)

        # Format response with session previews
        sessions_data = []
        for session in sessions:
            sessions_data.append({
                "session_id": session.session_id,
                "created_at": session.created_at.isoformat() if session.created_at else None,
                "node_count": len(session.diagram.nodes),
                "edge_count": len(session.diagram.edges),
                "message_count": len(session.messages),
                "has_design_doc": session.design_doc is not None,
                "model": session.model,
                "name": session.name,
            })

        log_event(
            EventType.API_REQUEST,
            user_ip=http_request.client.host if http_request.client else None,
            metadata={
                "endpoint": "/user/sessions",
                "session_count": len(sessions_data)
            }
        )

        return JSONResponse(content={"sessions": sessions_data, "total": len(sessions_data)})

    except Exception as e:
        log_error(
            error_type="get_user_sessions_failed",
            error_message=str(e),
            user_ip=http_request.client.host if http_request.client else None,
        )
        raise HTTPException(status_code=500, detail=f"Failed to retrieve sessions: {str(e)}")
