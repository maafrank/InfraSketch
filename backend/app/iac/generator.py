"""Generate Infrastructure-as-Code from a diagram.

Structured output via a forced tool call, so there is no fenced-code-block
parsing to get wrong. The scaffold header is prepended here rather than asked
for in the prompt, so it can never be dropped or reworded by the model.
"""

import io
import logging
import posixpath
import zipfile
from typing import Optional

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import tool

from app.agent.prompts import get_diagram_context
from app.config.models import (
    DEFAULT_MODEL,
    compute_max_output_tokens,
    estimate_input_tokens,
)
from app.iac.prompts import FILE_HEADER, IAC_PROMPT, TARGETS
from app.utils.secrets import get_anthropic_api_key

logger = logging.getLogger(__name__)

# Multi-file Terraform runs long. Below this the model truncates mid-resource.
IAC_MAX_OUTPUT_TOKENS = 16_384

# Guards against a runaway generation filling a session record (DynamoDB items
# cap at 400KB and the diagram + doc already live there).
MAX_FILES = 40
MAX_FILE_BYTES = 100_000
MAX_TOTAL_BYTES = 400_000


class IacGenerationError(Exception):
    """The model did not return usable infrastructure code."""


@tool
def emit_iac_files(files: list, warnings: list, assumptions: list) -> dict:
    """Report generated infrastructure-as-code.

    Args:
        files: List of files. Each is an object with `path` (relative path, e.g.
            "main.tf" or "manifests/api.yaml") and `content` (the full file text).
        warnings: Things the diagram is missing that this code cannot supply
            (no monitoring, no VPC, a component with no equivalent in this target).
        assumptions: Every choice made that the diagram did not specify: instance
            sizes, ports, replica counts, image tags, network layout.
    """
    # Never executed. Bound only to force structured output; the tool-call
    # arguments ARE the result.
    return {"files": files, "warnings": warnings, "assumptions": assumptions}


def _safe_path(raw_path: str) -> Optional[str]:
    """Normalize a model-supplied path, rejecting anything that escapes the bundle.

    The paths end up as entries in a zip the user extracts, so a `../` or an
    absolute path would write outside the extraction directory (zip-slip).
    """
    if not isinstance(raw_path, str):
        return None
    path = raw_path.strip().replace("\\", "/").lstrip("/")
    if not path:
        return None
    normalized = posixpath.normpath(path)
    if normalized.startswith("..") or normalized.startswith("/") or normalized == ".":
        return None
    return normalized


def _with_header(path: str, content: str, comment_prefix: str) -> str:
    """Prepend the scaffold notice as a comment.

    Markdown has no comment syntax that renders invisibly and the notice matters
    more than the aesthetics there, so README gets it as a blockquote instead.
    """
    if path.lower().endswith(".md"):
        banner = "\n".join(f"> {line}" for line in FILE_HEADER.split("\n"))
        return f"{banner}\n\n{content}"
    banner = "\n".join(f"{comment_prefix} {line}" for line in FILE_HEADER.split("\n"))
    return f"{banner}\n\n{content}"


def _normalize_files(raw_files, comment_prefix: str) -> list:
    """Validate, de-duplicate, and header-stamp the model's files."""
    files = []
    seen_paths = set()
    total_bytes = 0

    for raw in raw_files or []:
        if not isinstance(raw, dict):
            continue

        path = _safe_path(raw.get("path"))
        if not path:
            logger.warning(f"iac: dropping file with unusable path {raw.get('path')!r}")
            continue
        if path in seen_paths:
            logger.warning(f"iac: dropping duplicate path {path!r}")
            continue

        content = raw.get("content")
        if not isinstance(content, str) or not content.strip():
            continue
        if len(content.encode("utf-8")) > MAX_FILE_BYTES:
            logger.warning(f"iac: dropping oversized file {path!r}")
            continue

        stamped = _with_header(path, content, comment_prefix)
        size = len(stamped.encode("utf-8"))
        if total_bytes + size > MAX_TOTAL_BYTES:
            logger.warning(f"iac: total size cap reached, dropping {path!r} and any later files")
            break

        seen_paths.add(path)
        total_bytes += size
        files.append({"path": path, "content": stamped})

        if len(files) >= MAX_FILES:
            logger.warning("iac: file count cap reached, ignoring the rest")
            break

    return files


def generate_iac(diagram: dict, target: str, model: str = DEFAULT_MODEL) -> dict:
    """Generate infrastructure code for one target.

    Returns {target, files, warnings, assumptions}. Raises IacGenerationError if
    the model returns nothing usable.
    """
    if target not in TARGETS:
        raise IacGenerationError(f"Unknown IaC target: {target}")

    target_config = TARGETS[target]

    prompt = IAC_PROMPT.format(
        diagram_context=get_diagram_context(diagram),
        target_guidance=target_config["guidance"],
    )

    messages = [
        SystemMessage(content="You are a senior infrastructure engineer. You write valid, conservative infrastructure code."),
        HumanMessage(content=prompt),
    ]

    max_tokens = compute_max_output_tokens(
        model,
        estimated_input_tokens=estimate_input_tokens(messages),
        requested_max=IAC_MAX_OUTPUT_TOKENS,
    )

    llm = ChatAnthropic(
        model=model,
        api_key=get_anthropic_api_key(),
        temperature=0.2,
        max_tokens=max_tokens,
    ).bind_tools([emit_iac_files], tool_choice="emit_iac_files")

    logger.info(f"=== GENERATING IAC ({target}) === nodes={len(diagram.get('nodes', []))}")

    response = llm.invoke(messages)
    tool_calls = getattr(response, "tool_calls", []) or []

    if not tool_calls:
        raise IacGenerationError("Model returned no files (expected an emit_iac_files tool call)")

    args = tool_calls[0].get("args", {}) or {}
    files = _normalize_files(args.get("files"), target_config["comment_prefix"])

    if not files:
        raise IacGenerationError("Model returned no usable files")

    def _string_list(value):
        return [str(v).strip() for v in (value or []) if str(v).strip()]

    result = {
        "target": target,
        "label": target_config["label"],
        "files": files,
        "warnings": _string_list(args.get("warnings")),
        "assumptions": _string_list(args.get("assumptions")),
    }

    logger.info(f"IaC complete: {len(files)} file(s) for target {target}")
    return result


def build_zip(files: list, target: str) -> bytes:
    """Bundle generated files into a zip for download."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for file in files:
            archive.writestr(f"infrasketch-{target}/{file['path']}", file["content"])
    return buffer.getvalue()
