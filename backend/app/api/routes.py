from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response, JSONResponse
from pydantic import BaseModel
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
)
from app.session.manager import session_manager
from app.agent.graph import agent_graph
from app.agent.doc_generator import generate_design_document
from app.utils.diagram_export import generate_diagram_png, convert_markdown_to_pdf
from app.utils.logger import (
    log_diagram_generation,
    log_chat_interaction,
    log_export,
    log_event,
    log_error,
    EventType,
)
import json
import base64
import time

router = APIRouter()


class ExportRequest(BaseModel):
    diagram_image: str | None = None  # Base64 encoded PNG from frontend


@router.post("/generate", response_model=GenerateResponse)
async def generate_diagram(request: GenerateRequest, http_request: Request):
    """Generate initial system diagram from user prompt."""
    start_time = time.time()
    user_ip = http_request.client.host if http_request.client else None

    try:
        # Run agent
        result = agent_graph.invoke({
            "intent": "generate",
            "user_message": request.prompt,
            "diagram": None,
            "node_id": None,
            "conversation_history": [],
            "output": "",
            "diagram_updated": False,
        })

        # Parse diagram
        diagram_dict = json.loads(result["output"])
        diagram = Diagram(**diagram_dict)

        # Create session
        session_id = session_manager.create_session(diagram)

        # Add initial message
        session_manager.add_message(
            session_id,
            Message(role="user", content=request.prompt)
        )

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
async def chat(request: ChatRequest, http_request: Request):
    """Continue conversation about diagram/node."""
    start_time = time.time()
    user_ip = http_request.client.host if http_request.client else None

    try:
        # Get session
        session = session_manager.get_session(request.session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        # Update current node if provided
        if request.node_id:
            session_manager.set_current_node(request.session_id, request.node_id)

        # Build conversation history
        conversation_history = [
            {"role": msg.role, "content": msg.content}
            for msg in session.messages
        ]

        # Run agent
        result = agent_graph.invoke({
            "intent": "chat",
            "user_message": request.message,
            "diagram": session.diagram.model_dump(),
            "node_id": request.node_id,
            "conversation_history": conversation_history,
            "output": "",
            "diagram_updated": False,
            "display_text": "",
        })

        # Add user message to history
        session_manager.add_message(
            request.session_id,
            Message(role="user", content=request.message)
        )

        # Check if diagram was updated
        response_diagram = None
        display_message = result.get("display_text", result["output"])

        if result["diagram_updated"]:
            diagram_dict = json.loads(result["output"])
            response_diagram = Diagram(**diagram_dict)
            session_manager.update_diagram(request.session_id, response_diagram)

            # Add assistant response with cleaned text
            session_manager.add_message(
                request.session_id,
                Message(role="assistant", content=display_message)
            )
        else:
            # Add assistant text response
            session_manager.add_message(
                request.session_id,
                Message(role="assistant", content=display_message)
            )

        # Log chat interaction
        duration_ms = (time.time() - start_time) * 1000
        log_chat_interaction(
            session_id=request.session_id,
            message_length=len(request.message),
            node_id=request.node_id,
            diagram_updated=result["diagram_updated"],
            duration_ms=duration_ms,
            user_ip=user_ip,
        )

        return ChatResponse(
            response=display_message,
            diagram=response_diagram
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
async def get_session(session_id: str):
    """Retrieve current session state."""
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


@router.post("/session/{session_id}/nodes", response_model=Diagram)
async def add_node(session_id: str, node: Node, http_request: Request):
    """Add a new node to the diagram."""
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Check for duplicate node ID
    if any(n.id == node.id for n in session.diagram.nodes):
        raise HTTPException(status_code=400, detail=f"Node with id '{node.id}' already exists")

    # Add node to diagram
    session.diagram.nodes.append(node)

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
    """Delete a node and its connected edges from the diagram."""
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Find and remove node
    original_count = len(session.diagram.nodes)
    session.diagram.nodes = [n for n in session.diagram.nodes if n.id != node_id]

    if len(session.diagram.nodes) == original_count:
        raise HTTPException(status_code=404, detail=f"Node '{node_id}' not found")

    # Remove edges connected to this node
    edges_removed = len([e for e in session.diagram.edges if e.source == node_id or e.target == node_id])
    session.diagram.edges = [
        e for e in session.diagram.edges
        if e.source != node_id and e.target != node_id
    ]

    # Log event
    user_ip = http_request.client.host if http_request.client else None
    log_event(
        EventType.NODE_DELETED,
        session_id=session_id,
        user_ip=user_ip,
        metadata={"node_id": node_id, "edges_removed": edges_removed},
    )

    return session.diagram


@router.patch("/session/{session_id}/nodes/{node_id}", response_model=Diagram)
async def update_node(session_id: str, node_id: str, updated_node: Node):
    """Update an existing node's properties."""
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

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

    return session.diagram


@router.post("/session/{session_id}/edges", response_model=Diagram)
async def add_edge(session_id: str, edge: Edge):
    """Add a new edge to the diagram."""
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

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

    return session.diagram


@router.delete("/session/{session_id}/edges/{edge_id}", response_model=Diagram)
async def delete_edge(session_id: str, edge_id: str):
    """Delete an edge from the diagram."""
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Find and remove edge
    original_count = len(session.diagram.edges)
    session.diagram.edges = [e for e in session.diagram.edges if e.id != edge_id]

    if len(session.diagram.edges) == original_count:
        raise HTTPException(status_code=404, detail=f"Edge '{edge_id}' not found")

    return session.diagram


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

    try:
        # Get session
        session = session_manager.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

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

        # Generate markdown document using LLM
        markdown_content = generate_design_document(
            session.diagram.model_dump(),
            conversation_history
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
