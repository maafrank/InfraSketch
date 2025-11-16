"""
Tool schemas for agent-driven design document modifications.

These tools allow the AI agent to make granular changes to design documents
instead of regenerating the entire markdown content.
"""

from pydantic import BaseModel, Field
from typing import Literal, List, Union, Optional


class UpdateSectionTool(BaseModel):
    """
    Update content within a specific section of the design document.

    Use this tool when the user wants to modify existing content in the design document,
    such as changing a technology name, updating a description, or modifying bullet points
    within a specific section. This tool performs a find-and-replace operation within the
    target section only, leaving all other sections unchanged. Returns the updated document.

    IMPORTANT: You must specify BOTH the section header (to locate where to edit) and the
    exact text to find/replace. Be precise with the find text - it must match exactly.
    """
    action: Literal["update_section"] = "update_section"
    section_header: str = Field(
        ...,
        description="The markdown header that identifies the section to edit. Must match exactly, "
                    "including the # symbols. Examples: '## System Overview', '### Redis Cache', "
                    "'## Component Details'. Use the exact header text from the current document."
    )
    find_text: str = Field(
        ...,
        description="The exact text to find within this section. Must match character-for-character, "
                    "including whitespace. Example: '**Technology**: Redis 7.0'. If unsure about exact "
                    "formatting, use replace_section instead of update_section."
    )
    replace_text: str = Field(
        ...,
        description="The new text to replace the found text with. Can be different length, can include "
                    "markdown formatting. Example: '**Technology**: Memcached 1.6' or a multi-line "
                    "bullet list. Preserves all formatting you include."
    )


class ReplaceSectionTool(BaseModel):
    """
    Replace the entire content of a specific section in the design document.

    Use this tool when the user wants to completely rewrite a section, add substantial new content,
    or when the changes are too complex for simple find-and-replace. This tool replaces everything
    under the section header (until the next same-level header) with your new content. The section
    header itself remains unchanged. Returns the updated document.

    CRITICAL: Only replace the content that needs to change. If the user asks to modify one section,
    do NOT replace other sections. This tool only affects the specified section.
    """
    action: Literal["replace_section"] = "replace_section"
    section_header: str = Field(
        ...,
        description="The markdown header that identifies the section to replace. Must match exactly, "
                    "including the # symbols. Examples: '## Executive Summary', '### PostgreSQL Database', "
                    "'## Trade-offs & Alternatives'. The header itself will NOT be replaced, only the "
                    "content underneath it."
    )
    new_content: str = Field(
        ...,
        description="The complete new content for this section (everything under the header until the "
                    "next same-level header). Should include all markdown formatting (bullet points, "
                    "bold text, code blocks, etc.). Do NOT include the section header itself - only "
                    "the content. Example: '- **Purpose**: Caching layer\\n- **Technology**: Redis 7.0\\n\\n"
                    "This component improves read performance.'"
    )


class AppendSectionTool(BaseModel):
    """
    Add new content to the end of a specific section in the design document.

    Use this tool when the user wants to add new bullet points, paragraphs, or details to an
    existing section without removing what's already there. This tool appends your content to
    the end of the specified section (before the next header). Returns the updated document.

    Example use cases: Adding a new component to "Component Details", adding a new bullet to
    "Security Considerations", appending implementation notes to a section.
    """
    action: Literal["append_section"] = "append_section"
    section_header: str = Field(
        ...,
        description="The markdown header that identifies the section to append to. Must match exactly, "
                    "including the # symbols. Examples: '## Component Details', '## Security Considerations'. "
                    "Your content will be added at the end of this section."
    )
    content: str = Field(
        ...,
        description="The new content to append to this section. Should include proper markdown formatting "
                    "and typically starts with a blank line for spacing. Example: '\\n\\n### New Component\\n"
                    "- **Purpose**: Load balancing\\n- **Technology**: NGINX' or '\\n- New security consideration "
                    "about API keys'"
    )


class DeleteSectionTool(BaseModel):
    """
    Remove an entire section from the design document.

    Use this tool when the user wants to delete a section that's no longer relevant, such as
    removing a component that was deleted from the diagram, or removing an entire major section
    like "Future Enhancements". This deletes the section header AND all content under it (until
    the next same-level header). Returns the updated document.

    WARNING: This is destructive! Make sure the user really wants to delete the section before
    using this tool. If they want to modify content, use update_section or replace_section instead.
    """
    action: Literal["delete_section"] = "delete_section"
    section_header: str = Field(
        ...,
        description="The markdown header of the section to delete. Must match exactly, including "
                    "the # symbols. Examples: '### Redis Cache', '## Future Enhancements'. Both the "
                    "header and all content under it will be removed."
    )


class AddSectionTool(BaseModel):
    """
    Create a new section in the design document at a specific location.

    Use this tool when the user wants to add a completely new section that doesn't exist yet,
    such as adding a new component to "Component Details" or adding a new major section like
    "Disaster Recovery". You can specify where to insert it (after which section). Returns the
    updated document.

    Example use cases: Adding a new component section, adding a new major section between existing
    sections, inserting subsections.
    """
    action: Literal["add_section"] = "add_section"
    section_header: str = Field(
        ...,
        description="The full markdown header for the new section, including # symbols. Must match "
                    "the level of surrounding sections. Examples: '### Load Balancer' (for a component), "
                    "'## Monitoring Strategy' (for a major section). This will become the header."
    )
    content: str = Field(
        ...,
        description="The complete content for this new section. Should include all markdown formatting "
                    "(bullet points, paragraphs, code blocks, etc.). Do NOT include the section header - "
                    "it's specified separately. Example: '- **Purpose**: Distributes traffic\\n- **Technology**: "
                    "NGINX\\n\\nHandles load balancing across backend servers.'"
    )
    insert_after: Optional[str] = Field(
        None,
        description="The section header after which to insert this new section. If not provided, the section "
                    "will be appended to the end of the document. Example: '## Component Details' to insert "
                    "a new section right after Component Details. Must match exactly."
    )


# Union type for all possible design doc tools
DesignDocToolType = Union[
    UpdateSectionTool,
    ReplaceSectionTool,
    AppendSectionTool,
    DeleteSectionTool,
    AddSectionTool
]


class DesignDocToolInvocation(BaseModel):
    """
    Container for design document tool invocations and explanation.

    The agent returns this structure when modifying the design document.
    """
    doc_tools: List[DesignDocToolType] = Field(
        ...,
        description="List of design doc editing tools to execute in order"
    )
    explanation: str = Field(
        ...,
        description="Human-readable explanation of what changed in the design document"
    )


# Example orchestration patterns
DOC_EDITING_EXAMPLES = """
DESIGN DOCUMENT EDITING PATTERNS:

**Pattern 1: Changing a technology in one component**
Example: "Change Redis to Memcached in the caching section"
Steps:
- update_section with section_header='### Redis Cache', find='**Technology**: Redis 7.0', replace='**Technology**: Memcached 1.6'
- update_section with section_header='### Redis Cache', find='Redis Cache', replace='Memcached Cache' (if header text appears in content)

JSON output:
{
  "doc_tools": [
    {
      "action": "update_section",
      "section_header": "### Redis Cache",
      "find_text": "**Technology**: Redis 7.0",
      "replace_text": "**Technology**: Memcached 1.6"
    }
  ],
  "explanation": "Changed caching technology from Redis to Memcached"
}

**Pattern 2: Adding a new component section**
Example: "Add a load balancer component to the design doc"
Steps:
- add_section with header='### Load Balancer', content='...', insert_after='## Component Details'

JSON output:
{
  "doc_tools": [
    {
      "action": "add_section",
      "section_header": "### Load Balancer",
      "content": "- **Purpose**: Distributes incoming traffic across backend servers\\n- **Technology**: NGINX\\n- **Inputs**: ['HTTP requests']\\n- **Outputs**: ['Load-balanced requests']\\n- **Rationale**: Ensures high availability and prevents single point of failure\\n- **Scalability Considerations**: Can handle 10,000+ requests/sec per instance\\n- **Potential Bottlenecks**: Network bandwidth, SSL termination overhead",
      "insert_after": "## Component Details"
    }
  ],
  "explanation": "Added Load Balancer component section to design document"
}

**Pattern 3: Completely rewriting a section**
Example: "Rewrite the Executive Summary to focus on scalability"
Steps:
- replace_section with section_header='## Executive Summary', new_content='...'

JSON output:
{
  "doc_tools": [
    {
      "action": "replace_section",
      "section_header": "## Executive Summary",
      "new_content": "This system is designed for horizontal scalability, supporting millions of concurrent users through distributed architecture.\\n\\nKey architectural decisions prioritize scalability: microservices design, message queues for async processing, and caching layers to reduce database load. The system can scale each component independently based on demand."
    }
  ],
  "explanation": "Rewrote Executive Summary to emphasize scalability focus"
}

**Pattern 4: Adding a bullet point to existing list**
Example: "Add rate limiting to Security Considerations"
Steps:
- append_section with section_header='## Security Considerations', content='\\n- **Rate Limiting**: API gateway enforces 100 req/min per client to prevent abuse'

JSON output:
{
  "doc_tools": [
    {
      "action": "append_section",
      "section_header": "## Security Considerations",
      "content": "\\n- **Rate Limiting**: API gateway enforces 100 requests/minute per client IP to prevent abuse and DDoS attacks"
    }
  ],
  "explanation": "Added rate limiting details to Security Considerations section"
}

**Pattern 5: Removing an obsolete section**
Example: "Remove the Redis Cache component section"
Steps:
- delete_section with section_header='### Redis Cache'

JSON output:
{
  "doc_tools": [
    {
      "action": "delete_section",
      "section_header": "### Redis Cache"
    }
  ],
  "explanation": "Removed Redis Cache component section as it was deleted from the architecture"
}

IMPORTANT RULES:
1. Section headers must match EXACTLY (including # symbols and spacing)
2. For update_section, find_text must match EXACTLY (character-for-character)
3. If you're not sure about exact formatting, use replace_section instead of update_section
4. Use append_section for adding to existing content, add_section for new sections
5. Multiple edits to the same section should be combined when possible
6. Execute tools in logical order (e.g., add sections before updating them)
7. Provide clear explanation of what changed
"""
