"""Shared FastAPI dependencies + helpers for the api package.

ClerkAuthMiddleware (middleware/clerk_auth.py) validates the JWT and
attaches user_id to request.state. The Depends-prefixed helpers here are
typed accessors over that state, plus a session-ownership wrapper that
returns the loaded SessionState so endpoints don't load it again.

verify_session_access is the imperative form, kept for endpoints that
haven't been migrated to Depends yet. New code should prefer
Depends(get_session_for_user).

Tests can override either Depends helper via app.dependency_overrides.
"""

from fastapi import Depends, HTTPException, Request

from app.models import SessionState
from app.session.manager import session_manager


def get_current_user(request: Request) -> str:
    """Return the authenticated user_id, or raise 401 if missing.

    The Clerk middleware always attaches user_id when auth succeeds, so
    a missing value here means the middleware was bypassed (test paths
    without auth headers, or DISABLE_CLERK_AUTH in dev).
    """
    user_id = getattr(request.state, "user_id", None)
    if not user_id:
        raise HTTPException(status_code=401, detail="User authentication required")
    return user_id


def verify_session_access(session_id: str, user_id: str, http_request: Request = None) -> SessionState:
    """Imperative session-ownership check, used by endpoints not yet on Depends.

    Raises 401 if user_id is empty, 404 if the session does not exist,
    403 if it belongs to another user. Returns the loaded SessionState.

    The http_request parameter is unused but kept for backwards compatibility
    with existing call sites.
    """
    if not user_id:
        raise HTTPException(status_code=401, detail="User authentication required")
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if not session_manager.verify_ownership(session_id, user_id):
        raise HTTPException(status_code=403, detail="You don't have permission to access this session")
    return session


def get_session_for_user(
    session_id: str,
    user_id: str = Depends(get_current_user),
) -> SessionState:
    """FastAPI Depends version of verify_session_access.

    Use this in new endpoint signatures to avoid the user_id-extraction
    + session-load boilerplate. Tests can override this dependency to
    bypass session loading.
    """
    return verify_session_access(session_id, user_id)
