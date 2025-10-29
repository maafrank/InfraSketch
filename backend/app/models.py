from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Literal


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


class SessionState(BaseModel):
    session_id: str
    diagram: Diagram
    messages: List[Message] = Field(default_factory=list)
    current_node: Optional[str] = None


class GenerateRequest(BaseModel):
    prompt: str


class GenerateResponse(BaseModel):
    session_id: str
    diagram: Diagram


class ChatRequest(BaseModel):
    session_id: str
    message: str
    node_id: Optional[str] = None


class ChatResponse(BaseModel):
    response: str
    diagram: Optional[Diagram] = None
