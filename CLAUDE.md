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
- `main.py` - FastAPI app with CORS, rate limiting, optional auth, and request logging middleware
- `models.py` - Pydantic models for Node, Edge, Diagram, SessionState
- `api/routes.py` - Endpoints for generate, chat, session management, CRUD operations, with structured event logging
- `session/manager.py` - **Hybrid session storage** (in-memory for local, DynamoDB for Lambda)
- `session/dynamodb_storage.py` - DynamoDB-backed persistent session storage
- `lambda_handler.py` - Lambda entry point that routes API Gateway requests and async task invocations
- `agent/graph.py` - **LangGraph agent** (see below)
- `agent/prompts.py` - System prompts for Claude
- `agent/doc_generator.py` - Standalone LLM call for design document generation
- `middleware/rate_limit.py` - Token bucket algorithm, 60 req/min per IP by default
- `middleware/auth.py` - Optional API key auth (enable via REQUIRE_API_KEY=true)
- `middleware/logging.py` - Request/response logging middleware
- `utils/secrets.py` - Helper for retrieving API keys (supports both .env and AWS Secrets Manager)
- `utils/logger.py` - Structured JSON logging for CloudWatch (tracks events, errors, performance)
- `utils/diagram_export.py` - PDF/image generation utilities

**Frontend (`frontend/src/`)**:
- `App.jsx` - Main component managing state (diagram, sessionId, selectedNode, messages, designDoc, designDocLoading, chatPanelWidth)
- `components/DiagramCanvas.jsx` - React Flow canvas with auto-layout using dagre, supports drag connections between nodes
- `components/ChatPanel.jsx` - Chat UI for node-focused conversations, resizable with width tracking
- `components/DesignDocPanel.jsx` - Editable design doc panel with TipTap editor, shows loading overlay during generation, resizable with width tracking
- `components/NodePalette.jsx` - Bottom toolbar for adding nodes, slides up from bottom, resizable vertically, adapts to both side panels
- `components/CustomNode.jsx` - Styled node component with color coding by type
- `components/InputPanel.jsx` - Initial prompt input for generating diagrams
- `components/NodeTooltip.jsx` - Hover tooltip showing node details
- `components/AddNodeModal.jsx` - Modal for manually adding nodes (opened from NodePalette or header button)
- `components/ExportButton.jsx` - Export dropdown with PNG/PDF/Markdown options, includes screenshot capture
- `utils/layout.js` - Auto-layout logic using dagre algorithm
- `api/client.js` - Axios client for backend API, includes `pollDesignDocStatus()` for async generation

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
- Both nodes call `create_llm()` which returns Claude Haiku 4.5 with `max_tokens=32768`
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

**POST `/api/session/{session_id}/design-doc/generate`** - Start background design document generation
- Request body: `{ "diagram_image": base64_png_string? }` (optional screenshot)
- Response: `{ "status": "started", "message": "..." }` (returns immediately)
- Starts generation in background using FastAPI BackgroundTasks
- Non-blocking: Chat and other operations work while generating

**GET `/api/session/{session_id}/design-doc/status`** - Poll design document generation status
- Response: `{ "status": "not_started" | "generating" | "completed" | "failed", "elapsed_seconds": float?, "design_doc": string?, "error": string? }`
- Frontend polls every 2 seconds until complete
- Returns generated document when `status === "completed"`

**PATCH `/api/session/{session_id}/design-doc`** - Update design document content
- Request body: `{ "content": string }`
- Used for manual edits in the design doc panel

**POST `/api/session/{session_id}/design-doc/export?format={format}`** - Export stored design document
- Query params: `format` = "pdf" | "markdown" | "both" (default: "pdf")
- Request body: `{ "diagram_image": base64_png_string }` (screenshot from frontend)
- Response: JSON with base64 encoded files: `{ "pdf": { "content": base64, "filename": string }, "markdown": {...}, "diagram_png": {...} }`
- Fast: Uses already-generated document from session state
- Note: Frontend can also export PNG directly without calling this endpoint

**POST `/api/session/{session_id}/export/design-doc?format={format}`** - DEPRECATED: Generate and export in one call
- Legacy endpoint that blocks for 30-150 seconds
- Use the new generate → poll → export flow instead

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

**DesignDocStatus** (for async generation tracking):
```python
{
    "status": "not_started" | "generating" | "completed" | "failed",
    "error": Optional[str],
    "started_at": Optional[float],  # Unix timestamp
    "completed_at": Optional[float]  # Unix timestamp
}
```

**SessionState** (includes design doc state):
```python
{
    "session_id": str,
    "diagram": Diagram,
    "messages": List[Message],
    "current_node": Optional[str],
    "design_doc": Optional[str],  # Generated markdown content
    "design_doc_status": DesignDocStatus,  # Generation status tracking
    "model": str  # Model used for this session (e.g., "claude-haiku-4-5-20251001")
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
**Solution**: `max_tokens=32768` in `create_llm()` should prevent this. Haiku 4.5 supports up to 64k output tokens.

### Issue: Design doc generation stuck or not updating
**Cause**: Frontend not polling correctly or backend task failed
**Solution**:
1. Check backend logs for "=== BACKGROUND: GENERATE DESIGN DOC ===" and completion message
2. Check browser console for polling logs: "Generation status: generating (Xs elapsed)"
3. Call `/design-doc/status` endpoint directly to check status
4. If `status === "failed"`, check the `error` field for details
5. Verify session exists and has diagram data

### Issue: Session not found (404) after generating diagram
**Cause**: DynamoDB save failed due to float/Decimal conversion issue
**Solution**: Check Lambda logs for "Error saving session". The `dynamodb_storage.py` has `convert_floats_to_decimals()` function that recursively converts all floats to Decimals before saving. If this fails, sessions won't persist.

### Issue: Lambda crashes on startup in production
**Cause**: Missing IAM permissions or DynamoDB table creation timeout
**Solution**:
1. Verify IAM role has all required DynamoDB permissions (including `TagResource`)
2. Check if `infrasketch-sessions` table exists: `aws dynamodb describe-table --table-name infrasketch-sessions`
3. First Lambda cold start may take 20+ seconds due to table creation
4. Check logs for "Creating DynamoDB table" or "DynamoDB table exists"

## Model Configuration

Users can now select their preferred AI model at diagram generation time via a dropdown in the input panel.

**Available Models:**
- **Claude Haiku 4.5** (`claude-haiku-4-5`) - Default
  - Alias automatically points to latest Haiku version
  - Cost: $1 input / $5 output per million tokens
  - Speed: 2x faster than Sonnet 4.5
  - Max output: 64k tokens (configured to 32k)
  - Best for: Most use cases, fast iteration

- **Claude Sonnet 4.5** (`claude-sonnet-4-5`)
  - Alias automatically points to latest Sonnet version
  - Cost: ~$3 input / $15 output per million tokens (3x more expensive)
  - Quality: Superior reasoning and architectural insights
  - Max output: 64k tokens (configured to 32k)
  - Best for: Complex systems requiring nuanced design decisions

**Implementation Details:**
- Model choice is stored in session state (persists across chat and design doc generation)
- Selected model is used for all session operations: diagram generation, chat, and design doc creation
- Uses model aliases (`claude-haiku-4-5`, `claude-sonnet-4-5`) which auto-update to latest versions
- Default: Haiku 4.5 if no model specified
- Model parameter flows: Frontend → API → SessionState → Agent/DocGenerator

## Session Management

**Hybrid Storage Architecture:**
- **Local development**: In-memory dict (`session_id → SessionState`)
- **AWS Lambda**: DynamoDB persistent storage (`infrasketch-sessions` table)
- Auto-detects environment via `AWS_LAMBDA_FUNCTION_NAME` env variable

`SessionManager` (backend/app/session/manager.py):
- `create_session()` - generates UUID, stores diagram (saves to DynamoDB in Lambda)
- `get_session()` - retrieves session from appropriate storage backend
- `update_diagram()` - replaces diagram when modified (persists to DynamoDB in Lambda)
- `add_message()` - appends to conversation history (persists to DynamoDB in Lambda)
- `update_design_doc()` - stores generated or edited design document
- `set_design_doc_status()` - updates generation status with automatic timestamp tracking
- `get_design_doc_status()` - retrieves current generation status

**DynamoDB Implementation** (`session/dynamodb_storage.py`):
- Table: `infrasketch-sessions` (pay-per-request billing)
- TTL: Sessions expire after 24 hours
- **Critical**: Converts Python `float` to `Decimal` before saving (DynamoDB requirement)
- Shares sessions across all Lambda instances for async operations
- Auto-creates table on first run if it doesn't exist

## Frontend State Management

`App.jsx` is the single source of truth:
- `diagram` - current diagram (passed to DiagramCanvas)
- `sessionId` - backend session ID
- `selectedNode` - currently clicked node (opens ChatPanel)
- `messages` - conversation history for ChatPanel
- `designDoc` - generated design document markdown content
- `designDocOpen` - whether design doc panel is visible
- `designDocLoading` - whether design doc is currently being generated (shows loading overlay)
- `isMobile` - mobile viewport detection (≤768px)

When `diagram` prop changes in `DiagramCanvas.jsx`, the `useEffect` hook:
1. Transforms backend diagram format to React Flow format
2. Applies auto-layout using dagre algorithm (hierarchical top-to-bottom layout)
3. Calls `setNodes()` and `setEdges()` to update canvas

**User Interactions (Desktop >768px):**
- Click node → Opens chat panel focused on that node
- Hover node → Shows tooltip with details
- Right-click node → Context menu to delete
- Drag from node handle → Create new connection
- Right-click edge → Context menu to delete
- Click floating pencil button → Opens NodePalette toolbar from bottom
- Click node type in palette → Opens AddNodeModal with pre-selected type
- Click "Add Node" button (header) → Opens modal for manual node creation
- Click "Create Design Doc" button → Starts async generation, opens panel with loading overlay
- Click "New Design" button → Clears session and starts fresh
- Drag palette top edge → Resize palette height (min: 60px, max: 800px)
- Drag chat panel left edge → Resize chat panel width
- Drag design doc panel right edge → Resize design doc panel width

**User Interactions (Mobile ≤768px):**
- Click node → Opens chat panel as fullscreen modal (hides diagram)
- Click X in chat header → Returns to diagram
- Click "Create Design Doc" → Opens design doc as fullscreen modal (hides diagram)
- Click X in design doc header → Returns to diagram
- Node palette → Fullscreen width, 2-column grid on phones (<480px)
- React Flow controls → Hidden (use pinch-to-zoom instead)
- All panels → Non-resizable on mobile
- Header → Stacks vertically with buttons in horizontal row
- Landing page → Single-column layout, smaller fonts
- Tooltips → Max width constrained to viewport

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
- Frontend: https://infrasketch.net (also available at legacy URL: https://dr6smezctn6x0.cloudfront.net)
- API: https://b31htlojb0.execute-api.us-east-1.amazonaws.com/prod

**Infrastructure:**
- Backend: AWS Lambda + API Gateway (with execution logging enabled)
  - Timeout: 300 seconds (5 minutes) for design doc generation
  - Memory: 512 MB
  - Runtime: Python 3.11
  - IAM permissions: DynamoDB (GetItem, PutItem, UpdateItem, DeleteItem, CreateTable, TagResource), Lambda (InvokeFunction for self-invocation), Secrets Manager
- Session Storage: DynamoDB table `infrasketch-sessions` (pay-per-request, 24hr TTL)
- Frontend: S3 + CloudFront (with access logging to S3)
- Secrets: AWS Secrets Manager (ANTHROPIC_API_KEY)
- Monitoring: CloudWatch Logs, Metrics, and Dashboard
- Weekly Reports: Lambda function triggered by EventBridge (Mondays 9 AM PST)

**Deployment scripts** (`./deploy-*.sh`):
- Backend: Packages dependencies for Linux, creates Lambda zip, uploads to S3, updates function
- Frontend: Builds React app, syncs to S3, invalidates CloudFront cache

**Logging Resources:**
- CloudWatch Log Groups:
  - `/aws/lambda/infrasketch-backend` - Application logs with structured JSON events
  - `/aws/apigateway/infrasketch-api` - API Gateway execution logs
- S3 Bucket: `infrasketch-cloudfront-logs-059409992371` - CloudFront access logs
- Dashboard: `InfraSketch-Overview` - Real-time metrics and usage analytics

## Mobile Responsive Design

**Responsive Breakpoints:**
- **Desktop**: >1024px - Full desktop experience with resizable panels
- **Tablet**: 768px-1024px - Reduced panel widths, maintained functionality
- **Mobile**: ≤768px - Modal panels, simplified interactions
- **Phone**: ≤480px - Extra compact layout, 2-column grids

**Mobile-First Approach:**
The app uses a hybrid CSS + JavaScript approach for mobile optimization:
- **CSS Media Queries** ([App.css](frontend/src/App.css:1568-1959), [NodePalette.css](frontend/src/components/NodePalette.css:163-206)): Handle layout, typography, spacing
- **JavaScript Detection**: Mobile components (ChatPanel, DesignDocPanel) detect viewport width and switch to modal mode

**Key Mobile Optimizations:**
1. **Fullscreen Modals**: Side panels become fullscreen overlays on mobile
2. **Touch-Friendly Targets**: Minimum 44px height for all interactive elements
3. **Hidden Controls**: React Flow zoom buttons hidden (use pinch-to-zoom)
4. **Simplified Navigation**: Close buttons replace resize handles on mobile
5. **Responsive Typography**: Font sizes scale down proportionally
6. **Grid Layouts**: Multi-column grids collapse to 1-2 columns on small screens
7. **Viewport-Based Sizing**: Elements use `calc()` and viewport units for responsive sizing

**Mobile Components:**
- `ChatPanel` - Adds `mobile-modal` class when `window.innerWidth ≤ 768`
- `DesignDocPanel` - Adds `mobile-modal` class when `window.innerWidth ≤ 768`
- `App.jsx` - Hides diagram when mobile panels are open (fullscreen modal behavior)
- `NodePalette` - Uses CSS-only responsive grid (no JS changes needed)

**Testing Mobile:**
- Chrome DevTools → Toggle Device Toolbar (Cmd+Shift+M)
- Test breakpoints: 375px (iPhone SE), 768px (iPad), 1024px (iPad Pro)
- Verify touch targets are ≥44px

## Important Implementation Details

**Panel Resizing Architecture:**
All resizable panels (DesignDocPanel, ChatPanel, NodePalette) use a consistent performance-optimized pattern:
- **requestAnimationFrame (RAF) throttling**: Mouse move events throttled to 60fps for smooth resizing
- **Width/Height tracking**: Panels notify parent component of size changes via `onWidthChange` callback
- **Throttled parent notifications**: Parent updates throttled to 16ms (60fps) to prevent excessive re-renders
- **useCallback optimization**: All handler functions wrapped in useCallback to prevent unnecessary re-renders
- **CSS will-change**: GPU acceleration enabled on resizing elements
- **Dynamic positioning**: NodePalette adjusts left/right edges based on actual panel widths (not hardcoded)

**NodePalette Specific Behavior:**
- Slides up from bottom (not left/right, to avoid conflict with side panels)
- Visibility controlled by `chatPanelOpen={!!diagram}` not `!!selectedNode` (ChatPanel always rendered when diagram exists)
- Acts as persistent toolbar (stays open until X button clicked)
- Default height: 120px, Min: 60px, Max: 800px
- Compact design: 70px min card width, 11px font size, 8px gaps
- Color-coded cards matching node type colors with hover tooltips

**Auto-Layout Algorithm:**
- Uses dagre library for hierarchical graph layout
- Applied automatically on every diagram update in `utils/layout.js`
- Direction: Top-to-bottom (TB)
- Node spacing: 150px horizontal, 100px vertical

**CORS Configuration:**
- Backend allows specific origins in production: CloudFront URL, localhost:5173
- Extra origins can be added via `EXTRA_ALLOWED_ORIGINS` env var (comma-separated)
- Credentials enabled for specific origins
- See `main.py` ALLOWED_ORIGINS list

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

## Design Document Feature

**Overview:**
The app generates comprehensive technical design documents from diagrams using **asynchronous background generation** with polling, allowing users to continue chatting while the document is being created.

**Architecture:**
- **Asynchronous generation**:
  - **Local**: Uses FastAPI BackgroundTasks
  - **Lambda**: Uses async self-invocation (`InvocationType='Event'`) to bypass API Gateway 30s timeout
- **Lambda async flow**:
  1. `/design-doc/generate` endpoint triggers Lambda async invocation with `boto3`
  2. `lambda_handler.py` detects `async_task` payload and routes to background function
  3. Background function runs in separate Lambda instance (up to 5 minutes)
  4. Updates session status in DynamoDB (shared across instances)
  5. Frontend polls `/design-doc/status` every 2 seconds until complete
- **Status tracking**: `DesignDocStatus` model tracks `not_started`, `generating`, `completed`, `failed`
- **Separate from chat agent**: Uses dedicated prompt optimized for technical writing
- **Model**: Claude Haiku 4.5 (max_tokens: 32768)
- **Generation time**: 30-150 seconds depending on diagram complexity
- **Diagram capture**: Frontend screenshots React Flow canvas using `html-to-image`

**Components:**
- `backend/app/models.py` - `DesignDocStatus` model for status tracking
- `backend/app/session/manager.py` - Status management methods (`set_design_doc_status`, `get_design_doc_status`)
- `backend/app/agent/doc_generator.py` - LLM call for document generation
- `backend/app/agent/prompts.py` - `DESIGN_DOC_PROMPT` with technical writing instructions
- `backend/app/utils/diagram_export.py` - PDF conversion utilities (with ReportLab fallback)
- `backend/app/api/routes.py` - Background task function `_generate_design_doc_background()`
- `frontend/src/components/DesignDocPanel.jsx` - Editable design doc panel with TipTap editor
- `frontend/src/api/client.js` - `pollDesignDocStatus()` function for status polling
- `frontend/node_modules/html-to-image` - Screenshot library for capturing React Flow diagram

**Document Generation Flow:**
1. User clicks "Create Design Doc" button
2. **Frontend immediately**:
   - Opens design doc panel with loading overlay ("Generating... may take 1-2 minutes")
   - Calls `/design-doc/generate` endpoint (returns immediately with `status: "started"`)
   - Starts polling `/design-doc/status` every 2 seconds
   - Console logs show progress: "Generation status: generating (23s elapsed)"
3. **Backend background task**:
   - Retrieves session (diagram + conversation history)
   - Calls Claude with specialized technical writer prompt
   - Stores generated markdown in session state
   - Updates status to `completed` or `failed`
4. **Frontend polling detects completion**:
   - Receives generated document from status endpoint
   - Updates panel with editable document content
   - Loading overlay disappears, showing TipTap editor
5. **User can**:
   - Edit document inline with formatting toolbar
   - Auto-saves edits after 3 seconds (debounced)
   - Export to PDF, Markdown, or PNG via dropdown
   - Continue chatting while all this happens (non-blocking!)
   - **Ask the chat bot to make edits** to the design document

**Design Document Chat Editing:**
Users can ask the chat bot to modify the design document. The bot is instructed to:
- **Make surgical, targeted edits**: Only modify the specific parts requested
- **Preserve all unchanged content exactly**: Copy unchanged sections word-for-word from the current document
- **Avoid rewriting or "improving" other sections**: This prevents unwanted changes to parts the user didn't ask to modify
- **Return the full updated document**: While only the requested parts should change, the bot must return the complete document

The bot receives the **full design document** in its context (not just a preview), enabling it to accurately preserve unchanged sections. This approach minimizes token usage and prevents accidental rewrites of unrelated content.

**Example interactions:**
- ✅ "Change Redis to Memcached in the caching section" → Bot changes only that technology name
- ✅ "Add a bullet point about rate limiting to the Security section" → Bot adds only that point
- ✅ "Fix the typo in the Executive Summary" → Bot fixes only that typo
- ❌ "Improve the document" → Bot suggests improvements instead of making changes (subjective)

**Export Flow (After Generation):**
1. User selects format from export dropdown (PNG, PDF, Markdown, or Both)
2. **Frontend captures screenshot**:
   - Uses `html-to-image` to capture `.react-flow__viewport`
   - Temporarily hides edge labels (to avoid rendering artifacts)
   - Captures at 2x pixel ratio for high quality
   - Converts to base64 PNG
3. **PNG-only export**: Downloads screenshot directly (instant, no backend call)
4. **PDF/Markdown export**:
   - Frontend sends screenshot + session_id to `/design-doc/export` endpoint
   - Backend retrieves stored document from session state (fast, no LLM call)
   - Embeds frontend screenshot in document
   - Converts markdown to PDF using ReportLab (or WeasyPrint if available)
   - Returns base64 encoded files
5. Frontend decodes base64 and triggers browser downloads

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

## Middleware Architecture

The backend uses a layered middleware approach (order matters):

1. **CORS** - Restricts origins to CloudFront + localhost
2. **Rate Limiting** (`RateLimitMiddleware`) - Token bucket algorithm, 60 req/min per IP by default
   - Configure via env: `RATE_LIMIT_PER_MINUTE`, `RATE_LIMIT_BURST`
   - In-memory only (resets on restart)
   - Skips `/health` and `/` endpoints
3. **API Key Auth** (`APIKeyMiddleware`) - Optional authentication (disabled by default)
   - Enable via `REQUIRE_API_KEY=true`
   - Provide keys via `VALID_API_KEYS=key1,key2,key3`
   - Accepts keys in: `X-API-Key` header, `Authorization: Bearer` header, or `api_key` query param
4. **Request Logging** (`RequestLoggingMiddleware`) - Logs all requests with timing
   - Should be last middleware to capture complete request lifecycle
   - Skips `/health`, `/`, `/favicon.ico` to reduce noise

## Logging & Monitoring

**Structured Application Logging** (`utils/logger.py`):

All events are logged as JSON to CloudWatch for easy querying:

```python
{
  "timestamp": "2025-11-14T00:30:00.123456",
  "event_type": "diagram_generated",  # See EventType enum
  "session_id": "uuid",
  "user_ip": "192.168.1.0",  # Anonymized (last octet zeroed)
  "metadata": {
    "node_count": 12,
    "edge_count": 15,
    "duration_ms": 3245.67
  }
}
```

**Event Types Tracked:**
- `diagram_generated` - User creates a diagram (tracks nodes, edges, prompt length, duration)
- `chat_message` - User interacts with chat (tracks message length, node focus, diagram updates)
- `export_design_doc` - User exports document (tracks format, duration, success/failure)
- `node_added/deleted/updated` - Manual node operations
- `edge_added/deleted` - Manual edge operations
- `api_request` - Every API call (method, path, status, duration, user IP)
- `api_error` - Errors with full context
- `rate_limit_exceeded` - When users hit rate limits

**Viewing Logs:**
```bash
# Recent application events
aws logs tail /aws/lambda/infrasketch-backend --since 24h --follow

# Filter for specific events
aws logs tail /aws/lambda/infrasketch-backend --since 7d --filter-pattern '{ $.event_type = "diagram_generated" }'

# CloudWatch Insights queries (in AWS Console or CLI)
# Example: Count diagrams per day
fields @timestamp, metadata.node_count, metadata.edge_count
| filter event_type = "diagram_generated"
| stats count() as total by bin(@timestamp, 1d)
```

**CloudWatch Dashboard:**
Access at: https://console.aws.amazon.com/cloudwatch/home?region=us-east-1#dashboards/dashboard/InfraSketch-Overview

Widgets include:
- Frontend traffic (CloudFront requests)
- Backend metrics (Lambda invocations, errors, duration)
- API Gateway metrics (requests, 4XX/5XX errors)
- Diagrams created over time
- Document exports
- Estimated daily active users
- Average diagram generation time
- Top 10 active sessions

**Weekly Email Reports:**

Automated reports sent every Monday at 9 AM PST to mattafrank2439@gmail.com

Report includes:
- User engagement (unique users, sessions, diagrams created)
- Activity breakdown (diagrams, chat interactions, exports)
- Diagram complexity metrics
- Performance stats (response time, error rate)
- Top errors (if any)

Manual report generation:
```bash
aws lambda invoke \
  --function-name infrasketch-weekly-report \
  --payload '{}' \
  /tmp/report.json
```

**Monitoring Resources:**
- CloudFront logs: Check `s3://infrasketch-cloudfront-logs-059409992371/cloudfront/`
  - Contains: IP addresses, edge locations, user agents, HTTP methods, status codes
  - Useful for geographic analysis and traffic patterns
  - Logs appear 1-2 hours after traffic occurs
- API Gateway logs: CloudWatch Logs Insights on `/aws/apigateway/infrasketch-api`
- Lambda logs: CloudWatch Logs on `/aws/lambda/infrasketch-backend`

## Security Features

**Rate Limiting:**
- Default: 60 requests per minute per IP
- Burst allowance: 10 requests
- Configurable via environment variables
- Returns HTTP 429 with `Retry-After` header when exceeded

**API Key Authentication (Optional):**
- Disabled by default for public access
- Enable by setting `REQUIRE_API_KEY=true` in Lambda environment
- Provide comma-separated keys in `VALID_API_KEYS`
- Public endpoints exempt: `/`, `/health`, `/docs`, `/openapi.json`, `/redoc`

**IP Anonymization:**
- All logged IP addresses have last octet zeroed for privacy
- Example: `192.168.1.100` → `192.168.1.0`

**CORS Security:**
- Production only allows CloudFront distribution domain
- Local development allows localhost:5173
- No wildcard origins in production
