"""Design-document lifecycle endpoints (generate, status, edit, export)."""

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


class ExportRequest(BaseModel):
    diagram_image: str | None = None  # Base64 encoded PNG from frontend


def _generate_design_doc_preview_background(session_id: str, user_ip: str):
    """Background task to generate the Executive-Summary-only preview for free users."""
    start_time = time.time()

    try:
        session = session_manager.get_session(session_id)
        if not session:
            logger.info(f"Session {session_id} not found in preview background task")
            return

        conversation_history = [
            {"role": msg.role, "content": msg.content}
            for msg in session.messages
        ]

        logger.info(f"\n=== BACKGROUND: GENERATE DESIGN DOC PREVIEW ===")
        logger.info(f"Session ID: {session_id}")
        logger.info(f"Nodes: {len(session.diagram.nodes)}")
        logger.info(f"Edges: {len(session.diagram.edges)}")

        markdown_content = generate_design_document_preview(
            session.diagram.model_dump(),
            conversation_history,
            session.model
        )

        session_manager.update_design_doc(session_id, markdown_content)
        session_manager.mark_design_doc_preview_used(session_id)
        session_manager.set_design_doc_status(session_id, "completed", is_preview=True)

        duration_ms = (time.time() - start_time) * 1000
        log_event(
            EventType.EXPORT_DESIGN_DOC,
            session_id=session_id,
            user_ip=user_ip,
            metadata={
                "action": "preview_generated",
                "doc_length": len(markdown_content),
                "duration_ms": duration_ms,
            },
        )

        logger.info(f"Generated preview design doc ({len(markdown_content)} chars)")
        logger.info(f"================================================\n")

    except Exception as e:
        logger.exception(f"Error generating design doc preview in background: {str(e)}")
        session_manager.set_design_doc_status(session_id, "failed", error=str(e), is_preview=True)


def _generate_design_doc_background(session_id: str, user_ip: str):
    """Background task to generate design document."""
    start_time = time.time()

    try:
        # Get session
        session = session_manager.get_session(session_id)
        if not session:
            logger.info(f"Session {session_id} not found in background task")
            return

        # Get conversation history
        conversation_history = [
            {"role": msg.role, "content": msg.content}
            for msg in session.messages
        ]

        logger.info(f"\n=== BACKGROUND: GENERATE DESIGN DOC ===")
        logger.info(f"Session ID: {session_id}")
        logger.info(f"Nodes: {len(session.diagram.nodes)}")
        logger.info(f"Edges: {len(session.diagram.edges)}")

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

        logger.info(f"Generated and stored design doc ({len(markdown_content)} chars)")
        logger.info(f"========================================\n")

        # Gamification: track design doc generation
        if session:
            process_action(session.user_id, "design_doc_generated")

    except Exception as e:
        logger.exception(f"Error generating design doc in background: {str(e)}")

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


class DesignDocUpdateRequest(BaseModel):
    content: str


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

        logger.info(f"\n=== EXPORT DESIGN DOC ===")
        logger.info(f"Session ID: {session_id}")
        logger.info(f"Format requested: {format}")
        logger.info(f"Nodes: {len(session.diagram.nodes)}")
        logger.info(f"Edges: {len(session.diagram.edges)}")
        logger.info(f"Has custom diagram image: {request.diagram_image is not None}")

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
            logger.info("Using frontend screenshot for diagram")
        else:
            # Fallback to generated diagram
            diagram_png = generate_diagram_png(session.diagram.model_dump())
            logger.info("Generated diagram using Pillow")

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

        logger.info(f"Generated documents successfully")
        logger.info(f"========================\n")

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
            gamification_result = process_action(user_id, "export_completed", {"format": format})
            result["gamification"] = gamification_result

        return JSONResponse(content=result)

    except ImportError as e:
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
        logger.exception(f"Error generating design doc: {str(e)}")
        duration_ms = (time.time() - start_time) * 1000
        log_export(
            session_id=session_id,
            format=format,
            duration_ms=duration_ms,
            user_ip=user_ip,
            success=False,
        )
        raise HTTPException(status_code=500, detail=f"Failed to generate design document: {str(e)}")


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

        # Determine free vs paid plan to decide preview vs full generation
        is_preview_path = False
        if user_id:
            credits_storage = get_user_credits_storage()
            user_credits = credits_storage.get_or_create_credits(user_id)
            if user_credits.plan not in DESIGN_DOC_PLANS:
                if session.design_doc_preview_used:
                    return JSONResponse(
                        status_code=403,
                        content={
                            "error": "feature_locked",
                            "feature": "design_doc_generation",
                            "required_plan": "starter",
                            "message": "You've already previewed the design doc for this diagram. Upgrade to Starter ($1/mo) to generate the full design document.",
                        },
                    )
                is_preview_path = True

        # Check if already generating (before deducting credits to avoid double-charge)
        if session.design_doc_status.status == "generating":
            return JSONResponse(content={
                "status": "already_generating",
                "message": "Design document generation already in progress"
            })

        if is_preview_path:
            # Free preview: no credit deduction, generate Executive Summary only
            session_manager.set_design_doc_status(session_id, "generating", is_preview=True)
            async_task_name = "generate_design_doc_preview"
            background_fn = _generate_design_doc_preview_background
            log_message = f"Starting preview generation for session {session_id}"
        else:
            # Paid full generation
            await check_and_deduct_credits(
                user_id=user_id,
                action="design_doc_generation",
                session_id=session_id,
            )
            session_manager.set_design_doc_status(session_id, "generating", is_preview=False)
            async_task_name = "generate_design_doc"
            background_fn = _generate_design_doc_background
            log_message = f"Starting full generation for session {session_id}"

        # Check if running in Lambda (AWS_LAMBDA_FUNCTION_NAME env var is set)
        is_lambda = os.environ.get('AWS_LAMBDA_FUNCTION_NAME') is not None

        if is_lambda:
            # In Lambda: Use async invocation to avoid API Gateway 30s timeout
            # API Gateway has a 30s timeout, but generation takes 30-150s
            # Solution: Invoke Lambda asynchronously for the actual generation
            import boto3
            import json as json_lib

            logger.info(f"Lambda environment detected - {log_message}")

            try:
                lambda_client = boto3.client('lambda')
                function_name = os.environ.get('AWS_LAMBDA_FUNCTION_NAME')

                payload = {
                    "async_task": async_task_name,
                    "session_id": session_id,
                    "user_ip": user_ip
                }

                lambda_client.invoke(
                    FunctionName=function_name,
                    InvocationType='Event',  # Async invocation
                    Payload=json_lib.dumps(payload)
                )

                logger.info(f"Async Lambda invocation triggered for session {session_id}")
            except Exception as e:
                logger.exception(f"Failed to trigger async invocation: {e}")
                # Fall back to inline execution (will timeout after 30s but generation continues)
                background_tasks.add_task(background_fn, session_id, user_ip)
        else:
            # Local development: Use true background tasks (non-blocking)
            logger.info(f"Local environment - {log_message}")
            background_tasks.add_task(background_fn, session_id, user_ip)

        return JSONResponse(content={
            "status": "started",
            "is_preview": is_preview_path,
            "message": "Design document generation started"
        })

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error starting design doc generation: {str(e)}")
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
        "is_preview": status.is_preview,
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

        logger.info(f"Updated design doc for session {session_id} ({len(request.content)} chars)")

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

        logger.info(f"\n=== EXPORT DESIGN DOC FROM SESSION ===")
        logger.info(f"Session ID: {session_id}")
        logger.info(f"Format requested: {format}")
        logger.info(f"Design doc length: {len(session.design_doc)} chars")
        logger.info(f"Has custom diagram image: {request.diagram_image is not None}")

        markdown_content = session.design_doc

        # Use provided diagram image or generate one
        if request.diagram_image:
            # Use the screenshot from frontend
            diagram_png = base64.b64decode(request.diagram_image)
            logger.info("Using frontend screenshot for diagram")
        else:
            # Fallback to generated diagram
            diagram_png = generate_diagram_png(session.diagram.model_dump())
            logger.info("Generated diagram using Pillow")

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

        logger.info(f"Exported documents successfully")
        logger.info(f"======================================\n")

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
            gamification_result = process_action(user_id, "export_completed", {"format": format})
            result["gamification"] = gamification_result

        return JSONResponse(content=result)

    except HTTPException:
        raise
    except ImportError as e:
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
        logger.exception(f"Error exporting design doc: {str(e)}")
        duration_ms = (time.time() - start_time) * 1000
        log_export(
            session_id=session_id,
            format=format,
            duration_ms=duration_ms,
            user_ip=user_ip,
            success=False,
        )
        raise HTTPException(status_code=500, detail=f"Failed to export design document: {str(e)}")
