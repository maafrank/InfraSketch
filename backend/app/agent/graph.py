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

    # Check if response is a diagram update (JSON)
    try:
        diagram_json = json.loads(content)
        # Validate it has nodes and edges
        if "nodes" in diagram_json and "edges" in diagram_json:
            state["output"] = content
            state["diagram"] = diagram_json
            state["diagram_updated"] = True
            return state
    except json.JSONDecodeError:
        pass

    # Try to extract JSON if embedded
    if "```json" in content or "```" in content:
        try:
            if "```json" in content:
                json_str = content.split("```json")[1].split("```")[0].strip()
            else:
                json_str = content.split("```")[1].split("```")[0].strip()

            diagram_json = json.loads(json_str)
            if "nodes" in diagram_json and "edges" in diagram_json:
                state["output"] = json_str
                state["diagram"] = diagram_json
                state["diagram_updated"] = True
                return state
        except:
            pass

    # Not a diagram update, just a text response
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
