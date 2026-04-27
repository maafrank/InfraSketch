"""Prompts for diagram <-> design-doc auto-sync.

Phase 1 ships diagram_to_doc only. doc_to_diagram is a Phase 2 artifact.
"""

DIAGRAM_TO_DOC_SYNC_PROMPT = """You are syncing a design document to match a system architecture diagram.

The diagram has just been updated. Your job: update the design doc to reflect the
current state of the diagram, using SURGICAL edits via the update_design_doc_section tool.

Current diagram:
{diagram_context}

Current design document:
{design_doc}

Recent change hint: {change_hint}

Rules:
1. Make the SMALLEST possible edits to keep the doc accurate.
2. Update only sections that reference what changed (Component Details, Data Flow,
   Architecture Diagram bullets, etc.). Leave the Executive Summary alone unless the
   change is fundamental to the system's purpose.
3. Do NOT invent components that aren't in the diagram. Do NOT remove sections that
   describe components still in the diagram.
4. If no doc change is warranted (for example, only label rewording or trivial changes),
   respond with the literal text NO_SYNC_NEEDED and call NO tools.
5. Use update_design_doc_section repeatedly for multiple section updates. Match section
   markers EXACTLY as they appear in the document (including the # symbols and any
   bold marker formatting like **Purpose and Goals:**).

Return tool calls only, with no conversational prose between them. If returning
NO_SYNC_NEEDED, return that single token and nothing else.
"""
