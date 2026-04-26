"""
Design document generation module.
Generates comprehensive technical documentation from system diagrams.
"""
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage
from app.agent.prompts import DESIGN_DOC_PROMPT, DESIGN_DOC_PREVIEW_PROMPT, get_diagram_context
from app.utils.secrets import get_anthropic_api_key
from app.config.models import DEFAULT_MODEL

import logging
logger = logging.getLogger(__name__)


def create_doc_llm(model_name: str = DEFAULT_MODEL, max_tokens: int = 32768):
    """Create Claude LLM instance for document generation."""
    api_key = get_anthropic_api_key()
    return ChatAnthropic(
        model=model_name,
        api_key=api_key,
        temperature=0.7,
        max_tokens=max_tokens,
    )


def generate_design_document(diagram: dict, conversation_history: list[dict], model: str = DEFAULT_MODEL) -> str:
    """
    Generate a comprehensive design document from a system diagram.

    Args:
        diagram: The system diagram (nodes and edges)
        conversation_history: List of conversation messages for context
        model: The model to use for generation (defaults to Haiku)

    Returns:
        Markdown formatted design document
    """
    llm = create_doc_llm(model)

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

    logger.info(f"\n=== GENERATING DESIGN DOCUMENT ===")
    logger.info(f"Diagram nodes: {len(diagram.get('nodes', []))}")
    logger.info(f"Diagram edges: {len(diagram.get('edges', []))}")
    logger.info(f"Conversation messages: {len(conversation_history)}")

    response = llm.invoke(messages)

    logger.info(f"Generated document length: {len(response.content)} characters")
    logger.info(f"===================================\n")

    return response.content


def generate_design_document_preview(diagram: dict, conversation_history: list[dict], model: str = DEFAULT_MODEL) -> str:
    """
    Generate the Executive Summary section only as a free-tier preview.

    Args:
        diagram: The system diagram (nodes and edges)
        conversation_history: List of conversation messages for context
        model: The model to use for generation (defaults to Haiku)

    Returns:
        Markdown formatted document containing only the title and Executive Summary
    """
    llm = create_doc_llm(model, max_tokens=512)

    diagram_context = get_diagram_context(diagram)

    history_str = "\n".join([
        f"{msg['role']}: {msg['content']}"
        for msg in conversation_history[-10:]
    ]) if conversation_history else "No conversation history available."

    prompt = DESIGN_DOC_PREVIEW_PROMPT.format(
        diagram_context=diagram_context,
        conversation_history=history_str
    )

    messages = [
        SystemMessage(content="You are an expert technical writer specializing in system architecture documentation."),
        HumanMessage(content=prompt)
    ]

    logger.info(f"\n=== GENERATING DESIGN DOCUMENT PREVIEW ===")
    logger.info(f"Diagram nodes: {len(diagram.get('nodes', []))}")
    logger.info(f"Diagram edges: {len(diagram.get('edges', []))}")
    logger.info(f"Conversation messages: {len(conversation_history)}")

    response = llm.invoke(messages)

    logger.info(f"Generated preview length: {len(response.content)} characters")
    logger.info(f"==========================================\n")

    return response.content
