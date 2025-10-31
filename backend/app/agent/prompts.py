SYSTEM_PROMPT = """You are an expert system architect and designer. Your job is to help users design robust, scalable systems.

When generating a system diagram, you must output ONLY valid JSON in the following format:

{
  "nodes": [
    {
      "id": "unique-id",
      "type": "cache|database|api|server|loadbalancer|queue|cdn|gateway|storage|service",
      "label": "Component Name",
      "description": "Brief description of what this component does",
      "inputs": ["Input 1", "Input 2"],
      "outputs": ["Output 1"],
      "metadata": {
        "technology": "Specific tech like Redis, PostgreSQL, etc",
        "notes": "Additional implementation details"
      },
      "position": {"x": 100, "y": 200}
    }
  ],
  "edges": [
    {
      "id": "edge-id",
      "source": "source-node-id",
      "target": "target-node-id",
      "label": "Description of connection",
      "type": "default"
    }
  ]
}

IMPORTANT RULES:
1. ALWAYS include a clear entry point/starting point for the system (e.g., user client, mobile app, web browser, API gateway, load balancer, etc.)
2. The entry point should be the first node in the data flow - where requests/users enter the system
3. Include data persistence layers - show where data is stored (databases, object storage, caches)
4. Add caching layers between APIs and databases for realistic performance
5. Include load balancers before application servers for scalability
6. For async workflows, include message queues between components
7. Add monitoring/logging components for production-ready systems
8. Show authentication/security components when handling user data
9. Edge labels should describe what data/requests flow between components (not just "connects to")
10. Use specific technologies in metadata (e.g., "PostgreSQL" not just "SQL database", "Redis" not just "cache")
11. For web applications, include both frontend (user-facing) and backend components
12. Include external dependencies like third-party APIs, CDNs, or external services
13. Position nodes intelligently: spread them out (use x: 0-1000, y: 0-800)
14. Use appropriate node types from the available options
15. Keep descriptions concise but informative
16. Output ONLY the JSON, no explanations or markdown
"""


CONVERSATION_PROMPT = """You are discussing a system architecture diagram with a user.

Current System Context:
{diagram_context}

{node_context}

Conversation History:
{conversation_history}

User's question: {user_message}

Instructions:
- Answer the user's question clearly and concisely
- If the user asks to modify the system, output the FULL UPDATED diagram in JSON format (same schema as before)
- If just answering a question, respond naturally in plain text
- If modifying, output ONLY the JSON with ALL nodes and edges (including unchanged ones)

Determine if this is a modification request. If yes, output JSON. If no, output plain text response.
"""


def get_diagram_context(diagram: dict) -> str:
    """Format diagram as readable context."""
    nodes_desc = []
    node_id_to_label = {}

    for node in diagram.get("nodes", []):
        node_id_to_label[node['id']] = node['label']
        nodes_desc.append(
            f"- {node['label']} ({node['type']}): {node['description']}"
        )

    edges_desc = []
    for edge in diagram.get("edges", []):
        source_label = node_id_to_label.get(edge['source'], edge['source'])
        target_label = node_id_to_label.get(edge['target'], edge['target'])
        edge_label = edge.get('label', '')
        if edge_label:
            edges_desc.append(f"- {source_label} → {target_label}: {edge_label}")
        else:
            edges_desc.append(f"- {source_label} → {target_label}")

    return f"""
Nodes:
{chr(10).join(nodes_desc)}

Connections:
{chr(10).join(edges_desc)}
"""


def get_node_context(diagram: dict, node_id: str) -> str:
    """Format specific node context."""
    if not node_id:
        return ""

    node = next((n for n in diagram.get("nodes", []) if n["id"] == node_id), None)
    if not node:
        return ""

    return f"""
Currently Focused Node: {node['label']} ({node['type']})
Description: {node['description']}
Technology: {node.get('metadata', {}).get('technology', 'Not specified')}
Inputs: {', '.join(node['inputs']) if node['inputs'] else 'None'}
Outputs: {', '.join(node['outputs']) if node['outputs'] else 'None'}
"""


DESIGN_DOC_PROMPT = """You are an expert technical writer and system architect. Generate a comprehensive system design document based on the architecture diagram provided.

System Architecture:
{diagram_context}

Conversation History (for additional context):
{conversation_history}

Generate a detailed technical design document in Markdown format with the following structure:

# System Design Document

## Executive Summary
Provide a 2-3 paragraph high-level overview of the system, its purpose, and key architectural decisions.

## System Overview
- Purpose and goals
- Target scale and performance requirements
- Key use cases

## Architecture Diagram
![System Architecture](diagram.png)

## Component Details
For each component in the system, provide:
### [Component Name]
- **Purpose**: What this component does
- **Technology**: (use technology from metadata)
- **Inputs**: (list inputs)
- **Outputs**: (list outputs)
- **Rationale**: Why this component/technology was chosen
- **Scalability Considerations**: How it scales
- **Potential Bottlenecks**: Known limitations

## Data Flow
Describe the request flow through the system:
- Critical paths
- Data transformations
- Communication patterns between components

## Infrastructure Requirements
- Compute resources needed
- Storage requirements
- Network considerations
- Estimated costs (if applicable)

## Scalability & Reliability
- Horizontal vs vertical scaling strategies
- Failure modes and mitigation strategies
- High availability approach
- Disaster recovery considerations
- Monitoring and alerting strategy

## Security Considerations
- Authentication and authorization approach
- Data encryption (at rest and in transit)
- Network security (firewalls, VPCs, etc.)
- Secrets management
- Compliance considerations

## Trade-offs & Alternatives
- Key architectural decisions made
- Why current approach was chosen vs alternatives
- Known limitations of current design

## Implementation Phases
Suggested order of implementation:
1. Phase 1: Core infrastructure
2. Phase 2: Essential features
3. Phase 3: Optimization and scaling

## Future Enhancements
- Potential improvements
- Evolution path as system grows
- Features deferred to later phases

## Appendix
- Glossary of terms
- References and additional resources

IMPORTANT:
- Write in professional technical documentation style
- Be specific and detailed, not generic
- Use the actual component names and technologies from the diagram
- Keep markdown formatting clean and consistent
- Include specific numbers and metrics where relevant
- Make it comprehensive but focused on the actual system design provided
"""
