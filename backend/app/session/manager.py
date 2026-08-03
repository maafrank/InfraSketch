from typing import Dict, Optional, List
import copy
import os
import secrets
import uuid
import time
from datetime import datetime, timezone
from app.models import SessionState, Diagram, Message, DesignDocStatus, DiagramGenerationStatus, RepoAnalysisStatus
from app.config.models import DEFAULT_MODEL
from app.sync.context import current_mutation_provenance

import logging
logger = logging.getLogger(__name__)


class SessionManager:
    def __init__(self):
        # Detect if running in Lambda
        self.is_lambda = os.environ.get('AWS_LAMBDA_FUNCTION_NAME') is not None

        if self.is_lambda:
            # Use DynamoDB for persistent storage in Lambda
            logger.info("SessionManager: Using DynamoDB storage (Lambda environment)")
            from app.session.dynamodb_storage import DynamoDBSessionStorage
            self.storage = DynamoDBSessionStorage()
        else:
            # Use in-memory storage for local development
            logger.info("SessionManager: Using in-memory storage (local environment)")
            self.sessions: Dict[str, SessionState] = {}
            self.storage = None

    def create_session(self, diagram: Diagram, user_id: str, model: str = DEFAULT_MODEL) -> str:
        """
        Create a new session with initial diagram.

        Args:
            diagram: Initial diagram state
            user_id: Clerk user ID (from authenticated request)
            model: AI model to use for this session

        Returns:
            session_id: UUID for the new session
        """
        session_id = str(uuid.uuid4())
        session = SessionState(
            session_id=session_id,
            user_id=user_id,
            diagram=diagram,
            messages=[],
            current_node=None,
            model=model,
            created_at=datetime.now(timezone.utc)
        )

        # Save to appropriate storage
        if self.is_lambda:
            self.storage.save_session(session)
        else:
            self.sessions[session_id] = session

        return session_id

    def get_session(self, session_id: str) -> Optional[SessionState]:
        """
        Retrieve session by ID.

        Args:
            session_id: UUID of the session

        Returns:
            SessionState or None if not found
        """
        # Get from appropriate storage
        if self.is_lambda:
            session = self.storage.get_session(session_id)
        else:
            session = self.sessions.get(session_id)

        return session

    def verify_ownership(self, session_id: str, user_id: str) -> bool:
        """
        Check if user owns the session.

        Args:
            session_id: UUID of the session
            user_id: Clerk user ID

        Returns:
            True if user owns the session, False otherwise
        """
        session = self.get_session(session_id)
        if not session:
            return False
        return session.user_id == user_id

    def get_user_sessions(self, user_id: str) -> List[SessionState]:
        """
        Get all sessions belonging to a user.

        Args:
            user_id: Clerk user ID

        Returns:
            List of SessionState objects, sorted by created_at (newest first)
        """
        if self.is_lambda:
            # Use DynamoDB GSI query
            sessions = self.storage.get_sessions_by_user(user_id)
        else:
            # Filter in-memory sessions
            sessions = [
                session for session in self.sessions.values()
                if session.user_id == user_id
            ]

        # Sort by created_at (newest first)
        # Helper to normalize datetimes for comparison (handle both naive and aware)
        def get_sort_key(session):
            if not session.created_at:
                return datetime.min.replace(tzinfo=timezone.utc)
            # If datetime is naive, assume UTC
            if session.created_at.tzinfo is None:
                return session.created_at.replace(tzinfo=timezone.utc)
            return session.created_at

        sessions.sort(key=get_sort_key, reverse=True)
        return sessions

    def update_diagram(self, session_id: str, diagram: Diagram) -> bool:
        """Update diagram for a session.

        The mutation's provenance is read from the `current_mutation_provenance`
        contextvar (set by tools_node, the SyncEngine, or generation paths). It
        controls whether SyncEngine.schedule schedules a follow-up sync.
        """
        session = self.get_session(session_id)
        if not session:
            return False

        old_diagram = copy.deepcopy(session.diagram) if session.diagram else None
        provenance = current_mutation_provenance.get()

        session.diagram = diagram
        session.diagram_revision += 1

        if self.is_lambda:
            saved = self.storage.save_session(session)
        else:
            saved = True

        if saved:
            self._maybe_schedule_sync(
                session,
                side="diagram",
                provenance=provenance,
                old_diagram=old_diagram,
                new_diagram=diagram,
            )
        return saved

    def add_message(self, session_id: str, message: Message) -> bool:
        """Add message to session history."""
        session = self.get_session(session_id)
        if not session:
            return False
        session.messages.append(message)

        # Save updated session
        if self.is_lambda:
            return self.storage.save_session(session)
        return True

    def set_current_node(self, session_id: str, node_id: Optional[str]) -> bool:
        """Set the currently focused node."""
        session = self.get_session(session_id)
        if not session:
            return False
        session.current_node = node_id

        # Save updated session
        if self.is_lambda:
            return self.storage.save_session(session)
        return True

    def update_design_doc(self, session_id: str, design_doc: str) -> bool:
        """Update design document content for a session.

        Provenance handling matches `update_diagram` (Phase 2 will use this for
        doc -> diagram sync). For now, the design_doc_revision counter is bumped
        so concurrency guards in the sync engine can detect mid-sync edits.
        """
        session = self.get_session(session_id)
        if not session:
            return False

        provenance = current_mutation_provenance.get()
        session.design_doc = design_doc
        session.design_doc_revision += 1

        if self.is_lambda:
            saved = self.storage.save_session(session)
        else:
            saved = True

        if saved:
            self._maybe_schedule_sync(
                session,
                side="design_doc",
                provenance=provenance,
            )
        return saved

    def set_design_doc_status(self, session_id: str, status: str, error: Optional[str] = None, is_preview: Optional[bool] = None) -> bool:
        """Update design document generation status.

        If is_preview is provided, also updates the is_preview flag (use when starting
        or completing a preview generation). Pass False explicitly to clear the flag
        when starting a full generation.
        """
        session = self.get_session(session_id)
        if not session:
            return False

        session.design_doc_status.status = status
        session.design_doc_status.error = error
        if is_preview is not None:
            session.design_doc_status.is_preview = is_preview

        if status == "generating" and not session.design_doc_status.started_at:
            session.design_doc_status.started_at = time.time()
        elif status in ["completed", "failed"]:
            session.design_doc_status.completed_at = time.time()

        # Save updated session
        if self.is_lambda:
            return self.storage.save_session(session)
        return True

    def mark_design_doc_preview_used(self, session_id: str) -> bool:
        """Mark this session as having consumed its one-time design doc preview."""
        session = self.get_session(session_id)
        if not session:
            return False
        session.design_doc_preview_used = True
        if self.is_lambda:
            return self.storage.save_session(session)
        return True

    def get_design_doc_status(self, session_id: str) -> Optional[DesignDocStatus]:
        """Get current design document generation status."""
        session = self.get_session(session_id)
        if not session:
            return None
        return session.design_doc_status

    def create_session_for_generation(self, user_id: str, model: str, prompt: str) -> str:
        """
        Create a new session with empty diagram for async generation.

        Args:
            user_id: Clerk user ID (from authenticated request)
            model: AI model to use for this session
            prompt: User prompt to store for background task

        Returns:
            session_id: UUID for the new session
        """
        session_id = str(uuid.uuid4())

        # Create empty diagram placeholder
        empty_diagram = Diagram(nodes=[], edges=[])

        # Create session with "generating" status
        session = SessionState(
            session_id=session_id,
            user_id=user_id,
            diagram=empty_diagram,
            messages=[],
            current_node=None,
            model=model,
            created_at=datetime.now(timezone.utc),
            generation_prompt=prompt,
            diagram_generation_status=DiagramGenerationStatus(
                status="generating",
                started_at=time.time()
            )
        )

        # Save to appropriate storage
        if self.is_lambda:
            self.storage.save_session(session)
        else:
            self.sessions[session_id] = session

        return session_id

    def set_diagram_generation_status(self, session_id: str, status: str, error: Optional[str] = None) -> bool:
        """Update diagram generation status."""
        session = self.get_session(session_id)
        if not session:
            return False

        session.diagram_generation_status.status = status
        session.diagram_generation_status.error = error

        if status == "generating" and not session.diagram_generation_status.started_at:
            session.diagram_generation_status.started_at = time.time()
        elif status in ["completed", "failed"]:
            session.diagram_generation_status.completed_at = time.time()

        # Save updated session
        if self.is_lambda:
            return self.storage.save_session(session)
        return True

    def get_diagram_generation_status(self, session_id: str) -> Optional[DiagramGenerationStatus]:
        """Get current diagram generation status."""
        session = self.get_session(session_id)
        if not session:
            return None
        return session.diagram_generation_status

    def update_session_name(self, session_id: str, name: str) -> bool:
        """Update session name and mark as generated."""
        session = self.get_session(session_id)
        if not session:
            return False
        session.name = name
        session.name_generated = True

        # Save updated session
        if self.is_lambda:
            return self.storage.save_session(session)
        return True

    def update_model(self, session_id: str, model: str) -> bool:
        """Update AI model for a session."""
        session = self.get_session(session_id)
        if not session:
            return False
        session.model = model

        # Save updated session
        if self.is_lambda:
            return self.storage.save_session(session)
        return True

    def delete_session(self, session_id: str) -> bool:
        """
        Delete a session from storage.

        Args:
            session_id: UUID of the session to delete

        Returns:
            True if session was deleted successfully, False otherwise
        """
        if self.is_lambda:
            # Use DynamoDB delete
            return self.storage.delete_session(session_id)
        else:
            # Delete from in-memory storage
            if session_id in self.sessions:
                del self.sessions[session_id]
                return True
            return False

    def create_session_for_repo_analysis(self, user_id: str, model: str, repo_url: str) -> str:
        """
        Create a new session for GitHub repository analysis.

        Args:
            user_id: Clerk user ID (from authenticated request)
            model: AI model to use for diagram generation
            repo_url: GitHub repository URL to analyze

        Returns:
            session_id: UUID for the new session
        """
        session_id = str(uuid.uuid4())

        # Create empty diagram placeholder
        empty_diagram = Diagram(nodes=[], edges=[])

        # Create session with "fetching" status
        session = SessionState(
            session_id=session_id,
            user_id=user_id,
            diagram=empty_diagram,
            messages=[],
            current_node=None,
            model=model,
            created_at=datetime.now(timezone.utc),
            repo_url=repo_url,
            repo_analysis_status=RepoAnalysisStatus(
                status="fetching",
                phase="fetch",
                progress_message="Fetching repository metadata...",
                started_at=time.time()
            )
        )

        # Save to appropriate storage
        if self.is_lambda:
            self.storage.save_session(session)
        else:
            self.sessions[session_id] = session

        return session_id

    def set_repo_analysis_status(
        self,
        session_id: str,
        status: str,
        phase: Optional[str] = None,
        progress_message: Optional[str] = None,
        error: Optional[str] = None
    ) -> bool:
        """
        Update repository analysis status.

        Args:
            session_id: Session UUID
            status: Status value (fetching, analyzing, generating, completed, failed)
            phase: Current phase (fetch, analyze, generate)
            progress_message: Human-readable progress message
            error: Error message if failed

        Returns:
            True if update succeeded
        """
        session = self.get_session(session_id)
        if not session:
            return False

        session.repo_analysis_status.status = status
        if phase is not None:
            session.repo_analysis_status.phase = phase
        if progress_message is not None:
            session.repo_analysis_status.progress_message = progress_message
        session.repo_analysis_status.error = error

        if status == "fetching" and not session.repo_analysis_status.started_at:
            session.repo_analysis_status.started_at = time.time()
        elif status in ["completed", "failed"]:
            session.repo_analysis_status.completed_at = time.time()

        # Save updated session
        if self.is_lambda:
            return self.storage.save_session(session)
        return True

    def get_repo_analysis_status(self, session_id: str) -> Optional[RepoAnalysisStatus]:
        """Get current repository analysis status."""
        session = self.get_session(session_id)
        if not session:
            return None
        return session.repo_analysis_status

    def share_session(self, session_id: str, allow_fork: bool = True) -> Optional[str]:
        """Make a session public and return its share token.

        Idempotent: re-sharing an already-shared session keeps the existing
        token so previously-distributed links keep working.
        """
        session = self.get_session(session_id)
        if not session:
            return None

        if not session.share_token:
            # 12 bytes -> 16 url-safe chars. Unguessable, but the token is not
            # the only protection: the payload is sanitized before it leaves.
            session.share_token = secrets.token_urlsafe(12)

        session.is_public = True
        session.public_flag = "1"
        session.allow_fork = allow_fork
        if not session.shared_at:
            session.shared_at = datetime.now(timezone.utc)

        if self.is_lambda:
            if not self.storage.save_session(session):
                return None
        return session.share_token

    def unshare_session(self, session_id: str) -> bool:
        """Revoke public access.

        Clears the token outright rather than just flipping is_public, so a
        previously-shared link can never be reactivated by a later re-share.
        """
        session = self.get_session(session_id)
        if not session:
            return False
        session.share_token = None
        session.is_public = False
        session.public_flag = None
        session.shared_at = None
        if self.is_lambda:
            return self.storage.save_session(session)
        return True

    def get_session_by_share_token(self, share_token: str) -> Optional[SessionState]:
        """Resolve a share token to its session, or None if not shared."""
        if not share_token:
            return None

        if self.is_lambda:
            session = self.storage.get_session_by_share_token(share_token)
        else:
            session = next(
                (s for s in self.sessions.values() if s.share_token == share_token),
                None,
            )

        # A stale index entry (or a revoked share) must not serve content.
        if session and not session.is_public:
            return None
        return session

    def list_public_sessions(self, limit: int = 1000) -> List[SessionState]:
        """List publicly shared sessions, newest first. Backs the share sitemap."""
        if self.is_lambda:
            sessions = self.storage.list_public_sessions(limit=limit)
        else:
            sessions = [s for s in self.sessions.values() if s.is_public]

        sessions.sort(key=lambda s: s.shared_at or datetime.min.replace(tzinfo=timezone.utc), reverse=True)
        return sessions[:limit]

    def increment_share_views(self, session_id: str) -> None:
        """Bump the view counter. Best-effort: never fail a page load over it."""
        try:
            session = self.get_session(session_id)
            if not session:
                return
            session.share_view_count += 1
            if self.is_lambda:
                self.storage.save_session(session)
        except Exception as e:
            logger.warning(f"Could not record share view for {session_id}: {e}")

    def set_review_status(
        self,
        session_id: str,
        status: str,
        error: Optional[str] = None,
        reviewed_diagram_revision: Optional[int] = None,
    ) -> bool:
        """Update architecture review generation status."""
        session = self.get_session(session_id)
        if not session:
            return False

        session.review_status.status = status
        session.review_status.error = error
        if reviewed_diagram_revision is not None:
            session.review_status.reviewed_diagram_revision = reviewed_diagram_revision

        if status == "generating":
            session.review_status.started_at = time.time()
            session.review_status.completed_at = None
        elif status in ("completed", "failed"):
            session.review_status.completed_at = time.time()

        if self.is_lambda:
            return self.storage.save_session(session)
        return True

    def update_review(self, session_id: str, review: dict) -> bool:
        """Store a completed architecture review, stamped with the reviewed revision."""
        session = self.get_session(session_id)
        if not session:
            return False
        session.review = review
        session.review_status.reviewed_diagram_revision = session.diagram_revision
        if self.is_lambda:
            return self.storage.save_session(session)
        return True

    def set_iac_status(
        self,
        session_id: str,
        status: str,
        target: Optional[str] = None,
        error: Optional[str] = None,
    ) -> bool:
        """Update Infrastructure-as-Code generation status."""
        session = self.get_session(session_id)
        if not session:
            return False

        session.iac_status.status = status
        session.iac_status.error = error
        if target is not None:
            session.iac_status.target = target

        if status == "generating":
            session.iac_status.started_at = time.time()
            session.iac_status.completed_at = None
        elif status in ("completed", "failed"):
            session.iac_status.completed_at = time.time()

        if self.is_lambda:
            return self.storage.save_session(session)
        return True

    def store_iac_artifact(self, session_id: str, target: str, artifact: dict) -> bool:
        """Store generated IaC for one target, stamped with the source revision.

        Stamping lets the UI tell the user their Terraform was generated from an
        older diagram instead of silently handing them stale files.
        """
        session = self.get_session(session_id)
        if not session:
            return False
        artifact = {**artifact, "diagram_revision": session.diagram_revision}
        session.iac_artifacts[target] = artifact
        if self.is_lambda:
            return self.storage.save_session(session)
        return True

    def _maybe_schedule_sync(
        self,
        session: SessionState,
        side: str,
        provenance: str,
        old_diagram: Optional[Diagram] = None,
        new_diagram: Optional[Diagram] = None,
    ) -> None:
        """Hand off to SyncEngine.schedule. Imported lazily to avoid a circular import."""
        try:
            from app.sync.engine import schedule
            schedule(session, side, provenance, old_diagram=old_diagram, new_diagram=new_diagram)
        except Exception as e:
            logger.exception(f"_maybe_schedule_sync failed: {e}")

    def update_sync_status(self, session_id: str, **fields) -> bool:
        """Update fields on session.sync_status. Pass only the fields you want to change.

        Any field passed (including with a None value) overwrites the existing value.
        Fields not passed are left untouched.
        """
        session = self.get_session(session_id)
        if not session:
            return False
        valid = {"state", "direction", "sync_due_at", "started_at", "error", "completed_at", "last_run_summary"}
        for name, value in fields.items():
            if name in valid:
                setattr(session.sync_status, name, value)
        if self.is_lambda:
            return self.storage.save_session(session)
        return True

    def mark_sync_succeeded(
        self,
        session_id: str,
        diagram_revision: int,
        design_doc_revision: int,
        summary: str,
    ) -> bool:
        """Record a successful sync run. Bumps last_synced_* and resets failure counter."""
        session = self.get_session(session_id)
        if not session:
            return False
        session.last_synced_diagram_revision = diagram_revision
        session.last_synced_design_doc_revision = design_doc_revision
        session.sync_status.state = "idle"
        session.sync_status.error = None
        session.sync_status.last_run_summary = summary
        session.sync_status.completed_at = time.time()
        session.sync_status.sync_due_at = None
        session.sync_status.consecutive_failures = 0
        if self.is_lambda:
            return self.storage.save_session(session)
        return True

    def reset_sync_failures(self, session_id: str) -> bool:
        """Clear the consecutive-failure counter that auto-disables scheduling.

        Once `consecutive_failures` hits MAX_CONSECUTIVE_FAILURES the scheduler
        stops scheduling for the session permanently. A manual "Sync now" is the
        user telling us to try again, so it clears the counter first.
        """
        session = self.get_session(session_id)
        if not session:
            return False
        session.sync_status.consecutive_failures = 0
        session.sync_status.error = None
        if self.is_lambda:
            return self.storage.save_session(session)
        return True

    def mark_sync_failed(self, session_id: str, error: str) -> bool:
        """Record a failed sync run. After MAX_CONSECUTIVE_FAILURES, scheduler stops scheduling."""
        session = self.get_session(session_id)
        if not session:
            return False
        session.sync_status.state = "failed"
        session.sync_status.error = error
        session.sync_status.completed_at = time.time()
        session.sync_status.sync_due_at = None
        session.sync_status.consecutive_failures += 1
        if self.is_lambda:
            return self.storage.save_session(session)
        return True

    def bump_last_synced_diagram_revision(self, session_id: str) -> bool:
        """Mark the current diagram_revision as already-synced. Used after design-doc generation
        so we don't immediately re-sync a freshly-generated doc against an unchanged diagram."""
        session = self.get_session(session_id)
        if not session:
            return False
        session.last_synced_diagram_revision = session.diagram_revision
        session.last_synced_design_doc_revision = session.design_doc_revision
        if self.is_lambda:
            return self.storage.save_session(session)
        return True

    def store_repo_analysis(self, session_id: str, analysis_data: dict) -> bool:
        """
        Store repository analysis results for potential re-generation.

        Args:
            session_id: Session UUID
            analysis_data: Serialized RepoAnalysis data

        Returns:
            True if store succeeded
        """
        session = self.get_session(session_id)
        if not session:
            return False

        session.repo_analysis = analysis_data

        # Save updated session
        if self.is_lambda:
            return self.storage.save_session(session)
        return True


# Global session manager instance
session_manager = SessionManager()
