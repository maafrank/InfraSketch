from typing import Dict, Optional
import uuid
from app.models import SessionState, Diagram, Message


class SessionManager:
    def __init__(self):
        self.sessions: Dict[str, SessionState] = {}

    def create_session(self, diagram: Diagram) -> str:
        """Create a new session with initial diagram."""
        session_id = str(uuid.uuid4())
        self.sessions[session_id] = SessionState(
            session_id=session_id,
            diagram=diagram,
            messages=[],
            current_node=None
        )
        return session_id

    def get_session(self, session_id: str) -> Optional[SessionState]:
        """Retrieve session by ID."""
        return self.sessions.get(session_id)

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
