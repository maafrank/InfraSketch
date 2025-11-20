"""
LangGraph agent with native tool calling support.

Uses Claude's native tool calling API instead of manual JSON parsing,
providing better reliability and self-correction capabilities.
"""

import json
from typing import Literal
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage, ToolMessage
from langgraph.graph import StateGraph, END

from app.agent.state import InfraSketchState
from app.agent.tools import all_tools
from app.agent.prompts import (
    SYSTEM_PROMPT,
    CONVERSATION_PROMPT,
    get_diagram_context,
    get_node_context,
    get_design_doc_context,
)
from app.models import Diagram
from app.utils.secrets import get_anthropic_api_key


def create_llm(model_name: str = "claude-haiku-4-5"):
    """Create Claude LLM instance with specified model."""
    api_key = get_anthropic_api_key()
    return ChatAnthropic(
        model=model_name,
        api_key=api_key,
        temperature=0.4,
        max_tokens=32768,  # Supports up to 64k output tokens
    )


def generate_diagram_node(state: InfraSketchState) -> dict:
    """Generate initial diagram from user prompt."""
    llm = create_llm(state.model or "claude-haiku-4-5")

    # Get user message from last message in conversation
    user_message = state.messages[-1].content if state.messages else ""

    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=f"Create a system architecture for: {user_message}")
    ]

    response = llm.invoke(messages)

    print(f"\n=== CLAUDE RESPONSE ===")
    print(f"Content: {response.content}")
    print(f"======================\n")

    diagram = None
    try:
        # Parse JSON response
        diagram_json = json.loads(response.content)
        print(f"✓ Successfully parsed JSON directly")
        diagram = Diagram(**diagram_json)
    except json.JSONDecodeError as e:
        print(f"✗ Failed to parse JSON directly: {e}")
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
            print(f"✓ Successfully parsed extracted JSON")
            diagram = Diagram(**diagram_json)
        except Exception as e2:
            print(f"✗ Failed to parse extracted JSON: {e2}")
            print(f"JSON string was: {json_str[:500]}")
            # Create error response
            diagram = Diagram(nodes=[], edges=[])

    # Return updates (message + diagram)
    return {
        "messages": AIMessage(content=response.content),
        "diagram": diagram
    }


def chat_node(state: InfraSketchState) -> dict:
    """
    Handle conversation about diagram/node with native tool calling.

    This node uses Claude's native tool calling API. The LLM can:
    1. Respond with text
    2. Call tools to modify the diagram
    3. Both respond AND call tools

    If tools are called, the tool loop will execute them and return here.
    """
    # Bind tools to LLM (includes both diagram and design doc tools)
    llm = create_llm(state.model or "claude-haiku-4-5-20251001").bind_tools(all_tools)

    # Build context
    diagram_dict = state.diagram.model_dump() if state.diagram else {}
    diagram_context = get_diagram_context(diagram_dict)
    node_context = get_node_context(
        diagram_dict,
        state.node_id
    ) if state.node_id else ""
    design_doc_context = get_design_doc_context(state.design_doc)

    # Format conversation history from messages (skip system messages)
    history_messages = [msg for msg in state.messages if not isinstance(msg, SystemMessage)]
    history_str = "\n".join([
        f"{'user' if isinstance(msg, HumanMessage) else 'assistant'}: {msg.content}"
        for msg in history_messages[:-1]  # Exclude current message
    ])

    # Get current user message
    current_message = state.messages[-1].content if state.messages else ""

    # Create prompt
    prompt = CONVERSATION_PROMPT.format(
        diagram_context=diagram_context,
        node_context=node_context,
        design_doc_context=design_doc_context,
        conversation_history=history_str,
        user_message=current_message
    )

    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=prompt)
    ]

    response = llm.invoke(messages)

    print(f"\n=== CHAT NODE RESPONSE ===")
    print(f"Response type: {type(response)}")
    print(f"Has tool_calls: {hasattr(response, 'tool_calls') and len(response.tool_calls) > 0}")
    if hasattr(response, 'tool_calls') and response.tool_calls:
        print(f"Tool calls: {len(response.tool_calls)}")
        for i, tc in enumerate(response.tool_calls):
            print(f"  Tool {i+1}: {tc.get('name', 'unknown')}")
    print(f"Content length: {len(response.content) if response.content else 0}")
    print(f"==========================\n")

    # Return the AIMessage - tool loop will handle tool execution if needed
    return {
        "messages": response
    }


def tools_node(state: InfraSketchState) -> dict:
    """
    Execute tools called by the AI.

    This node extracts tool calls from the last AIMessage and executes them.
    Results are returned as ToolMessages that will be sent back to the agent.
    """
    last_message = state.messages[-1]

    if not isinstance(last_message, AIMessage) or not hasattr(last_message, 'tool_calls'):
        return {"messages": []}

    tool_calls = last_message.tool_calls
    if not tool_calls:
        return {"messages": []}

    print(f"\n=== EXECUTING {len(tool_calls)} TOOL(S) ===")

    # Build a map of tool names to tool functions
    tool_map = {tool.name: tool for tool in all_tools}

    tool_messages = []
    for tool_call in tool_calls:
        tool_name = tool_call.get("name")
        tool_args = tool_call.get("args", {})
        tool_id = tool_call.get("id", "unknown")

        print(f"Tool: {tool_name}")
        print(f"Args: {tool_args}")

        if tool_name not in tool_map:
            result = {"error": f"Unknown tool: {tool_name}"}
            print(f"✗ Unknown tool")
        else:
            try:
                # Execute the tool
                tool_func = tool_map[tool_name]
                # Inject session_id into args (required by all tools)
                tool_args["session_id"] = state.session_id
                result = tool_func.invoke(tool_args)
                print(f"✓ Result: {result}")
            except Exception as e:
                result = {"error": str(e)}
                print(f"✗ Error: {e}")

        # Create ToolMessage with result
        tool_messages.append(
            ToolMessage(
                content=json.dumps(result),
                tool_call_id=tool_id
            )
        )

    print(f"=== TOOL EXECUTION COMPLETE ===\n")

    return {"messages": tool_messages}


def route_tool_decision(state: InfraSketchState) -> Literal["tools", "finalize"]:
    """
    Route based on whether the last message has tool calls.

    If the AI decided to call tools, route to "tools" node.
    Otherwise, route to "finalize" to prepare the final response.
    """
    last_message = state.messages[-1]
    if isinstance(last_message, AIMessage) and hasattr(last_message, 'tool_calls') and last_message.tool_calls:
        print(f"→ Routing to tools ({len(last_message.tool_calls)} tool call(s))")
        return "tools"
    print(f"→ Routing to finalize (no tool calls)")
    return "finalize"


def finalize_chat_response(state: InfraSketchState) -> dict:
    """
    Finalize chat response after tool execution (if any).

    This node:
    1. Checks if tools were executed in this turn
    2. Updates the diagram and design doc in state if tools modified them
    3. Adds visual indicators to the message
    """
    from app.session.manager import session_manager

    # Get the updated session
    session = session_manager.get_session(state.session_id)
    if not session:
        return {}

    # Check recent messages for tool calls
    recent_messages = state.messages[-10:]  # Check last 10 messages for tool activity

    # Check what types of tools were called
    diagram_tools_called = False
    design_doc_tools_called = False

    for msg in recent_messages:
        if isinstance(msg, AIMessage) and hasattr(msg, 'tool_calls') and msg.tool_calls:
            for tool_call in msg.tool_calls:
                tool_name = tool_call.get("name", "")
                if tool_name in ["add_node", "delete_node", "update_node", "add_edge", "delete_edge"]:
                    diagram_tools_called = True
                elif tool_name in ["update_design_doc_section", "replace_entire_design_doc"]:
                    design_doc_tools_called = True

    # Build updates
    updates = {}

    # Update diagram in state if diagram tools were called
    if diagram_tools_called:
        print(f"✓ Diagram tools were executed, updating diagram in state")
        updates["diagram"] = session.diagram

    # Update design doc in state if design doc tools were called
    if design_doc_tools_called:
        print(f"✓ Design doc tools were executed, updating design doc in state")
        updates["design_doc"] = session.design_doc

    # Add visual indicators to the last message if tools were called
    if diagram_tools_called or design_doc_tools_called:
        last_msg = state.messages[-1]
        if isinstance(last_msg, AIMessage) and last_msg.content:
            content = last_msg.content

            # Add appropriate indicators
            indicators = []
            if diagram_tools_called:
                indicators.append("*(Graph has been updated)*")
            if design_doc_tools_called:
                indicators.append("*(Design document has been updated)*")

            updated_content = content + "\n\n" + "\n".join(indicators)

            # Replace the last message
            new_messages = list(state.messages[:-1])
            new_messages.append(AIMessage(content=updated_content))
            updates["messages"] = new_messages

    return updates


def route_intent(state: InfraSketchState) -> str:
    """
    Route based on whether we have an existing diagram.

    If no diagram exists, it's a generate request.
    If diagram exists, it's a chat request.
    """
    if state.diagram is None:
        return "generate"
    else:
        return "chat"


# Create the graph
def create_agent_graph():
    """Create and compile the LangGraph agent with native tool calling."""
    workflow = StateGraph(InfraSketchState)

    # Add nodes
    workflow.add_node("generate", generate_diagram_node)
    workflow.add_node("chat", chat_node)
    workflow.add_node("tools", tools_node)
    workflow.add_node("finalize", finalize_chat_response)

    # Add conditional entry
    workflow.set_conditional_entry_point(
        route_intent,
        {
            "generate": "generate",
            "chat": "chat",
        }
    )

    # Generate ends immediately
    workflow.add_edge("generate", END)

    # Chat flow with tool loop
    workflow.add_conditional_edges(
        "chat",
        route_tool_decision,
        {
            "tools": "tools",      # If tools called, execute them
            "finalize": "finalize"  # Otherwise, finalize response
        }
    )

    # After tools execute, loop back to chat for agent to see results
    workflow.add_edge("tools", "chat")

    # Finalize ends the conversation turn
    workflow.add_edge("finalize", END)

    return workflow.compile()


# Global agent instance
agent_graph = create_agent_graph()
