# CLAUDE.md

## Writing Style
- Do not use em-dashes (—). Use commas, parentheses, or separate sentences instead.

## Running the Application

Two terminals required:

```bash
# Terminal 1: Backend (http://127.0.0.1:8000)
cd backend && python3 -m uvicorn app.main:app --reload --port 8000

# Terminal 2: Frontend (http://localhost:5173)
cd frontend && npm run dev
```

**Other Commands:**
```bash
npm run build              # Frontend production build
npm run lint               # ESLint
pip install -r backend/requirements.txt  # Backend deps
./deploy-all.sh            # Deploy both (requires AWS CLI)
./deploy-backend.sh        # Backend only
./deploy-frontend.sh       # Frontend only
```

## Architecture Overview

InfraSketch: AI-powered system design tool with **React frontend** + **FastAPI backend** using **LangGraph** to orchestrate Claude.

### Request Flow (Async Generation)
1. User prompt → `POST /api/generate` → Backend creates session with `status: "generating"`
2. Backend triggers async Lambda (or BackgroundTask locally), returns immediately
3. Frontend polls `GET /session/{id}/diagram/status` every 2s
4. Background task runs LangGraph → Claude returns JSON diagram
5. Session updated, status → `completed`, frontend renders with React Flow

**Why async?** API Gateway 30s timeout; complex diagrams take 30-60+ seconds.

### Chat Modification Flow
1. Click node → Chat panel opens
2. Message → `POST /api/chat` with session_id + node_id
3. Agent builds context (diagram + history + node focus + design doc)
4. Claude responds with text and/or tool calls
5. If tool calls: execute → loop back → Claude can call more tools
6. Finalize: sync state, add indicators if diagram/doc changed

### Tool-Based Architecture

Claude uses **native tool calling API** (no JSON parsing):
- `add_node`, `delete_node`, `update_node` - Diagram modifications
- `add_edge`, `delete_edge` - Connection modifications
- `update_design_doc_section` - Surgical doc edits (preferred)
- `replace_entire_design_doc` - Complete doc replacement (rare)

**Why:** Reliable (structured API), self-correcting (retries on error), surgical edits, type-safe, auditable.

### Key Components

| Backend (`backend/app/`) | Purpose |
|--------------------------|---------|
| `main.py` | FastAPI app with CORS, rate limiting, Clerk auth, logging middleware |
| `models.py` | Pydantic models: Node, Edge, Diagram, SessionState |
| `api/routes.py` | All endpoints: generate, chat, session CRUD, with event logging |
| `session/manager.py` | Hybrid storage (in-memory local, DynamoDB Lambda) |
| `session/dynamodb_storage.py` | DynamoDB persistent storage |
| `lambda_handler.py` | Lambda entry: routes API Gateway + async task invocations |
| `agent/graph.py` | LangGraph agent with tool calling |
| `agent/state.py` | State model with LangGraph reducers |
| `agent/tools.py` | Native tools for diagram/doc modifications |
| `agent/prompts.py` | System prompts (generation + conversation) |
| `agent/doc_generator.py` | LLM call for design document generation |
| `middleware/clerk_auth.py` | Clerk JWT authentication |
| `middleware/rate_limit.py` | Token bucket, 60 req/min default |
| `utils/logger.py` | Structured JSON logging for CloudWatch |
| `utils/diagram_export.py` | PDF/image generation |

| Frontend (`frontend/src/`) | Purpose |
|----------------------------|---------|
| `App.jsx` | Main state: diagram, sessionId, selectedNode, messages, designDoc |
| `components/DiagramCanvas.jsx` | React Flow canvas with dagre auto-layout |
| `components/ChatPanel.jsx` | Chat UI, resizable |
| `components/DesignDocPanel.jsx` | TipTap editor, loading overlay during generation |
| `components/SessionHistorySidebar.jsx` | Left sidebar: saved sessions, rename/delete |
| `components/NodePalette.jsx` | Bottom toolbar for adding nodes |
| `components/CustomNode.jsx` | Styled node with color coding by type |
| `components/ExportButton.jsx` | Export dropdown: PNG/PDF/Markdown |
| `api/client.js` | Axios client with polling functions |

### LangGraph Agent

**State Schema** (`agent/state.py`):
```python
{"messages": Sequence[AnyMessage], "diagram": Diagram | None, "design_doc": str | None,
 "session_id": str, "model": str, "node_id": str | None}
```

**Graph Flow:**
```
Entry → route_intent() → "generate" (no diagram) OR "chat" (has diagram)
"chat" → route_tool_decision() → "tools" (if calls) OR "finalize"
"tools" → execute → "chat" (loop) | "finalize" → add indicators → END
```

Tools are defined WITHOUT `session_id`; `tools_node()` injects it automatically.

## Environment Setup

```env
# Backend (.env in root) - Required
ANTHROPIC_API_KEY=your-api-key
CLERK_SECRET_KEY=sk_test_your-key
# Optional
LANGSMITH_TRACING=False
RATE_LIMIT_PER_MINUTE=60
DISABLE_CLERK_AUTH=true  # Local dev only, false in production

# Frontend (frontend/.env) - Required
VITE_CLERK_PUBLISHABLE_KEY=pk_test_your-key
VITE_API_URL=http://localhost:8000
# Production: VITE_API_URL=https://b31htlojb0.execute-api.us-east-1.amazonaws.com/prod
```

## API Endpoints

All under `/api` prefix. Persists to DynamoDB in Lambda, in-memory locally.

| Endpoint | Method | Request | Response | Notes |
|----------|--------|---------|----------|-------|
| `/generate` | POST | `{prompt, model?}` | `{session_id, status:"generating"}` | Async, poll `/diagram/status` |
| `/session/{id}/diagram/status` | GET | - | `{status, elapsed_seconds?, diagram?, error?}` | Poll every 2s |
| `/chat` | POST | `{session_id, message, node_id?}` | `{response, diagram?}` | Conversational |
| `/session/{id}` | GET | - | `SessionState` | Full session |
| `/session/create-blank` | POST | - | `{session_id, diagram}` | Empty diagram |
| `/session/{id}/name` | PATCH | `{name}` | `{success, name}` | Rename |
| `/session/{id}` | DELETE | - | `{success, message}` | Delete |
| `/user/sessions` | GET | - | `[{session_id, name, node_count, ...}]` | User's sessions |
| `/session/{id}/nodes` | POST | `Node` | `Diagram` | Add node |
| `/session/{id}/nodes/{node_id}` | DELETE | - | `Diagram` | Delete node + edges |
| `/session/{id}/nodes/{node_id}` | PATCH | `Node` | `Diagram` | Update node |
| `/session/{id}/edges` | POST | `Edge` | `Diagram` | Add edge |
| `/session/{id}/edges/{edge_id}` | DELETE | - | `Diagram` | Delete edge |
| `/session/{id}/groups` | POST | `{child_node_ids:[...]}` | `{diagram, group_id}` | Create group |
| `/session/{id}/groups/{group_id}/collapse` | PATCH | - | `Diagram` | Toggle collapse |
| `/session/{id}/design-doc/generate` | POST | `{diagram_image?}` | `{status:"started"}` | Async generation |
| `/session/{id}/design-doc/status` | GET | - | `{status, elapsed_seconds?, design_doc?}` | Poll every 2s |
| `/session/{id}/design-doc` | PATCH | `{content}` | - | Manual edit |
| `/session/{id}/design-doc/export` | POST | `{diagram_image}` | `{pdf, markdown, diagram_png}` | Export formats |

## Data Models

```python
# Node (backend/app/models.py)
{"id": str, "type": str,  # cache|database|api|server|loadbalancer|queue|cdn|gateway|storage|service|group
 "label": str, "description": str, "inputs": List[str], "outputs": List[str],
 "metadata": {"technology": str, "notes": str}, "position": {"x": float, "y": float},
 # Group fields
 "parent_id": Optional[str], "is_group": bool, "is_collapsed": bool, "child_ids": List[str]}

# Edge
{"id": str, "source": str, "target": str, "label": str, "type": "default" | "animated"}

# SessionState
{"session_id": str, "user_id": str, "diagram": Diagram, "messages": List[Message],
 "current_node": Optional[str], "design_doc": Optional[str], "model": str,
 "design_doc_status": {"status": str, "error?": str, "started_at?": float},
 "diagram_generation_status": {"status": str, "error?": str, "started_at?": float},
 "created_at": datetime, "name": str, "name_generated": bool}
```

## Common Issues & Solutions

| Issue | Cause | Solution |
|-------|-------|----------|
| Diagram not updating after chat | Tool execution failed | Check logs for "=== EXECUTING TOOL(S) ===" and tool errors |
| White screen after generate | Empty diagram / parse fail | Check console for "nodes: 0", backend for "✗ Failed to parse JSON" |
| Wrong node IDs in tool calls | Claude guessing IDs | Verify "Nodes (with exact IDs)" in prompt context |
| Diagram generation stuck | Polling or task failed | Check logs for "BACKGROUND: GENERATE DIAGRAM", call `/diagram/status` directly |
| Design doc generation stuck | Polling or task failed | Check logs for "BACKGROUND: GENERATE DESIGN DOC", call `/design-doc/status` |
| Session not found (404) | DynamoDB float/Decimal issue | Check Lambda logs for "Error saving session" |
| Lambda crashes on startup | Missing IAM or table timeout | Verify DynamoDB permissions incl. `TagResource`, check table exists |
| 401 Unauthorized | Invalid Clerk token | Check `VITE_CLERK_PUBLISHABLE_KEY` (FE), `CLERK_SECRET_KEY` (BE), user signed in |
| Node won't merge into group | Insufficient overlap | Need 5% overlap, check console for "drop target" logs |
| Group collapse not working | State not syncing | Check PATCH `/groups/{id}/collapse` in logs, verify `onToggleCollapse` prop chain |

## Model Configuration

| Model | ID | Cost (per 1M tokens) | Best For |
|-------|-----|---------------------|----------|
| **Haiku 4.5** (default) | `claude-haiku-4-5` | $1 in / $5 out | Most use cases, fast |
| **Sonnet 4.5** | `claude-sonnet-4-5` | $3 in / $15 out | Complex systems |
| **Opus 4.5** | `claude-opus-4-5` | $5 in / $25 out | Premium reasoning, agents |

Model stored in session, used for all operations. Aliases auto-update to latest versions.

## Session Management

**Hybrid Storage:** In-memory (local) / DynamoDB (Lambda). Auto-detects via `AWS_LAMBDA_FUNCTION_NAME`.

**SessionManager** (`session/manager.py`): `create_session()`, `get_session()`, `update_diagram()`, `add_message()`, `update_design_doc()`, `set_design_doc_status()`, `set_diagram_generation_status()`, `update_session_name()`

**DynamoDB** (`dynamodb_storage.py`): Table `infrasketch-sessions`, pay-per-request, 1-year TTL. Converts `float` → `Decimal`. Auto-creates table on first run.

**Session History:** Sessions sorted by most recent. Each has: session_id, name, node_count, edge_count, timestamps. Default name: "Untitled Design". Rename via header click or right-click menu.

## Frontend State & Interactions

**App.jsx state:** `diagram`, `sessionId`, `selectedNode`, `messages`, `designDoc`, `designDocOpen`, `designDocLoading`, `sessionHistoryOpen`, `sessionName`, `isMobile`

**DiagramCanvas:** Transforms backend format → React Flow, applies dagre auto-layout (TB direction, 150px H / 100px V spacing).

| Action | Desktop (>768px) | Mobile (≤768px) |
|--------|------------------|-----------------|
| Click node | Opens side chat panel | Fullscreen modal |
| Hover node | Shows tooltip | - |
| Right-click node/edge | Context menu (delete) | - |
| Drag from handle | Create connection | - |
| Drag node onto node | Merge into group (5% overlap) | - |
| Click ▼/▶ on group | Toggle collapse | Toggle collapse |
| Click palette item | Opens AddNodeModal | Opens AddNodeModal |
| "Create Design Doc" | Opens panel + loading overlay | Fullscreen modal |
| "📋 History" | Opens left sidebar | Fullscreen modal |
| Panel edges | Draggable to resize | Non-resizable |

## Debugging

| Context | Log Pattern | Meaning |
|---------|-------------|---------|
| Diagram generation | "BACKGROUND: GENERATE DIAGRAM" | Task starting |
| | "Generated diagram: N nodes, M edges" | Success |
| | "✗ Error generating diagram" | Failed |
| Chat | "=== CHAT NODE RESPONSE ===" | Response type |
| | "Has tool_calls: True" | Tools requested |
| Tools | "=== EXECUTING N TOOL(S) ===" | Starting execution |
| | "✓ Result: {success: True}" | Tool succeeded |
| | "✗ Error: Node 'xyz' not found" | Tool failed |
| Finalize | "→ Routing to tools/finalize" | Decision |
| Frontend | "API Response:" / "DiagramCanvas received" | Data flow |

Both servers auto-reload (`--reload` backend, Vite HMR frontend).

## Deployment

**Production URLs:** Frontend: https://infrasketch.net | API: https://b31htlojb0.execute-api.us-east-1.amazonaws.com/prod

**Infrastructure:**
- Backend: Lambda + API Gateway (300s timeout, 512MB, Python 3.11)
- IAM Role: `infrasketch-lambda-role` (shared by all Lambdas). Policies: `DynamoDBSessionStorage` (inline, lists all table ARNs), `LambdaSelfInvoke` (inline), `SecretsManagerReadWrite` (managed), `AWSLambdaBasicExecutionRole` (managed). When adding new DynamoDB tables, update the `DynamoDBSessionStorage` inline policy.
- Storage: DynamoDB `infrasketch-sessions` (pay-per-request, 1yr TTL)
- Frontend: S3 + CloudFront
- Secrets: AWS Secrets Manager (ANTHROPIC_API_KEY)
- Monitoring: CloudWatch Logs/Metrics/Dashboard, Weekly reports (Monday 9AM PST), Lambda error alarms via SNS to mattafrank2439@gmail.com. Setup script: `scripts/setup-streak-monitoring.sh`

**Deploy scripts:** Backend packages deps for Linux → Lambda zip → S3 → update function. Frontend builds → S3 sync → CloudFront invalidate.

**Lambda Deployment Checklist:**
When deploying or modifying any Lambda function, always verify:
1. **IAM permissions** - Check the Lambda's execution role has access to all AWS services it uses (DynamoDB tables, Secrets Manager, S3, SES, etc.). Run: `aws iam get-role-policy --role-name infrasketch-lambda-role --policy-name DynamoDBSessionStorage` to see current DynamoDB table access. If adding a new DynamoDB table, add its ARN to the policy.
2. **New DynamoDB tables** - If the Lambda accesses a new table, add `arn:aws:dynamodb:us-east-1:059409992371:table/<TABLE_NAME>` and its `/index/*` variant to the `DynamoDBSessionStorage` inline policy.
3. **Test after deploy** - Always invoke the Lambda manually after deploying and check the output for errors: `aws lambda invoke --function-name <FUNCTION_NAME> /tmp/output.json && cat /tmp/output.json`
4. **Check CloudWatch logs** - After test invocation, check logs for errors: `aws logs tail /aws/lambda/<FUNCTION_NAME> --since 5m`
5. **Third-party API keys** - If the Lambda uses external APIs (Resend, etc.), verify the API key is in Secrets Manager and the key has correct permissions on the provider's side.

**Updating CSP Headers:** Edit `infrastructure/response-headers-policy.json`, then:
```bash
POLICY_ID=$(aws cloudfront list-response-headers-policies --query "ResponseHeadersPolicyList.Items[?ResponseHeadersPolicy.ResponseHeadersPolicyConfig.Name=='infrasketch-security-headers'].ResponseHeadersPolicy.Id" --output text)
ETAG=$(aws cloudfront get-response-headers-policy --id $POLICY_ID --query 'ETag' --output text)
aws cloudfront update-response-headers-policy --id $POLICY_ID --if-match $ETAG --response-headers-policy-config file://infrastructure/response-headers-policy.json
```

**Logs:** `/aws/lambda/infrasketch-backend` (app), `/aws/apigateway/infrasketch-api` (API Gateway), `s3://infrasketch-cloudfront-logs-059409992371/cloudfront/` (CloudFront)

## Mobile Responsive Design

**Breakpoints:** Desktop >1024px | Tablet 768-1024px | Mobile ≤768px | Phone ≤480px

**Mobile behavior:** Side panels → fullscreen modals. React Flow controls hidden (pinch-to-zoom). Min 44px touch targets. Panels non-resizable. CSS media queries in `App.css:1568-1959`, `NodePalette.css:163-206`.

**Testing:** Chrome DevTools Device Toolbar (Cmd+Shift+M). Test: 375px, 768px, 1024px.

## Collapsible Groups / Node Merging

**How:** Drag node onto another (5% overlap) → `POST /groups` with `child_node_ids` → Backend creates group or adds to existing.

**Group structure:** `is_group: true`, `is_collapsed: true/false`, `child_ids: [...]`. Children get `parent_id`.

**Behavior:** Collapsed = children hidden, edges through parent, count badge. Expanded = children in cluster. Controls: ▼/▶ toggle, 📦 on children collapses parent.

**Key files:** `routes.py:690-836`, `DiagramCanvas.jsx:406-483`, `CustomNode.jsx:13-26,50-77`, `App.jsx:454-471`

**Details:** 5% overlap threshold, 50ms debounce, groups can't nest, delete group = delete children, edges deduplicated.

## Panel Resizing

All panels use RAF throttling (60fps), `onWidthChange` callback, `useCallback` optimization, CSS `will-change`.

**NodePalette:** Slides from bottom (not sides). Height: 120px default, 60-800px range. Visibility: `chatPanelOpen={!!diagram}`. Compact: 70px min card width, 11px font.

## Design Document Feature

**Async generation:** Same pattern as diagrams. Local: FastAPI BackgroundTasks. Lambda: async self-invocation. Status: `not_started` → `generating` → `completed`/`failed`. Generation: 30-150s. Model: Haiku 4.5 (32k tokens).

**Components:** `doc_generator.py` (LLM call), `prompts.py` (DESIGN_DOC_PROMPT), `diagram_export.py` (PDF), `DesignDocPanel.jsx` (TipTap editor), `html-to-image` (screenshot).

**Flow:** Click "Create Design Doc" → Panel opens with loading → Poll `/design-doc/status` → Backend generates with Claude → Completion triggers panel update → Edit inline, auto-saves after 3s.

**Chat editing:** Bot uses `update_design_doc_section` tool for surgical edits (finds section header, replaces only that section). Never overwrites entire doc unless explicitly asked.

**Export:** PNG (instant, frontend only) | PDF/Markdown (screenshot + session_id → backend retrieves doc → embeds image → returns base64). Edge labels hidden during screenshot. 2x pixel ratio.

**Document sections:** Executive Summary, System Overview, Architecture Diagram, Component Details, Data Flow, Infrastructure, Scalability, Security, Trade-offs, Implementation Phases, Future Enhancements, Appendix.

**Dependencies:** Frontend: `html-to-image`. Backend: `Pillow`, `markdown2`, `reportlab` (primary), `weasyprint` (fallback, needs `brew install pango`).

## Authentication & Security (Clerk)

**Frontend:** ClerkProvider wraps app. Axios interceptor adds `Authorization: Bearer {token}`. User ID stored in session.

**Backend:** `ClerkAuthMiddleware` intercepts all requests (except `/`, `/health`, `/docs`). Fetches JWKS from Clerk (cached 1hr). Validates JWT signature + claims (issuer, expiry, subject). Attaches `user_id` to `request.state`. Returns 401 (invalid token) or 403 (no permission).

**Session ownership:** Every session has `user_id`. Routes verify `session.user_id == request.state.user_id`.

**Files:** `middleware/clerk_auth.py`, `main.jsx` (ClerkProvider), `api/client.js` (interceptor)

**Env vars:** `CLERK_SECRET_KEY` (backend), `VITE_CLERK_PUBLISHABLE_KEY` (frontend), `CLERK_DOMAIN` (defaults to `clerk.infrasketch.net`)

**Rate limiting:** 60 req/min per IP, burst 10. Token bucket algorithm. Returns 429 with `Retry-After`. Config: `RATE_LIMIT_PER_MINUTE`, `RATE_LIMIT_BURST`.

**CORS:** Production allows CloudFront + infrasketch.net. Local allows localhost:5173. No wildcards. Credentials enabled.

**IP anonymization:** Last octet zeroed in logs (192.168.1.100 → 192.168.1.0).

## Middleware Stack (Order Matters)

1. **CORS** - Origin restrictions
2. **RateLimitMiddleware** - Token bucket, skips `/health`, `/`
3. **ClerkAuthMiddleware** - JWT validation, attaches user_id
4. **APIKeyMiddleware** - Legacy (disabled, enable via `REQUIRE_API_KEY=true`)
5. **RequestLoggingMiddleware** - Timing, skips `/health`, `/`, `/favicon.ico`

## Logging & Monitoring

**Structured JSON logging** (`utils/logger.py`):
```python
{"timestamp": "...", "event_type": "diagram_generated", "session_id": "uuid",
 "user_ip": "192.168.1.0", "metadata": {"node_count": 12, "duration_ms": 3245}}
```

**Event types:** `diagram_generated`, `chat_message`, `export_design_doc`, `node_added/deleted/updated`, `edge_added/deleted`, `api_request`, `api_error`, `rate_limit_exceeded`

**View logs:**
```bash
aws logs tail /aws/lambda/infrasketch-backend --since 24h --follow
aws logs tail /aws/lambda/infrasketch-backend --since 7d --filter-pattern '{ $.event_type = "diagram_generated" }'
```

**Dashboard:** https://console.aws.amazon.com/cloudwatch/home?region=us-east-1#dashboards/dashboard/InfraSketch-Overview

**Weekly reports:** Mondays 9AM PST to mattafrank2439@gmail.com. Manual: `aws lambda invoke --function-name infrasketch-weekly-report --payload '{}' /tmp/report.json`

## Blog & SEO

**Blog:** Routes `/blog` (list), `/blog/:slug` (post). Content: `/frontend/public/blog/posts/*.md`. Metadata: `index.json`. Components: `BlogListPage.jsx`, `BlogPostPage.jsx`. Rendering: `react-markdown`.

**Add post:** Create `.md` file → Add to `index.json` → Add to `sitemap.xml` → Deploy

**SEO files** (`/frontend/public/`): `llms.txt`, `robots.txt`, `sitemap.xml`, `og-image.png`

**Meta tags:** SEO in `index.html`, Open Graph, Twitter Cards, Schema.org JSON-LD (WebSite, SoftwareApplication, Organization)

## Email Subscriptions

**Provider:** Resend (infrasketch.net verified). **Storage:** DynamoDB `infrasketch-subscribers`. Auto-subscribe on Clerk account creation.

**Endpoints:** `POST /subscribe`, `GET /subscription/status`, `POST /unsubscribe`, `GET /unsubscribe/{token}` (public), `GET /resubscribe/{token}` (public)

**Send announcements:**
```bash
python scripts/send_announcement.py announcements/my-feature.html --preview  # Browser preview
python scripts/send_announcement.py announcements/my-feature.html            # Test (your email)
python scripts/send_announcement.py announcements/my-feature.html --production  # All subscribers
```

**IMPORTANT: Deploy images BEFORE sending!** Images in emails must be hosted at `https://infrasketch.net/announcements/`. Before sending any announcement:
1. Copy images to `frontend/public/announcements/`
2. Run `./deploy-frontend.sh`
3. Verify images load: `curl -I https://infrasketch.net/announcements/your-image.png` (should return `content-type: image/png`)
4. Then send the email

**Templates:** `/announcements/`. Subject from `<title>`. Placeholder: `{{UNSUBSCRIBE_URL}}`. Env: `RESEND_API_KEY`.
