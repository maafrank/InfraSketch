"""
Hybrid state model for InfraSketch agent.

Combines message-based conversation tracking (using LangGraph reducers)
with direct field access for structured artifacts (diagram, design_doc).
"""

from dataclasses import dataclass, field
from typing import Annotated, Sequence, Optional
from langchain_core.messages import AnyMessage
from langgraph.graph import add_messages

from app.models import Diagram


@dataclass(kw_only=True)
class InfraSketchState:
    """
    Hybrid state for InfraSketch agent.

    Uses LangGraph's add_messages reducer for automatic conversation management
    while keeping structured artifacts as direct fields for clarity.
    """

    # Message-based conversation (automatic history via reducer)
    messages: Annotated[Sequence[AnyMessage], add_messages] = field(
        default_factory=list
    )

    # Structured artifacts (direct field access)
    diagram: Optional[Diagram] = None
    design_doc: Optional[str] = None

    # Metadata
    session_id: str = ""
    model: str = "claude-haiku-4-5"

    # Optional context
    node_id: Optional[str] = None  # For node-focused conversations
