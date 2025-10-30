# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Running the Application

The application requires **two terminal windows** running simultaneously:

### Backend (Terminal 1)
```bash
cd backend
python3 -m uvicorn app.main:app --reload --port 8000
```
Backend runs at: http://127.0.0.1:8000

### Frontend (Terminal 2)
```bash
cd frontend
npm run dev
```
Frontend runs at: http://localhost:5173

### Other Commands
```bash
# Frontend
npm run build          # Production build
npm run lint          # Run ESLint
npm run preview       # Preview production build

# Backend - no test suite currently implemented
pip install -r backend/requirements.txt  # Install dependencies

# Deployment (requires AWS CLI configured)
./deploy-all.sh        # Deploy both frontend and backend
./deploy-backend.sh    # Backend only
./deploy-frontend.sh   # Frontend only
```

## Architecture Overview

InfraSketch is an AI-powered system design tool with a **React frontend** and **FastAPI backend** that uses **LangGraph** to orchestrate a Claude AI agent.

### Request Flow
1. User enters prompt → Frontend POST `/api/generate` → Backend
2. Backend invokes LangGraph agent with `intent: "generate"`
3. Agent calls Claude with system prompt → Claude returns JSON diagram
4. Backend parses JSON, creates session → Returns `{session_id, diagram}`
5. Frontend renders diagram using React Flow

### Conversational Modification Flow
1. User clicks node → Chat panel opens
2. User asks question/requests change → POST `/api/chat` with session_id + node_id
3. Agent retrieves full diagram + conversation history from session
4. Agent calls Claude with context (diagram + node + history)
5. **Critical**: Agent extracts JSON from Claude's response using multiple strategies:
   - Direct JSON parsing
   - Extract from ```json code blocks
   - **Extract JSON embedded in text** (finds `{` and matching `}`)
6. If JSON contains nodes/edges → `diagram_updated: true` → Frontend updates diagram
7. Otherwise → Text response only → Chat panel shows response

### Key Components

**Backend (`backend/app/`)**:
- `main.py` - FastAPI app with CORS for localhost:5173
- `models.py` - Pydantic models for Node, Edge, Diagram, SessionState
- `api/routes.py` - Endpoints for generate, chat, session management, and CRUD operations (add/delete nodes and edges)
- `session/manager.py` - In-memory dict storing session_id → SessionState
- `agent/graph.py` - **LangGraph agent** (see below)
- `agent/prompts.py` - System prompts for Claude
- `utils/secrets.py` - Helper for retrieving API keys (supports both .env and AWS Secrets Manager)

**Frontend (`frontend/src/`)**:
- `App.jsx` - Main component managing state (diagram, sessionId, selectedNode, messages)
- `components/DiagramCanvas.jsx` - React Flow canvas with auto-layout using dagre, supports drag connections between nodes
- `components/ChatPanel.jsx` - Chat UI for node-focused conversations
- `components/CustomNode.jsx` - Styled node component with color coding by type
- `components/InputPanel.jsx` - Initial prompt input for generating diagrams
- `components/NodeTooltip.jsx` - Hover tooltip showing node details
- `components/AddNodeModal.jsx` - Modal for manually adding nodes
- `components/ExportButton.jsx` - Export dropdown with PNG/PDF/Markdown options, includes screenshot capture
- `utils/layout.js` - Auto-layout logic using dagre algorithm
- `api/client.js` - Axios client for backend API

### LangGraph Agent Implementation

The agent (`backend/app/agent/graph.py`) uses LangGraph's `StateGraph` with:

**State Schema**:
```python
{
    "intent": "generate" | "chat",
    "user_message": str,
    "diagram": dict | None,
    "node_id": str | None,
    "conversation_history": list[dict],
    "output": str,
    "diagram_updated": bool,
    "display_text": str  # Text to show in chat (without JSON)
}
```

**Graph Structure**:
- Entry point → `route_intent()` → routes to "generate" or "chat" node
- Both nodes call `create_llm()` which returns Claude 3 Haiku with `max_tokens=4096`
- Both nodes end execution (no loops)

**Critical: JSON Extraction Logic**

Claude often returns text before JSON (e.g., "This is a modification request..."). The `chat_node` has **three extraction strategies**:

1. Try direct `json.loads(content)`
2. If fails, extract from ```json or ``` code blocks
3. **If no code blocks, find embedded JSON**:
   - Find first `{` character
   - Count braces to find matching `}`
   - Extract substring and parse

This is why diagram updates work even when Claude adds explanatory text.

## Environment Setup

Create `.env` file in root:
```env
ANTHROPIC_API_KEY=your-api-key-here
LANGSMITH_TRACING=False  # Optional
```

## API Endpoints

The backend exposes these REST endpoints (all under `/api` prefix):

**POST `/api/generate`** - Generate initial diagram from prompt
- Request: `{ "prompt": string }`
- Response: `{ "session_id": string, "diagram": Diagram }`

**POST `/api/chat`** - Continue conversation about diagram/node
- Request: `{ "session_id": string, "message": string, "node_id": string? }`
- Response: `{ "response": string, "diagram": Diagram? }`

**GET `/api/session/{session_id}`** - Retrieve session state
- Response: `SessionState` object

**POST `/api/session/{session_id}/nodes`** - Manually add a node
- Request: `Node` object
- Response: Updated `Diagram`

**DELETE `/api/session/{session_id}/nodes/{node_id}`** - Delete node and connected edges
- Response: Updated `Diagram`

**PATCH `/api/session/{session_id}/nodes/{node_id}`** - Update node properties
- Request: Updated `Node` object
- Response: Updated `Diagram`

**POST `/api/session/{session_id}/edges`** - Manually add an edge
- Request: `Edge` object
- Response: Updated `Diagram`

**DELETE `/api/session/{session_id}/edges/{edge_id}`** - Delete edge
- Response: Updated `Diagram`

**POST `/api/session/{session_id}/export/design-doc?format={format}`** - Generate comprehensive design document
- Query params: `format` = "pdf" | "markdown" | "both" (default: "pdf")
- Request body: `{ "diagram_image": base64_png_string }` (screenshot from frontend)
- Response: JSON with base64 encoded files: `{ "pdf": { "content": base64, "filename": string }, "markdown": {...}, "diagram_png": {...} }`
- Uses Claude Haiku (max_tokens: 4096) to generate comprehensive technical documentation
- Processing time: 10-30 seconds depending on diagram complexity
- Note: Frontend can also export PNG directly without calling this endpoint

## Data Models

**Node** (backend/app/models.py):
```python
{
    "id": str,
    "type": str,  # cache|database|api|server|loadbalancer|queue|cdn|gateway|storage|service
    "label": str,
    "description": str,
    "inputs": List[str],
    "outputs": List[str],
    "metadata": {"technology": str, "notes": str},
    "position": {"x": float, "y": float}
}
```

**Edge**:
```python
{
    "id": str,
    "source": str,  # node id
    "target": str,  # node id
    "label": str,
    "type": "default" | "animated"
}
```

## Common Issues & Solutions

### Issue: Diagram not updating after chat request
**Cause**: Claude returned text + JSON, but JSON extraction failed
**Solution**: Check backend logs for "✗ Failed to extract JSON". The brace-counting logic should catch this, but if JSON is malformed, agent returns empty nodes/edges array.

### Issue: White screen after generate
**Cause**: Infinite render loop (fixed) or empty diagram
**Solution**: Check browser console for "Number of nodes: 0". If 0, Claude didn't return valid JSON - check backend logs.

### Issue: Token limit error
**Cause**: Claude's response was cut off mid-JSON
**Solution**: `max_tokens=4096` in `create_llm()` should prevent this. If still occurring, increase further.

## Model Configuration

Current model: **Claude 3 Haiku** (`claude-3-haiku-20240307`)
- Cost: $0.25 input / $1.25 output per million tokens (cheapest)
- To upgrade: Change model name in `backend/app/agent/graph.py` → `create_llm()`
- Available models: claude-3-5-sonnet-20241022 (more expensive but better quality)

## Session Management

Sessions are **in-memory only** (not persisted). Restarting backend clears all sessions.

`SessionManager` (backend/app/session/manager.py):
- Stores dict of `session_id: SessionState`
- `create_session()` - generates UUID, stores diagram
- `add_message()` - appends to conversation history
- `update_diagram()` - replaces diagram when modified

## Frontend State Management

`App.jsx` is the single source of truth:
- `diagram` - current diagram (passed to DiagramCanvas)
- `sessionId` - backend session ID
- `selectedNode` - currently clicked node (opens ChatPanel)
- `messages` - conversation history for ChatPanel

When `diagram` prop changes in `DiagramCanvas.jsx`, the `useEffect` hook:
1. Transforms backend diagram format to React Flow format
2. Applies auto-layout using dagre algorithm (hierarchical top-to-bottom layout)
3. Calls `setNodes()` and `setEdges()` to update canvas

**User Interactions:**
- Click node → Opens chat panel focused on that node
- Hover node → Shows tooltip with details
- Right-click node → Context menu to delete
- Drag from node handle → Create new connection
- Right-click edge → Context menu to delete
- Click "Add Node" button → Opens modal for manual node creation
- Click "New Design" button → Clears session and starts fresh

## Debugging

**Backend logs** (`print` statements in graph.py):
- "=== CLAUDE RESPONSE ===" - shows raw Claude output
- "✓ Successfully parsed" - JSON extraction succeeded
- "✗ Failed to parse" - shows error and attempted JSON string

**Frontend logs** (browser console):
- "API Response:" - full backend response
- "Has diagram update?" - whether backend returned diagram
- "DiagramCanvas received diagram" - what canvas is rendering

Both servers have auto-reload enabled (`--reload` for backend, Vite HMR for frontend).

## Deployment

**Production URLs:**
- Frontend: https://dr6smezctn6x0.cloudfront.net
- API: https://b31htlojb0.execute-api.us-east-1.amazonaws.com/prod

**Infrastructure:**
- Backend: AWS Lambda + API Gateway
- Frontend: S3 + CloudFront
- Secrets: AWS Secrets Manager (ANTHROPIC_API_KEY)

**Deployment scripts** (`./deploy-*.sh`):
- Backend: Packages dependencies for Linux, creates Lambda zip, uploads to S3, updates function
- Frontend: Builds React app, syncs to S3, invalidates CloudFront cache

## Important Implementation Details

**Auto-Layout Algorithm:**
- Uses dagre library for hierarchical graph layout
- Applied automatically on every diagram update in `utils/layout.js`
- Direction: Top-to-bottom (TB)
- Node spacing: 150px horizontal, 100px vertical

**CORS Configuration:**
- Backend allows all origins (`allow_origins=["*"]`)
- Credentials set to False for compatibility
- Required for local dev (localhost:5173 → localhost:8000)

**State Synchronization:**
- Backend is source of truth for diagram data
- Frontend makes API call for any modification (add/delete node/edge)
- Agent-generated updates flow through `/api/chat` endpoint
- Manual updates flow through CRUD endpoints

**Response Handling:**
- Agent returns `display_text` separate from JSON diagram
- When diagram updates, frontend shows "*(Graph has been updated)*" message
- Text before/after JSON in Claude's response is preserved in chat

**Error Recovery:**
- If JSON parsing fails completely, agent returns empty diagram with error flag
- Frontend validates nodes/edges arrays exist before rendering
- Session not found returns 404, triggering user to start new session

## Design Document Export Feature

**Overview:**
The app can generate comprehensive technical design documents from diagrams using a dedicated LLM call, plus direct diagram image export.

**Architecture:**
- **Standalone endpoint**: `/api/session/{session_id}/export/design-doc`
- **Separate from chat agent**: Uses dedicated prompt optimized for technical writing
- **Model**: Claude 3 Haiku (max_tokens: 4096)
- **Diagram capture**: Frontend screenshots React Flow canvas using `html-to-image`

**Components:**
- `backend/app/agent/doc_generator.py` - LLM call for document generation
- `backend/app/agent/prompts.py` - `DESIGN_DOC_PROMPT` with technical writing instructions
- `backend/app/utils/diagram_export.py` - PDF conversion utilities (with ReportLab fallback)
- `frontend/src/components/ExportButton.jsx` - Dropdown menu UI component with screenshot capture
- `frontend/node_modules/html-to-image` - Screenshot library for capturing React Flow diagram

**Document Generation Flow:**
1. User clicks "Export Design Doc" button → Dropdown menu appears
2. User selects format (PNG, PDF, Markdown, or Both)
3. **Frontend captures screenshot**:
   - Uses `html-to-image` to capture `.react-flow__viewport`
   - Temporarily hides edge labels (to avoid rendering artifacts)
   - Captures at 2x pixel ratio for high quality
   - Converts to base64 PNG
4. **PNG-only export**: Downloads screenshot directly (instant, no backend call)
5. **PDF/Markdown export**:
   - Frontend sends screenshot + session_id to backend
   - Backend retrieves session (diagram + conversation history)
   - Calls Claude with specialized technical writer prompt
   - Embeds frontend screenshot in document (not generated PNG)
   - Converts markdown to PDF using ReportLab (or WeasyPrint if available)
   - Returns base64 encoded files
6. Frontend decodes base64 and triggers browser downloads

**Document Structure:**
- Executive Summary
- System Overview
- Architecture Diagram (embedded screenshot from frontend)
- Component Details (for each node)
- Data Flow
- Infrastructure Requirements
- Scalability & Reliability
- Security Considerations
- Trade-offs & Alternatives
- Implementation Phases
- Future Enhancements
- Appendix

**Dependencies:**
- **Frontend**: `html-to-image` - Captures React Flow diagram as PNG
- **Backend**:
  - `Pillow` - Image processing
  - `markdown2` - Markdown to HTML conversion
  - `reportlab` - PDF generation (primary, no system dependencies)
  - `weasyprint` - PDF generation (fallback, requires: `brew install pango`)

**Export Formats:**
- **🖼️ PNG**: Just the diagram image (instant, no LLM call)
- **📕 PDF**: Full design document with embedded diagram
- **📝 Markdown**: Markdown doc + separate diagram PNG
- **📦 PDF + Markdown**: Both formats together

**Key Implementation Details:**
- Edge labels are hidden during screenshot to avoid black bar rendering artifacts
- Frontend screenshot matches exact React Flow appearance (arrows, layout, colors)
- ReportLab is used as primary PDF generator (works out-of-box on macOS)
- WeasyPrint fallback requires system libraries but produces better formatting
- Screenshot uses 2x pixel ratio for high-resolution export
