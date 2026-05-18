"""
Design document generation module.
Generates comprehensive technical documentation from system diagrams.
"""
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage
from app.agent.prompts import DESIGN_DOC_PROMPT, DESIGN_DOC_PREVIEW_PROMPT, get_diagram_context
from app.utils.secrets import get_anthropic_api_key
from app.config.models import (
    DEFAULT_MODEL,
    compute_max_output_tokens,
    estimate_input_tokens,
    get_model_limits,
)

import logging
logger = logging.getLogger(__name__)


def create_doc_llm(model_name: str = DEFAULT_MODEL, max_tokens: int | None = None):
    """Create Claude LLM instance for document generation.

    If max_tokens is None, defaults to the model's full max output.
    """
    api_key = get_anthropic_api_key()
    if max_tokens is None:
        max_tokens = get_model_limits(model_name)["max_output"]
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

    # Size max_tokens dynamically. Large diagrams + long histories can push input
    # close to the context window, so cap output to whatever's left.
    max_tokens = compute_max_output_tokens(
        model,
        estimated_input_tokens=estimate_input_tokens(messages),
    )
    llm = create_doc_llm(model, max_tokens=max_tokens)

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

    # Preview intentionally caps output at 512 tokens (free-tier teaser). Wrap
    # through compute_max_output_tokens so very large diagrams still don't
    # exceed the context window.
    max_tokens = compute_max_output_tokens(
        model,
        estimated_input_tokens=estimate_input_tokens(messages),
        requested_max=512,
    )
    llm = create_doc_llm(model, max_tokens=max_tokens)

    logger.info(f"\n=== GENERATING DESIGN DOCUMENT PREVIEW ===")
    logger.info(f"Diagram nodes: {len(diagram.get('nodes', []))}")
    logger.info(f"Diagram edges: {len(diagram.get('edges', []))}")
    logger.info(f"Conversation messages: {len(conversation_history)}")

    response = llm.invoke(messages)

    logger.info(f"Generated preview length: {len(response.content)} characters")
    logger.info(f"==========================================\n")

    return response.content
