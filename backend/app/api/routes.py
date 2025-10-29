from fastapi import APIRouter, HTTPException
from app.models import (
    GenerateRequest,
    GenerateResponse,
    ChatRequest,
    ChatResponse,
    SessionState,
    Diagram,
    Message,
)
from app.session.manager import session_manager
from app.agent.graph import agent_graph
import json

router = APIRouter()


@router.post("/generate", response_model=GenerateResponse)
async def generate_diagram(request: GenerateRequest):
    """Generate initial system diagram from user prompt."""
    try:
        # Run agent
        result = agent_graph.invoke({
            "intent": "generate",
            "user_message": request.prompt,
            "diagram": None,
            "node_id": None,
            "conversation_history": [],
            "output": "",
            "diagram_updated": False,
        })

        # Parse diagram
        diagram_dict = json.loads(result["output"])
        diagram = Diagram(**diagram_dict)

        # Create session
        session_id = session_manager.create_session(diagram)

        # Add initial message
        session_manager.add_message(
            session_id,
            Message(role="user", content=request.prompt)
        )

        return GenerateResponse(
            session_id=session_id,
            diagram=diagram
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate diagram: {str(e)}")


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Continue conversation about diagram/node."""
    try:
        # Get session
        session = session_manager.get_session(request.session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        # Update current node if provided
        if request.node_id:
            session_manager.set_current_node(request.session_id, request.node_id)

        # Build conversation history
        conversation_history = [
            {"role": msg.role, "content": msg.content}
            for msg in session.messages
        ]

        # Run agent
        result = agent_graph.invoke({
            "intent": "chat",
            "user_message": request.message,
            "diagram": session.diagram.model_dump(),
            "node_id": request.node_id,
            "conversation_history": conversation_history,
            "output": "",
            "diagram_updated": False,
            "display_text": "",
        })

        # Add user message to history
        session_manager.add_message(
            request.session_id,
            Message(role="user", content=request.message)
        )

        # Check if diagram was updated
        response_diagram = None
        display_message = result.get("display_text", result["output"])

        if result["diagram_updated"]:
            diagram_dict = json.loads(result["output"])
            response_diagram = Diagram(**diagram_dict)
            session_manager.update_diagram(request.session_id, response_diagram)

            # Add assistant response with cleaned text
            session_manager.add_message(
                request.session_id,
                Message(role="assistant", content=display_message)
            )
        else:
            # Add assistant text response
            session_manager.add_message(
                request.session_id,
                Message(role="assistant", content=display_message)
            )

        return ChatResponse(
            response=display_message,
            diagram=response_diagram
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chat failed: {str(e)}")


@router.get("/session/{session_id}", response_model=SessionState)
async def get_session(session_id: str):
    """Retrieve current session state."""
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session
