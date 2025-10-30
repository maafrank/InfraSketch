# InfraSketch

An AI-powered system design tool that generates interactive architecture diagrams from natural language prompts. Built with React, FastAPI, LangGraph, and Claude AI.

🚀 **[Live Demo](https://dr6smezctn6x0.cloudfront.net)**

## Features

- **AI-Generated Diagrams**: Describe your system in plain English and get an instant architecture diagram
- **Interactive Visualization**: Hover over components to see details (inputs, outputs, technology stack)
- **Conversational Design**: Click any component to chat about it, ask questions, or request modifications
- **Real-time Updates**: The diagram updates automatically as you refine your design through conversation
- **Visual Node Types**: Color-coded components (database, cache, server, API, load balancer, queue, CDN, etc.)

## Tech Stack

### Backend
- **FastAPI** - Python web framework
- **LangGraph** - Agent orchestration
- **Claude 3 Haiku** - Anthropic's cost-effective LLM ($0.25/$1.25 per million tokens)
- **Pydantic** - Data validation

### Frontend
- **React** - UI framework
- **React Flow** - Interactive diagram visualization
- **Vite** - Build tool
- **Axios** - HTTP client

## Prerequisites

- Python 3.11+
- Node.js 18+
- Anthropic API key

## Installation

### 1. Clone the repository

```bash
git clone <repository-url>
cd InfraSketch
```

### 2. Set up environment variables

Create a `.env` file in the root directory:

```env
ANTHROPIC_API_KEY=your-api-key-here

# LangSmith (Optional - for tracing and debugging)
LANGSMITH_TRACING=False
LANGSMITH_ENDPOINT="https://api.smith.langchain.com"
LANGSMITH_API_KEY="your-langsmith-key"
LANGSMITH_PROJECT="InfraSketch"
```

### 3. Install backend dependencies

```bash
cd backend
pip install -r requirements.txt
```

### 4. Install frontend dependencies

```bash
cd ../frontend
npm install
```

## Running the Application

You'll need two terminal windows:

### Terminal 1: Start the backend

```bash
cd backend
python3 -m uvicorn app.main:app --reload --port 8000
```

Backend will be available at: http://127.0.0.1:8000

### Terminal 2: Start the frontend

```bash
cd frontend
npm run dev
```

Frontend will be available at: http://localhost:5173

## Usage

1. **Open the app** in your browser at http://localhost:5173
2. **Enter a system description**:
   - Example: "Build a scalable video streaming platform"
   - Example: "Design a microservices e-commerce system with Redis cache"
   - Example: "Create a real-time chat application with WebSocket support"
3. **Explore the diagram**:
   - Hover over nodes to see details (description, technology, inputs/outputs)
   - Pan and zoom to navigate the diagram
4. **Click any node** to open a chat panel and:
   - Ask questions: "What database should this use?"
   - Request changes: "Add a read replica for this database"
   - Expand functionality: "How should we handle authentication?"
5. **Watch the diagram update** automatically when you request modifications
6. **Start over** by clicking the "New Design" button

## Project Structure

```
InfraSketch/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI application
│   │   ├── models.py            # Pydantic data models
│   │   ├── api/
│   │   │   └── routes.py        # API endpoints
│   │   ├── agent/
│   │   │   ├── graph.py         # LangGraph agent
│   │   │   └── prompts.py       # System prompts
│   │   └── session/
│   │       └── manager.py       # Session management
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── DiagramCanvas.jsx    # React Flow diagram
│   │   │   ├── InputPanel.jsx       # Initial prompt input
│   │   │   ├── ChatPanel.jsx        # Node conversation
│   │   │   ├── CustomNode.jsx       # Styled nodes
│   │   │   └── NodeTooltip.jsx      # Hover tooltips
│   │   ├── api/
│   │   │   └── client.js            # API client
│   │   ├── App.jsx
│   │   └── App.css
│   └── package.json
├── .env
├── PLAN.md
└── README.md
```

## API Endpoints

### POST `/api/generate`
Generate initial system diagram from prompt
```json
{
  "prompt": "Build a scalable e-commerce system"
}
```

### POST `/api/chat`
Continue conversation about a node or system
```json
{
  "session_id": "uuid",
  "message": "Add a Redis cache",
  "node_id": "optional-node-id"
}
```

### GET `/api/session/{session_id}`
Retrieve current session state

## Architecture

The application uses a **single LangGraph agent** that:
1. **Generates diagrams** - Parses requirements and creates JSON structure with nodes/edges
2. **Answers questions** - Provides detailed explanations about components
3. **Modifies diagrams** - Updates the architecture based on conversation

Sessions are stored **in-memory** (not persisted to database).

## Future Enhancements

- Database persistence (save/load designs)
- Export to code/Terraform/CloudFormation
- Multi-user collaboration
- Version history
- Auto-layout optimization
- Diagram templates
- Multi-agent system (specialized agents per domain)

## Model Information

**Current Model**: Claude 3 Haiku
- **Cost**: $0.25 input / $1.25 output per million tokens (cheapest Claude model)
- **Speed**: Fast response times
- **Quality**: Suitable for diagram generation and conversational AI

To upgrade to a more powerful model (e.g., Claude 3.5 Sonnet), edit `backend/app/agent/graph.py` and change the model name in the `create_llm()` function.

## Contributing

Contributions welcome! Please open an issue or submit a pull request.
