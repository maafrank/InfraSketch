"""
Structured logging utility for tracking user events and system metrics.
Logs are sent to stdout and captured by CloudWatch Logs.
"""

import json
import logging
import sys
from datetime import datetime
from typing import Any, Dict, Optional
from enum import Enum

# Use root logger (pre-configured by Lambda)
# Lambda's logging is already set up, so we just need to get the root logger
logger = logging.getLogger()
logger.setLevel(logging.INFO)  # Ensure INFO level is enabled


class EventType(str, Enum):
    """Event types for tracking different user actions"""
    DIAGRAM_GENERATED = "diagram_generated"
    CHAT_MESSAGE = "chat_message"
    NODE_ADDED = "node_added"
    NODE_DELETED = "node_deleted"
    NODE_UPDATED = "node_updated"
    EDGE_ADDED = "edge_added"
    EDGE_DELETED = "edge_deleted"
    DESIGN_DOC_GENERATED = "design_doc_generated"
    EXPORT_DESIGN_DOC = "export_design_doc"
    SESSION_CREATED = "session_created"
    SESSION_RETRIEVED = "session_retrieved"
    API_REQUEST = "api_request"
    API_ERROR = "api_error"
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"


def log_event(
    event_type: EventType,
    session_id: Optional[str] = None,
    user_ip: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
    error: Optional[str] = None,
) -> None:
    """
    Log a structured event to CloudWatch.

    Args:
        event_type: Type of event being logged
        session_id: Session ID if applicable
        user_ip: User's IP address (anonymized)
        metadata: Additional event-specific data
        error: Error message if this is an error event
    """
    log_entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "event_type": event_type.value,
        "session_id": session_id,
        "user_ip": anonymize_ip(user_ip) if user_ip else None,
        "metadata": metadata or {},
    }

    if error:
        log_entry["error"] = error

    # Remove None values for cleaner logs
    log_entry = {k: v for k, v in log_entry.items() if v is not None}

    # Log as JSON for easy parsing in CloudWatch Insights
    logger.info(json.dumps(log_entry))


def log_api_request(
    method: str,
    path: str,
    status_code: int,
    duration_ms: float,
    user_ip: Optional[str] = None,
    session_id: Optional[str] = None,
) -> None:
    """Log API request with performance metrics"""
    log_event(
        EventType.API_REQUEST,
        session_id=session_id,
        user_ip=user_ip,
        metadata={
            "method": method,
            "path": path,
            "status_code": status_code,
            "duration_ms": round(duration_ms, 2),
        }
    )


def log_diagram_generation(
    session_id: str,
    node_count: int,
    edge_count: int,
    prompt_length: int,
    duration_ms: float,
    user_ip: Optional[str] = None,
    prompt: Optional[str] = None,
) -> None:
    """Log diagram generation event with details"""
    metadata = {
        "node_count": node_count,
        "edge_count": edge_count,
        "prompt_length": prompt_length,
        "duration_ms": round(duration_ms, 2),
    }
    # Store truncated prompt for analytics (first 500 chars)
    if prompt:
        metadata["prompt"] = prompt[:500] if len(prompt) > 500 else prompt

    log_event(
        EventType.DIAGRAM_GENERATED,
        session_id=session_id,
        user_ip=user_ip,
        metadata=metadata
    )


def log_chat_interaction(
    session_id: str,
    message_length: int,
    node_id: Optional[str],
    diagram_updated: bool,
    duration_ms: float,
    user_ip: Optional[str] = None,
    message: Optional[str] = None,
) -> None:
    """Log chat interaction event"""
    metadata = {
        "message_length": message_length,
        "node_id": node_id,
        "diagram_updated": diagram_updated,
        "duration_ms": round(duration_ms, 2),
    }
    # Store truncated message for analytics (first 300 chars)
    if message:
        metadata["message"] = message[:300] if len(message) > 300 else message

    log_event(
        EventType.CHAT_MESSAGE,
        session_id=session_id,
        user_ip=user_ip,
        metadata=metadata
    )


def log_design_doc_generation(
    session_id: str,
    duration_ms: float,
    doc_length: int,
    user_ip: Optional[str] = None,
    success: bool = True,
) -> None:
    """Log design document generation event"""
    log_event(
        EventType.DESIGN_DOC_GENERATED,
        session_id=session_id,
        user_ip=user_ip,
        metadata={
            "duration_ms": round(duration_ms, 2),
            "doc_length": doc_length,
            "success": success,
        }
    )


def log_export(
    session_id: str,
    format: str,
    duration_ms: float,
    user_ip: Optional[str] = None,
    success: bool = True,
) -> None:
    """Log design document export event"""
    log_event(
        EventType.EXPORT_DESIGN_DOC,
        session_id=session_id,
        user_ip=user_ip,
        metadata={
            "format": format,
            "duration_ms": round(duration_ms, 2),
            "success": success,
        }
    )


def log_error(
    error_type: str,
    error_message: str,
    session_id: Optional[str] = None,
    user_ip: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> None:
    """Log error event"""
    log_event(
        EventType.API_ERROR,
        session_id=session_id,
        user_ip=user_ip,
        metadata={"error_type": error_type, **(metadata or {})},
        error=error_message,
    )


def anonymize_ip(ip: str) -> str:
    """
    Anonymize IP address by zeroing out last octet for privacy.
    Example: 192.168.1.100 -> 192.168.1.0
    """
    if not ip:
        return "unknown"

    # Handle IPv4
    if "." in ip:
        parts = ip.split(".")
        if len(parts) == 4:
            return f"{parts[0]}.{parts[1]}.{parts[2]}.0"

    # Handle IPv6 - keep first 4 segments
    if ":" in ip:
        parts = ip.split(":")
        if len(parts) >= 4:
            return ":".join(parts[:4]) + "::"

    return "unknown"
