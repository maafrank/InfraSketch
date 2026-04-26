"""Core endpoints: chat, session CRUD, and the public visitor badge."""

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
            logger.info(f"✓ Diagram updated: {len(updated_session.diagram.nodes)} nodes, {len(updated_session.diagram.edges)} edges")

        # Check if design doc was updated (reload from session like diagram)
        response_design_doc = None
        if updated_session.design_doc and updated_session.design_doc != old_design_doc:
            response_design_doc = updated_session.design_doc
            logger.info(f"✓ Design doc updated via chat ({len(response_design_doc)} chars)")

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
        model=DEFAULT_MODEL
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
    process_action(user_id, "session_created", {"model": DEFAULT_MODEL})

    return {
        "session_id": session_id,
        "diagram": empty_diagram
    }


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
        logger.exception(f"Error generating monthly visitors badge: {e}")
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
