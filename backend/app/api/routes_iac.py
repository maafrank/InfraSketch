"""Infrastructure-as-Code export endpoints.

Async job with polling, matching the design-doc and review flows. IaC generation
produces long output (multi-file Terraform) and routinely exceeds the API Gateway
30s timeout.
"""

import base64
import json
import logging
import os
import time

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.api._helpers import check_and_deduct_credits, enforce_plan_feature
from app.api.deps import get_current_user, get_session_for_user
from app.billing.credit_costs import IAC_EXPORT_PLANS
from app.gamification.engine import process_action
from app.iac.generator import IacGenerationError, build_zip, generate_iac
from app.iac.prompts import TARGETS
from app.models import SessionState
from app.session.manager import session_manager
from app.utils.logger import EventType, log_error, log_event

logger = logging.getLogger(__name__)
router = APIRouter()


class IacGenerateRequest(BaseModel):
    target: str  # terraform | kubernetes | compose


def _generate_iac_background(session_id: str, target: str, user_ip: str = None):
    """Background task: generate IaC for one target and store it on the session."""
    start_time = time.time()

    try:
        session = session_manager.get_session(session_id)
        if not session:
            logger.info(f"Session {session_id} not found in IaC background task")
            return

        logger.info(f"\n=== BACKGROUND: GENERATE IAC ({target}) ===")
        logger.info(f"Session ID: {session_id} Nodes: {len(session.diagram.nodes)}")

        artifact = generate_iac(session.diagram.model_dump(), target, model=session.model)

        session_manager.store_iac_artifact(session_id, target, artifact)
        session_manager.set_iac_status(session_id, "completed", target=target)

        duration_ms = (time.time() - start_time) * 1000
        log_event(
            EventType.EXPORT_DESIGN_DOC,
            session_id=session_id,
            user_ip=user_ip,
            metadata={
                "action": "iac_export",
                "target": target,
                "file_count": len(artifact["files"]),
                "duration_ms": duration_ms,
            },
        )

        if session.user_id:
            try:
                process_action(session.user_id, "iac_exported", {"target": target})
            except Exception as e:
                logger.exception(f"Gamification failed after IaC export: {e}")

        logger.info(f"✓ IaC stored for session {session_id} ({len(artifact['files'])} files)")

    except IacGenerationError as e:
        logger.warning(f"✗ IaC produced no output for {session_id}: {e}")
        session_manager.set_iac_status(session_id, "failed", target=target, error=str(e))
    except Exception as e:
        logger.exception(f"✗ Error generating IaC: {e}")
        session_manager.set_iac_status(session_id, "failed", target=target, error=str(e))
        log_error(
            error_type="iac_export_failed",
            error_message=str(e),
            session_id=session_id,
            user_ip=user_ip,
        )


@router.post("/session/{session_id}/iac/generate")
async def start_iac_generation(
    session_id: str,
    request: IacGenerateRequest,
    http_request: Request,
    background_tasks: BackgroundTasks,
    user_id: str = Depends(get_current_user),
    session: SessionState = Depends(get_session_for_user),
):
    """Kick off IaC generation for one target. Poll /iac/status for the result."""
    user_ip = http_request.client.host if http_request.client else None

    if request.target not in TARGETS:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown target '{request.target}'. Expected one of: {', '.join(TARGETS)}",
        )

    if not session.diagram or not session.diagram.nodes:
        raise HTTPException(status_code=400, detail="Session has no diagram to export")

    if session.iac_status.status == "generating":
        return JSONResponse(content={
            "status": "already_generating",
            "message": "An export is already in progress",
        })

    enforce_plan_feature(
        user_id,
        feature="iac_export",
        allowed_plans=IAC_EXPORT_PLANS,
        required_plan="pro",
        message=(
            "Infrastructure-as-Code export requires the Pro plan. "
            "Upgrade to Pro ($4.99/mo) to turn your diagram into Terraform, "
            "Kubernetes manifests, or Docker Compose."
        ),
    )

    await check_and_deduct_credits(
        user_id=user_id,
        action="iac_export",
        model=session.model,
        session_id=session_id,
        metadata={"target": request.target},
    )

    session_manager.set_iac_status(session_id, "generating", target=request.target)

    is_lambda = os.environ.get("AWS_LAMBDA_FUNCTION_NAME") is not None
    if is_lambda:
        import boto3
        try:
            boto3.client("lambda").invoke(
                FunctionName=os.environ["AWS_LAMBDA_FUNCTION_NAME"],
                InvocationType="Event",
                Payload=json.dumps({
                    "async_task": "generate_iac",
                    "session_id": session_id,
                    "target": request.target,
                    "user_ip": user_ip,
                }),
            )
            logger.info(f"Async Lambda invocation triggered for IaC export of {session_id}")
        except Exception as e:
            logger.exception(f"Failed to trigger async IaC invocation: {e}")
            background_tasks.add_task(_generate_iac_background, session_id, request.target, user_ip)
    else:
        background_tasks.add_task(_generate_iac_background, session_id, request.target, user_ip)

    return JSONResponse(content={"status": "started", "target": request.target})


@router.get("/session/{session_id}/iac/status")
async def get_iac_status(
    session_id: str,
    http_request: Request,
    target: str = None,
    user_id: str = Depends(get_current_user),
    session: SessionState = Depends(get_session_for_user),
):
    """Poll for IaC progress and, once complete, the generated files."""
    status = session.iac_status
    requested_target = target or status.target

    response = {
        "status": status.status,
        "target": status.target,
        "error": status.error,
        "started_at": status.started_at,
        "completed_at": status.completed_at,
    }

    artifact = session.iac_artifacts.get(requested_target) if requested_target else None
    if artifact:
        response["artifact"] = artifact
        # The diagram may have changed since these files were generated. Say so
        # rather than handing over stale infrastructure code silently.
        response["is_stale"] = artifact.get("diagram_revision") != session.diagram_revision

    if status.started_at and not status.completed_at:
        response["elapsed_seconds"] = time.time() - status.started_at

    return JSONResponse(content=response)


@router.post("/session/{session_id}/iac/download")
async def download_iac(
    session_id: str,
    request: IacGenerateRequest,
    http_request: Request,
    user_id: str = Depends(get_current_user),
    session: SessionState = Depends(get_session_for_user),
):
    """Return the already-generated files for a target as a base64 zip.

    Not charged: generation was already paid for, and re-downloading the same
    bundle is not new work.
    """
    artifact = session.iac_artifacts.get(request.target)
    if not artifact:
        raise HTTPException(
            status_code=404,
            detail=f"No generated {request.target} files for this session. Generate them first.",
        )

    zip_bytes = build_zip(artifact["files"], request.target)

    return JSONResponse(content={
        "zip": {
            "content": base64.b64encode(zip_bytes).decode("utf-8"),
            "filename": f"infrasketch-{request.target}.zip",
        },
        "file_count": len(artifact["files"]),
    })
