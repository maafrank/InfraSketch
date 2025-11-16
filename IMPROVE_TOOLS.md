# Tool-Based Architecture Improvements

## Executive Summary

This document proposes migrating from **full JSON regeneration** to **granular tool-based operations** for both diagram modifications and design document edits. The goal is to give the AI agent access to the same CRUD operations that manual users have, plus text editing capabilities.

---

## Current Architecture Problems

### Diagram Modifications (Current State)
**Problem**: Agent must regenerate entire diagram JSON (all nodes + edges) for any change
- ❌ **Token waste**: Sending 50-node diagram when only adding 1 node
- ❌ **Error-prone**: Claude must remember all existing IDs, positions, connections
- ❌ **Parsing complexity**: Multi-strategy JSON extraction ([graph.py:140-246](backend/app/agent/graph.py:140-246))
- ❌ **Failure modes**: If JSON is malformed, entire diagram update fails

**Current Workaround**: Extensive prompt engineering to ensure "output ALL nodes and edges (including unchanged ones)"

### Design Doc Modifications (Current State)
**Problem**: Agent must return full 5k-15k character document for small edits
- ❌ **Token waste**: ~10k-30k output tokens to change "Redis" → "Memcached"
- ❌ **Reliability risk**: Claude might accidentally rephrase unchanged sections despite instructions
- ❌ **Cost**: 3x more expensive with Sonnet ($15/million output tokens)

**Current Workaround**: Prompt warnings like "PRESERVE UNCHANGED CONTENT EXACTLY" and "DO NOT rewrite"

---

## Proposed Solution 1: Tool-Based Diagram Editing

### Overview
Give the agent access to the same CRUD tools that manual users have, plus teach it orchestration patterns.

### Implementation Plan

#### Step 1: Define Tool Schemas
Create Pydantic models for tool invocations:

```python
# backend/app/agent/tools.py

from pydantic import BaseModel
from typing import Literal

class AddNodeTool(BaseModel):
    action: Literal["add_node"]
    node_id: str
    type: str  # cache, database, api, etc.
    label: str
    description: str
    technology: str
    position: dict  # {"x": 100, "y": 200}

class DeleteNodeTool(BaseModel):
    action: Literal["delete_node"]
    node_id: str

class UpdateNodeTool(BaseModel):
    action: Literal["update_node"]
    node_id: str
    # All fields optional (only update what's specified)
    label: str | None = None
    description: str | None = None
    technology: str | None = None

class AddEdgeTool(BaseModel):
    action: Literal["add_edge"]
    edge_id: str
    source: str  # node_id
    target: str  # node_id
    label: str

class DeleteEdgeTool(BaseModel):
    action: Literal["delete_edge"]
    edge_id: str

class ToolInvocation(BaseModel):
    tools: list[AddNodeTool | DeleteNodeTool | UpdateNodeTool | AddEdgeTool | DeleteEdgeTool]
```

#### Step 2: Update Agent System Prompt
Replace JSON generation instructions with tool-calling instructions:

```markdown
When the user asks to modify the diagram, output a JSON array of tool invocations:

{
  "tools": [
    {"action": "add_node", "node_id": "cache-1", "type": "cache", ...},
    {"action": "add_edge", "edge_id": "e1", "source": "api-1", "target": "cache-1", ...}
  ],
  "explanation": "Added Redis cache layer between API and database"
}

ORCHESTRATION PATTERNS:

**Adding a new component:**
1. add_node - Create the new node
2. add_edge - Connect it to upstream component(s)
3. add_edge - Connect it to downstream component(s)
4. (Optional) delete_edge - Remove old direct connections you're replacing

Example: "Add Redis cache between API and PostgreSQL"
→ add_node(cache-1, type=cache, label=Redis)
→ add_edge(api → cache-1, label="Query with cache key")
→ add_edge(cache-1 → db, label="Cache miss query")
→ delete_edge(api → db)  // Remove old direct connection

**Removing a component:**
1. delete_edge - Remove all connections TO this node
2. delete_edge - Remove all connections FROM this node
3. delete_node - Delete the node itself
4. (Optional) add_edge - Add new direct connections to bridge the gap

**Updating a component:**
1. update_node - Modify properties (label, description, technology)

**Replacing a technology:**
1. update_node - Change the technology field and description

RULES:
- Always include "explanation" field describing what you did
- Use descriptive edge labels (what data flows, not just "connects to")
- When adding nodes, position them logically (estimate x/y based on neighbors)
- Generate unique IDs (use descriptive names: "redis-cache-1" not "node-123")
```

#### Step 3: Update Agent Graph Logic
Modify `chat_node` to execute tools instead of parsing full JSON:

```python
# backend/app/agent/graph.py

def chat_node(state: AgentState) -> AgentState:
    """Handle conversation with tool-based diagram editing."""
    llm = create_llm(state.get("model", "claude-haiku-4-5-20251001"))

    # ... build context and prompt ...

    response = llm.invoke(messages)
    content = response.content.strip()

    # Try to parse as tool invocation
    try:
        tool_response = json.loads(content)
        if "tools" in tool_response:
            # Execute tools sequentially
            session_id = state.get("session_id")  # Need to add this to state
            for tool in tool_response["tools"]:
                action = tool["action"]

                if action == "add_node":
                    node = Node(
                        id=tool["node_id"],
                        type=tool["type"],
                        label=tool["label"],
                        description=tool["description"],
                        metadata=NodeMetadata(technology=tool["technology"]),
                        position=NodePosition(**tool["position"]),
                        inputs=[],
                        outputs=[]
                    )
                    # Call existing API function
                    from app.api.routes import add_node as api_add_node
                    state["diagram"] = api_add_node(session_id, node)

                elif action == "delete_node":
                    from app.api.routes import delete_node as api_delete_node
                    state["diagram"] = api_delete_node(session_id, tool["node_id"])

                elif action == "add_edge":
                    edge = Edge(
                        id=tool["edge_id"],
                        source=tool["source"],
                        target=tool["target"],
                        label=tool.get("label"),
                    )
                    from app.api.routes import add_edge as api_add_edge
                    state["diagram"] = api_add_edge(session_id, edge)

                # ... handle other actions ...

            state["diagram_updated"] = True
            state["display_text"] = tool_response.get("explanation", "*(Graph has been updated)*")
            return state

    except json.JSONDecodeError:
        pass  # Fall back to text response

    # Not a tool invocation, just text response
    state["output"] = content
    state["diagram_updated"] = False
    state["display_text"] = content
    return state
```

#### Step 4: Add Session ID to Agent State
Modify `AgentState` to include session ID:

```python
class AgentState(TypedDict):
    session_id: str  # NEW: needed for tool execution
    intent: Literal["generate", "chat"]
    user_message: str
    diagram: dict | None
    # ... rest unchanged ...
```

Update API routes to pass session_id:

```python
# backend/app/api/routes.py

result = agent_graph.invoke({
    "session_id": request.session_id,  # NEW
    "intent": "chat",
    # ... rest unchanged ...
})
```

### Advantages of Tool-Based Approach

✅ **Token efficiency**: 500 tokens instead of 5,000 tokens for simple changes
✅ **Better reliability**: Validate each operation individually (fail fast)
✅ **Clearer errors**: "Node 'api-1' not found" vs "JSON parse failed"
✅ **Easier debugging**: See exact sequence of operations in logs
✅ **Matches mental model**: Agent thinks "add node then connect" (like humans do)
✅ **Reuses existing code**: Leverages battle-tested CRUD endpoints
✅ **Atomic rollback**: Could implement transaction-style rollback if any tool fails

### Disadvantages / Risks

⚠️ **Sequential execution**: Tools run one-by-one (but diagram ops are fast ~10ms each)
⚠️ **Tool calling support**: Need to verify Claude supports structured output reliably
⚠️ **Orchestration complexity**: Agent must learn multi-step patterns (but this is solvable with good prompts)
⚠️ **Position estimation**: Agent must guess x/y coordinates for new nodes (but auto-layout runs anyway)
⚠️ **Migration complexity**: Need to support both old (full JSON) and new (tools) formats during transition

### Mitigation Strategies

1. **Hybrid approach during migration**: Keep full JSON regeneration as fallback if tools fail
2. **Position hints**: Provide "near node X" syntax → backend calculates position
3. **Validation layer**: Pre-validate all tools before executing (check IDs exist, etc.)
4. **Transaction wrapper**: If any tool fails, rollback all changes in that batch
5. **Extensive prompt examples**: Show 10+ examples of common orchestration patterns

---

## Proposed Solution 2: Diff-Based Design Doc Editing

### Overview
Instead of returning full 15k character documents, agent returns surgical edit commands.

### Implementation Options

#### Option A: Line-Based Diffs (Simpler)
Agent returns line numbers and replacement text:

```json
{
  "doc_edits": [
    {
      "line_start": 45,
      "line_end": 45,
      "replacement": "- **Technology**: Memcached 1.6"
    }
  ],
  "explanation": "Changed caching technology from Redis to Memcached"
}
```

**Pros**: Simple to implement, easy to debug
**Cons**: Line numbers are fragile (whitespace changes break them)

#### Option B: Section-Based Edits (Recommended)
Agent identifies sections by header and replaces content:

```json
{
  "doc_edits": [
    {
      "section": "## Component Details ### Redis Cache",
      "find": "**Technology**: Redis 7.0",
      "replace": "**Technology**: Memcached 1.6"
    }
  ],
  "explanation": "Changed caching technology from Redis to Memcached"
}
```

**Pros**: Robust to formatting changes, matches how humans think
**Cons**: Need fuzzy matching for section headers

#### Option C: Regex-Based Edits (Most Powerful)
Agent generates regex patterns and replacements:

```json
{
  "doc_edits": [
    {
      "pattern": "### Redis Cache\\n.*?\\*\\*Technology\\*\\*: Redis 7\\.0",
      "replacement": "### Memcached Cache\\n- **Purpose**: In-memory caching layer\\n- **Technology**: Memcached 1.6",
      "flags": "DOTALL"
    }
  ],
  "explanation": "Changed caching technology from Redis to Memcached"
}
```

**Pros**: Most flexible, can handle complex multi-line edits
**Cons**: Claude might generate invalid regex, security risk if not sandboxed

### Recommended Approach: Section-Based (Option B)

#### Step 1: Parse Design Doc into Sections
Create a utility to split markdown by headers:

```python
# backend/app/utils/doc_parser.py

from typing import List, Dict
import re

class DocSection:
    def __init__(self, header: str, content: str, level: int):
        self.header = header  # "## Component Details"
        self.content = content  # Text after header until next same-level header
        self.level = level  # 2 for ##, 3 for ###

def parse_sections(markdown: str) -> List[DocSection]:
    """Split markdown into hierarchical sections."""
    sections = []
    lines = markdown.split('\n')

    current_section = None
    current_content = []

    for line in lines:
        header_match = re.match(r'^(#{1,6})\s+(.+)$', line)

        if header_match:
            # Save previous section
            if current_section:
                current_section.content = '\n'.join(current_content).strip()
                sections.append(current_section)

            # Start new section
            level = len(header_match.group(1))
            header_text = header_match.group(2)
            current_section = DocSection(line, "", level)
            current_content = []
        else:
            current_content.append(line)

    # Save last section
    if current_section:
        current_section.content = '\n'.join(current_content).strip()
        sections.append(current_section)

    return sections

def apply_section_edit(sections: List[DocSection], edit: dict) -> List[DocSection]:
    """Apply a section-based edit to the document."""
    target_header = edit["section"]  # "## Component Details ### Redis Cache"
    find_text = edit["find"]
    replace_text = edit["replace"]

    # Find matching section (fuzzy match on header)
    for section in sections:
        if section.header in target_header or target_header in section.header:
            # Replace within this section's content
            section.content = section.content.replace(find_text, replace_text)
            return sections

    raise ValueError(f"Section not found: {target_header}")

def sections_to_markdown(sections: List[DocSection]) -> str:
    """Rebuild markdown from sections."""
    parts = []
    for section in sections:
        parts.append(section.header)
        if section.content:
            parts.append(section.content)
    return '\n\n'.join(parts)
```

#### Step 2: Update Agent Prompt for Doc Edits

```markdown
When the user asks to modify the design document, output edit commands:

{
  "doc_edits": [
    {
      "section": "HEADER_OF_SECTION",
      "find": "TEXT_TO_FIND",
      "replace": "TEXT_TO_REPLACE"
    }
  ],
  "explanation": "What you changed and why"
}

SECTION SYNTAX:
- Use the exact header text from the document
- For nested sections, include parent: "## Component Details ### Redis Cache"
- Section matching is fuzzy (close match is OK)

EDITING PATTERNS:

**Change a single field:**
{
  "section": "### Redis Cache",
  "find": "**Technology**: Redis 7.0",
  "replace": "**Technology**: Memcached 1.6"
}

**Add a bullet point:**
{
  "section": "## Security Considerations",
  "find": "- Data encryption (at rest and in transit)",
  "replace": "- Data encryption (at rest and in transit)\n- Rate limiting to prevent abuse"
}

**Replace entire section content:**
{
  "section": "## Executive Summary",
  "find": "CURRENT_EXECUTIVE_SUMMARY_TEXT",
  "replace": "NEW_EXECUTIVE_SUMMARY_TEXT"
}

**Multiple edits (executed in order):**
{
  "doc_edits": [
    {"section": "### Redis Cache", "find": "Redis", "replace": "Memcached"},
    {"section": "## Data Flow", "find": "queries the Redis cache", "replace": "queries the Memcached cache"}
  ]
}

RULES:
- Be surgical: Only change what's needed
- Test your find/replace: Make sure "find" text exists exactly
- For multi-line changes, use \n in the replacement text
- Always include explanation of what you changed
```

#### Step 3: Update Agent Graph Logic

```python
# backend/app/agent/graph.py

def chat_node(state: AgentState) -> AgentState:
    """Handle conversation with doc editing."""
    llm = create_llm(state.get("model"))

    response = llm.invoke(messages)
    content = response.content.strip()

    # Try to parse as doc edit command
    try:
        edit_response = json.loads(content)

        if "doc_edits" in edit_response:
            from app.utils.doc_parser import parse_sections, apply_section_edit, sections_to_markdown

            # Parse current doc
            current_doc = state.get("design_doc", "")
            sections = parse_sections(current_doc)

            # Apply each edit
            for edit in edit_response["doc_edits"]:
                sections = apply_section_edit(sections, edit)

            # Rebuild document
            updated_doc = sections_to_markdown(sections)

            state["design_doc"] = updated_doc
            state["design_doc_updated"] = True
            state["display_text"] = edit_response.get("explanation", "*(Design document updated)*")
            return state

    except json.JSONDecodeError:
        pass

    # ... rest of function (check for diagram updates, etc.) ...
```

### Advantages of Section-Based Edits

✅ **Massive token savings**: 200 tokens vs 15k tokens for simple changes
✅ **Cost reduction**: ~75x cheaper for typical edits ($0.003 vs $0.225 per edit with Sonnet)
✅ **Faster execution**: 0.5s to generate edit vs 3s to regenerate full doc
✅ **Less error-prone**: Claude can't accidentally rephrase other sections
✅ **Audit trail**: Clear log of what changed (great for debugging)
✅ **Reversible**: Could implement undo by storing edit history

### Disadvantages / Risks

⚠️ **Find/replace failures**: If "find" text doesn't match exactly, edit fails
⚠️ **Section ambiguity**: Multiple sections with similar headers (mitigated by hierarchical syntax)
⚠️ **Complex edits**: Restructuring entire doc is harder (but keep full regeneration as fallback)
⚠️ **Testing burden**: Need extensive tests for edge cases (empty sections, special characters, etc.)

### Mitigation Strategies

1. **Fuzzy matching**: Use difflib to find close matches if exact match fails
2. **Preview mode**: Show user what would change before applying (frontend feature)
3. **Fallback to full regeneration**: If >3 edits or complex restructure, use old approach
4. **Validation**: Check that "find" text exists before asking Claude to edit
5. **Edit templates**: Provide examples for 20+ common edit patterns in prompt

---

## Alternative Considered: sed/awk Commands (Not Recommended)

### Approach
Agent generates actual `sed` commands to execute:

```json
{
  "doc_edits": [
    {"command": "sed -i 's/Redis 7\\.0/Memcached 1.6/g' design_doc.md"}
  ]
}
```

### Why Not Recommended

❌ **Security risk**: Executing arbitrary shell commands (even sandboxed is risky)
❌ **Platform-dependent**: `sed` syntax differs between macOS (BSD) and Linux (GNU)
❌ **Hard for LLM**: Claude struggles with sed escaping rules
❌ **Debugging nightmare**: sed errors are cryptic
❌ **No validation**: Can't preview changes before applying
❌ **Limited power**: sed is line-based, struggles with multi-line markdown

**Verdict**: Section-based edits provide 90% of sed's power with 10% of the complexity.

---

## Implementation Roadmap

### Phase 1: Tool-Based Diagram Editing (2-3 weeks)

**Week 1: Foundation**
- [ ] Define tool schemas in `backend/app/agent/tools.py`
- [ ] Create tool executor in `backend/app/agent/tool_executor.py`
- [ ] Add session_id to AgentState
- [ ] Write unit tests for tool execution

**Week 2: Agent Integration**
- [ ] Update CONVERSATION_PROMPT with tool-calling instructions
- [ ] Modify chat_node to detect and execute tools
- [ ] Add extensive orchestration examples to prompt (10+ patterns)
- [ ] Implement fallback to full JSON if tools fail

**Week 3: Testing & Refinement**
- [ ] Manual testing of common scenarios (add node, remove node, replace component)
- [ ] Load testing (50+ node diagrams with tools)
- [ ] Error handling improvements
- [ ] Add structured logging for tool invocations

### Phase 2: Section-Based Doc Editing (2 weeks)

**Week 1: Parser & Editor**
- [ ] Implement doc_parser.py with section splitting
- [ ] Implement apply_section_edit with fuzzy matching
- [ ] Write comprehensive tests (edge cases, special characters, nested sections)
- [ ] Add validation (check "find" text exists)

**Week 2: Agent Integration**
- [ ] Update CONVERSATION_PROMPT with doc editing instructions
- [ ] Modify chat_node to detect and apply doc edits
- [ ] Add 20+ edit pattern examples to prompt
- [ ] Implement fallback to full regeneration for complex edits

### Phase 3: Monitoring & Optimization (1 week)

- [ ] Add CloudWatch metrics for tool vs full-regeneration usage
- [ ] Track token savings and cost reduction
- [ ] Monitor error rates for tool invocations
- [ ] A/B test with real users (if applicable)
- [ ] Optimize prompts based on failure patterns

---

## Success Metrics

### Diagram Editing
- **Token reduction**: Target 70% reduction in output tokens for simple edits
- **Reliability**: Tool execution success rate >95%
- **Speed**: Sub-2s response time for single-node operations
- **User satisfaction**: Prefer tool-based vs full regeneration (user survey)

### Design Doc Editing
- **Token reduction**: Target 90% reduction for small edits (single section)
- **Cost savings**: Measure $/edit before vs after
- **Accuracy**: Find/replace success rate >90% (log failed matches)
- **Adoption**: % of edits using tools vs full regeneration

---

## Rollback Plan

If tool-based approach has >10% failure rate or causes user-facing errors:

1. **Immediate**: Feature flag to disable tools, revert to full regeneration
2. **Short-term**: Fix critical bugs, improve prompts
3. **Long-term**: If unfixable, document lessons learned and keep current architecture

---

## Open Questions

1. **Does Claude 4.5 Haiku support structured output reliably?**
   - Need to test tool calling accuracy with current model
   - May need to upgrade to Sonnet for better instruction following

2. **Should we allow multi-tool transactions with rollback?**
   - Pro: Atomic changes (all-or-nothing)
   - Con: More complexity, harder to debug

3. **How to handle position estimation for new nodes?**
   - Option A: Agent guesses x/y coordinates
   - Option B: Agent provides "near: node_id" and backend calculates
   - Option C: Just use (0, 0) and rely on auto-layout

4. **Should we expose tools to frontend for manual use?**
   - Could add "Undo" button that reverses last tool invocation
   - Would require storing tool history in session state

5. **How to version control design docs with edit history?**
   - Store list of edits in session state?
   - Would enable "view history" and "revert" features

---

## Conclusion

Both proposed improvements are **technically feasible** and would provide **significant benefits**:

### Tool-Based Diagram Editing
- **Recommended**: Yes, implement in Phase 1
- **Risk level**: Medium (requires careful prompt engineering)
- **Payoff**: High (70% token reduction, better reliability)

### Section-Based Doc Editing
- **Recommended**: Yes, implement in Phase 2
- **Risk level**: Low (fallback to full regen exists)
- **Payoff**: Very High (90% token reduction, 75x cost savings)

### NOT Recommended
- ❌ sed/awk command execution (security + complexity)

**Next Steps**: Review this document, decide on Phase 1 timeline, and begin tool schema design.
