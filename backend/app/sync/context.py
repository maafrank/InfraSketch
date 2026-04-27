"""Provenance tracking for session mutations.

Used to flag the source of an `update_diagram` / `update_design_doc` call
so the SyncEngine can skip scheduling a follow-up sync when the mutation
was itself made by sync. Without this, sync writes would re-trigger sync
in an infinite loop.

Values:
    - "user": REST endpoint called from the frontend (manual edit)
    - "agent": LangGraph chat tool call
    - "sync": SyncEngine itself - never schedules another sync
    - "generation": Initial diagram or design-doc generation - skips sync
"""
from contextvars import ContextVar
from typing import Literal

Provenance = Literal["user", "agent", "sync", "generation"]

current_mutation_provenance: ContextVar[Provenance] = ContextVar(
    "current_mutation_provenance",
    default="user",
)
