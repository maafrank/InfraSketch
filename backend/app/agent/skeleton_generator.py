"""
Code skeleton generation module.
Generates boilerplate code for all components in a system diagram.
"""
import json
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage
from app.models import Diagram, CodeSkeleton
from app.utils.secrets import get_anthropic_api_key


def create_skeleton_llm():
    """Create Claude LLM instance for skeleton generation."""
    api_key = get_anthropic_api_key()
    return ChatAnthropic(
        model="claude-haiku-4-5-20251001",
        api_key=api_key,
        temperature=0.3,  # Lower temp for more consistent code structure
        max_tokens=32768,
    )


SKELETON_PROMPT = """You are an expert software architect. Given a system architecture diagram, generate boilerplate code skeletons for each component.

For each node in the diagram, create:
1. Appropriate class definitions
2. Key methods/functions with signatures
3. Data models/interfaces where relevant
4. Comments explaining the component's role

Consider:
- The component's type (API, database, cache, queue, etc.)
- Its inputs and outputs
- Connected components (for interface design)
- Common patterns for this type of component

Choose the most appropriate language for each component based on its type:
- APIs/Services: Python, JavaScript/TypeScript, Go, Java
- Databases: SQL schemas
- Queues/Streams: Configuration + consumer/producer code
- CDN/Load Balancer: Configuration files

Return a JSON object with this structure:
{{
    "node_id_1": {{
        "language": "python",
        "code": "class UserService:\\n    def authenticate(self, credentials):\\n        pass",
        "classes": ["UserService"],
        "functions": ["authenticate", "validate_token"]
    }},
    "node_id_2": {{
        "language": "javascript",
        "code": "class ApiGateway {{\\n    async routeRequest(req) {{\\n        // TODO\\n    }}\\n}}",
        "classes": ["ApiGateway"],
        "functions": ["routeRequest", "handleError"]
    }}
}}

IMPORTANT: Return ONLY valid JSON. Do not include any text before or after the JSON object.

Here is the diagram:

NODES:
{nodes}

EDGES:
{edges}
"""


def generate_code_skeletons(diagram: Diagram) -> dict[str, CodeSkeleton]:
    """
    Generate code skeletons for all nodes in the diagram.

    Args:
        diagram: The system diagram with nodes and edges

    Returns:
        Dictionary mapping node_id to CodeSkeleton
    """
    llm = create_skeleton_llm()

    # Format nodes with all relevant information
    nodes_str = "\n\n".join([
        f"ID: {node.id}\n"
        f"Type: {node.type}\n"
        f"Label: {node.label}\n"
        f"Description: {node.description}\n"
        f"Inputs: {', '.join(node.inputs) if node.inputs else 'None'}\n"
        f"Outputs: {', '.join(node.outputs) if node.outputs else 'None'}\n"
        f"Technology: {node.metadata.technology or 'Not specified'}"
        for node in diagram.nodes
    ])

    # Format edges to show connections
    edges_str = "\n".join([
        f"{edge.source} → {edge.target}" + (f" ({edge.label})" if edge.label else "")
        for edge in diagram.edges
    ])

    prompt = SKELETON_PROMPT.format(
        nodes=nodes_str,
        edges=edges_str
    )

    messages = [
        SystemMessage(content="You are an expert software architect specializing in code generation."),
        HumanMessage(content=prompt)
    ]

    print(f"\n=== GENERATING CODE SKELETONS ===")
    print(f"Number of nodes: {len(diagram.nodes)}")
    print(f"Number of edges: {len(diagram.edges)}")

    response = llm.invoke(messages)
    content = response.content.strip()

    print(f"\n=== CLAUDE RESPONSE ===")
    print(content[:500] + "..." if len(content) > 500 else content)
    print("=" * 50)

    # Parse JSON response with multiple strategies
    skeletons_data = None

    # Strategy 1: Direct JSON parse
    try:
        skeletons_data = json.loads(content)
        print("✓ Successfully parsed JSON directly")
    except json.JSONDecodeError:
        # Strategy 2: Extract from code block
        if "```json" in content:
            start = content.find("```json") + 7
            end = content.find("```", start)
            json_str = content[start:end].strip()
            try:
                skeletons_data = json.loads(json_str)
                print("✓ Successfully extracted JSON from ```json block")
            except json.JSONDecodeError:
                pass

        # Strategy 3: Find embedded JSON (find first { and matching })
        if not skeletons_data:
            start = content.find("{")
            if start != -1:
                brace_count = 0
                for i in range(start, len(content)):
                    if content[i] == "{":
                        brace_count += 1
                    elif content[i] == "}":
                        brace_count -= 1
                        if brace_count == 0:
                            json_str = content[start:i+1]
                            try:
                                skeletons_data = json.loads(json_str)
                                print("✓ Successfully extracted embedded JSON")
                            except json.JSONDecodeError:
                                pass
                            break

    if not skeletons_data:
        print("✗ Failed to extract JSON from response")
        return {}

    # Convert to CodeSkeleton objects
    result = {}
    for node_id, skeleton_data in skeletons_data.items():
        try:
            result[node_id] = CodeSkeleton(**skeleton_data)
            print(f"✓ Created skeleton for node: {node_id} ({skeleton_data.get('language', 'unknown')})")
        except Exception as e:
            print(f"✗ Failed to create skeleton for {node_id}: {e}")

    print(f"\n=== GENERATION COMPLETE ===")
    print(f"Successfully generated {len(result)} skeletons")
    print("=" * 50 + "\n")

    return result
