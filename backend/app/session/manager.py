from typing import Dict, Optional
import uuid
from app.models import SessionState, Diagram, Message


class SessionManager:
    def __init__(self):
        self.sessions: Dict[str, SessionState] = {}
        # Track session ownership by client identifier
        self.session_owners: Dict[str, str] = {}  # {session_id: client_id}

    def create_session(self, diagram: Diagram, client_id: Optional[str] = None) -> str:
        """Create a new session with initial diagram."""
        session_id = str(uuid.uuid4())
        self.sessions[session_id] = SessionState(
            session_id=session_id,
            diagram=diagram,
            messages=[],
            current_node=None
        )
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
        return True

    def add_message(self, session_id: str, message: Message) -> bool:
        """Add message to session history."""
        session = self.get_session(session_id)
        if not session:
            return False
        session.messages.append(message)
        return True

    def set_current_node(self, session_id: str, node_id: Optional[str]) -> bool:
        """Set the currently focused node."""
        session = self.get_session(session_id)
        if not session:
            return False
        session.current_node = node_id
        return True


# Global session manager instance
session_manager = SessionManager()
