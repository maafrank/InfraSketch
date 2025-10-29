import json
import os
from typing import TypedDict, Literal
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import StateGraph, END
from app.agent.prompts import (
    SYSTEM_PROMPT,
    CONVERSATION_PROMPT,
    get_diagram_context,
    get_node_context,
)


class AgentState(TypedDict):
    intent: Literal["generate", "chat"]
    user_message: str
    diagram: dict | None
    node_id: str | None
    conversation_history: list[dict]
    output: str
    diagram_updated: bool


def create_llm():
    """Create Claude LLM instance."""
    api_key = os.getenv("ANTHROPIC_API_KEY")
    return ChatAnthropic(
        model="claude-3-haiku-20240307",
        api_key=api_key,
        temperature=0.7,
        max_tokens=4096,  # Increase to allow longer responses
    )


def generate_diagram_node(state: AgentState) -> AgentState:
    """Generate initial diagram from user prompt."""
    llm = create_llm()

    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=f"Create a system architecture for: {state['user_message']}")
    ]

    response = llm.invoke(messages)

    print(f"\n=== CLAUDE RESPONSE ===")
    print(f"Content: {response.content}")
    print(f"======================\n")

    try:
        # Parse JSON response
        diagram_json = json.loads(response.content)
        print(f"Successfully parsed JSON directly")
        state["output"] = json.dumps(diagram_json)
        state["diagram"] = diagram_json
        state["diagram_updated"] = True
    except json.JSONDecodeError as e:
        print(f"Failed to parse JSON directly: {e}")
        # Fallback: try to extract JSON from response
        content = response.content
        if "```json" in content:
            json_str = content.split("```json")[1].split("```")[0].strip()
            print(f"Extracted JSON from ```json block")
        elif "```" in content:
            json_str = content.split("```")[1].split("```")[0].strip()
            print(f"Extracted JSON from ``` block")
        else:
            json_str = content.strip()
            print(f"Using content as-is")

        try:
            diagram_json = json.loads(json_str)
            print(f"Successfully parsed extracted JSON")
            state["output"] = json.dumps(diagram_json)
            state["diagram"] = diagram_json
            state["diagram_updated"] = True
        except Exception as e2:
            print(f"Failed to parse extracted JSON: {e2}")
            print(f"JSON string was: {json_str[:500]}")
            # Create error response
            state["output"] = json.dumps({
                "nodes": [],
                "edges": [],
                "error": "Failed to generate valid diagram"
            })
            state["diagram_updated"] = False

    return state


def chat_node(state: AgentState) -> AgentState:
    """Handle conversation about diagram/node."""
    llm = create_llm()

    # Build context
    diagram_context = get_diagram_context(state["diagram"] or {})
    node_context = get_node_context(
        state["diagram"] or {},
        state.get("node_id")
    ) if state.get("node_id") else ""

    # Format conversation history
    history_str = "\n".join([
        f"{msg['role']}: {msg['content']}"
        for msg in state.get("conversation_history", [])
    ])

    # Create prompt
    prompt = CONVERSATION_PROMPT.format(
        diagram_context=diagram_context,
        node_context=node_context,
        conversation_history=history_str,
        user_message=state["user_message"]
    )

    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=prompt)
    ]

    response = llm.invoke(messages)
    content = response.content.strip()

    print(f"\n=== CHAT NODE RESPONSE ===")
    print(f"Content length: {len(content)}")
    print(f"First 200 chars: {content[:200]}")
    print(f"Has ```json: {'```json' in content}")
    print(f"Has ```: {'```' in content}")
    print(f"Has opening brace: {'{' in content}")

    # Check if response is a diagram update (JSON)
    try:
        diagram_json = json.loads(content)
        # Validate it has nodes and edges
        if "nodes" in diagram_json and "edges" in diagram_json:
            print(f"✓ Successfully parsed as direct JSON with nodes/edges")
            state["output"] = content
            state["diagram"] = diagram_json
            state["diagram_updated"] = True
            return state
    except json.JSONDecodeError as e:
        print(f"✗ Not direct JSON: {e}")

    # Try to extract JSON if embedded in code blocks
    if "```json" in content or "```" in content:
        print(f"Attempting to extract JSON from code block...")
        try:
            if "```json" in content:
                json_str = content.split("```json")[1].split("```")[0].strip()
                print(f"Extracted from ```json block")
            else:
                json_str = content.split("```")[1].split("```")[0].strip()
                print(f"Extracted from ``` block")

            print(f"Extracted JSON length: {len(json_str)}")
            print(f"First 200 chars: {json_str[:200]}")

            diagram_json = json.loads(json_str)
            if "nodes" in diagram_json and "edges" in diagram_json:
                print(f"✓ Successfully parsed extracted JSON with nodes/edges")
                state["output"] = json_str
                state["diagram"] = diagram_json
                state["diagram_updated"] = True
                return state
            else:
                print(f"✗ Extracted JSON missing nodes or edges")
        except Exception as e:
            print(f"✗ Failed to parse extracted JSON: {e}")

    # Try to extract JSON that's embedded in text (no code blocks)
    if "{" in content and "}" in content:
        print(f"Attempting to extract JSON from text...")
        try:
            # Find the JSON object in the text
            start_idx = content.find("{")
            # Find matching closing brace
            brace_count = 0
            end_idx = -1
            for i in range(start_idx, len(content)):
                if content[i] == "{":
                    brace_count += 1
                elif content[i] == "}":
                    brace_count -= 1
                    if brace_count == 0:
                        end_idx = i + 1
                        break

            if end_idx > start_idx:
                json_str = content[start_idx:end_idx]
                print(f"Extracted JSON from position {start_idx} to {end_idx}")
                print(f"Extracted JSON length: {len(json_str)}")
                print(f"First 200 chars: {json_str[:200]}")

                diagram_json = json.loads(json_str)
                if "nodes" in diagram_json and "edges" in diagram_json:
                    print(f"✓ Successfully parsed extracted JSON with nodes/edges")
                    state["output"] = json_str
                    state["diagram"] = diagram_json
                    state["diagram_updated"] = True
                    return state
                else:
                    print(f"✗ Extracted JSON missing nodes or edges")
        except Exception as e:
            print(f"✗ Failed to extract JSON from text: {e}")

    # Not a diagram update, just a text response
    print(f"Treating as text response (not diagram update)")
    print(f"==========================\n")
    state["output"] = content
    state["diagram_updated"] = False
    return state


def route_intent(state: AgentState) -> str:
    """Route based on intent."""
    if state["intent"] == "generate":
        return "generate"
    else:
        return "chat"


# Create the graph
def create_agent_graph():
    """Create and compile the LangGraph agent."""
    workflow = StateGraph(AgentState)

    # Add nodes
    workflow.add_node("generate", generate_diagram_node)
    workflow.add_node("chat", chat_node)

    # Add conditional entry
    workflow.set_conditional_entry_point(
        route_intent,
        {
            "generate": "generate",
            "chat": "chat",
        }
    )

    # Both nodes end after execution
    workflow.add_edge("generate", END)
    workflow.add_edge("chat", END)

    return workflow.compile()


# Global agent instance
agent_graph = create_agent_graph()
