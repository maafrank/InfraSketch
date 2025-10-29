# InfraSketch - System Design Assistant

## Overview
An interactive system design tool where users describe a system, and an LLM generates a visual architecture diagram. Users can hover over nodes for details, click to have conversations about specific components, and request modifications to the design.

## Tech Stack

### Frontend
- **React** - UI framework
- **React Flow** - Interactive diagram visualization
- **TailwindCSS** - Styling
- **Axios** - API calls

### Backend
- **FastAPI** - Python web framework
- **LangGraph** - Agent orchestration
- **Claude (Anthropic)** - LLM for generation and conversation
- **Pydantic** - Data validation

### State Management
- **Backend**: In-memory session storage (dict mapping session_id to state)
- **Frontend**: React state for UI, session_id in localStorage

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                         Frontend (React)                     │
│                                                              │
│  ┌────────────────┐  ┌──────────────────┐  ┌─────────────┐ │
│  │  Input Panel   │  │  Diagram Canvas  │  │  Chat Panel │ │
│  │  (Initial      │  │  (React Flow)    │  │  (Node      │ │
│  │   prompt)      │  │                  │  │   focused)  │ │
│  └────────────────┘  └──────────────────┘  └─────────────┘ │
│                                                              │
└──────────────────────────┬───────────────────────────────────┘
                           │ HTTP/REST
                           │
┌──────────────────────────▼───────────────────────────────────┐
│                      Backend (FastAPI)                       │
│                                                              │
│  ┌─────────────────────────────────────────────────────────┐│
│  │              Session Manager (In-Memory)                ││
│  │  { session_id: { diagram, messages, context } }         ││
│  └─────────────────────────────────────────────────────────┘│
│                           │                                  │
│  ┌────────────────────────▼─────────────────────────────┐   │
│  │             LangGraph Agent                          │   │
│  │  • Generate initial diagram                          │   │
│  │  • Answer questions about nodes                      │   │
│  │  • Modify diagram based on conversation              │   │
│  └────────────────────────┬─────────────────────────────┘   │
│                           │                                  │
│                           ▼                                  │
│                    Claude API (Anthropic)                    │
└──────────────────────────────────────────────────────────────┘
```

## Data Models

### Node Schema
```json
{
  "id": "unique-id",
  "type": "cache|database|api|server|loadbalancer|queue|cdn|etc",
  "label": "Node Name",
  "description": "What this component does",
  "inputs": ["Input 1", "Input 2"],
  "outputs": ["Output 1"],
  "metadata": {
    "technology": "Redis|PostgreSQL|etc",
    "notes": "Additional details"
  },
  "position": { "x": 100, "y": 200 }
}
```

### Edge Schema
```json
{
  "id": "edge-id",
  "source": "node-id-1",
  "target": "node-id-2",
  "label": "Connection description",
  "type": "default|animated"
}
```

### Session State
```python
{
  "session_id": "uuid",
  "diagram": {
    "nodes": [...],
    "edges": [...]
  },
  "messages": [
    {"role": "user", "content": "..."},
    {"role": "assistant", "content": "..."}
  ],
  "current_node": "node-id or null"
}
```

## API Endpoints

### POST /api/generate
Create initial system diagram from user prompt
- **Input**: `{ "prompt": "Build a scalable e-commerce system" }`
- **Output**: `{ "session_id": "uuid", "diagram": { nodes, edges } }`

### POST /api/chat
Continue conversation about a node or system
- **Input**: `{ "session_id": "uuid", "message": "...", "node_id": "optional" }`
- **Output**: `{ "response": "...", "diagram": { nodes, edges } (if modified) }`

### GET /api/session/{session_id}
Retrieve current session state
- **Output**: `{ "diagram": {...}, "messages": [...] }`

## LangGraph Agent Flow

```
START
  │
  ▼
[Determine Intent]
  │
  ├─→ Generate New Diagram
  │   └─→ [Parse Requirements] → [Generate JSON] → [Validate] → RETURN
  │
  ├─→ Answer Question
  │   └─→ [Get Context] → [Generate Response] → RETURN
  │
  └─→ Modify Diagram
      └─→ [Understand Change] → [Update JSON] → [Validate] → RETURN
```

### Agent Capabilities
1. **Generate Diagram**: Parse user requirements and create nodes/edges JSON
2. **Answer Questions**: Provide detailed explanations about nodes/components
3. **Modify Diagram**: Add/remove/update nodes based on conversation
4. **Maintain Context**: Keep track of entire system when discussing specific nodes

## User Flows

### Flow 1: Initial Generation
1. User enters prompt: "Build me a video streaming platform"
2. Backend agent generates diagram JSON
3. Frontend renders interactive diagram
4. User can hover nodes to see tooltips

### Flow 2: Node Conversation
1. User clicks on "Database" node
2. Chat panel opens with node context
3. User asks: "What type of database should this be?"
4. Agent responds with recommendations
5. User says: "Make it use PostgreSQL and add a read replica"
6. Agent modifies diagram, updates frontend

### Flow 3: System Expansion
1. User clicks "API Server" node
2. User asks: "How do we handle authentication?"
3. Agent explains current setup
4. User: "Add an OAuth service and Redis session store"
5. Agent adds new nodes and connections
6. Diagram updates in real-time

## Development Phases

### Phase 1: Core Infrastructure ✓
- [x] Project setup
- [ ] FastAPI backend skeleton
- [ ] React frontend skeleton
- [ ] Environment configuration (.env)

### Phase 2: Backend - Basic Agent
- [ ] LangGraph agent setup
- [ ] Claude integration
- [ ] Initial diagram generation (prompt → JSON)
- [ ] Session management

### Phase 3: Frontend - Diagram Display
- [ ] React Flow integration
- [ ] Render nodes/edges from JSON
- [ ] Hover tooltips
- [ ] Node click handling

### Phase 4: Conversation System
- [ ] Chat panel UI
- [ ] API endpoint for chat
- [ ] Agent conversation logic
- [ ] Context passing (node + full diagram)

### Phase 5: Diagram Modification
- [ ] Agent diagram update logic
- [ ] Frontend diagram refresh
- [ ] Validation and error handling

### Phase 6: Polish
- [ ] Better UI/UX
- [ ] Error handling
- [ ] Loading states
- [ ] Styling improvements

## File Structure

```
InfraSketch/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py              # FastAPI app
│   │   ├── models.py            # Pydantic models
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   └── routes.py        # API endpoints
│   │   ├── agent/
│   │   │   ├── __init__.py
│   │   │   ├── graph.py         # LangGraph agent
│   │   │   └── prompts.py       # System prompts
│   │   └── session/
│   │       ├── __init__.py
│   │       └── manager.py       # Session state management
│   ├── requirements.txt
│   └── .env
├── frontend/
│   ├── public/
│   ├── src/
│   │   ├── components/
│   │   │   ├── InputPanel.jsx
│   │   │   ├── DiagramCanvas.jsx
│   │   │   ├── ChatPanel.jsx
│   │   │   └── NodeTooltip.jsx
│   │   ├── api/
│   │   │   └── client.js        # API calls
│   │   ├── App.jsx
│   │   └── main.jsx
│   ├── package.json
│   └── vite.config.js
├── .env
├── PLAN.md
└── README.md
```

## Key Design Decisions

1. **Session-based, not persistent**: Simpler to start, can add DB later
2. **Single agent**: Reduces complexity, easier to reason about
3. **JSON diagram format**: Easy to serialize, validate, and render
4. **Full context on node click**: Agent sees entire system when discussing parts
5. **React Flow**: Mature library, handles layout and interaction well
6. **FastAPI**: Fast, modern, great Python async support

## Future Enhancements (Not in Scope)
- Database persistence (save/load designs)
- Multi-user collaboration
- Export to code/Terraform
- Version history
- Multi-agent system (specialized agents per domain)
- Auto-layout optimization
- Diagram templates
