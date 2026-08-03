"""Architecture review endpoints.

Async job with polling, matching the design-doc flow: the POST charges credits
and dispatches, the GET is polled every few seconds until the review lands.
Reviews take 10-40s, comfortably past the API Gateway 30s timeout.
"""

import json
import logging
import os
import time

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from fastapi.responses import JSONResponse

from app.api._helpers import check_and_deduct_credits, enforce_plan_feature
from app.api.deps import get_current_user, get_session_for_user
from app.billing.credit_costs import ARCHITECTURE_REVIEW_PLANS
from app.gamification.engine import process_action
from app.models import SessionState
from app.review.analyzer import ReviewGenerationError, generate_architecture_review
from app.session.manager import session_manager
from app.utils.logger import EventType, log_error, log_event

logger = logging.getLogger(__name__)
router = APIRouter()


def _generate_review_background(session_id: str, user_ip: str = None):
    """Background task: run the review and store it on the session."""
    start_time = time.time()

    try:
        session = session_manager.get_session(session_id)
        if not session:
            logger.info(f"Session {session_id} not found in review background task")
            return

        logger.info(f"\n=== BACKGROUND: GENERATE ARCHITECTURE REVIEW ===")
        logger.info(f"Session ID: {session_id}")
        logger.info(f"Nodes: {len(session.diagram.nodes)} Edges: {len(session.diagram.edges)}")

        review = generate_architecture_review(
            session.diagram.model_dump(),
            design_doc=session.design_doc,
            model=session.model,
        )

        session_manager.update_review(session_id, review)
        session_manager.set_review_status(session_id, "completed")

        duration_ms = (time.time() - start_time) * 1000
        log_event(
            EventType.API_REQUEST,
            session_id=session_id,
            user_ip=user_ip,
            metadata={
                "action": "architecture_review",
                "score": review["score"],
                "finding_count": len(review["findings"]),
                "duration_ms": duration_ms,
            },
        )

        if session.user_id:
            try:
                process_action(
                    session.user_id,
                    "review_completed",
                    {"score": review["score"], "finding_count": len(review["findings"])},
                )
            except Exception as e:
                # Gamification is never allowed to fail the work it decorates.
                logger.exception(f"Gamification failed after review: {e}")

        logger.info(f"✓ Review stored for session {session_id}")

    except ReviewGenerationError as e:
        logger.warning(f"✗ Review produced no output for {session_id}: {e}")
        session_manager.set_review_status(session_id, "failed", error=str(e))
    except Exception as e:
        logger.exception(f"✗ Error generating architecture review: {e}")
        session_manager.set_review_status(session_id, "failed", error=str(e))
        log_error(
            error_type="architecture_review_failed",
            error_message=str(e),
            session_id=session_id,
            user_ip=user_ip,
        )


@router.post("/session/{session_id}/review")
async def start_architecture_review(
    session_id: str,
    http_request: Request,
    background_tasks: BackgroundTasks,
    user_id: str = Depends(get_current_user),
    session: SessionState = Depends(get_session_for_user),
):
    """Kick off an architecture review. Poll /review/status for the result."""
    user_ip = http_request.client.host if http_request.client else None

    if not session.diagram or not session.diagram.nodes:
        raise HTTPException(status_code=400, detail="Session has no diagram to review")

    # Already running: return instead of charging twice.
    if session.review_status.status == "generating":
        return JSONResponse(content={
            "status": "already_generating",
            "message": "An architecture review is already in progress",
        })

    enforce_plan_feature(
        user_id,
        feature="architecture_review",
        allowed_plans=ARCHITECTURE_REVIEW_PLANS,
        required_plan="starter",
        message=(
            "Architecture review requires a paid plan. "
            "Upgrade to Starter ($1/mo) to have Sketch critique your design."
        ),
    )

    await check_and_deduct_credits(
        user_id=user_id,
        action="architecture_review",
        model=session.model,
        session_id=session_id,
    )

    session_manager.set_review_status(session_id, "generating")

    is_lambda = os.environ.get("AWS_LAMBDA_FUNCTION_NAME") is not None
    if is_lambda:
        # API Gateway times out at 30s; a review takes longer. Self-invoke.
        import boto3
        try:
            boto3.client("lambda").invoke(
                FunctionName=os.environ["AWS_LAMBDA_FUNCTION_NAME"],
                InvocationType="Event",
                Payload=json.dumps({
                    "async_task": "generate_review",
                    "session_id": session_id,
                    "user_ip": user_ip,
                }),
            )
            logger.info(f"Async Lambda invocation triggered for review of {session_id}")
        except Exception as e:
            logger.exception(f"Failed to trigger async review invocation: {e}")
            background_tasks.add_task(_generate_review_background, session_id, user_ip)
    else:
        background_tasks.add_task(_generate_review_background, session_id, user_ip)

    return JSONResponse(content={"status": "started", "message": "Architecture review started"})


@router.get("/session/{session_id}/review/status")
async def get_review_status(
    session_id: str,
    http_request: Request,
    user_id: str = Depends(get_current_user),
    session: SessionState = Depends(get_session_for_user),
):
    """Poll for review progress and, once complete, the review itself."""
    status = session.review_status

    response = {
        "status": status.status,
        "error": status.error,
        "started_at": status.started_at,
        "completed_at": status.completed_at,
    }

    if status.status == "completed" and session.review:
        response["review"] = session.review
        # The diagram may have moved on since the review ran, which makes the
        # findings' node anchors potentially stale. Let the panel say so.
        response["is_stale"] = (
            status.reviewed_diagram_revision is not None
            and status.reviewed_diagram_revision != session.diagram_revision
        )

    if status.started_at:
        if status.completed_at:
            response["duration_seconds"] = status.completed_at - status.started_at
        else:
            response["elapsed_seconds"] = time.time() - status.started_at

    return JSONResponse(content=response)
