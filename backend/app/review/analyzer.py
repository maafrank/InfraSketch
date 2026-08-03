"""Architecture review: run the critique LLM call and normalize its output.

Uses a forced tool call rather than asking for JSON in prose, so there is no
parsing step that can fail on a stray code fence. Same principle as the agent's
diagram tools.
"""

import logging
from typing import Optional

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import tool

from app.agent.prompts import get_design_doc_context, get_diagram_context
from app.config.models import (
    DEFAULT_MODEL,
    compute_max_output_tokens,
    estimate_input_tokens,
)
from app.review.prompts import (
    ARCHITECTURE_REVIEW_PROMPT,
    CATEGORIES,
    SEVERITY_PENALTIES,
)
from app.utils.secrets import get_anthropic_api_key

logger = logging.getLogger(__name__)

VALID_SEVERITIES = set(SEVERITY_PENALTIES)
VALID_CATEGORIES = set(CATEGORIES)


class ReviewGenerationError(Exception):
    """The model did not return a usable review."""


@tool
def emit_review(summary: str, findings: list) -> dict:
    """Report the results of an architecture review.

    Args:
        summary: Two or three sentences: what this system is, and the single most
            important thing to fix.
        findings: List of findings. Each is an object with:
            severity (one of "critical", "high", "medium", "low"),
            category (one of "reliability", "scalability", "security", "data",
            "cost", "observability"), title (short noun phrase), detail (why this
            is a problem for this specific system), node_ids (list of exact node
            IDs from the diagram this finding applies to), and recommendation (a
            concrete change to make to this diagram).
    """
    # Never executed. Bound only to force structured output out of the model;
    # the tool-call arguments ARE the result.
    return {"summary": summary, "findings": findings}


def _score_from_findings(findings: list) -> int:
    """Derive the 0-100 score from the findings.

    Computed rather than asked for, so the number can never disagree with the
    list shown beneath it (models are bad at keeping a self-reported score
    consistent with a list they generated in the same breath).
    """
    penalty = sum(SEVERITY_PENALTIES.get(f.get("severity"), 0) for f in findings)
    return max(0, min(100, 100 - penalty))


def _normalize_findings(raw_findings, valid_node_ids: set) -> list:
    """Coerce model output into the shape the frontend expects.

    Drops findings with an unknown severity or category rather than rendering an
    unstyled row, and drops node IDs that are not in the diagram so a click on a
    finding can always highlight something real.
    """
    normalized = []
    for index, raw in enumerate(raw_findings or []):
        if not isinstance(raw, dict):
            continue

        severity = str(raw.get("severity", "")).lower().strip()
        category = str(raw.get("category", "")).lower().strip()
        title = str(raw.get("title", "")).strip()

        if severity not in VALID_SEVERITIES:
            logger.warning(f"review: dropping finding with unknown severity {severity!r}")
            continue
        if category not in VALID_CATEGORIES:
            logger.warning(f"review: dropping finding with unknown category {category!r}")
            continue
        if not title:
            continue

        node_ids = [
            node_id for node_id in (raw.get("node_ids") or [])
            if isinstance(node_id, str) and node_id in valid_node_ids
        ]

        normalized.append({
            "id": f"finding-{index + 1}",
            "severity": severity,
            "category": category,
            "title": title,
            "detail": str(raw.get("detail", "")).strip(),
            "node_ids": node_ids,
            "recommendation": str(raw.get("recommendation", "")).strip(),
        })

    # Most severe first, so the panel needs no sorting of its own.
    order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    normalized.sort(key=lambda f: order[f["severity"]])
    return normalized


def generate_architecture_review(
    diagram: dict,
    design_doc: Optional[str] = None,
    model: str = DEFAULT_MODEL,
) -> dict:
    """Run an architecture review over a diagram.

    Returns {score, summary, findings, counts}. Raises ReviewGenerationError if
    the model declines to call the tool.
    """
    diagram_context = get_diagram_context(diagram)
    design_doc_context = get_design_doc_context(design_doc)

    prompt = ARCHITECTURE_REVIEW_PROMPT.format(
        diagram_context=diagram_context,
        design_doc_context=design_doc_context,
    )

    messages = [
        SystemMessage(content="You are a staff engineer running a rigorous design review."),
        HumanMessage(content=prompt),
    ]

    max_tokens = compute_max_output_tokens(
        model,
        estimated_input_tokens=estimate_input_tokens(messages),
        requested_max=8192,
    )

    # tool_choice forces the call: without it a model will sometimes answer in
    # prose and there is nothing structured to render.
    llm = ChatAnthropic(
        model=model,
        api_key=get_anthropic_api_key(),
        temperature=0.3,
        max_tokens=max_tokens,
    ).bind_tools([emit_review], tool_choice="emit_review")

    logger.info(
        f"=== GENERATING ARCHITECTURE REVIEW === "
        f"nodes={len(diagram.get('nodes', []))} edges={len(diagram.get('edges', []))}"
    )

    response = llm.invoke(messages)
    tool_calls = getattr(response, "tool_calls", []) or []

    if not tool_calls:
        raise ReviewGenerationError("Model returned no review (expected an emit_review tool call)")

    args = tool_calls[0].get("args", {}) or {}
    valid_node_ids = {n.get("id") for n in diagram.get("nodes", []) if n.get("id")}
    findings = _normalize_findings(args.get("findings"), valid_node_ids)

    counts = {severity: 0 for severity in VALID_SEVERITIES}
    for finding in findings:
        counts[finding["severity"]] += 1

    review = {
        "score": _score_from_findings(findings),
        "summary": str(args.get("summary", "")).strip(),
        "findings": findings,
        "counts": counts,
    }

    logger.info(
        f"Review complete: score={review['score']} findings={len(findings)} counts={counts}"
    )
    return review
