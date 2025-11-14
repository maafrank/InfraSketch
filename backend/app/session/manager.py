from typing import Dict, Optional
import os
import uuid
import time
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

        # Track session ownership by client identifier
        self.session_owners: Dict[str, str] = {}  # {session_id: client_id}

    def create_session(self, diagram: Diagram, client_id: Optional[str] = None) -> str:
        """Create a new session with initial diagram."""
        session_id = str(uuid.uuid4())
        session = SessionState(
            session_id=session_id,
            diagram=diagram,
            messages=[],
            current_node=None
        )

        # Save to appropriate storage
        if self.is_lambda:
            self.storage.save_session(session)
        else:
            self.sessions[session_id] = session

        # Track ownership if client_id provided
        if client_id:
            self.session_owners[session_id] = client_id

        return session_id

    def get_session(self, session_id: str, client_id: Optional[str] = None) -> Optional[SessionState]:
        """
        Retrieve session by ID.

        If client_id is provided and ownership is tracked, validates ownership.
        Returns None if session doesn't exist or client doesn't own it.
        """
        # Get from appropriate storage
        if self.is_lambda:
            session = self.storage.get_session(session_id)
        else:
            session = self.sessions.get(session_id)

        if not session:
            return None

        # If ownership tracking is enabled and client_id provided
        if client_id and session_id in self.session_owners:
            if self.session_owners[session_id] != client_id:
                # Client doesn't own this session
                return None

        return session

    def verify_ownership(self, session_id: str, client_id: str) -> bool:
        """Check if client owns the session."""
        if session_id not in self.session_owners:
            # No ownership tracked, allow access
            return True
        return self.session_owners.get(session_id) == client_id

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


# Global session manager instance
session_manager = SessionManager()
