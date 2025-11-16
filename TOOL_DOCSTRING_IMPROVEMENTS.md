# Tool Docstring Improvements - Anthropic Best Practices

## Status: ✅ **COMPLETE**

All 5 tool docstrings have been enhanced following Anthropic's best practices for AI agent tool documentation.

---

## Research Summary

Based on Anthropic's official documentation and best practices:

**Key Requirements:**
1. **Class docstrings**: 3-4+ sentences minimum
2. **When to use**: Explain scenarios where tool should be invoked
3. **What it does**: Clear explanation of the operation performed
4. **What it returns**: Describe the output/result
5. **Parameter descriptions**: Detailed Field descriptions with examples
6. **Constraints and warnings**: CRITICAL instructions for proper usage
7. **Examples**: Concrete examples of valid inputs

---

## Changes Made

### 1. AddNodeTool (Lines 12-76)

**Before:**
```python
"""Add a new component/node to the system architecture diagram."""
```

**After:**
```python
"""
Add a new component/node to the system architecture diagram.

Use this tool when the user wants to introduce a new component to their system design,
such as adding a cache layer, load balancer, database, API service, or any other
infrastructure component. This tool creates the node but does NOT create any connections
to other nodes - you must use add_edge separately to connect this node to others.
Returns the updated diagram with the new node included.

IMPORTANT: Generate a unique, descriptive node_id for NEW nodes (e.g., 'redis-cache-1',
'api-gateway-lb-1'). Do NOT use generic IDs like 'node-123'.
"""
```

**Field Enhancements:**
- `node_id`: Added examples, naming conventions, clarified difference between ID and display name
- `type`: Listed all valid types, explained visual impact
- `label`: Clarified it's the display name, added examples
- `description`: Added length guidance (1-2 sentences), example
- `technology`: Emphasized specificity with examples
- `position`: Explained logical positioning guidelines with x-coordinate ranges

---

### 2. DeleteNodeTool (Lines 79-96)

**Before:**
```python
"""Remove a component/node from the system architecture diagram."""
```

**After:**
```python
"""
Remove a component/node from the system architecture diagram.

Use this tool when the user wants to remove an existing component from their system design.
This tool automatically deletes ALL edges (connections) that are connected to this node,
so you do NOT need to manually delete edges first. Returns the updated diagram without the node.

CRITICAL: You MUST use the EXACT node_id from the "Nodes (with exact IDs)" section in the
diagram context. Do NOT guess or make up node IDs. If unsure about the node_id, ask the user.
"""
```

**Field Enhancements:**
- `node_id`: Emphasized exact ID requirement with example format, explained automatic edge deletion

---

### 3. UpdateNodeTool (Lines 99-147)

**Before:**
```python
"""Update properties of an existing node."""
```

**After:**
```python
"""
Update properties of an existing component/node in the diagram.

Use this tool when the user wants to modify an existing component without removing it,
such as changing the technology stack (PostgreSQL → MongoDB), updating the display name,
modifying the description, or changing the component type. This tool only updates the
specific fields you provide - all other fields remain unchanged. Returns the updated diagram.

CRITICAL: You MUST use the EXACT node_id from the "Nodes (with exact IDs)" section in the
diagram context. Do NOT guess or make up node IDs. If unsure about the node_id, ask the user.
"""
```

**Field Enhancements:**
- `node_id`: Emphasized exact ID requirement with example
- `label`: Explained when to provide, added examples
- `description`: Added length guidance and example
- `technology`: Emphasized specificity, added examples
- `type`: Listed valid types, explained visual impact
- `notes`: Added examples of typical use cases

---

### 4. AddEdgeTool (Lines 150-195)

**Before:**
```python
"""Add a new connection between two nodes."""
```

**After:**
```python
"""
Create a new connection (edge) between two existing nodes in the diagram.

Use this tool when the user wants to establish a data flow or relationship between two components,
such as connecting an API to a database, linking a load balancer to backend servers, or showing
message flow from a queue to a worker. The edge represents what flows between the nodes (data,
requests, messages, etc.). Both source and target nodes must already exist in the diagram - if they
don't, use add_node first to create them. Returns the updated diagram with the new connection.

CRITICAL: You MUST use the EXACT node IDs from the "Nodes (with exact IDs)" section for source
and target parameters. Do NOT guess or make up node IDs. If the nodes don't exist, this operation
will be skipped gracefully with a warning.
"""
```

**Field Enhancements:**
- `edge_id`: Added naming convention pattern ('source-to-target'), examples
- `source`: Emphasized exact ID requirement with example format
- `target`: Emphasized exact ID requirement with example format
- `label`: Explained importance of describing WHAT flows (not just "connects to"), added examples
- `type`: Explained difference between 'default' and 'animated', when to use each

---

### 5. DeleteEdgeTool (Lines 198-219)

**Before:**
```python
"""Delete a connection between nodes."""
```

**After:**
```python
"""
Remove a connection (edge) between nodes in the diagram.

Use this tool when the user wants to eliminate a data flow or relationship between components,
such as removing a direct API-to-database connection when adding a cache layer in between,
or deleting obsolete connections when restructuring the architecture. This tool only removes
the connection - the nodes themselves remain in the diagram. Returns the updated diagram without
the deleted edge.

CRITICAL: You MUST use the EXACT edge_id from the "Connections (with exact edge IDs)" section
in the diagram context. Do NOT guess or make up edge IDs. If the edge doesn't exist or was
already deleted, this operation will be skipped gracefully with a warning (not treated as an error).
"""
```

**Field Enhancements:**
- `edge_id`: Emphasized exact ID requirement with example format, explained graceful skipping behavior

---

## Key Improvements Summary

### 1. **Detailed Class Docstrings**
All tools now have 3-4 paragraph docstrings explaining:
- What the tool does
- When to use it
- What it returns
- Critical usage requirements

### 2. **CRITICAL Instructions**
Every tool that references existing nodes/edges now has a "CRITICAL" section emphasizing:
- Must use EXACT IDs from diagram context
- Do NOT guess or make up IDs
- Graceful handling when IDs don't exist

### 3. **Rich Field Descriptions**
All Field descriptions now include:
- Concrete examples (e.g., 'redis-cache-1', 'PostgreSQL 15')
- Constraints (e.g., "Must be one of: cache, database, api...")
- Guidance (e.g., "Use lowercase with hyphens")
- When to provide (for optional fields)

### 4. **Behavioral Clarity**
Explained important behaviors:
- `DeleteNodeTool`: Automatically deletes connected edges
- `UpdateNodeTool`: Only updates provided fields, others unchanged
- `AddEdgeTool`: Both nodes must exist first
- `DeleteEdgeTool`: Gracefully skips if edge doesn't exist

### 5. **Naming Conventions**
Documented ID naming patterns:
- Node IDs: 'redis-cache-1', 'api-gateway-lb-1' (descriptive + counter)
- Edge IDs: 'api-to-cache', 'lb-to-backend-1' (source-to-target pattern)

---

## Expected Benefits

### 1. **Reduced Node ID Hallucination**
The repeated "CRITICAL" instructions and exact ID examples should help Claude:
- Recognize the importance of using exact IDs
- Understand where to find the correct IDs (diagram context)
- Avoid guessing or making up node/edge IDs

### 2. **Better Tool Selection**
Detailed "when to use" sections help Claude choose the right tool:
- `UpdateNodeTool` vs `DeleteNodeTool` + `AddNodeTool`
- Understanding when to use `add_edge` after `add_node`
- Knowing automatic edge deletion happens with `delete_node`

### 3. **Higher Quality Parameters**
Rich field descriptions lead to better inputs:
- Specific technologies (e.g., "PostgreSQL 15" not "database")
- Descriptive edge labels (e.g., "User auth requests" not "connects to")
- Proper ID naming conventions

### 4. **Fewer Execution Errors**
Understanding graceful handling reduces failed operations:
- Claude knows `delete_edge` won't fail if edge missing
- Claude knows `add_edge` will skip if nodes don't exist
- Claude understands the execution order implications

---

## Testing Recommendations

Test these scenarios to verify improvements:

1. **Add component between existing ones**:
   - "Add Redis cache between API and database"
   - Should use exact IDs from context for source/target in edges

2. **Update technology**:
   - "Switch from PostgreSQL to MongoDB"
   - Should use exact node ID, update only technology field

3. **Remove component**:
   - "Remove the load balancer"
   - Should use exact node ID, understand edges auto-deleted

4. **Complex multi-step**:
   - "Add message queue and worker service for async job processing"
   - Should create both nodes first, then add edges between them

---

## Files Modified

1. **`backend/app/agent/tools.py`** (Lines 12-219)
   - Enhanced all 5 tool class docstrings (3-4 paragraphs each)
   - Enhanced all Field descriptions with examples and constraints
   - Added ~95 lines of documentation

**Total documentation added**: ~95 lines
**Documentation quality**: Anthropic-compliant with 3-4+ sentence docstrings and detailed field descriptions

---

## Next Steps

1. **User Testing**: Have user test with complex requests like:
   - "Add more load balancers"
   - "Add caching layer between API and database"
   - "Replace PostgreSQL with MongoDB"

2. **Monitor for ID Hallucination**: Watch backend logs for:
   - `⚠️ Source node 'X' not found` (indicates Claude used wrong ID)
   - `✓ Tool executed successfully` (indicates correct IDs used)

3. **Iterate if Needed**: If Claude still hallucinates IDs:
   - Consider adding examples directly in CONVERSATION_PROMPT
   - Add stricter validation with error messages
   - Consider few-shot learning examples in prompt

---

## Conclusion

All 5 tools now have **Anthropic-compliant documentation** with:
- ✅ 3-4 paragraph class docstrings
- ✅ "When to use" guidance
- ✅ "What it returns" explanation
- ✅ Detailed Field descriptions with examples
- ✅ CRITICAL instructions for exact ID usage
- ✅ Behavioral clarifications (automatic edge deletion, graceful skipping)
- ✅ Naming convention guidelines

This should significantly reduce Claude's tendency to hallucinate node IDs and improve overall tool execution reliability.
