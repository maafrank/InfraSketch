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
    get_design_doc_context,
)
from app.utils.secrets import get_anthropic_api_key


class AgentState(TypedDict):
    intent: Literal["generate", "chat"]
    user_message: str
    diagram: dict | None
    node_id: str | None
    conversation_history: list[dict]
    output: str
    diagram_updated: bool
    display_text: str  # Text to show in chat (without JSON)
    design_doc: str | None  # Current design document content (markdown)
    design_doc_updated: bool  # Whether design doc was updated in this interaction
    model: str  # Model to use for this invocation


def create_llm(model_name: str = "claude-haiku-4-5-20251001"):
    """Create Claude LLM instance with specified model."""
    api_key = get_anthropic_api_key()
    return ChatAnthropic(
        model=model_name,
        api_key=api_key,
        temperature=0.7,
        max_tokens=32768,  # Supports up to 64k output tokens
    )


def generate_diagram_node(state: AgentState) -> AgentState:
    """Generate initial diagram from user prompt."""
    llm = create_llm(state.get("model", "claude-haiku-4-5-20251001"))

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
    llm = create_llm(state.get("model", "claude-haiku-4-5-20251001"))

    # Build context
    diagram_context = get_diagram_context(state["diagram"] or {})
    node_context = get_node_context(
        state["diagram"] or {},
        state.get("node_id")
    ) if state.get("node_id") else ""
    design_doc_context = get_design_doc_context(state.get("design_doc"))

    # Format conversation history
    history_str = "\n".join([
        f"{msg['role']}: {msg['content']}"
        for msg in state.get("conversation_history", [])
    ])

    # Create prompt
    prompt = CONVERSATION_PROMPT.format(
        diagram_context=diagram_context,
        node_context=node_context,
        design_doc_context=design_doc_context,
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
            state["display_text"] = "*(Graph has been updated)*"
            return state
    except json.JSONDecodeError as e:
        print(f"✗ Not direct JSON: {e}")

    # Try to extract JSON if embedded in code blocks
    if "```json" in content or "```" in content:
        print(f"Attempting to extract JSON from code block...")
        try:
            if "```json" in content:
                parts = content.split("```json")
                text_before = parts[0].strip()
                remaining = parts[1].split("```")
                json_str = remaining[0].strip()
                text_after = remaining[1].strip() if len(remaining) > 1 else ""
                print(f"Extracted from ```json block")
            else:
                parts = content.split("```")
                text_before = parts[0].strip()
                json_str = parts[1].strip()
                text_after = parts[2].strip() if len(parts) > 2 else ""
                print(f"Extracted from ``` block")

            print(f"Extracted JSON length: {len(json_str)}")
            print(f"First 200 chars: {json_str[:200]}")

            diagram_json = json.loads(json_str)
            if "nodes" in diagram_json and "edges" in diagram_json:
                print(f"✓ Successfully parsed extracted JSON with nodes/edges")

                # Combine non-JSON text
                display_parts = []
                if text_before:
                    display_parts.append(text_before)
                display_parts.append("*(Graph has been updated)*")
                if text_after:
                    display_parts.append(text_after)

                state["output"] = json_str
                state["diagram"] = diagram_json
                state["diagram_updated"] = True
                state["display_text"] = "\n\n".join(display_parts)
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

                    # Extract text before and after JSON
                    text_before = content[:start_idx].strip()
                    text_after = content[end_idx:].strip()

                    # Combine non-JSON text
                    display_parts = []
                    if text_before:
                        display_parts.append(text_before)
                    display_parts.append("*(Graph has been updated)*")
                    if text_after:
                        display_parts.append(text_after)

                    state["output"] = json_str
                    state["diagram"] = diagram_json
                    state["diagram_updated"] = True
                    state["display_text"] = "\n\n".join(display_parts)
                    return state
                else:
                    print(f"✗ Extracted JSON missing nodes or edges")
        except Exception as e:
            print(f"✗ Failed to extract JSON from text: {e}")

    # Check for design doc update
    if "DESIGN_DOC_UPDATE:" in content:
        print(f"Found DESIGN_DOC_UPDATE marker, extracting...")
        try:
            parts = content.split("DESIGN_DOC_UPDATE:")
            text_before_marker = parts[0].strip()
            remaining = parts[1]

            # Extract markdown from code block if present
            if "```markdown" in remaining:
                markdown_parts = remaining.split("```markdown")
                markdown_content = markdown_parts[1].split("```")[0].strip()
                text_after_marker = markdown_parts[1].split("```")[1].strip() if "```" in markdown_parts[1] else ""
            elif "```" in remaining:
                code_parts = remaining.split("```")
                markdown_content = code_parts[1].strip()
                text_after_marker = code_parts[2].strip() if len(code_parts) > 2 else ""
            else:
                # No code block, use rest of content
                markdown_content = remaining.strip()
                text_after_marker = ""

            print(f"✓ Extracted design doc update ({len(markdown_content)} chars)")

            # Build display text
            display_parts = []
            if text_before_marker:
                display_parts.append(text_before_marker)
            display_parts.append("*(Design document has been updated)*")
            if text_after_marker:
                display_parts.append(text_after_marker)

            state["design_doc"] = markdown_content
            state["design_doc_updated"] = True
            state["display_text"] = "\n\n".join(display_parts)
            state["diagram_updated"] = False  # Design doc update only
            print(f"==========================\n")
            return state
        except Exception as e:
            print(f"✗ Failed to extract design doc update: {e}")

    # Not a diagram update or design doc update, just a text response
    print(f"Treating as text response (no updates)")
    print(f"==========================\n")
    state["output"] = content
    state["diagram_updated"] = False
    state["design_doc_updated"] = False
    state["display_text"] = content
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
