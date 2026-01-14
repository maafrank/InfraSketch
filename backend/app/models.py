from pydantic import BaseModel, Field, field_validator
from typing import List, Optional, Dict, Any, Literal
from datetime import datetime


# Security: Define allowed node types as Literal to prevent arbitrary values
NodeType = Literal[
    "cache", "database", "api", "server", "loadbalancer", "queue",
    "cdn", "gateway", "storage", "service", "client", "user",
    "function", "container", "kubernetes", "cloud", "network",
    "security", "monitoring", "analytics", "ml", "iot", "blockchain",
    "group"  # For collapsible groups
]


class NodePosition(BaseModel):
    x: float
    y: float


class NodeMetadata(BaseModel):
    # Security: Add max_length constraints to prevent memory exhaustion
    technology: Optional[str] = Field(default=None, max_length=200)
    notes: Optional[str] = Field(default=None, max_length=5000)
    child_types: Optional[List[str]] = None  # For group nodes: types of children for color blending


class Node(BaseModel):
    # Security: Add max_length constraints to all string fields
    id: str = Field(..., max_length=100)
    type: str = Field(..., max_length=50)  # Keep as str for backwards compatibility, validate separately
    label: str = Field(..., max_length=200)
    description: str = Field(..., max_length=5000)
    inputs: List[str] = Field(default_factory=list)
    outputs: List[str] = Field(default_factory=list)
    metadata: NodeMetadata = Field(default_factory=NodeMetadata)
    position: NodePosition = Field(default_factory=lambda: NodePosition(x=0, y=0))

    # Collapsible group fields
    parent_id: Optional[str] = Field(default=None, max_length=100)
    is_group: bool = False  # True if this node can contain children
    is_collapsed: bool = False  # True if children are hidden (only relevant if is_group=True)
    child_ids: List[str] = Field(default_factory=list)  # IDs of child nodes

    @field_validator('type')
    @classmethod
    def validate_node_type(cls, v: str) -> str:
        """Validate node type against allowed values, with fallback for unknown types."""
        allowed_types = {
            "cache", "database", "api", "server", "loadbalancer", "queue",
            "cdn", "gateway", "storage", "service", "client", "user",
            "function", "container", "kubernetes", "cloud", "network",
            "security", "monitoring", "analytics", "ml", "iot", "blockchain",
            "group"
        }
        # Allow unknown types but log them (for forward compatibility)
        # This prevents breaking if Claude suggests a new type
        if v.lower() not in allowed_types:
            # Accept but normalize - could add logging here if needed
            pass
        return v.lower() if v else "service"  # Default to service


class Edge(BaseModel):
    # Security: Add max_length constraints
    id: str = Field(..., max_length=100)
    source: str = Field(..., max_length=100)
    target: str = Field(..., max_length=100)
    label: Optional[str] = Field(default=None, max_length=500)
    type: Literal["default", "animated"] = "default"


class Diagram(BaseModel):
    nodes: List[Node]
    edges: List[Edge]


class Message(BaseModel):
    role: Literal["user", "assistant"]
    # Security: Limit message content to prevent memory exhaustion
    content: str = Field(..., max_length=50000)  # 50KB max per message


class DesignDocStatus(BaseModel):
    """Status of design document generation."""
    status: Literal["not_started", "generating", "completed", "failed"] = "not_started"
    error: Optional[str] = None
    started_at: Optional[float] = None  # Unix timestamp
    completed_at: Optional[float] = None  # Unix timestamp


class DiagramGenerationStatus(BaseModel):
    """Status of diagram generation (for async polling)."""
    status: Literal["not_started", "generating", "completed", "failed"] = "not_started"
    error: Optional[str] = None
    started_at: Optional[float] = None  # Unix timestamp
    completed_at: Optional[float] = None  # Unix timestamp


class SessionState(BaseModel):
    # Security: Add max_length constraints
    session_id: str = Field(..., max_length=100)
    user_id: str = Field(..., max_length=100)  # Clerk user ID - links session to authenticated user
    diagram: Diagram
    messages: List[Message] = Field(default_factory=list)
    current_node: Optional[str] = Field(default=None, max_length=100)
    design_doc: Optional[str] = Field(default=None, max_length=500000)  # 500KB max for design doc
    design_doc_status: DesignDocStatus = Field(default_factory=DesignDocStatus)
    diagram_generation_status: DiagramGenerationStatus = Field(default_factory=DiagramGenerationStatus)  # For async diagram generation
    generation_prompt: Optional[str] = Field(default=None, max_length=10000)  # Store prompt for background task
    model: str = Field(default="claude-haiku-4-5-20251001", max_length=100)  # Model used for this session
    created_at: Optional[datetime] = None  # When session was created (for sorting)
    name: Optional[str] = Field(default=None, max_length=200)  # Concise session name (e.g., "E-commerce Platform")
    name_generated: bool = False  # Prevents re-generating name once set


class GenerateRequest(BaseModel):
    # Security: Limit prompt size to prevent token exhaustion attacks
    prompt: str = Field(..., max_length=10000)  # 10KB max prompt
    model: Optional[str] = Field(default=None, max_length=100)  # Model to use (defaults to Haiku if not specified)


class GenerateResponse(BaseModel):
    session_id: str
    diagram: Diagram


class ChatRequest(BaseModel):
    # Security: Add max_length constraints
    session_id: str = Field(..., max_length=100)
    message: str = Field(..., max_length=10000)  # 10KB max message
    node_id: Optional[str] = Field(default=None, max_length=100)
    model: Optional[str] = Field(default=None, max_length=100)  # Allow changing model mid-session


class ChatResponse(BaseModel):
    response: str
    diagram: Optional[Diagram] = None
    design_doc: Optional[str] = None  # Updated design document content
    suggestions: List[str] = Field(default_factory=list)  # AI-generated follow-up suggestions


class CreateGroupRequest(BaseModel):
    child_node_ids: List[str]  # Node IDs to merge into a group


class CreateGroupResponse(BaseModel):
    diagram: Diagram
    group_id: str
