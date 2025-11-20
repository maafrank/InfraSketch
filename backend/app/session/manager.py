from typing import Dict, Optional, List
import os
import uuid
import time
from datetime import datetime
from app.models import SessionState, Diagram, Message, DesignDocStatus


class SessionManager:
    def __init__(self):
        # Detect if running in Lambda
        self.is_lambda = os.environ.get('AWS_LAMBDA_FUNCTION_NAME') is not None

        if self.is_lambda:
            # Use DynamoDB for persistent storage in Lambda
            print("SessionManager: Using DynamoDB storage (Lambda environment)")
            from app.session.dynamodb_storage import DynamoDBSessionStorage
            self.storage = DynamoDBSessionStorage()
        else:
            # Use in-memory storage for local development
            print("SessionManager: Using in-memory storage (local environment)")
            self.sessions: Dict[str, SessionState] = {}
            self.storage = None

    def create_session(self, diagram: Diagram, user_id: str, model: str = "claude-haiku-4-5-20251001") -> str:
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
            created_at=datetime.now()
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
        sessions.sort(key=lambda s: s.created_at or datetime.min, reverse=True)
        return sessions

    def update_diagram(self, session_id: str, diagram: Diagram) -> bool:
        """Update diagram for a session."""
        session = self.get_session(session_id)
        if not session:
            return False
        session.diagram = diagram

        # Save updated session
        if self.is_lambda:
            return self.storage.save_session(session)
        return True

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
        """Update design document content for a session."""
        session = self.get_session(session_id)
        if not session:
            return False
        session.design_doc = design_doc

        # Save updated session
        if self.is_lambda:
            return self.storage.save_session(session)
        return True

    def set_design_doc_status(self, session_id: str, status: str, error: Optional[str] = None) -> bool:
        """Update design document generation status."""
        session = self.get_session(session_id)
        if not session:
            return False

        session.design_doc_status.status = status
        session.design_doc_status.error = error

        if status == "generating" and not session.design_doc_status.started_at:
            session.design_doc_status.started_at = time.time()
        elif status in ["completed", "failed"]:
            session.design_doc_status.completed_at = time.time()

        # Save updated session
        if self.is_lambda:
            return self.storage.save_session(session)
        return True

    def get_design_doc_status(self, session_id: str) -> Optional[DesignDocStatus]:
        """Get current design document generation status."""
        session = self.get_session(session_id)
        if not session:
            return None
        return session.design_doc_status

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


# Global session manager instance
session_manager = SessionManager()
