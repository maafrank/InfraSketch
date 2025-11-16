"""
Tool schemas for agent-driven diagram modifications.

These tools allow the AI agent to make granular changes to diagrams
instead of regenerating the entire JSON structure.
"""

from pydantic import BaseModel, Field
from typing import Literal, List, Union, Optional


class AddNodeTool(BaseModel):
    """
    Add a new component/node to the system architecture diagram.

    Use this tool when the user wants to introduce a new component to their system design,
    such as adding a cache layer, load balancer, database, API service, or any other
    infrastructure component. This tool creates the node but does NOT create any connections
    to other nodes - you must use add_edge separately to connect this node to others.
    Returns the updated diagram with the new node included.

    IMPORTANT: Generate a unique, descriptive node_id for NEW nodes (e.g., 'redis-cache-1',
    'api-gateway-lb-1'). Do NOT use generic IDs like 'node-123'.
    """
    action: Literal["add_node"] = "add_node"
    node_id: str = Field(
        ...,
        description="Unique identifier for the new node. Must be descriptive and unique across "
                    "the entire diagram (e.g., 'redis-cache-1', 'user-service-lb'). Use lowercase "
                    "with hyphens. This is NOT the display name - it's the internal ID."
    )
    type: str = Field(
        ...,
        description="Component type category. Must be one of: cache, database, api, server, "
                    "loadbalancer, queue, cdn, gateway, storage, service. This determines the "
                    "visual appearance (color/icon) of the node in the diagram."
    )
    label: str = Field(
        ...,
        description="Human-readable display name shown on the diagram (e.g., 'Redis Cache', "
                    "'PostgreSQL Database', 'API Gateway Load Balancer'). This is what users see."
    )
    description: str = Field(
        ...,
        description="Detailed explanation of what this component does in the system, its purpose, "
                    "and why it's needed. Should be 1-2 sentences. Example: 'In-memory cache to "
                    "reduce database load and improve read performance for frequently accessed data.'"
    )
    technology: str = Field(
        ...,
        description="Specific technology, product, or implementation (e.g., 'Redis 7.0', "
                    "'PostgreSQL 15', 'NGINX', 'AWS Application Load Balancer'). Be specific - "
                    "not just 'database' but 'PostgreSQL 15' or 'MongoDB 6.0'."
    )
    position: dict = Field(
        ...,
        description="Visual position on the diagram as {x: float, y: float}. Use logical positioning: "
                    "entry points (x: 0-200), middle tier services (x: 300-600), data layer (x: 700-1000). "
                    "Vertical position (y) should separate parallel components. The auto-layout will adjust "
                    "these, so approximate positioning is fine."
    )
    inputs: List[str] = Field(
        default_factory=list,
        description="Optional list of input descriptions (e.g., ['User requests', 'API calls']). "
                    "Can be empty list if not applicable."
    )
    outputs: List[str] = Field(
        default_factory=list,
        description="Optional list of output descriptions (e.g., ['Cached data', 'Cache miss signals']). "
                    "Can be empty list if not applicable."
    )
    notes: Optional[str] = Field(
        None,
        description="Optional additional implementation details, configuration notes, or caveats "
                    "(e.g., 'Requires minimum 3 instances for HA', 'Consider sharding for >1M users')"
    )


class DeleteNodeTool(BaseModel):
    """
    Remove a component/node from the system architecture diagram.

    Use this tool when the user wants to remove an existing component from their system design.
    This tool automatically deletes ALL edges (connections) that are connected to this node,
    so you do NOT need to manually delete edges first. Returns the updated diagram without the node.

    CRITICAL: You MUST use the EXACT node_id from the "Nodes (with exact IDs)" section in the
    diagram context. Do NOT guess or make up node IDs. If unsure about the node_id, ask the user.
    """
    action: Literal["delete_node"] = "delete_node"
    node_id: str = Field(
        ...,
        description="The EXACT ID of the node to delete, as shown in the 'Nodes (with exact IDs)' "
                    "section above. Example: if the context shows 'id: `redis-cache-1`', use exactly "
                    "'redis-cache-1'. All edges connected to this node will be automatically removed."
    )


class UpdateNodeTool(BaseModel):
    """
    Update properties of an existing component/node in the diagram.

    Use this tool when the user wants to modify an existing component without removing it,
    such as changing the technology stack (PostgreSQL → MongoDB), updating the display name,
    modifying the description, or changing the component type. This tool only updates the
    specific fields you provide - all other fields remain unchanged. Returns the updated diagram.

    CRITICAL: You MUST use the EXACT node_id from the "Nodes (with exact IDs)" section in the
    diagram context. Do NOT guess or make up node IDs. If unsure about the node_id, ask the user.
    """
    action: Literal["update_node"] = "update_node"
    node_id: str = Field(
        ...,
        description="The EXACT ID of the node to update, as shown in the 'Nodes (with exact IDs)' "
                    "section above. Example: if the context shows 'id: `postgres-db-1`', use exactly "
                    "'postgres-db-1'. This is required - you cannot update a node without knowing its ID."
    )
    label: Optional[str] = Field(
        None,
        description="New human-readable display name for the component (e.g., 'MongoDB Database', "
                    "'Redis Cache Layer'). Only provide this if the user wants to change the label. "
                    "If not provided, the existing label remains unchanged."
    )
    description: Optional[str] = Field(
        None,
        description="New detailed explanation of what this component does. Should be 1-2 sentences. "
                    "Example: 'NoSQL document database for flexible schema and horizontal scalability.' "
                    "Only provide if the user wants to update the description."
    )
    technology: Optional[str] = Field(
        None,
        description="New specific technology or implementation (e.g., 'MongoDB 6.0', 'Redis 7.2', "
                    "'AWS Application Load Balancer'). Be specific - not just 'database' but "
                    "'PostgreSQL 15' or 'MongoDB 6.0'. Only provide if changing technology."
    )
    type: Optional[str] = Field(
        None,
        description="New component type category. Must be one of: cache, database, api, server, "
                    "loadbalancer, queue, cdn, gateway, storage, service. This changes the visual "
                    "appearance (color/icon) in the diagram. Only provide if changing the component type."
    )
    notes: Optional[str] = Field(
        None,
        description="New additional implementation details or configuration notes (e.g., 'Requires "
                    "minimum 3 instances for HA', 'Sharding enabled for >1M users'). Only provide "
                    "if adding or updating notes."
    )


class AddEdgeTool(BaseModel):
    """
    Create a new connection (edge) between two existing nodes in the diagram.

    Use this tool when the user wants to establish a data flow or relationship between two components,
    such as connecting an API to a database, linking a load balancer to backend servers, or showing
    message flow from a queue to a worker. The edge represents what flows between the nodes (data,
    requests, messages, etc.). Both source and target nodes must already exist in the diagram - if they
    don't, use add_node first to create them. Returns the updated diagram with the new connection.

    CRITICAL: You MUST use the EXACT node IDs from the "Nodes (with exact IDs)" section for source
    and target parameters. Do NOT guess or make up node IDs. If the nodes don't exist, this operation
    will be skipped gracefully with a warning.
    """
    action: Literal["add_edge"] = "add_edge"
    edge_id: str = Field(
        ...,
        description="Unique identifier for this edge. Must be descriptive and unique across the entire "
                    "diagram (e.g., 'api-to-cache', 'lb-to-backend-1', 'queue-to-worker'). Use lowercase "
                    "with hyphens. Follow pattern: 'source-to-target' or 'source-to-target-N' for clarity."
    )
    source: str = Field(
        ...,
        description="The EXACT ID of the source node where the connection starts, as shown in the "
                    "'Nodes (with exact IDs)' section. Example: if the context shows 'id: `api-server-1`', "
                    "use exactly 'api-server-1'. This node must already exist in the diagram."
    )
    target: str = Field(
        ...,
        description="The EXACT ID of the target node where the connection ends, as shown in the "
                    "'Nodes (with exact IDs)' section. Example: if the context shows 'id: `redis-cache-1`', "
                    "use exactly 'redis-cache-1'. This node must already exist in the diagram."
    )
    label: str = Field(
        ...,
        description="Human-readable description of WHAT flows through this connection. Be specific about "
                    "the data/requests being transmitted, not just 'connects to'. Examples: 'User authentication "
                    "requests', 'Cached user data', 'Database query results', 'Async job messages'. This helps "
                    "viewers understand the system's data flow."
    )
    type: Literal["default", "animated"] = Field(
        "default",
        description="Visual style of the edge. Use 'default' for most connections. Use 'animated' for "
                    "real-time or streaming data flows to emphasize high-frequency communication (e.g., "
                    "WebSocket connections, event streams, message queues)."
    )


class DeleteEdgeTool(BaseModel):
    """
    Remove a connection (edge) between nodes in the diagram.

    Use this tool when the user wants to eliminate a data flow or relationship between components,
    such as removing a direct API-to-database connection when adding a cache layer in between,
    or deleting obsolete connections when restructuring the architecture. This tool only removes
    the connection - the nodes themselves remain in the diagram. Returns the updated diagram without
    the deleted edge.

    CRITICAL: You MUST use the EXACT edge_id from the "Connections (with exact edge IDs)" section
    in the diagram context. Do NOT guess or make up edge IDs. If the edge doesn't exist or was
    already deleted, this operation will be skipped gracefully with a warning (not treated as an error).

    WARNING: When adding a load balancer BEFORE a node, only delete edges going INTO that node.
    DO NOT delete edges going OUT FROM that node, or you will disconnect the graph! For example,
    if adding LB before API that connects to Database:
    - ✓ Delete: Client → API (incoming edge)
    - ✓ Add: Client → LB, LB → API
    - ✗ DO NOT delete: API → Database (outgoing edge - must be preserved!)
    """
    action: Literal["delete_edge"] = "delete_edge"
    edge_id: str = Field(
        ...,
        description="The EXACT ID of the edge to delete, as shown in the 'Connections (with exact edge IDs)' "
                    "section above. Example: if the context shows 'id: `api-to-db-direct`', use exactly "
                    "'api-to-db-direct'. If the edge doesn't exist, the operation will be skipped gracefully "
                    "(this is useful when removing connections that may have already been deleted)."
    )


# Union type for all possible tools
ToolType = Union[AddNodeTool, DeleteNodeTool, UpdateNodeTool, AddEdgeTool, DeleteEdgeTool]


class ToolInvocation(BaseModel):
    """
    Container for tool invocations and explanation.

    The agent returns this structure when modifying the diagram.
    """
    tools: List[ToolType] = Field(..., description="List of tools to execute in order")
    explanation: str = Field(..., description="Human-readable explanation of what changed")


# Orchestration pattern examples for the agent prompt
ORCHESTRATION_EXAMPLES = """
ORCHESTRATION PATTERNS:

**Pattern 1: Adding a new component between existing components**
Example: "Add Redis cache between API and PostgreSQL"
Steps:
1. add_node - Create the new cache node
2. add_edge - Connect API → Cache
3. add_edge - Connect Cache → Database
4. delete_edge - Remove old direct API → Database connection

JSON output:
{
  "tools": [
    {
      "action": "add_node",
      "node_id": "redis-cache-1",
      "type": "cache",
      "label": "Redis Cache",
      "description": "In-memory cache to reduce database load",
      "technology": "Redis 7.0",
      "position": {"x": 400, "y": 300}
    },
    {
      "action": "add_edge",
      "edge_id": "api-to-cache",
      "source": "api-server-1",
      "target": "redis-cache-1",
      "label": "Query with cache key"
    },
    {
      "action": "add_edge",
      "edge_id": "cache-to-db",
      "source": "redis-cache-1",
      "target": "postgres-1",
      "label": "Cache miss query"
    },
    {
      "action": "delete_edge",
      "edge_id": "api-to-db-direct"
    }
  ],
  "explanation": "Added Redis cache layer between API and database to improve read performance. API now checks cache first, only querying database on cache misses."
}

**Pattern 2: Removing a component**
Example: "Remove the load balancer"
Steps:
1. Find connections TO the load balancer
2. Find connections FROM the load balancer
3. Delete all edges connected to it
4. Delete the node
5. (Optional) Add new direct connection to bridge the gap

JSON output:
{
  "tools": [
    {
      "action": "delete_edge",
      "edge_id": "client-to-lb"
    },
    {
      "action": "delete_edge",
      "edge_id": "lb-to-api"
    },
    {
      "action": "add_edge",
      "edge_id": "client-to-api-direct",
      "source": "web-client-1",
      "target": "api-server-1",
      "label": "HTTP requests"
    },
    {
      "action": "delete_node",
      "node_id": "load-balancer-1"
    }
  ],
  "explanation": "Removed load balancer and connected client directly to API server. This simplifies the architecture for single-server deployments."
}

**Pattern 3: Replacing a technology**
Example: "Switch from PostgreSQL to MongoDB"
Steps:
1. update_node - Change the database node's technology and description

JSON output:
{
  "tools": [
    {
      "action": "update_node",
      "node_id": "database-1",
      "label": "MongoDB Database",
      "description": "NoSQL document database for flexible schema",
      "technology": "MongoDB 6.0",
      "type": "database"
    }
  ],
  "explanation": "Switched database from PostgreSQL to MongoDB for flexible schema and horizontal scalability."
}

**Pattern 4: Adding a new microservice with multiple connections**
Example: "Add an authentication service"
Steps:
1. add_node - Create the auth service
2. add_edge - Connect API → Auth (for validation)
3. add_edge - Connect Auth → User DB (for credential lookup)

JSON output:
{
  "tools": [
    {
      "action": "add_node",
      "node_id": "auth-service-1",
      "type": "service",
      "label": "Authentication Service",
      "description": "Handles user authentication and JWT token generation",
      "technology": "Node.js + Passport.js",
      "position": {"x": 500, "y": 200},
      "inputs": ["Username/password", "JWT validation requests"],
      "outputs": ["JWT tokens", "Authentication status"]
    },
    {
      "action": "add_edge",
      "edge_id": "api-to-auth",
      "source": "api-server-1",
      "target": "auth-service-1",
      "label": "Validate JWT token"
    },
    {
      "action": "add_edge",
      "edge_id": "auth-to-userdb",
      "source": "auth-service-1",
      "target": "user-database-1",
      "label": "Query user credentials"
    }
  ],
  "explanation": "Added dedicated authentication service to handle user login and JWT token validation, separating auth logic from main API."
}

**Pattern 5: Adding parallel processing with a queue**
Example: "Add a message queue for async job processing"
Steps:
1. add_node - Create the queue
2. add_node - Create the worker service
3. add_edge - Connect API → Queue (publish jobs)
4. add_edge - Connect Queue → Worker (consume jobs)

JSON output:
{
  "tools": [
    {
      "action": "add_node",
      "node_id": "job-queue-1",
      "type": "queue",
      "label": "Job Queue",
      "description": "Message queue for asynchronous task processing",
      "technology": "RabbitMQ 3.11",
      "position": {"x": 300, "y": 400}
    },
    {
      "action": "add_node",
      "node_id": "worker-service-1",
      "type": "service",
      "label": "Background Worker",
      "description": "Processes async jobs from the queue",
      "technology": "Python + Celery",
      "position": {"x": 500, "y": 400}
    },
    {
      "action": "add_edge",
      "edge_id": "api-to-queue",
      "source": "api-server-1",
      "target": "job-queue-1",
      "label": "Publish async jobs"
    },
    {
      "action": "add_edge",
      "edge_id": "queue-to-worker",
      "source": "job-queue-1",
      "target": "worker-service-1",
      "label": "Consume and process jobs"
    }
  ],
  "explanation": "Added message queue and worker service to handle time-consuming tasks asynchronously, preventing API timeout issues."
}

IMPORTANT RULES:
1. Always generate unique, descriptive node_ids (e.g., 'redis-cache-1', not 'node-123')
2. Always generate unique, descriptive edge_ids (e.g., 'api-to-cache', not 'edge-1')
3. Edge labels should describe WHAT flows, not just "connects to" (e.g., "User authentication requests")
4. Position nodes logically - estimate x/y based on their role in the data flow
   - Entry points (clients, gateways): x: 0-200
   - Middle tier (APIs, services): x: 300-600
   - Data layer (databases, caches): x: 700-1000
   - Vertical spacing: y: 100, 200, 300, etc. (separate parallel components)
5. When adding nodes between existing nodes, position them midway
6. Use specific technologies, not generic (e.g., "PostgreSQL 15" not "SQL database")
7. Execute tools in the right order:
   - Delete edges BEFORE deleting nodes (avoid orphaned edges)
   - Create nodes BEFORE creating edges to them (avoid dangling references)
8. Include explanation field describing the high-level change
"""
