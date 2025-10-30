"""
Design document generation module.
Generates comprehensive technical documentation from system diagrams.
"""
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage
from app.agent.prompts import DESIGN_DOC_PROMPT, get_diagram_context
from app.utils.secrets import get_anthropic_api_key


def create_doc_llm():
    """Create Claude LLM instance for document generation."""
    api_key = get_anthropic_api_key()
    return ChatAnthropic(
        model="claude-3-haiku-20240307",
        api_key=api_key,
        temperature=0.7,
        max_tokens=4096,  # Maximum for Haiku
    )


def generate_design_document(diagram: dict, conversation_history: list[dict]) -> str:
    """
    Generate a comprehensive design document from a system diagram.

    Args:
        diagram: The system diagram (nodes and edges)
        conversation_history: List of conversation messages for context

    Returns:
        Markdown formatted design document
    """
    llm = create_doc_llm()

    # Format diagram context
    diagram_context = get_diagram_context(diagram)

    # Format conversation history
    history_str = "\n".join([
        f"{msg['role']}: {msg['content']}"
        for msg in conversation_history[-10:]  # Last 10 messages for context
    ]) if conversation_history else "No conversation history available."

    # Create prompt
    prompt = DESIGN_DOC_PROMPT.format(
        diagram_context=diagram_context,
        conversation_history=history_str
    )

    messages = [
        SystemMessage(content="You are an expert technical writer specializing in system architecture documentation."),
        HumanMessage(content=prompt)
    ]

    print(f"\n=== GENERATING DESIGN DOCUMENT ===")
    print(f"Diagram nodes: {len(diagram.get('nodes', []))}")
    print(f"Diagram edges: {len(diagram.get('edges', []))}")
    print(f"Conversation messages: {len(conversation_history)}")

    response = llm.invoke(messages)

    print(f"Generated document length: {len(response.content)} characters")
    print(f"===================================\n")

    return response.content
