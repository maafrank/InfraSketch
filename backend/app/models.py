from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Literal
from datetime import datetime


class NodePosition(BaseModel):
    x: float
    y: float


class NodeMetadata(BaseModel):
    technology: Optional[str] = None
    notes: Optional[str] = None


class Node(BaseModel):
    id: str
    type: str  # cache, database, api, server, loadbalancer, queue, cdn, etc.
    label: str
    description: str
    inputs: List[str] = Field(default_factory=list)
    outputs: List[str] = Field(default_factory=list)
    metadata: NodeMetadata = Field(default_factory=NodeMetadata)
    position: NodePosition


class Edge(BaseModel):
    id: str
    source: str
    target: str
    label: Optional[str] = None
    type: Literal["default", "animated"] = "default"


class Diagram(BaseModel):
    nodes: List[Node]
    edges: List[Edge]


class Message(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class DesignDocStatus(BaseModel):
    """Status of design document generation."""
    status: Literal["not_started", "generating", "completed", "failed"] = "not_started"
    error: Optional[str] = None
    started_at: Optional[float] = None  # Unix timestamp
    completed_at: Optional[float] = None  # Unix timestamp


class SessionState(BaseModel):
    session_id: str
    user_id: str  # Clerk user ID - links session to authenticated user
    diagram: Diagram
    messages: List[Message] = Field(default_factory=list)
    current_node: Optional[str] = None
    design_doc: Optional[str] = None  # Markdown content for design document
    design_doc_status: DesignDocStatus = Field(default_factory=DesignDocStatus)
    model: str = "claude-haiku-4-5-20251001"  # Model used for this session
    created_at: Optional[datetime] = None  # When session was created (for sorting)
    name: Optional[str] = None  # Concise session name (e.g., "E-commerce Platform")
    name_generated: bool = False  # Prevents re-generating name once set


class GenerateRequest(BaseModel):
    prompt: str
    model: Optional[str] = None  # Model to use (defaults to Haiku if not specified)


class GenerateResponse(BaseModel):
    session_id: str
    diagram: Diagram


class ChatRequest(BaseModel):
    session_id: str
    message: str
    node_id: Optional[str] = None
    model: Optional[str] = None  # Allow changing model mid-session


class ChatResponse(BaseModel):
    response: str
    diagram: Optional[Diagram] = None
    design_doc: Optional[str] = None  # Updated design document content
