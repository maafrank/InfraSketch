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
1. Position nodes intelligently: spread them out (use x: 0-1000, y: 0-800)
2. Create meaningful connections between nodes (edges)
3. Use appropriate node types
4. Keep descriptions concise but informative
5. Output ONLY the JSON, no explanations or markdown
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
    for node in diagram.get("nodes", []):
        nodes_desc.append(
            f"- {node['label']} ({node['type']}): {node['description']}"
        )

    edges_desc = []
    for edge in diagram.get("edges", []):
        edges_desc.append(
            f"- {edge['source']} → {edge['target']}: {edge.get('label', 'connected')}"
        )

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
