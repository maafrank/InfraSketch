"""Public share links.

Three surfaces:
  - Owner-only: POST/DELETE /api/session/{id}/share
  - Public JSON: GET /api/share/{token}, consumed by the React viewer
  - Authenticated: POST /api/share/{token}/fork, clones into the caller's account

The HTML shell and OG image live in routes_share_html.py, which is mounted at
the root rather than under /api because the shareable URL is infrasketch.net/share/{token}.
"""

import logging
import os
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.api.deps import get_current_user, get_session_for_user
from app.models import Diagram, SessionState
from app.session.manager import session_manager
from app.utils.logger import EventType, log_event

logger = logging.getLogger(__name__)
router = APIRouter()

SITE_URL = os.environ.get("PUBLIC_SITE_URL", "https://infrasketch.net")


class ShareRequest(BaseModel):
    allow_fork: bool = True


def public_share_payload(session: SessionState) -> dict:
    """Build the public view of a shared session.

    An explicit allowlist, not a `model_dump(exclude=...)` denylist. A denylist
    silently starts leaking the moment someone adds a field to SessionState;
    this cannot. Everything a viewer does not need stays out: user_id, the chat
    transcript, the original prompt, repo analysis, credits, and sync state.

    Covered by test_public_share_payload_allowlist, which asserts the forbidden
    keys are absent against a fully-populated session.
    """
    diagram = session.diagram.model_dump() if session.diagram else {"nodes": [], "edges": []}

    return {
        "name": session.name or "Untitled Design",
        "diagram": diagram,
        "design_doc": session.design_doc,
        "created_at": session.created_at.isoformat() if session.created_at else None,
        "shared_at": session.shared_at.isoformat() if session.shared_at else None,
        "allow_fork": session.allow_fork,
        "node_count": len(diagram.get("nodes", [])),
        "edge_count": len(diagram.get("edges", [])),
    }


@router.post("/session/{session_id}/share")
async def share_session(
    session_id: str,
    request: ShareRequest,
    http_request: Request,
    user_id: str = Depends(get_current_user),
    session: SessionState = Depends(get_session_for_user),
):
    """Publish a session and return its share URL."""
    token = session_manager.share_session(session_id, allow_fork=request.allow_fork)
    if not token:
        raise HTTPException(status_code=500, detail="Could not create a share link")

    log_event(
        EventType.API_REQUEST,
        session_id=session_id,
        user_ip=http_request.client.host if http_request.client else None,
        metadata={"action": "session_shared", "allow_fork": request.allow_fork},
    )

    return JSONResponse(content={
        "token": token,
        "share_url": f"{SITE_URL}/share/{token}",
        "allow_fork": request.allow_fork,
    })


@router.delete("/session/{session_id}/share")
async def unshare_session(
    session_id: str,
    http_request: Request,
    user_id: str = Depends(get_current_user),
    session: SessionState = Depends(get_session_for_user),
):
    """Revoke public access. The old link stops working immediately."""
    if not session_manager.unshare_session(session_id):
        raise HTTPException(status_code=500, detail="Could not revoke the share link")
    return JSONResponse(content={"success": True})


@router.get("/share/{token}")
async def get_shared_session(token: str, http_request: Request):
    """Public, unauthenticated read of a shared diagram."""
    session = session_manager.get_session_by_share_token(token)
    if not session:
        raise HTTPException(status_code=404, detail="This diagram is not shared or the link has expired")

    session_manager.increment_share_views(session.session_id)
    return JSONResponse(content=public_share_payload(session))


@router.post("/share/{token}/fork")
async def fork_shared_session(
    token: str,
    http_request: Request,
    user_id: str = Depends(get_current_user),
):
    """Clone a shared diagram into a new session owned by the caller.

    Authenticated: forking creates a session, which needs an owner. The original
    is never modified, and the copy carries no trace of the original owner.
    """
    source = session_manager.get_session_by_share_token(token)
    if not source:
        raise HTTPException(status_code=404, detail="This diagram is not shared or the link has expired")
    if not source.allow_fork:
        raise HTTPException(status_code=403, detail="The owner has disabled copying for this diagram")

    # Deep-copy through the model so the new session shares no mutable state
    # with the original.
    diagram = Diagram.model_validate(source.diagram.model_dump())

    new_session_id = session_manager.create_session(
        diagram=diagram,
        user_id=user_id,
        model=source.model,
    )

    new_session = session_manager.get_session(new_session_id)
    if new_session:
        base_name = source.name or "Untitled Design"
        new_session.name = f"{base_name} (copy)"
        # Suppress the auto-namer: the inherited name is the intended one.
        new_session.name_generated = True
        if source.design_doc:
            new_session.design_doc = source.design_doc
            new_session.design_doc_status.status = "completed"
            new_session.design_doc_status.completed_at = datetime.now(timezone.utc).timestamp()
        if session_manager.is_lambda:
            session_manager.storage.save_session(new_session)

    log_event(
        EventType.API_REQUEST,
        session_id=new_session_id,
        user_ip=http_request.client.host if http_request.client else None,
        metadata={"action": "session_forked", "source_token": token},
    )

    return JSONResponse(content={
        "session_id": new_session_id,
        "name": new_session.name if new_session else None,
    })
