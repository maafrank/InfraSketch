"""SyncEngine: orchestrates diagram <-> design-doc auto-sync.

Phase 1 implements diagram_to_doc only. The flow:
    1. SessionManager.update_diagram() calls SyncEngine.schedule()
    2. schedule() decides whether to enqueue (paid plan, doc exists, structural change, etc.),
       sets sync_status.sync_due_at = now + DEBOUNCE_SECONDS, and triggers a Lambda
       async self-invoke (or BackgroundTask in local dev) for run_diagram_to_doc.
    3. run_diagram_to_doc() re-checks sync_due_at on entry. If another mutation has
       extended the debounce window, it no-ops.
    4. Otherwise it snapshots revisions, calls Claude with the existing
       update_design_doc_section tool, executes any tool calls under provenance="sync",
       re-checks design_doc_revision before persisting (concurrency guard), charges credits,
       and resets sync_status to idle.
"""
from __future__ import annotations

import json
import logging
import os
import time
from typing import Optional

from app.billing.credit_costs import DESIGN_DOC_PLANS, calculate_cost
from app.billing.storage import get_user_credits_storage
from app.models import Diagram, Node, SyncStatus
from app.sync.context import current_mutation_provenance
from app.sync.prompts import DIAGRAM_TO_DOC_SYNC_PROMPT

logger = logging.getLogger(__name__)

DEBOUNCE_SECONDS_DIAGRAM_TO_DOC = 8.0
MAX_CONSECUTIVE_FAILURES = 3
SYNC_ENABLED_ENV = "ENABLE_AUTO_SYNC"


def _is_lambda() -> bool:
    return os.environ.get("AWS_LAMBDA_FUNCTION_NAME") is not None


def _feature_flag_enabled() -> bool:
    return os.environ.get(SYNC_ENABLED_ENV, "false").lower() == "true"


def _node_signature(node: Node) -> tuple:
    """Hashable signature of a node, EXCLUDING position and group-only fields.

    Used by `_is_structural_change` to decide whether a diagram mutation
    actually changed anything that the design doc would describe. If two
    diagrams produce identical node signatures, only positions or group
    structure changed.
    """
    return (
        node.id,
        node.type,
        node.label,
        node.description,
        tuple(node.inputs),
        tuple(node.outputs),
        node.metadata.technology,
        node.metadata.notes,
    )


def _is_structural_change(old: Optional[Diagram], new: Diagram) -> bool:
    """Return True if the diff between old and new is structural enough to warrant doc sync.

    Position-only and group-only mutations (drag, collapse, create_group) return False
    so we don't burn LLM credits regenerating doc content for purely visual changes.
    """
    if old is None:
        return True

    old_nodes = {n.id: _node_signature(n) for n in old.nodes if not n.is_group}
    new_nodes = {n.id: _node_signature(n) for n in new.nodes if not n.is_group}

    if old_nodes != new_nodes:
        return True

    old_edges = {(e.source, e.target, e.label) for e in old.edges}
    new_edges = {(e.source, e.target, e.label) for e in new.edges}
    return old_edges != new_edges


def _user_is_paid(user_id: str) -> bool:
    """Check if user is on a plan that includes design doc generation."""
    try:
        storage = get_user_credits_storage()
        credits = storage.get_or_create_credits(user_id)
        return credits.plan in DESIGN_DOC_PLANS
    except Exception as e:
        logger.exception(f"sync: failed to check user plan, treating as free: {e}")
        return False


def _user_auto_sync_enabled(user_id: str) -> bool:
    """Check if the user has auto-sync enabled in their preferences."""
    try:
        from app.user.storage import get_user_preferences_storage
        prefs = get_user_preferences_storage().get_or_create_preferences(user_id)
        return getattr(prefs, "auto_sync_enabled", True)
    except Exception as e:
        logger.exception(f"sync: failed to read user prefs, defaulting to enabled: {e}")
        return True


def _dispatch_async(session_id: str, direction: str) -> None:
    """Trigger the background sync run.

    In Lambda: self-invoke with InvocationType=Event so this returns immediately.
    Locally: schedule a background thread (we can't use BackgroundTasks here because
    schedule() may be called outside a request context, e.g. from a chat tool).
    """
    if _is_lambda():
        try:
            import boto3
            client = boto3.client("lambda")
            payload = {
                "async_task": f"sync_{direction}",
                "session_id": session_id,
            }
            client.invoke(
                FunctionName=os.environ["AWS_LAMBDA_FUNCTION_NAME"],
                InvocationType="Event",
                Payload=json.dumps(payload),
            )
            logger.info(f"sync: dispatched Lambda async invoke for session {session_id} ({direction})")
        except Exception as e:
            logger.exception(f"sync: failed to dispatch Lambda async invoke: {e}")
    else:
        import threading
        if direction == "diagram_to_doc":
            target = run_diagram_to_doc
        else:
            logger.warning(f"sync: unknown direction {direction}, skipping local dispatch")
            return

        def _runner():
            # Sleep until sync_due_at (read from session). Bounded to 30s.
            try:
                from app.session.manager import session_manager
                s = session_manager.get_session(session_id)
                if s and s.sync_status.sync_due_at:
                    wait = max(0.0, s.sync_status.sync_due_at - time.time())
                    wait = min(wait, 30.0)
                    if wait > 0:
                        time.sleep(wait)
                target(session_id)
            except Exception as e:
                logger.exception(f"sync: local background runner failed: {e}")

        threading.Thread(target=_runner, daemon=True).start()
        logger.info(f"sync: scheduled local background runner for session {session_id} ({direction})")


def schedule(
    session,
    side: str,
    provenance: str,
    old_diagram: Optional[Diagram] = None,
    new_diagram: Optional[Diagram] = None,
) -> None:
    """Decide whether to enqueue a sync after a mutation.

    Called from SessionManager.update_diagram / update_design_doc.

    Args:
        session: The just-updated SessionState (already has the new diagram/doc).
        side: "diagram" or "design_doc" - which side just changed.
        provenance: "user" | "agent" | "sync" | "generation".
        old_diagram: Pre-mutation diagram (only relevant for side="diagram").
        new_diagram: Post-mutation diagram (only relevant for side="diagram").
    """
    from app.session.manager import session_manager

    if not _feature_flag_enabled():
        return

    # Loop prevention: never schedule a follow-up sync when sync itself made the mutation.
    if provenance == "sync":
        return

    # Initial generation: don't sync. The generation paths bump last_synced_* themselves.
    if provenance == "generation":
        return

    # Phase 1: only diagram -> doc.
    if side != "diagram":
        return

    # Doc must exist for diagram_to_doc to make sense.
    if not session.design_doc:
        return

    # Skip preview docs (free-tier).
    if session.design_doc_status.is_preview:
        return

    # Don't sync while another async generation is in flight.
    if session.diagram_generation_status.status == "generating":
        return
    if session.design_doc_status.status == "generating":
        return

    # Gating: paid users only.
    if not _user_is_paid(session.user_id):
        return

    if not _user_auto_sync_enabled(session.user_id):
        return

    # Auto-disable after repeated failures.
    if session.sync_status.consecutive_failures >= MAX_CONSECUTIVE_FAILURES:
        return

    # Skip non-structural changes (drag-to-reposition, group create/collapse).
    if not _is_structural_change(old_diagram, new_diagram):
        return

    now = time.time()
    new_due_at = now + DEBOUNCE_SECONDS_DIAGRAM_TO_DOC

    already_pending = (
        session.sync_status.state == "pending"
        and session.sync_status.sync_due_at is not None
    )

    session_manager.update_sync_status(
        session.session_id,
        state="pending",
        direction="diagram_to_doc",
        sync_due_at=new_due_at,
    )

    # If a sync is already pending, the existing background runner / Lambda invocation
    # will pick up the extended sync_due_at when it fires. No need to dispatch again.
    if not already_pending:
        _dispatch_async(session.session_id, "diagram_to_doc")


def run_diagram_to_doc(session_id: str) -> None:
    """Background worker: regenerate relevant doc sections from the current diagram.

    Idempotent: re-checks sync_due_at on entry so coalesced calls no-op.
    """
    from app.session.manager import session_manager

    session = session_manager.get_session(session_id)
    if not session:
        logger.warning(f"sync: session {session_id} not found in run_diagram_to_doc")
        return

    status = session.sync_status
    if status.state != "pending" or status.sync_due_at is None:
        logger.info(f"sync: session {session_id} is not pending, no-op")
        return

    now = time.time()
    if status.sync_due_at > now:
        # Debounce window was extended by another mutation while we were sleeping.
        # Re-dispatch ourselves so the sync still fires after the new window.
        # (We can't just no-op: schedule() doesn't re-dispatch when a sync is already
        # pending, so without this self-redispatch the sync would stall indefinitely.)
        logger.info(
            f"sync: session {session_id} debounce extended "
            f"(due in {status.sync_due_at - now:.1f}s), re-dispatching"
        )
        _dispatch_async(session_id, "diagram_to_doc")
        return

    snapshot_diagram_revision = session.diagram_revision
    snapshot_design_doc_revision = session.design_doc_revision

    if snapshot_diagram_revision == session.last_synced_diagram_revision:
        logger.info(f"sync: session {session_id} already synced at this revision, no-op")
        session_manager.update_sync_status(session_id, state="idle", sync_due_at=None)
        return

    session_manager.update_sync_status(
        session_id,
        state="running",
        direction="diagram_to_doc",
        started_at=now,
    )

    try:
        summary = _execute_diagram_to_doc(session)

        # Concurrency guard: if the doc was edited while we were running, abort and reschedule.
        post = session_manager.get_session(session_id)
        if post is None:
            return
        if post.design_doc_revision != snapshot_design_doc_revision:
            logger.info(
                f"sync: session {session_id} doc was edited mid-sync "
                f"(rev {snapshot_design_doc_revision} -> {post.design_doc_revision}), rescheduling"
            )
            session_manager.update_sync_status(
                session_id,
                state="pending",
                direction="diagram_to_doc",
                sync_due_at=time.time() + DEBOUNCE_SECONDS_DIAGRAM_TO_DOC,
                started_at=None,
            )
            _dispatch_async(session_id, "diagram_to_doc")
            return

        # Charge credits only for runs that actually changed something.
        charged = False
        if summary != "NO_SYNC_NEEDED":
            try:
                cost = calculate_cost("diagram_to_doc_sync", model=session.model)
                ok, _credits = get_user_credits_storage().deduct_credits(
                    user_id=session.user_id,
                    amount=cost,
                    action="diagram_to_doc_sync",
                    session_id=session_id,
                    metadata={"direction": "diagram_to_doc"},
                )
                charged = ok
                if not ok:
                    logger.info(f"sync: session {session_id} insufficient credits, marking idle")
                    session_manager.update_sync_status(
                        session_id,
                        state="idle",
                        error="insufficient_credits",
                        sync_due_at=None,
                        completed_at=time.time(),
                    )
                    return
            except Exception as e:
                logger.exception(f"sync: credit charge failed: {e}")

        session_manager.mark_sync_succeeded(
            session_id,
            diagram_revision=snapshot_diagram_revision,
            design_doc_revision=snapshot_design_doc_revision,
            summary=summary if summary != "NO_SYNC_NEEDED" else "No update needed",
        )
        logger.info(
            f"sync: session {session_id} diagram_to_doc complete "
            f"(charged={charged}, summary={summary[:80]!r})"
        )

    except Exception as e:
        logger.exception(f"sync: run_diagram_to_doc failed for {session_id}: {e}")
        session_manager.mark_sync_failed(session_id, error=str(e))


def _execute_diagram_to_doc(session) -> str:
    """Run the LLM call and execute any tool calls. Returns a short summary string.

    Returns "NO_SYNC_NEEDED" if the LLM declined to make changes.
    """
    from langchain_anthropic import ChatAnthropic
    from langchain_core.messages import HumanMessage, SystemMessage

    from app.agent.prompts import get_diagram_context
    from app.agent.tools import update_design_doc_section
    from app.config.models import DEFAULT_MODEL
    from app.utils.secrets import get_anthropic_api_key

    llm = ChatAnthropic(
        model=session.model or DEFAULT_MODEL,
        api_key=get_anthropic_api_key(),
        temperature=0.2,
        max_tokens=8192,
    ).bind_tools([update_design_doc_section])

    diagram_context = get_diagram_context(session.diagram.model_dump())
    change_hint = (
        f"diagram_revision={session.diagram_revision}, "
        f"last_synced={session.last_synced_diagram_revision}"
    )

    prompt = DIAGRAM_TO_DOC_SYNC_PROMPT.format(
        diagram_context=diagram_context,
        design_doc=session.design_doc,
        change_hint=change_hint,
    )

    messages = [
        SystemMessage(content="You are a precise technical writer."),
        HumanMessage(content=prompt),
    ]

    response = llm.invoke(messages)

    text_content = response.content if isinstance(response.content, str) else ""
    tool_calls = getattr(response, "tool_calls", []) or []

    if not tool_calls and "NO_SYNC_NEEDED" in text_content.upper():
        return "NO_SYNC_NEEDED"

    if not tool_calls:
        logger.info("sync: LLM returned no tool calls and no NO_SYNC_NEEDED token, treating as no-op")
        return "NO_SYNC_NEEDED"

    sections_updated = []
    token = current_mutation_provenance.set("sync")
    try:
        for tc in tool_calls:
            name = tc.get("name")
            args = dict(tc.get("args", {}))
            if name != "update_design_doc_section":
                logger.warning(f"sync: ignoring unexpected tool call {name}")
                continue
            args["session_id"] = session.session_id
            try:
                result = update_design_doc_section.invoke(args)
                if isinstance(result, dict) and result.get("success"):
                    marker = args.get("section_start_marker", "?")
                    sections_updated.append(marker)
                else:
                    logger.warning(f"sync: section update failed: {result}")
            except Exception as e:
                logger.exception(f"sync: tool execution failed: {e}")
    finally:
        current_mutation_provenance.reset(token)

    if not sections_updated:
        return "NO_SYNC_NEEDED"

    return f"Updated {len(sections_updated)} section(s): {', '.join(sections_updated[:3])}"
