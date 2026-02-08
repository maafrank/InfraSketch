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
    AnalyzeRepoRequest,
    AnalyzeRepoResponse,
)
from app.session.manager import session_manager
from app.agent.graph import agent_graph, generate_suggestions
from app.agent.doc_generator import generate_design_document
from app.agent.name_generator import generate_session_name
from app.utils.diagram_export import generate_diagram_png, convert_markdown_to_pdf
from app.utils.logger import (
    log_diagram_generation,
    log_chat_interaction,
    log_design_doc_generation,
    log_export,
    log_event,
    log_error,
    EventType,
)
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import SystemMessage
from app.utils.secrets import get_anthropic_api_key
from app.billing.storage import get_user_credits_storage
from app.billing.credit_costs import calculate_cost
from app.billing.promo_codes import redeem_promo_code, validate_promo_code
from app.gamification.engine import process_action
from app.gamification.storage import get_gamification_storage
from app.gamification.achievements import get_achievement_progress, ACHIEVEMENT_DEFINITIONS
from app.gamification.xp import get_level_progress
import json
import base64
import time


async def check_and_deduct_credits(
    user_id: str,
    action: str,
    model: str = None,
    session_id: str = None,
    metadata: dict = None,
) -> int:
    """
    Check if user has sufficient credits and deduct if so.

    Args:
        user_id: The authenticated user's ID
        action: The action being performed (e.g., "diagram_generation")
        model: Optional model name for model-specific pricing
        session_id: Optional session ID for audit trail
        metadata: Optional additional metadata for logging

    Returns:
        The number of credits deducted

    Raises:
        HTTPException 402 if insufficient credits
    """
    cost = calculate_cost(action, model)
    storage = get_user_credits_storage()

    success, credits = storage.deduct_credits(
        user_id=user_id,
        amount=cost,
        action=action,
        session_id=session_id,
        metadata=metadata or {},
    )

    if not success:
        raise HTTPException(
            status_code=402,
            detail={
                "error": "insufficient_credits",
                "required": cost,
                "available": credits.credits_balance,
                "message": "You don't have enough credits. Please upgrade your plan or purchase more credits.",
            },
        )

    return cost

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

        # Generate name using LLM (synchronous - no asyncio.run needed)
        name = generate_session_name(prompt, api_key, model)

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

        # Generate name using LLM (synchronous - no asyncio.run needed)
        name = generate_session_name(prompt, api_key, model)

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


def _generate_diagram_background(session_id: str, prompt: str, model: str, user_ip: str):
    """Background task to generate diagram asynchronously."""
    start_time = time.time()

    try:
        print(f"\n=== BACKGROUND: GENERATE DIAGRAM ===")
        print(f"Session ID: {session_id}")
        print(f"Model: {model}")
        print(f"Prompt length: {len(prompt)}")

        # Run agent with message-based state
        result = agent_graph.invoke({
            "messages": [HumanMessage(content=prompt)],
            "diagram": None,
            "session_id": session_id,
            "model": model,
        })

        # Extract diagram from result
        diagram = result["diagram"]

        # Update session with generated diagram
        session_manager.update_diagram(session_id, diagram)

        # Add messages to session (user + formatted assistant overview)
        session_manager.add_message(
            session_id,
            Message(role="user", content=prompt)
        )
        system_overview = generate_system_overview(diagram)
        session_manager.add_message(
            session_id,
            Message(role="assistant", content=system_overview)
        )

        # Mark as completed
        session_manager.set_diagram_generation_status(session_id, "completed")

        # Generate session name (inline since we're already in background)
        # Note: generate_session_name is synchronous - no asyncio.run() needed
        try:
            from app.utils.secrets import get_anthropic_api_key
            api_key = get_anthropic_api_key()
            name = generate_session_name(prompt, api_key, model)
            if name:
                session_manager.update_session_name(session_id, name)
                print(f"Session name generated: {name}")
        except Exception as name_error:
            print(f"Failed to generate session name: {name_error}")
            session_manager.update_session_name(session_id, "Untitled Design")

        # Log diagram generation event
        duration_ms = (time.time() - start_time) * 1000
        log_diagram_generation(
            session_id=session_id,
            node_count=len(diagram.nodes),
            edge_count=len(diagram.edges),
            prompt_length=len(prompt),
            duration_ms=duration_ms,
            user_ip=user_ip,
            prompt=prompt,  # Include actual prompt for analytics
        )

        print(f"Generated diagram: {len(diagram.nodes)} nodes, {len(diagram.edges)} edges")
        print(f"Duration: {duration_ms:.0f}ms")
        print(f"========================================\n")

        # Gamification: track diagram generation and session creation
        session = session_manager.get_session(session_id)
        if session:
            process_action(session.user_id, "session_created", {"model": model})
            process_action(session.user_id, "diagram_generated", {
                "node_count": len(diagram.nodes),
                "model": model,
            })

    except Exception as e:
        import traceback
        print(f"Error generating diagram in background: {str(e)}")
        traceback.print_exc()

        # Mark as failed
        session_manager.set_diagram_generation_status(session_id, "failed", error=str(e))

        log_error(
            error_type="diagram_generation_failed",
            error_message=str(e),
            user_ip=user_ip,
            metadata={"session_id": session_id},
        )


@router.post("/generate")
async def generate_diagram(request: GenerateRequest, http_request: Request, background_tasks: BackgroundTasks):
    """
    Start diagram generation asynchronously.

    Returns immediately with session_id and status. Frontend should poll
    /session/{session_id}/diagram/status until generation completes.
    """
    import os
    user_ip = http_request.client.host if http_request.client else None

    # Extract user_id from request state (set by Clerk middleware)
    user_id = getattr(http_request.state, "user_id", None)
    if not user_id:
        raise HTTPException(status_code=401, detail="User authentication required")

    try:
        # Use specified model or default to Haiku (alias auto-updates to latest)
        model = request.model or "claude-haiku-4-5"

        # Check and deduct credits BEFORE creating session
        await check_and_deduct_credits(
            user_id=user_id,
            action="diagram_generation",
            model=model,
            metadata={"prompt_length": len(request.prompt)},
        )

        # Create session immediately with "generating" status
        session_id = session_manager.create_session_for_generation(
            user_id=user_id,
            model=model,
            prompt=request.prompt
        )

        # Check if running in Lambda
        is_lambda = os.environ.get('AWS_LAMBDA_FUNCTION_NAME') is not None

        if is_lambda:
            # In Lambda: Use async invocation to avoid API Gateway 30s timeout
            import boto3
            import json as json_lib

            print(f"Lambda environment detected - triggering async diagram generation for session {session_id}")

            try:
                lambda_client = boto3.client('lambda')
                function_name = os.environ.get('AWS_LAMBDA_FUNCTION_NAME')

                payload = {
                    "async_task": "generate_diagram",
                    "session_id": session_id,
                    "prompt": request.prompt,
                    "model": model,
                    "user_ip": user_ip
                }

                lambda_client.invoke(
                    FunctionName=function_name,
                    InvocationType='Event',  # Async invocation
                    Payload=json_lib.dumps(payload)
                )

                print(f"Async Lambda invocation triggered for diagram generation")
            except Exception as e:
                print(f"Failed to trigger async invocation: {e}")
                # Fall back to background task (will timeout but generation continues)
                background_tasks.add_task(_generate_diagram_background, session_id, request.prompt, model, user_ip)
        else:
            # Local development: Use true background tasks (non-blocking)
            print(f"Local environment - starting background diagram generation for session {session_id}")
            background_tasks.add_task(_generate_diagram_background, session_id, request.prompt, model, user_ip)

        # Return immediately with session_id and generating status
        return JSONResponse(content={
            "session_id": session_id,
            "status": "generating"
        })

    except Exception as e:
        log_error(
            error_type="diagram_generation_start_failed",
            error_message=str(e),
            user_ip=user_ip,
        )
        raise HTTPException(status_code=500, detail=f"Failed to start diagram generation: {str(e)}")


@router.get("/session/{session_id}/diagram/status")
async def get_diagram_status(session_id: str, http_request: Request):
    """
    Get the current status of diagram generation.

    Poll this endpoint every 2 seconds until status is "completed" or "failed".

    Returns:
        JSON with status, elapsed_seconds, and diagram (when completed)
    """
    user_id = getattr(http_request.state, "user_id", None)
    session = verify_session_access(session_id, user_id, http_request)

    status = session.diagram_generation_status

    response = {
        "status": status.status,
        "error": status.error,
    }

    # Include timing information
    if status.started_at:
        if status.completed_at:
            response["duration_seconds"] = status.completed_at - status.started_at
        else:
            response["elapsed_seconds"] = time.time() - status.started_at

    # Include diagram and messages if completed
    if status.status == "completed":
        response["diagram"] = session.diagram.model_dump()
        response["messages"] = [{"role": m.role, "content": m.content} for m in session.messages]
        response["name"] = session.name

        # Generate initial suggestions for the newly created diagram
        try:
            suggestions = generate_suggestions(
                diagram=session.diagram,
                node_id=None,
                last_message="Initial diagram generated"
            )
            response["suggestions"] = suggestions
        except Exception as e:
            print(f"✗ Error generating initial suggestions: {e}")
            response["suggestions"] = []

    return JSONResponse(content=response)


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

        # Check and deduct credits for chat message
        model_to_use = request.model if request.model else session.model
        await check_and_deduct_credits(
            user_id=user_id,
            action="chat_message",
            model=model_to_use,
            session_id=request.session_id,
            metadata={"message_length": len(request.message)},
        )

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
            message=request.message,  # Include actual message for analytics
        )

        # Gamification: track chat message
        gamification_result = process_action(user_id, "chat_message", {
            "node_id": request.node_id,
            "model": model_to_use,
        })

        # Generate session name in background if this was the first message
        if needs_name:
            background_tasks.add_task(_generate_session_name_from_content, request.session_id, session.model)

        # Extract suggestions from agent result
        suggestions = result.get("suggestions", [])

        return ChatResponse(
            response=response_text,
            diagram=response_diagram,
            design_doc=response_design_doc,
            suggestions=suggestions,
            gamification=gamification_result,
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

    # Gamification: track session creation
    process_action(user_id, "session_created", {"model": "claude-haiku-4-5"})

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

    # Gamification: track node addition
    process_action(user_id, "node_added", {"node_type": node.type})

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

    # Gamification: track edge addition
    process_action(user_id, "edge_added")

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
    process_action(user_id, "group_created")

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

    # Gamification: track group collapse (only when collapsing, not expanding)
    if group_node.is_collapsed:
        process_action(user_id, "group_collapsed")

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

        # Gamification: track export
        if user_id:
            process_action(user_id, "export_completed", {"format": format})

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

        # Log design doc generation event
        duration_ms = (time.time() - start_time) * 1000
        log_design_doc_generation(
            session_id=session_id,
            duration_ms=duration_ms,
            doc_length=len(markdown_content),
            user_ip=user_ip,
            success=True,
        )

        print(f"Generated and stored design doc ({len(markdown_content)} chars)")
        print(f"========================================\n")

        # Gamification: track design doc generation
        if session:
            process_action(session.user_id, "design_doc_generated")

    except Exception as e:
        import traceback
        print(f"Error generating design doc in background: {str(e)}")
        traceback.print_exc()

        # Mark as failed
        session_manager.set_design_doc_status(session_id, "failed", error=str(e))

        duration_ms = (time.time() - start_time) * 1000
        log_design_doc_generation(
            session_id=session_id,
            duration_ms=duration_ms,
            doc_length=0,
            user_ip=user_ip,
            success=False,
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

        # Check and deduct credits for design doc generation
        await check_and_deduct_credits(
            user_id=user_id,
            action="design_doc_generation",
            session_id=session_id,
        )

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

        # Check and deduct credits for export (PDF/markdown generation)
        await check_and_deduct_credits(
            user_id=user_id,
            action="design_doc_export",
            session_id=session_id,
            metadata={"format": format},
        )

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


# =============================================================================
# SUBSCRIPTION ENDPOINTS
# =============================================================================

from app.subscription.storage import get_subscriber_storage
from app.subscription.models import SubscriptionStatus, SubscribeRequest
from fastapi.responses import HTMLResponse


@router.post("/subscribe", response_model=SubscriptionStatus)
async def subscribe(request: SubscribeRequest, http_request: Request):
    """
    Subscribe a user to email notifications.
    Creates a new subscriber record if one doesn't exist.
    """
    user_id = getattr(http_request.state, "user_id", None)
    if not user_id:
        raise HTTPException(status_code=401, detail="User authentication required")

    try:
        storage = get_subscriber_storage()
        subscriber = storage.create_subscriber(user_id, request.email)

        log_event(
            EventType.API_REQUEST,
            user_ip=http_request.client.host if http_request.client else None,
            metadata={
                "endpoint": "/subscribe",
                "user_id": user_id,
                "email": request.email[:3] + "***",  # Partially redact email
            }
        )

        return SubscriptionStatus(subscribed=subscriber.subscribed, email=subscriber.email)

    except Exception as e:
        log_error(
            error_type="subscribe_failed",
            error_message=str(e),
            user_ip=http_request.client.host if http_request.client else None,
        )
        raise HTTPException(status_code=500, detail=f"Failed to subscribe: {str(e)}")


@router.get("/subscription/status", response_model=SubscriptionStatus)
async def get_subscription_status(http_request: Request):
    """
    Get the current user's subscription status.
    """
    user_id = getattr(http_request.state, "user_id", None)
    if not user_id:
        raise HTTPException(status_code=401, detail="User authentication required")

    try:
        storage = get_subscriber_storage()
        subscriber = storage.get_subscriber(user_id)

        if not subscriber:
            # User not subscribed yet - return default state
            return SubscriptionStatus(subscribed=False, email="")

        return SubscriptionStatus(subscribed=subscriber.subscribed, email=subscriber.email)

    except Exception as e:
        log_error(
            error_type="get_subscription_status_failed",
            error_message=str(e),
            user_ip=http_request.client.host if http_request.client else None,
        )
        raise HTTPException(status_code=500, detail=f"Failed to get subscription status: {str(e)}")


@router.post("/unsubscribe")
async def unsubscribe_authenticated(http_request: Request):
    """
    Unsubscribe the current authenticated user from emails.
    """
    user_id = getattr(http_request.state, "user_id", None)
    if not user_id:
        raise HTTPException(status_code=401, detail="User authentication required")

    try:
        storage = get_subscriber_storage()
        success = storage.unsubscribe(user_id)

        if not success:
            raise HTTPException(status_code=404, detail="Subscriber not found")

        log_event(
            EventType.API_REQUEST,
            user_ip=http_request.client.host if http_request.client else None,
            metadata={
                "endpoint": "/unsubscribe",
                "user_id": user_id,
            }
        )

        return {"success": True, "message": "You have been unsubscribed from email notifications."}

    except HTTPException:
        raise
    except Exception as e:
        log_error(
            error_type="unsubscribe_failed",
            error_message=str(e),
            user_ip=http_request.client.host if http_request.client else None,
        )
        raise HTTPException(status_code=500, detail=f"Failed to unsubscribe: {str(e)}")


@router.post("/resubscribe")
async def resubscribe_authenticated(http_request: Request):
    """
    Re-subscribe the current authenticated user to marketing emails.
    """
    user_id = getattr(http_request.state, "user_id", None)
    if not user_id:
        raise HTTPException(status_code=401, detail="User authentication required")

    try:
        storage = get_subscriber_storage()
        success = storage.resubscribe(user_id)

        if not success:
            raise HTTPException(status_code=404, detail="Subscriber not found")

        log_event(
            EventType.API_REQUEST,
            user_ip=http_request.client.host if http_request.client else None,
            metadata={
                "endpoint": "/resubscribe",
                "user_id": user_id,
            }
        )

        return {"success": True, "message": "You have been re-subscribed to email notifications."}

    except HTTPException:
        raise
    except Exception as e:
        log_error(
            error_type="resubscribe_failed",
            error_message=str(e),
            user_ip=http_request.client.host if http_request.client else None,
        )
        raise HTTPException(status_code=500, detail=f"Failed to re-subscribe: {str(e)}")


@router.get("/unsubscribe/{token}", response_class=HTMLResponse)
async def unsubscribe_via_token(token: str, http_request: Request):
    """
    Public endpoint for unsubscribe links in emails.
    No authentication required - the token IS the authentication.
    Returns a simple HTML confirmation page.
    """
    try:
        storage = get_subscriber_storage()
        subscriber = storage.get_subscriber_by_token(token)

        if not subscriber:
            return HTMLResponse(
                content="""
                <!DOCTYPE html>
                <html>
                <head>
                    <title>Unsubscribe - InfraSketch</title>
                    <style>
                        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                               max-width: 600px; margin: 50px auto; padding: 20px; text-align: center; }
                        h1 { color: #dc2626; }
                        p { color: #6b7280; }
                        a { color: #2563eb; }
                    </style>
                </head>
                <body>
                    <h1>Invalid Link</h1>
                    <p>This unsubscribe link is invalid or has expired.</p>
                    <p><a href="https://infrasketch.net">Return to InfraSketch</a></p>
                </body>
                </html>
                """,
                status_code=404
            )

        # Perform unsubscribe
        storage.unsubscribe(subscriber.user_id)

        log_event(
            EventType.API_REQUEST,
            user_ip=http_request.client.host if http_request.client else None,
            metadata={
                "endpoint": "/unsubscribe/{token}",
                "user_id": subscriber.user_id,
            }
        )

        # Build re-subscribe URL with the same token
        resubscribe_url = f"https://b31htlojb0.execute-api.us-east-1.amazonaws.com/prod/api/resubscribe/{token}"

        return HTMLResponse(
            content=f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>Unsubscribed - InfraSketch</title>
                <style>
                    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                           max-width: 600px; margin: 50px auto; padding: 20px; text-align: center; }}
                    h1 {{ color: #10b981; }}
                    p {{ color: #6b7280; }}
                    a {{ color: #2563eb; }}
                    .emoji {{ font-size: 48px; margin-bottom: 20px; }}
                    .resubscribe-btn {{
                        display: inline-block;
                        background-color: #2563eb;
                        color: white !important;
                        padding: 12px 24px;
                        border-radius: 6px;
                        text-decoration: none;
                        margin: 20px 0;
                        font-weight: 500;
                    }}
                    .resubscribe-btn:hover {{ background-color: #1d4ed8; }}
                </style>
            </head>
            <body>
                <div class="emoji">✅</div>
                <h1>You've Been Unsubscribed</h1>
                <p>You will no longer receive feature announcement emails from InfraSketch.</p>
                <p>Changed your mind?</p>
                <a href="{resubscribe_url}" class="resubscribe-btn">Re-subscribe</a>
                <p><a href="https://infrasketch.net">Return to InfraSketch</a></p>
            </body>
            </html>
            """,
            status_code=200
        )

    except Exception as e:
        log_error(
            error_type="unsubscribe_via_token_failed",
            error_message=str(e),
            user_ip=http_request.client.host if http_request.client else None,
        )
        return HTMLResponse(
            content="""
            <!DOCTYPE html>
            <html>
            <head>
                <title>Error - InfraSketch</title>
                <style>
                    body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                           max-width: 600px; margin: 50px auto; padding: 20px; text-align: center; }
                    h1 { color: #dc2626; }
                    p { color: #6b7280; }
                    a { color: #2563eb; }
                </style>
            </head>
            <body>
                <h1>Something Went Wrong</h1>
                <p>We couldn't process your unsubscribe request. Please try again later.</p>
                <p><a href="https://infrasketch.net">Return to InfraSketch</a></p>
            </body>
            </html>
            """,
            status_code=500
        )


@router.get("/resubscribe/{token}", response_class=HTMLResponse)
async def resubscribe_via_token(token: str, http_request: Request):
    """
    Public endpoint for re-subscribe links.
    No authentication required - the token IS the authentication.
    Returns a simple HTML confirmation page.
    """
    try:
        storage = get_subscriber_storage()
        subscriber = storage.get_subscriber_by_token(token)

        if not subscriber:
            return HTMLResponse(
                content="""
                <!DOCTYPE html>
                <html>
                <head>
                    <title>Re-subscribe - InfraSketch</title>
                    <style>
                        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                               max-width: 600px; margin: 50px auto; padding: 20px; text-align: center; }
                        h1 { color: #dc2626; }
                        p { color: #6b7280; }
                        a { color: #2563eb; }
                    </style>
                </head>
                <body>
                    <h1>Invalid Link</h1>
                    <p>This re-subscribe link is invalid or has expired.</p>
                    <p><a href="https://infrasketch.net">Return to InfraSketch</a></p>
                </body>
                </html>
                """,
                status_code=404
            )

        # Perform re-subscribe
        storage.resubscribe(subscriber.user_id)

        log_event(
            EventType.API_REQUEST,
            user_ip=http_request.client.host if http_request.client else None,
            metadata={
                "endpoint": "/resubscribe/{token}",
                "user_id": subscriber.user_id,
            }
        )

        # Build unsubscribe URL in case they want to undo
        unsubscribe_url = f"https://b31htlojb0.execute-api.us-east-1.amazonaws.com/prod/api/unsubscribe/{token}"

        return HTMLResponse(
            content=f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>Re-subscribed - InfraSketch</title>
                <style>
                    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                           max-width: 600px; margin: 50px auto; padding: 20px; text-align: center; }}
                    h1 {{ color: #10b981; }}
                    p {{ color: #6b7280; }}
                    a {{ color: #2563eb; }}
                    .emoji {{ font-size: 48px; margin-bottom: 20px; }}
                </style>
            </head>
            <body>
                <div class="emoji">🎉</div>
                <h1>You're Re-subscribed!</h1>
                <p>You'll now receive feature announcement emails from InfraSketch.</p>
                <p>Changed your mind? <a href="{unsubscribe_url}">Unsubscribe again</a></p>
                <p><a href="https://infrasketch.net">Return to InfraSketch</a></p>
            </body>
            </html>
            """,
            status_code=200
        )

    except Exception as e:
        log_error(
            error_type="resubscribe_via_token_failed",
            error_message=str(e),
            user_ip=http_request.client.host if http_request.client else None,
        )
        return HTMLResponse(
            content="""
            <!DOCTYPE html>
            <html>
            <head>
                <title>Error - InfraSketch</title>
                <style>
                    body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                           max-width: 600px; margin: 50px auto; padding: 20px; text-align: center; }
                    h1 { color: #dc2626; }
                    p { color: #6b7280; }
                    a { color: #2563eb; }
                </style>
            </head>
            <body>
                <h1>Something Went Wrong</h1>
                <p>We couldn't process your re-subscribe request. Please try again later.</p>
                <p><a href="https://infrasketch.net">Return to InfraSketch</a></p>
            </body>
            </html>
            """,
            status_code=500
        )


# =============================================================================
# Webhook Endpoints
# =============================================================================

@router.post("/webhooks/clerk")
async def clerk_webhook(request: Request):
    """
    Handle Clerk webhook events.
    Automatically subscribes new users to email list on signup.

    Clerk webhooks use Svix for delivery and signature verification.
    The signing secret is used to verify that requests are authentic.
    """
    import os
    from svix.webhooks import Webhook, WebhookVerificationError

    # Get raw body (required for signature verification - must be exact bytes)
    payload = await request.body()
    headers = dict(request.headers)

    # Get webhook secret from environment
    webhook_secret = os.getenv("CLERK_WEBHOOK_SECRET")
    if not webhook_secret:
        log_error(
            error_type="webhook_config_error",
            error_message="CLERK_WEBHOOK_SECRET not configured",
        )
        raise HTTPException(status_code=500, detail="Webhook secret not configured")

    # Verify webhook signature using Svix
    try:
        wh = Webhook(webhook_secret)
        event = wh.verify(payload, headers)
    except WebhookVerificationError as e:
        log_error(
            error_type="webhook_verification_failed",
            error_message=str(e),
            user_ip=request.client.host if request.client else None,
        )
        raise HTTPException(status_code=400, detail="Invalid webhook signature")

    # Handle user.created event
    event_type = event.get("type")

    if event_type == "user.created":
        user_data = event.get("data", {})
        user_id = user_data.get("id")

        # Extract primary email address
        primary_email_id = user_data.get("primary_email_address_id")
        email = None
        for email_obj in user_data.get("email_addresses", []):
            if email_obj.get("id") == primary_email_id:
                email = email_obj.get("email_address")
                break

        # Fallback to first email if no primary designated
        if not email:
            email_addresses = user_data.get("email_addresses", [])
            if email_addresses:
                email = email_addresses[0].get("email_address")

        if user_id and email:
            try:
                storage = get_subscriber_storage()
                subscriber = storage.create_subscriber(user_id, email)

                log_event(
                    EventType.API_REQUEST,
                    user_ip=request.client.host if request.client else None,
                    metadata={
                        "endpoint": "/webhooks/clerk",
                        "event_type": "user.created",
                        "user_id": user_id,
                        "new_subscriber": subscriber.created_at == subscriber.updated_at,
                    }
                )
            except Exception as e:
                log_error(
                    error_type="webhook_subscriber_creation_failed",
                    error_message=str(e),
                    metadata={"user_id": user_id},
                )
                # Don't fail the webhook - Clerk would retry

    # Always return success to acknowledge receipt
    # (even if we didn't process the event type)
    return {"status": "received", "type": event_type}


# =============================================================================
# USER PREFERENCES ENDPOINTS (for tutorial status, etc.)
# =============================================================================

from app.user.storage import get_user_preferences_storage
from app.user.models import UserPreferences


class UserPreferencesResponse(BaseModel):
    """Response model for user preferences."""

    user_id: str
    tutorial_completed: bool
    tutorial_completed_at: Optional[str] = None


@router.get("/user/preferences", response_model=UserPreferencesResponse)
async def get_user_preferences(http_request: Request):
    """
    Get the current user's preferences (tutorial status, etc.).

    Returns default preferences if none exist yet.
    """
    user_id = getattr(http_request.state, "user_id", None)
    if not user_id:
        raise HTTPException(status_code=401, detail="User authentication required")

    storage = get_user_preferences_storage()
    prefs = storage.get_or_create_preferences(user_id)

    return UserPreferencesResponse(
        user_id=prefs.user_id,
        tutorial_completed=prefs.tutorial_completed,
        tutorial_completed_at=(
            prefs.tutorial_completed_at.isoformat() if prefs.tutorial_completed_at else None
        ),
    )


@router.post("/user/tutorial/complete")
async def complete_tutorial(http_request: Request):
    """
    Mark the tutorial as completed for the current user.
    """
    user_id = getattr(http_request.state, "user_id", None)
    if not user_id:
        raise HTTPException(status_code=401, detail="User authentication required")

    storage = get_user_preferences_storage()
    success = storage.mark_tutorial_completed(user_id)

    if not success:
        raise HTTPException(status_code=500, detail="Failed to save tutorial completion")

    return {"success": True, "message": "Tutorial marked as completed"}


@router.post("/user/tutorial/reset")
async def reset_tutorial(http_request: Request):
    """
    Reset the tutorial status so the user can replay it.
    """
    user_id = getattr(http_request.state, "user_id", None)
    if not user_id:
        raise HTTPException(status_code=401, detail="User authentication required")

    storage = get_user_preferences_storage()
    success = storage.reset_tutorial(user_id)

    if not success:
        raise HTTPException(status_code=500, detail="Failed to reset tutorial status")

    return {"success": True, "message": "Tutorial reset successfully"}


# =============================================================================
# GAMIFICATION ENDPOINTS
# =============================================================================


@router.get("/user/gamification")
async def get_user_gamification(http_request: Request):
    """Get the user's gamification state (level, XP, streak, pending notifications)."""
    user_id = getattr(http_request.state, "user_id", None)
    if not user_id:
        raise HTTPException(status_code=401, detail="User authentication required")

    storage = get_gamification_storage()
    gamification = storage.get_or_create(user_id)

    level_info = get_level_progress(gamification.xp_total)

    # Build pending notification details
    pending = []
    for notif in gamification.pending_notifications:
        from app.gamification.achievements import ACHIEVEMENTS_BY_ID
        defn = ACHIEVEMENTS_BY_ID.get(notif.id, {})
        pending.append({
            "id": notif.id,
            "unlocked_at": notif.unlocked_at.isoformat(),
            "name": defn.get("name", notif.id),
            "description": defn.get("description", ""),
            "rarity": defn.get("rarity", "common"),
        })

    return {
        "xp_total": gamification.xp_total,
        "xp_to_next_level": level_info["xp_to_next_level"],
        "xp_current_level_start": level_info["xp_current_level_start"],
        "xp_next_level_threshold": level_info["xp_next_level_threshold"],
        "level": gamification.level,
        "level_name": gamification.level_name,
        "level_color": level_info["level_color"],
        "current_streak": gamification.current_streak,
        "longest_streak": gamification.longest_streak,
        "achievement_count": len(gamification.achievements),
        "total_achievements": len(ACHIEVEMENT_DEFINITIONS),
        "pending_notifications": pending,
        "streak_reminders_enabled": gamification.streak_reminders_enabled,
    }


@router.get("/user/gamification/achievements")
async def get_user_achievements(http_request: Request):
    """Get all achievement definitions with unlock status and progress."""
    user_id = getattr(http_request.state, "user_id", None)
    if not user_id:
        raise HTTPException(status_code=401, detail="User authentication required")

    storage = get_gamification_storage()
    gamification = storage.get_or_create(user_id)

    achievements = get_achievement_progress(gamification)

    # Compute stats by category
    by_category = {}
    for a in achievements:
        cat = a["category"]
        if cat not in by_category:
            by_category[cat] = {"unlocked": 0, "total": 0}
        by_category[cat]["total"] += 1
        if a["unlocked"]:
            by_category[cat]["unlocked"] += 1

    unlocked_count = sum(1 for a in achievements if a["unlocked"])

    return {
        "achievements": achievements,
        "stats": {
            "unlocked": unlocked_count,
            "total": len(achievements),
            "by_category": by_category,
        },
    }


class DismissNotificationsRequest(BaseModel):
    achievement_ids: list[str]


@router.post("/user/gamification/notifications/dismiss")
async def dismiss_gamification_notifications(
    request: DismissNotificationsRequest, http_request: Request
):
    """Clear pending notifications after the user has seen them."""
    user_id = getattr(http_request.state, "user_id", None)
    if not user_id:
        raise HTTPException(status_code=401, detail="User authentication required")

    storage = get_gamification_storage()
    gamification = storage.get_or_create(user_id)

    ids_to_dismiss = set(request.achievement_ids)
    gamification.pending_notifications = [
        n for n in gamification.pending_notifications if n.id not in ids_to_dismiss
    ]
    storage.save(gamification)

    return {"success": True}


class StreakReminderPreferenceRequest(BaseModel):
    enabled: bool


@router.patch("/user/gamification/streak-reminders")
async def update_streak_reminder_preference(
    request: StreakReminderPreferenceRequest, http_request: Request
):
    """Update whether the user receives streak reminder emails."""
    user_id = getattr(http_request.state, "user_id", None)
    if not user_id:
        raise HTTPException(status_code=401, detail="User authentication required")

    storage = get_gamification_storage()
    gamification = storage.get_or_create(user_id)
    gamification.streak_reminders_enabled = request.enabled
    storage.save(gamification)

    return {"success": True, "streak_reminders_enabled": request.enabled}


# =============================================================================
# BILLING ENDPOINTS
# =============================================================================


class RedeemPromoRequest(BaseModel):
    """Request body for redeeming a promo code."""
    code: str


@router.get("/user/credits")
async def get_user_credits(http_request: Request):
    """
    Get current user's credit balance and subscription status.

    Returns:
        JSON with plan, credit balances, and subscription info
    """
    user_id = getattr(http_request.state, "user_id", None)
    if not user_id:
        raise HTTPException(status_code=401, detail="User authentication required")

    storage = get_user_credits_storage()
    credits = storage.get_or_create_credits(user_id)

    return {
        "plan": credits.plan,
        "credits_balance": credits.credits_balance,
        "credits_monthly_allowance": credits.credits_monthly_allowance,
        "credits_used_this_period": credits.credits_used_this_period,
        "subscription_status": credits.subscription_status,
        "plan_started_at": credits.plan_started_at.isoformat() if credits.plan_started_at else None,
        "plan_expires_at": credits.plan_expires_at.isoformat() if credits.plan_expires_at else None,
        "last_credit_reset_at": credits.last_credit_reset_at.isoformat() if credits.last_credit_reset_at else None,
    }


@router.get("/user/credits/history")
async def get_credit_history(http_request: Request, limit: int = 50):
    """
    Get user's credit transaction history.

    Args:
        limit: Maximum number of transactions to return (default 50)

    Returns:
        JSON with list of transactions
    """
    user_id = getattr(http_request.state, "user_id", None)
    if not user_id:
        raise HTTPException(status_code=401, detail="User authentication required")

    storage = get_user_credits_storage()
    transactions = storage.get_transaction_history(user_id, limit=limit)

    return {
        "transactions": [
            {
                "transaction_id": t.transaction_id,
                "type": t.type,
                "amount": t.amount,
                "balance_after": t.balance_after,
                "action": t.action,
                "session_id": t.session_id,
                "metadata": t.metadata,
                "created_at": t.created_at.isoformat(),
            }
            for t in transactions
        ]
    }


@router.post("/promo/redeem")
async def redeem_promo(request: RedeemPromoRequest, http_request: Request):
    """
    Redeem a promo code for credits.

    Args:
        request: Request body with promo code

    Returns:
        JSON with success status and credits granted
    """
    user_id = getattr(http_request.state, "user_id", None)
    if not user_id:
        raise HTTPException(status_code=401, detail="User authentication required")

    success, error, credits_granted = redeem_promo_code(request.code, user_id)

    if not success:
        raise HTTPException(status_code=400, detail=error)

    # Get updated balance
    storage = get_user_credits_storage()
    updated_credits = storage.get_credits(user_id)

    return {
        "success": True,
        "credits_granted": credits_granted,
        "new_balance": updated_credits.credits_balance if updated_credits else credits_granted,
        "message": f"Successfully redeemed {credits_granted} credits!",
    }


@router.post("/promo/validate")
async def validate_promo(request: RedeemPromoRequest, http_request: Request):
    """
    Validate a promo code without redeeming it.

    Args:
        request: Request body with promo code

    Returns:
        JSON with validity status and code info
    """
    user_id = getattr(http_request.state, "user_id", None)
    if not user_id:
        raise HTTPException(status_code=401, detail="User authentication required")

    is_valid, error = validate_promo_code(request.code, user_id)

    if not is_valid:
        return {
            "valid": False,
            "error": error,
        }

    # Get code info for display
    from app.billing.promo_codes import get_promo_code_info
    code_info = get_promo_code_info(request.code)

    return {
        "valid": True,
        "credits": code_info["credits"] if code_info else 0,
    }


# =============================================================================
# CLERK BILLING WEBHOOK
# =============================================================================


# Clerk plan ID to our plan name mapping
CLERK_PLAN_ID_MAP = {
    "cplan_37cOR2Mjs1jWOjaJfUGTX0U1Jf4": "pro",
    "cplan_37cOpDf5Cm7GGUl2K8lUarQf7Bp": "enterprise",
}


def _get_plan_from_clerk_id(plan_id: str) -> str:
    """Map Clerk plan ID to our plan name."""
    # First check exact match
    if plan_id in CLERK_PLAN_ID_MAP:
        return CLERK_PLAN_ID_MAP[plan_id]
    # Fall back to fuzzy match on plan key
    plan_id_lower = plan_id.lower()
    if "pro" in plan_id_lower:
        return "pro"
    elif "enterprise" in plan_id_lower:
        return "enterprise"
    return "free"


@router.post("/webhooks/clerk-billing")
async def clerk_billing_webhook(http_request: Request):
    """
    Handle Clerk Billing webhook events for subscription changes.

    Events handled:
    - subscription.created/updated/active/pastDue: Handle subscription state
    - subscriptionItem.created/updated/active/canceled/ended: Handle plan changes
    - user.created: Initialize credits for new users

    Note: This endpoint is exempt from Clerk auth middleware (public webhook).
    """
    import os
    from svix.webhooks import Webhook, WebhookVerificationError

    try:
        # Get raw body for signature verification
        body = await http_request.body()
        headers = dict(http_request.headers)

        # Verify webhook signature (if secret is configured)
        webhook_secret = os.environ.get("CLERK_BILLING_WEBHOOK_SECRET")
        if webhook_secret:
            try:
                wh = Webhook(webhook_secret)
                payload = wh.verify(body, headers)
            except WebhookVerificationError:
                print("Clerk billing webhook signature verification failed")
                raise HTTPException(status_code=401, detail="Invalid webhook signature")
        else:
            # In development, parse without verification
            payload = json.loads(body)
            print("WARNING: Clerk billing webhook signature not verified (no secret configured)")

        event_type = payload.get("type")
        data = payload.get("data", {})

        print(f"\n=== CLERK BILLING WEBHOOK ===")
        print(f"Event type: {event_type}")
        print(f"Data: {json.dumps(data, indent=2)}")

        storage = get_user_credits_storage()

        # Helper to extract user_id from webhook data
        # Clerk puts user_id in different places depending on event type:
        # - subscription.* events: data.payer.user_id
        # - subscriptionItem.* events: data.payer.user_id
        # - user.* events: data.id
        def get_user_id_from_data(d: dict) -> str | None:
            # Try payer.user_id first (subscription and subscriptionItem events)
            payer = d.get("payer", {})
            if payer and payer.get("user_id"):
                return payer.get("user_id")
            # Fall back to direct user_id
            return d.get("user_id")

        # Handle user.created - initialize credits for new users
        if event_type == "user.created":
            user_id = data.get("id")
            if user_id:
                # This will create credits with free tier defaults if not exists
                storage.get_or_create_credits(user_id)
                print(f"Initialized credits for new user {user_id}")

        # Handle subscription events
        elif event_type in ["subscription.created", "subscription.active"]:
            user_id = get_user_id_from_data(data)
            plan_id = data.get("plan_id", "")
            subscription_id = data.get("id")
            stripe_customer_id = data.get("stripe_customer_id")

            if user_id:
                plan = _get_plan_from_clerk_id(plan_id)
                storage.update_plan(
                    user_id=user_id,
                    new_plan=plan,
                    clerk_subscription_id=subscription_id,
                    stripe_customer_id=stripe_customer_id,
                )
                print(f"Created/activated subscription for user {user_id}: {plan}")

        elif event_type == "subscription.updated":
            user_id = get_user_id_from_data(data)
            plan_id = data.get("plan_id", "")
            subscription_id = data.get("id")

            if user_id:
                plan = _get_plan_from_clerk_id(plan_id)
                storage.update_plan(
                    user_id=user_id,
                    new_plan=plan,
                    clerk_subscription_id=subscription_id,
                )
                print(f"Updated subscription for user {user_id}: {plan}")

        elif event_type == "subscription.pastDue":
            user_id = get_user_id_from_data(data)
            if user_id:
                credits = storage.get_credits(user_id)
                if credits:
                    credits.subscription_status = "past_due"
                    storage.save_credits(credits)
                    print(f"Marked subscription as past_due for user {user_id}")

        # Handle subscriptionItem events (for plan changes)
        elif event_type in ["subscriptionItem.created", "subscriptionItem.active", "subscriptionItem.updated"]:
            # subscriptionItem contains plan details
            user_id = get_user_id_from_data(data)
            plan_id = data.get("plan_id", "")
            subscription_id = data.get("subscription_id")

            if user_id and plan_id:
                plan = _get_plan_from_clerk_id(plan_id)
                storage.update_plan(
                    user_id=user_id,
                    new_plan=plan,
                    clerk_subscription_id=subscription_id,
                )
                print(f"SubscriptionItem {event_type} for user {user_id}: {plan}")

        elif event_type in ["subscriptionItem.canceled", "subscriptionItem.ended"]:
            # User canceled or subscription ended - revert to free
            user_id = get_user_id_from_data(data)
            if user_id:
                storage.update_plan(
                    user_id=user_id,
                    new_plan="free",
                )
                print(f"Subscription canceled/ended for user {user_id}, reverted to free")

        elif event_type == "subscriptionItem.upcoming":
            # Upcoming renewal - could use this to reset credits
            user_id = get_user_id_from_data(data)
            if user_id:
                storage.reset_monthly_credits(user_id)
                print(f"Reset monthly credits for upcoming renewal: user {user_id}")

        # Log unhandled events for debugging
        else:
            print(f"Unhandled Clerk billing event: {event_type}")

        return {"received": True}

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error processing Clerk billing webhook: {e}")
        raise HTTPException(status_code=500, detail=f"Webhook processing failed: {str(e)}")


# =============================================================================
# BADGES
# =============================================================================

from app.utils.badge_generator import get_monthly_visitors_badge_svg


@router.get("/badges/monthly-visitors.svg")
async def get_monthly_visitors_badge():
    """
    Generate an SVG badge showing the monthly visitor count.

    This endpoint is public (no authentication required).
    The badge displays unique visitor IPs from CloudFront logs over the last 30 days.
    Results are cached in DynamoDB for 24 hours.
    """
    try:
        svg_content = get_monthly_visitors_badge_svg()

        return Response(
            content=svg_content,
            media_type="image/svg+xml",
            headers={
                "Cache-Control": "public, max-age=3600",  # Cache for 1 hour
            }
        )
    except Exception as e:
        print(f"Error generating monthly visitors badge: {e}")
        # Return a fallback badge on error
        fallback_svg = '''<svg xmlns="http://www.w3.org/2000/svg" width="140" height="28" viewBox="0 0 140 28">
  <rect width="140" height="28" rx="6" ry="6" fill="#2d2d2d"/>
  <text x="12" y="18" font-family="sans-serif" font-size="11" fill="#aaa">Monthly visitors</text>
</svg>'''
        return Response(
            content=fallback_svg,
            media_type="image/svg+xml",
            headers={"Cache-Control": "public, max-age=300"}  # Short cache on error
        )


# =============================================================================
# GITHUB REPOSITORY ANALYSIS
# =============================================================================


def _analyze_repo_background(session_id: str, repo_url: str, model: str, user_ip: str):
    """Background task to analyze GitHub repository and generate diagram."""
    from app.github.analyzer import GitHubAnalyzer, RepoNotFoundError, RepoAccessDeniedError, GitHubRateLimitError
    from app.github.prompts import format_repo_analysis_prompt
    from app.agent.graph import process_diagram_groups
    from dataclasses import asdict
    import traceback

    start_time = time.time()

    try:
        print(f"\n=== BACKGROUND: ANALYZE REPO ===")
        print(f"Session ID: {session_id}")
        print(f"Repo URL: {repo_url}")
        print(f"Model: {model}")

        # Phase 1: Fetch repository data
        session_manager.set_repo_analysis_status(
            session_id, "fetching", "fetch", "Fetching repository metadata..."
        )

        analyzer = GitHubAnalyzer()

        # Phase 2: Analyze repository
        session_manager.set_repo_analysis_status(
            session_id, "analyzing", "analyze", "Analyzing dependencies and code structure..."
        )

        analysis = analyzer.analyze_repo(repo_url)

        # Store analysis results for potential re-generation
        analysis_dict = asdict(analysis)
        session_manager.store_repo_analysis(session_id, analysis_dict)

        print(f"Analysis complete: {analysis.name}")
        print(f"  - Languages: {list(analysis.languages.keys())}")
        print(f"  - Dependencies: {list(analysis.dependencies.keys())}")
        print(f"  - Databases: {analysis.database_connections}")
        print(f"  - Services: {analysis.external_services}")

        # Phase 3: Generate diagram
        session_manager.set_repo_analysis_status(
            session_id, "generating", "generate", "Generating architecture diagram..."
        )

        # Format prompt with analysis data
        prompt = format_repo_analysis_prompt(analysis)

        # Use LangGraph agent to generate diagram
        result = agent_graph.invoke({
            "messages": [HumanMessage(content=prompt)],
            "diagram": None,
            "session_id": session_id,
            "model": model,
        })

        diagram = result["diagram"]

        # Apply group processing for large diagrams
        if len(diagram.nodes) > 6:
            diagram = process_diagram_groups(diagram, max_visible_nodes=6, model=model)

        # Update session with generated diagram
        session_manager.update_diagram(session_id, diagram)

        # Generate overview message
        overview = f"""## Repository Analysis Complete

I've analyzed the **{analysis.name}** repository and generated an architecture diagram with {len(diagram.nodes)} components.

**Repository Details**
- **Language**: {analysis.primary_language or 'Unknown'}
- **Description**: {analysis.description or 'No description'}

**Detected Components**
- **Databases**: {', '.join(analysis.database_connections) if analysis.database_connections else 'None detected'}
- **External Services**: {', '.join(analysis.external_services) if analysis.external_services else 'None detected'}
- **Infrastructure**: {'Docker' if analysis.has_docker else ''} {'Kubernetes' if analysis.has_kubernetes else ''} {'Terraform' if analysis.has_terraform else ''}

**What's Next?**
- Click any node to learn more about that component
- Ask questions about the architecture
- Request modifications or additions

Feel free to explore the diagram and ask me anything!"""

        session_manager.add_message(
            session_id,
            Message(role="user", content=f"Analyze repository: {repo_url}")
        )
        session_manager.add_message(
            session_id,
            Message(role="assistant", content=overview)
        )

        # Set session name from repo
        session_manager.update_session_name(session_id, f"{analysis.name} Architecture")

        # Mark as completed
        session_manager.set_repo_analysis_status(session_id, "completed")

        # Log event
        duration_ms = (time.time() - start_time) * 1000
        log_event(
            EventType.DIAGRAM_GENERATED,
            session_id=session_id,
            user_ip=user_ip,
            metadata={
                "source": "github_repo",
                "repo_url": repo_url,
                "repo_name": analysis.name,
                "node_count": len(diagram.nodes),
                "edge_count": len(diagram.edges),
                "duration_ms": duration_ms,
            }
        )

        print(f"Generated diagram: {len(diagram.nodes)} nodes, {len(diagram.edges)} edges")
        print(f"Duration: {duration_ms:.0f}ms")
        print(f"========================================\n")

        # Gamification: track repo analysis and session creation
        session = session_manager.get_session(session_id)
        if session:
            process_action(session.user_id, "session_created", {"model": model})
            process_action(session.user_id, "repo_analyzed")
            process_action(session.user_id, "diagram_generated", {
                "node_count": len(diagram.nodes),
                "model": model,
            })

        analyzer.close()

    except RepoNotFoundError as e:
        print(f"Repository not found: {e}")
        session_manager.set_repo_analysis_status(
            session_id, "failed", error=f"Repository not found: {repo_url}"
        )
        log_error(
            error_type="repo_not_found",
            error_message=str(e),
            user_ip=user_ip,
            metadata={"session_id": session_id, "repo_url": repo_url},
        )

    except RepoAccessDeniedError as e:
        print(f"Repository access denied: {e}")
        session_manager.set_repo_analysis_status(
            session_id, "failed",
            error="Private repos coming soon. For now, please use a public repository."
        )
        log_error(
            error_type="repo_access_denied",
            error_message=str(e),
            user_ip=user_ip,
            metadata={"session_id": session_id, "repo_url": repo_url},
        )

    except GitHubRateLimitError as e:
        print(f"GitHub rate limit exceeded: {e}")
        session_manager.set_repo_analysis_status(
            session_id, "failed",
            error="GitHub API rate limit exceeded. Please try again later."
        )
        log_error(
            error_type="github_rate_limit",
            error_message=str(e),
            user_ip=user_ip,
            metadata={"session_id": session_id, "repo_url": repo_url, "reset_time": e.reset_time},
        )

    except Exception as e:
        print(f"Error analyzing repository: {str(e)}")
        traceback.print_exc()

        session_manager.set_repo_analysis_status(
            session_id, "failed", error=f"Analysis failed: {str(e)}"
        )

        log_error(
            error_type="repo_analysis_failed",
            error_message=str(e),
            user_ip=user_ip,
            metadata={"session_id": session_id, "repo_url": repo_url},
        )


@router.post("/analyze-repo")
async def analyze_repo(request: AnalyzeRepoRequest, http_request: Request, background_tasks: BackgroundTasks):
    """
    Start GitHub repository analysis asynchronously.

    Returns immediately with session_id and status. Frontend should poll
    /session/{session_id}/repo-analysis/status until analysis completes.

    The analysis performs:
    1. Fetches repository metadata and file structure via GitHub API
    2. Analyzes dependencies, infrastructure, and code patterns
    3. Generates an architecture diagram using Claude

    Args:
        request: AnalyzeRepoRequest with repo_url and optional model

    Returns:
        JSON with session_id and status
    """
    import os
    from app.github.analyzer import GitHubAnalyzer

    user_ip = http_request.client.host if http_request.client else None

    # Extract user_id from request state (set by Clerk middleware)
    user_id = getattr(http_request.state, "user_id", None)
    if not user_id:
        raise HTTPException(status_code=401, detail="User authentication required")

    try:
        # Validate GitHub URL format
        try:
            analyzer = GitHubAnalyzer()
            owner, repo = analyzer.parse_github_url(request.repo_url)
            analyzer.close()
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

        # Use specified model or default to Haiku
        model = request.model or "claude-haiku-4-5"

        # Check and deduct credits BEFORE creating session
        await check_and_deduct_credits(
            user_id=user_id,
            action="repo_analysis",
            model=model,
            metadata={"repo_url": request.repo_url},
        )

        # Create session with "fetching" status
        session_id = session_manager.create_session_for_repo_analysis(
            user_id=user_id,
            model=model,
            repo_url=request.repo_url
        )

        # Check if running in Lambda
        is_lambda = os.environ.get('AWS_LAMBDA_FUNCTION_NAME') is not None

        if is_lambda:
            # In Lambda: Use async invocation to avoid API Gateway 30s timeout
            import boto3
            import json as json_lib

            print(f"Lambda environment detected - triggering async repo analysis for session {session_id}")

            try:
                lambda_client = boto3.client('lambda')
                function_name = os.environ.get('AWS_LAMBDA_FUNCTION_NAME')

                payload = {
                    "async_task": "analyze_repo",
                    "session_id": session_id,
                    "repo_url": request.repo_url,
                    "model": model,
                    "user_ip": user_ip
                }

                lambda_client.invoke(
                    FunctionName=function_name,
                    InvocationType='Event',  # Async invocation
                    Payload=json_lib.dumps(payload)
                )

                print(f"Async Lambda invocation triggered for repo analysis")
            except Exception as e:
                print(f"Failed to trigger async invocation: {e}")
                # Fall back to background task
                background_tasks.add_task(_analyze_repo_background, session_id, request.repo_url, model, user_ip)
        else:
            # Local development: Use true background tasks
            print(f"Local environment - starting background repo analysis for session {session_id}")
            background_tasks.add_task(_analyze_repo_background, session_id, request.repo_url, model, user_ip)

        # Return immediately with session_id and fetching status
        return JSONResponse(content={
            "session_id": session_id,
            "status": "fetching"
        })

    except HTTPException:
        raise
    except Exception as e:
        log_error(
            error_type="repo_analysis_start_failed",
            error_message=str(e),
            user_ip=user_ip,
        )
        raise HTTPException(status_code=500, detail=f"Failed to start repo analysis: {str(e)}")


@router.get("/session/{session_id}/repo-analysis/status")
async def get_repo_analysis_status(session_id: str, http_request: Request):
    """
    Get the current status of repository analysis.

    Poll this endpoint every 2 seconds until status is "completed" or "failed".

    Returns:
        JSON with status, phase, progress_message, elapsed_seconds,
        and diagram/messages when completed.
    """
    user_id = getattr(http_request.state, "user_id", None)
    session = verify_session_access(session_id, user_id, http_request)

    status = session.repo_analysis_status

    response = {
        "status": status.status,
        "phase": status.phase,
        "progress_message": status.progress_message,
        "error": status.error,
    }

    # Include timing information
    if status.started_at:
        if status.completed_at:
            response["duration_seconds"] = status.completed_at - status.started_at
        else:
            response["elapsed_seconds"] = time.time() - status.started_at

    # Include diagram and messages if completed
    if status.status == "completed":
        response["diagram"] = session.diagram.model_dump()
        response["messages"] = [{"role": m.role, "content": m.content} for m in session.messages]
        response["name"] = session.name

        # Generate suggestions
        try:
            suggestions = generate_suggestions(
                diagram=session.diagram,
                node_id=None,
                last_message="Repository analyzed"
            )
            response["suggestions"] = suggestions
        except Exception as e:
            print(f"Error generating suggestions: {e}")
            response["suggestions"] = []

    return JSONResponse(content=response)
