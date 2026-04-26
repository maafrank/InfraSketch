"""Diagram + node + edge endpoints, plus repo-analysis (which generates a diagram from a GitHub repo)."""

import base64
import json
import logging
import time

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from fastapi.encoders import jsonable_encoder
from fastapi.responses import HTMLResponse, JSONResponse, Response
from pydantic import BaseModel
from typing import Optional

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from app.agent.doc_generator import generate_design_document, generate_design_document_preview
from app.agent.graph import agent_graph, generate_suggestions, process_diagram_groups
from app.agent.name_generator import generate_session_name
from app.api.deps import get_current_user, get_session_for_user, verify_session_access
from app.api._helpers import (
    check_and_deduct_credits,
    generate_system_overview,
    _should_generate_session_name,
    _generate_session_name_from_content,
)
from app.billing.credit_costs import DESIGN_DOC_PLANS, calculate_cost
from app.billing.promo_codes import get_promo_code_info, redeem_promo_code, validate_promo_code
from app.billing.storage import get_user_credits_storage
from app.config.models import DEFAULT_MODEL
from app.gamification.achievements import (
    ACHIEVEMENT_DEFINITIONS,
    ACHIEVEMENTS_BY_ID,
    get_achievement_progress,
)
from app.gamification.engine import process_action
from app.gamification.storage import get_gamification_storage
from app.gamification.streaks import check_streak_expired
from app.gamification.xp import get_level_progress
from app.github.analyzer import (
    GitHubAnalyzer,
    GitHubRateLimitError,
    RepoAccessDeniedError,
    RepoNotFoundError,
)
from app.github.prompts import format_repo_analysis_prompt
from app.models import (
    AnalyzeRepoRequest,
    AnalyzeRepoResponse,
    ChatRequest,
    ChatResponse,
    CreateGroupRequest,
    CreateGroupResponse,
    Diagram,
    Edge,
    GenerateRequest,
    GenerateResponse,
    Message,
    Node,
    NodeMetadata,
    NodePosition,
    SessionState,
)
from app.session.manager import session_manager
from app.subscription.models import SubscribeRequest, SubscriptionStatus
from app.subscription.storage import get_subscriber_storage
from app.user.models import UserPreferences
from app.user.storage import get_user_preferences_storage
from app.utils.badge_generator import get_monthly_visitors_badge_svg
from app.utils.diagram_export import convert_markdown_to_pdf, generate_diagram_png
from app.utils.logger import (
    EventType,
    log_chat_interaction,
    log_design_doc_generation,
    log_diagram_generation,
    log_error,
    log_event,
    log_export,
)
from app.utils.secrets import get_anthropic_api_key

logger = logging.getLogger(__name__)
router = APIRouter()


def _generate_diagram_background(session_id: str, prompt: str, model: str, user_ip: str):
    """Background task to generate diagram asynchronously."""
    start_time = time.time()

    try:
        logger.info(f"\n=== BACKGROUND: GENERATE DIAGRAM ===")
        logger.info(f"Session ID: {session_id}")
        logger.info(f"Model: {model}")
        logger.info(f"Prompt length: {len(prompt)}")

        # Run agent with message-based state
        result = agent_graph.invoke({
            "messages": [HumanMessage(content=prompt)],
            "diagram": None,
            "session_id": session_id,
            "model": model,
        })

        # Extract diagram from result
        diagram = result["diagram"]

        # Update session with generated diagram
        session_manager.update_diagram(session_id, diagram)

        # Add messages to session (user + formatted assistant overview)
        session_manager.add_message(
            session_id,
            Message(role="user", content=prompt)
        )
        system_overview = generate_system_overview(diagram)
        session_manager.add_message(
            session_id,
            Message(role="assistant", content=system_overview)
        )

        # Mark as completed
        session_manager.set_diagram_generation_status(session_id, "completed")

        # Generate session name (inline since we're already in background)
        # Note: generate_session_name is synchronous - no asyncio.run() needed
        try:
            from app.utils.secrets import get_anthropic_api_key
            api_key = get_anthropic_api_key()
            name = generate_session_name(prompt, api_key, model)
            if name:
                session_manager.update_session_name(session_id, name)
                logger.info(f"Session name generated: {name}")
        except Exception as name_error:
            logger.exception(f"Failed to generate session name: {name_error}")
            session_manager.update_session_name(session_id, "Untitled Design")

        # Log diagram generation event
        duration_ms = (time.time() - start_time) * 1000
        log_diagram_generation(
            session_id=session_id,
            node_count=len(diagram.nodes),
            edge_count=len(diagram.edges),
            prompt_length=len(prompt),
            duration_ms=duration_ms,
            user_ip=user_ip,
            prompt=prompt,  # Include actual prompt for analytics
        )

        logger.info(f"Generated diagram: {len(diagram.nodes)} nodes, {len(diagram.edges)} edges")
        logger.info(f"Duration: {duration_ms:.0f}ms")
        logger.info(f"========================================\n")

        # Gamification: track diagram generation and session creation
        session = session_manager.get_session(session_id)
        if session:
            process_action(session.user_id, "session_created", {"model": model})
            process_action(session.user_id, "diagram_generated", {
                "node_count": len(diagram.nodes),
                "model": model,
            })

    except Exception as e:
        logger.exception(f"Error generating diagram in background: {str(e)}")

        # Mark as failed
        session_manager.set_diagram_generation_status(session_id, "failed", error=str(e))

        log_error(
            error_type="diagram_generation_failed",
            error_message=str(e),
            user_ip=user_ip,
            metadata={"session_id": session_id},
        )


class GenerateDescriptionResponse(BaseModel):
    """Response model for AI-generated node description."""
    label: str
    description: str
    technology: Optional[str] = None
    notes: Optional[str] = None
    diagram: Diagram  # Updated diagram with new description


def _analyze_repo_background(session_id: str, repo_url: str, model: str, user_ip: str):
    """Background task to analyze GitHub repository and generate diagram."""
    from dataclasses import asdict

    start_time = time.time()

    try:
        logger.info(f"\n=== BACKGROUND: ANALYZE REPO ===")
        logger.info(f"Session ID: {session_id}")
        logger.info(f"Repo URL: {repo_url}")
        logger.info(f"Model: {model}")

        # Phase 1: Fetch repository data
        session_manager.set_repo_analysis_status(
            session_id, "fetching", "fetch", "Fetching repository metadata..."
        )

        analyzer = GitHubAnalyzer()

        # Phase 2: Analyze repository
        session_manager.set_repo_analysis_status(
            session_id, "analyzing", "analyze", "Analyzing dependencies and code structure..."
        )

        analysis = analyzer.analyze_repo(repo_url)

        # Store analysis results for potential re-generation
        analysis_dict = asdict(analysis)
        session_manager.store_repo_analysis(session_id, analysis_dict)

        logger.info(f"Analysis complete: {analysis.name}")
        logger.info(f"  - Languages: {list(analysis.languages.keys())}")
        logger.info(f"  - Dependencies: {list(analysis.dependencies.keys())}")
        logger.info(f"  - Databases: {analysis.database_connections}")
        logger.info(f"  - Services: {analysis.external_services}")

        # Phase 3: Generate diagram
        session_manager.set_repo_analysis_status(
            session_id, "generating", "generate", "Generating architecture diagram..."
        )

        # Format prompt with analysis data
        prompt = format_repo_analysis_prompt(analysis)

        # Use LangGraph agent to generate diagram
        result = agent_graph.invoke({
            "messages": [HumanMessage(content=prompt)],
            "diagram": None,
            "session_id": session_id,
            "model": model,
        })

        diagram = result["diagram"]

        # Apply group processing for large diagrams
        if len(diagram.nodes) > 6:
            diagram = process_diagram_groups(diagram, max_visible_nodes=6, model=model)

        # Update session with generated diagram
        session_manager.update_diagram(session_id, diagram)

        # Generate overview message
        overview = f"""## Repository Analysis Complete

I've analyzed the **{analysis.name}** repository and generated an architecture diagram with {len(diagram.nodes)} components.

**Repository Details**
- **Language**: {analysis.primary_language or 'Unknown'}
- **Description**: {analysis.description or 'No description'}

**Detected Components**
- **Databases**: {', '.join(analysis.database_connections) if analysis.database_connections else 'None detected'}
- **External Services**: {', '.join(analysis.external_services) if analysis.external_services else 'None detected'}
- **Infrastructure**: {'Docker' if analysis.has_docker else ''} {'Kubernetes' if analysis.has_kubernetes else ''} {'Terraform' if analysis.has_terraform else ''}

**What's Next?**
- Click any node to learn more about that component
- Ask questions about the architecture
- Request modifications or additions

Feel free to explore the diagram and ask me anything!"""

        session_manager.add_message(
            session_id,
            Message(role="user", content=f"Analyze repository: {repo_url}")
        )
        session_manager.add_message(
            session_id,
            Message(role="assistant", content=overview)
        )

        # Set session name from repo
        session_manager.update_session_name(session_id, f"{analysis.name} Architecture")

        # Mark as completed
        session_manager.set_repo_analysis_status(session_id, "completed")

        # Log event
        duration_ms = (time.time() - start_time) * 1000
        log_event(
            EventType.DIAGRAM_GENERATED,
            session_id=session_id,
            user_ip=user_ip,
            metadata={
                "source": "github_repo",
                "repo_url": repo_url,
                "repo_name": analysis.name,
                "node_count": len(diagram.nodes),
                "edge_count": len(diagram.edges),
                "duration_ms": duration_ms,
            }
        )

        logger.info(f"Generated diagram: {len(diagram.nodes)} nodes, {len(diagram.edges)} edges")
        logger.info(f"Duration: {duration_ms:.0f}ms")
        logger.info(f"========================================\n")

        # Gamification: track repo analysis and session creation
        session = session_manager.get_session(session_id)
        if session:
            process_action(session.user_id, "session_created", {"model": model})
            process_action(session.user_id, "repo_analyzed")
            process_action(session.user_id, "diagram_generated", {
                "node_count": len(diagram.nodes),
                "model": model,
            })

        analyzer.close()

    except RepoNotFoundError as e:
        logger.info(f"Repository not found: {e}")
        session_manager.set_repo_analysis_status(
            session_id, "failed", error=f"Repository not found: {repo_url}"
        )
        log_error(
            error_type="repo_not_found",
            error_message=str(e),
            user_ip=user_ip,
            metadata={"session_id": session_id, "repo_url": repo_url},
        )

    except RepoAccessDeniedError as e:
        logger.info(f"Repository access denied: {e}")
        session_manager.set_repo_analysis_status(
            session_id, "failed",
            error="Private repos coming soon. For now, please use a public repository."
        )
        log_error(
            error_type="repo_access_denied",
            error_message=str(e),
            user_ip=user_ip,
            metadata={"session_id": session_id, "repo_url": repo_url},
        )

    except GitHubRateLimitError as e:
        logger.info(f"GitHub rate limit exceeded: {e}")
        session_manager.set_repo_analysis_status(
            session_id, "failed",
            error="GitHub API rate limit exceeded. Please try again later."
        )
        log_error(
            error_type="github_rate_limit",
            error_message=str(e),
            user_ip=user_ip,
            metadata={"session_id": session_id, "repo_url": repo_url, "reset_time": e.reset_time},
        )

    except Exception as e:
        logger.exception(f"Error analyzing repository: {str(e)}")

        session_manager.set_repo_analysis_status(
            session_id, "failed", error=f"Analysis failed: {str(e)}"
        )

        log_error(
            error_type="repo_analysis_failed",
            error_message=str(e),
            user_ip=user_ip,
            metadata={"session_id": session_id, "repo_url": repo_url},
        )


@router.post("/generate")
async def generate_diagram(request: GenerateRequest, http_request: Request, background_tasks: BackgroundTasks,
    user_id: str = Depends(get_current_user)
):
    """
    Start diagram generation asynchronously.

    Returns immediately with session_id and status. Frontend should poll
    /session/{session_id}/diagram/status until generation completes.
    """
    import os
    user_ip = http_request.client.host if http_request.client else None

    # Extract user_id from request state (set by Clerk middleware)
    
    try:
        # Use specified model or default to Haiku (alias auto-updates to latest)
        model = request.model or DEFAULT_MODEL

        # Check and deduct credits BEFORE creating session
        await check_and_deduct_credits(
            user_id=user_id,
            action="diagram_generation",
            model=model,
            metadata={"prompt_length": len(request.prompt)},
        )

        # Create session immediately with "generating" status
        session_id = session_manager.create_session_for_generation(
            user_id=user_id,
            model=model,
            prompt=request.prompt
        )

        # Check if running in Lambda
        is_lambda = os.environ.get('AWS_LAMBDA_FUNCTION_NAME') is not None

        if is_lambda:
            # In Lambda: Use async invocation to avoid API Gateway 30s timeout
            import boto3
            import json as json_lib

            logger.info(f"Lambda environment detected - triggering async diagram generation for session {session_id}")

            try:
                lambda_client = boto3.client('lambda')
                function_name = os.environ.get('AWS_LAMBDA_FUNCTION_NAME')

                payload = {
                    "async_task": "generate_diagram",
                    "session_id": session_id,
                    "prompt": request.prompt,
                    "model": model,
                    "user_ip": user_ip
                }

                lambda_client.invoke(
                    FunctionName=function_name,
                    InvocationType='Event',  # Async invocation
                    Payload=json_lib.dumps(payload)
                )

                logger.info(f"Async Lambda invocation triggered for diagram generation")
            except Exception as e:
                logger.exception(f"Failed to trigger async invocation: {e}")
                # Fall back to background task (will timeout but generation continues)
                background_tasks.add_task(_generate_diagram_background, session_id, request.prompt, model, user_ip)
        else:
            # Local development: Use true background tasks (non-blocking)
            logger.info(f"Local environment - starting background diagram generation for session {session_id}")
            background_tasks.add_task(_generate_diagram_background, session_id, request.prompt, model, user_ip)

        # Return immediately with session_id and generating status
        return JSONResponse(content={
            "session_id": session_id,
            "status": "generating"
        })

    except Exception as e:
        log_error(
            error_type="diagram_generation_start_failed",
            error_message=str(e),
            user_ip=user_ip,
        )
        raise HTTPException(status_code=500, detail=f"Failed to start diagram generation: {str(e)}")


@router.get("/session/{session_id}/diagram/status")
async def get_diagram_status(session_id: str, http_request: Request,
    user_id: str = Depends(get_current_user),
    session: SessionState = Depends(get_session_for_user)
):
    """
    Get the current status of diagram generation.

    Poll this endpoint every 2 seconds until status is "completed" or "failed".

    Returns:
        JSON with status, elapsed_seconds, and diagram (when completed)
    """
    
    status = session.diagram_generation_status

    response = {
        "status": status.status,
        "error": status.error,
    }

    # Include timing information
    if status.started_at:
        if status.completed_at:
            response["duration_seconds"] = status.completed_at - status.started_at
        else:
            response["elapsed_seconds"] = time.time() - status.started_at

    # Include diagram and messages if completed
    if status.status == "completed":
        response["diagram"] = session.diagram.model_dump()
        response["messages"] = [{"role": m.role, "content": m.content} for m in session.messages]
        response["name"] = session.name

        # Generate initial suggestions for the newly created diagram
        try:
            suggestions = generate_suggestions(
                diagram=session.diagram,
                node_id=None,
                last_message="Initial diagram generated"
            )
            response["suggestions"] = suggestions
        except Exception as e:
            logger.exception(f"✗ Error generating initial suggestions: {e}")
            response["suggestions"] = []

    return JSONResponse(content=response)


@router.post("/session/{session_id}/nodes", response_model=Diagram)
async def add_node(session_id: str, node: Node, http_request: Request, background_tasks: BackgroundTasks,
    user_id: str = Depends(get_current_user)
):
    """Add a new node to the diagram."""
    # Extract user_id and verify ownership
    
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if not session_manager.verify_ownership(session_id, user_id):
        raise HTTPException(status_code=403, detail="You don't have permission to modify this session")

    # Check for duplicate node ID
    if any(n.id == node.id for n in session.diagram.nodes):
        raise HTTPException(status_code=400, detail=f"Node with id '{node.id}' already exists")

    # Check current node count before adding
    nodes_before = len(session.diagram.nodes)

    # Add node to diagram
    session.diagram.nodes.append(node)

    # Persist to storage (critical for DynamoDB in production)
    session_manager.update_diagram(session_id, session.diagram)

    # Check if we just added the 5th node and name hasn't been generated
    nodes_after = len(session.diagram.nodes)
    if nodes_after == 5 and _should_generate_session_name(session):
        background_tasks.add_task(_generate_session_name_from_content, session_id, session.model)

    # Log event
    user_ip = http_request.client.host if http_request.client else None
    log_event(
        EventType.NODE_ADDED,
        session_id=session_id,
        user_ip=user_ip,
        metadata={"node_id": node.id, "node_type": node.type},
    )

    # Gamification: track node addition
    gamification_result = process_action(user_id, "node_added", {"node_type": node.type})

    content = jsonable_encoder(session.diagram)
    content["gamification"] = gamification_result
    return JSONResponse(content=content)


@router.delete("/session/{session_id}/nodes/{node_id}", response_model=Diagram)
async def delete_node(session_id: str, node_id: str, http_request: Request,
    user_id: str = Depends(get_current_user),
    session: SessionState = Depends(get_session_for_user)
):
    """Delete a node and its connected edges from the diagram.

    If the node is a group, all child nodes are also deleted (cascade delete).
    """
    
    # Find the node to delete
    node_to_delete = next((n for n in session.diagram.nodes if n.id == node_id), None)
    if not node_to_delete:
        raise HTTPException(status_code=404, detail=f"Node '{node_id}' not found")

    # Collect all node IDs to delete (group + children if applicable)
    nodes_to_delete = [node_id]
    if node_to_delete.is_group and node_to_delete.child_ids:
        nodes_to_delete.extend(node_to_delete.child_ids)

    # Remove all nodes (group and children)
    original_count = len(session.diagram.nodes)
    session.diagram.nodes = [n for n in session.diagram.nodes if n.id not in nodes_to_delete]

    # Remove edges connected to any deleted node
    edges_removed = len([
        e for e in session.diagram.edges
        if e.source in nodes_to_delete or e.target in nodes_to_delete
    ])
    session.diagram.edges = [
        e for e in session.diagram.edges
        if e.source not in nodes_to_delete and e.target not in nodes_to_delete
    ]

    # Persist to storage (critical for DynamoDB in production)
    session_manager.update_diagram(session_id, session.diagram)

    # Log event
    user_ip = http_request.client.host if http_request.client else None
    log_event(
        EventType.NODE_DELETED,
        session_id=session_id,
        user_ip=user_ip,
        metadata={
            "node_id": node_id,
            "is_group": node_to_delete.is_group,
            "child_nodes_deleted": len(nodes_to_delete) - 1,
            "edges_removed": edges_removed
        },
    )

    return session.diagram


@router.patch("/session/{session_id}/nodes/{node_id}", response_model=Diagram)
async def update_node(session_id: str, node_id: str, updated_node: Node, http_request: Request,
    user_id: str = Depends(get_current_user),
    session: SessionState = Depends(get_session_for_user)
):
    """Update an existing node's properties."""
    
    # Ensure IDs match
    if updated_node.id != node_id:
        raise HTTPException(status_code=400, detail="Node ID in body must match URL parameter")

    # Find and update node
    node_found = False
    for i, node in enumerate(session.diagram.nodes):
        if node.id == node_id:
            session.diagram.nodes[i] = updated_node
            node_found = True
            break

    if not node_found:
        raise HTTPException(status_code=404, detail=f"Node '{node_id}' not found")

    # Persist to storage (critical for DynamoDB in production)
    session_manager.update_diagram(session_id, session.diagram)

    return session.diagram


@router.post("/session/{session_id}/edges", response_model=Diagram)
async def add_edge(session_id: str, edge: Edge, http_request: Request,
    user_id: str = Depends(get_current_user),
    session: SessionState = Depends(get_session_for_user)
):
    """Add a new edge to the diagram."""
    
    # Validate source and target nodes exist
    node_ids = {n.id for n in session.diagram.nodes}
    if edge.source not in node_ids:
        raise HTTPException(status_code=400, detail=f"Source node '{edge.source}' does not exist")
    if edge.target not in node_ids:
        raise HTTPException(status_code=400, detail=f"Target node '{edge.target}' does not exist")

    # Check for duplicate edge ID
    if any(e.id == edge.id for e in session.diagram.edges):
        raise HTTPException(status_code=400, detail=f"Edge with id '{edge.id}' already exists")

    # Add edge to diagram
    session.diagram.edges.append(edge)

    # Persist to storage (critical for DynamoDB in production)
    session_manager.update_diagram(session_id, session.diagram)

    # Gamification: track edge addition
    gamification_result = process_action(user_id, "edge_added")

    content = jsonable_encoder(session.diagram)
    content["gamification"] = gamification_result
    return JSONResponse(content=content)


@router.delete("/session/{session_id}/edges/{edge_id}", response_model=Diagram)
async def delete_edge(session_id: str, edge_id: str, http_request: Request,
    user_id: str = Depends(get_current_user),
    session: SessionState = Depends(get_session_for_user)
):
    """Delete an edge from the diagram."""
    
    # Find and remove edge
    original_count = len(session.diagram.edges)
    session.diagram.edges = [e for e in session.diagram.edges if e.id != edge_id]

    if len(session.diagram.edges) == original_count:
        raise HTTPException(status_code=404, detail=f"Edge '{edge_id}' not found")

    # Persist to storage (critical for DynamoDB in production)
    session_manager.update_diagram(session_id, session.diagram)

    return session.diagram


@router.post("/session/{session_id}/nodes/{node_id}/generate-description", response_model=GenerateDescriptionResponse)
async def generate_node_description(
    session_id: str,
    node_id: str,
    http_request: Request
,
    user_id: str = Depends(get_current_user),
    session: SessionState = Depends(get_session_for_user)
):
    """
    Generate AI-powered description for a group node.

    This endpoint regenerates the label, description, and metadata for an existing
    group node based on its child nodes using AI.

    Args:
        session_id: The session ID
        node_id: The group node ID to regenerate description for

    Returns:
        Updated node description and full diagram
    """
    
    # Find the node
    target_node = None
    for node in session.diagram.nodes:
        if node.id == node_id:
            target_node = node
            break

    if not target_node:
        raise HTTPException(status_code=404, detail=f"Node '{node_id}' not found")

    if not target_node.is_group:
        raise HTTPException(status_code=400, detail=f"Node '{node_id}' is not a group. AI description generation is only available for group nodes.")

    # Get child nodes
    child_nodes = [n for n in session.diagram.nodes if n.id in target_node.child_ids]

    if not child_nodes:
        raise HTTPException(status_code=400, detail=f"Group '{node_id}' has no child nodes")

    # Generate AI description
    ai_result = generate_group_description_ai(child_nodes, session.model)

    if not ai_result:
        raise HTTPException(status_code=500, detail="Failed to generate AI description. Please try again.")

    # Update node with AI-generated content
    target_node.label = ai_result.get("label", target_node.label)
    target_node.description = ai_result.get("description", target_node.description)
    if ai_result.get("technology"):
        target_node.metadata.technology = ai_result["technology"]
    if ai_result.get("notes"):
        target_node.metadata.notes = ai_result["notes"]

    # Persist to storage
    session_manager.update_diagram(session_id, session.diagram)

    # Log event
    user_ip = http_request.client.host if http_request.client else None
    log_event(
        EventType.NODE_UPDATED,
        session_id=session_id,
        user_ip=user_ip,
        metadata={"node_id": node_id, "action": "ai_description_generated"},
    )

    return GenerateDescriptionResponse(
        label=target_node.label,
        description=target_node.description,
        technology=target_node.metadata.technology,
        notes=target_node.metadata.notes,
        diagram=session.diagram
    )


@router.post("/analyze-repo")
async def analyze_repo(request: AnalyzeRepoRequest, http_request: Request, background_tasks: BackgroundTasks,
    user_id: str = Depends(get_current_user)
):
    """
    Start GitHub repository analysis asynchronously.

    Returns immediately with session_id and status. Frontend should poll
    /session/{session_id}/repo-analysis/status until analysis completes.

    The analysis performs:
    1. Fetches repository metadata and file structure via GitHub API
    2. Analyzes dependencies, infrastructure, and code patterns
    3. Generates an architecture diagram using Claude

    Args:
        request: AnalyzeRepoRequest with repo_url and optional model

    Returns:
        JSON with session_id and status
    """
    import os

    user_ip = http_request.client.host if http_request.client else None

    # Extract user_id from request state (set by Clerk middleware)
    
    try:
        # Validate GitHub URL format
        try:
            analyzer = GitHubAnalyzer()
            owner, repo = analyzer.parse_github_url(request.repo_url)
            analyzer.close()
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

        # Use specified model or default to Haiku
        model = request.model or DEFAULT_MODEL

        # Check and deduct credits BEFORE creating session
        await check_and_deduct_credits(
            user_id=user_id,
            action="repo_analysis",
            model=model,
            metadata={"repo_url": request.repo_url},
        )

        # Create session with "fetching" status
        session_id = session_manager.create_session_for_repo_analysis(
            user_id=user_id,
            model=model,
            repo_url=request.repo_url
        )

        # Check if running in Lambda
        is_lambda = os.environ.get('AWS_LAMBDA_FUNCTION_NAME') is not None

        if is_lambda:
            # In Lambda: Use async invocation to avoid API Gateway 30s timeout
            import boto3
            import json as json_lib

            logger.info(f"Lambda environment detected - triggering async repo analysis for session {session_id}")

            try:
                lambda_client = boto3.client('lambda')
                function_name = os.environ.get('AWS_LAMBDA_FUNCTION_NAME')

                payload = {
                    "async_task": "analyze_repo",
                    "session_id": session_id,
                    "repo_url": request.repo_url,
                    "model": model,
                    "user_ip": user_ip
                }

                lambda_client.invoke(
                    FunctionName=function_name,
                    InvocationType='Event',  # Async invocation
                    Payload=json_lib.dumps(payload)
                )

                logger.info(f"Async Lambda invocation triggered for repo analysis")
            except Exception as e:
                logger.exception(f"Failed to trigger async invocation: {e}")
                # Fall back to background task
                background_tasks.add_task(_analyze_repo_background, session_id, request.repo_url, model, user_ip)
        else:
            # Local development: Use true background tasks
            logger.info(f"Local environment - starting background repo analysis for session {session_id}")
            background_tasks.add_task(_analyze_repo_background, session_id, request.repo_url, model, user_ip)

        # Return immediately with session_id and fetching status
        return JSONResponse(content={
            "session_id": session_id,
            "status": "fetching"
        })

    except HTTPException:
        raise
    except Exception as e:
        log_error(
            error_type="repo_analysis_start_failed",
            error_message=str(e),
            user_ip=user_ip,
        )
        raise HTTPException(status_code=500, detail=f"Failed to start repo analysis: {str(e)}")


@router.get("/session/{session_id}/repo-analysis/status")
async def get_repo_analysis_status(session_id: str, http_request: Request,
    user_id: str = Depends(get_current_user),
    session: SessionState = Depends(get_session_for_user)
):
    """
    Get the current status of repository analysis.

    Poll this endpoint every 2 seconds until status is "completed" or "failed".

    Returns:
        JSON with status, phase, progress_message, elapsed_seconds,
        and diagram/messages when completed.
    """
    
    status = session.repo_analysis_status

    response = {
        "status": status.status,
        "phase": status.phase,
        "progress_message": status.progress_message,
        "error": status.error,
    }

    # Include timing information
    if status.started_at:
        if status.completed_at:
            response["duration_seconds"] = status.completed_at - status.started_at
        else:
            response["elapsed_seconds"] = time.time() - status.started_at

    # Include diagram and messages if completed
    if status.status == "completed":
        response["diagram"] = session.diagram.model_dump()
        response["messages"] = [{"role": m.role, "content": m.content} for m in session.messages]
        response["name"] = session.name

        # Generate suggestions
        try:
            suggestions = generate_suggestions(
                diagram=session.diagram,
                node_id=None,
                last_message="Repository analyzed"
            )
            response["suggestions"] = suggestions
        except Exception as e:
            logger.exception(f"Error generating suggestions: {e}")
            response["suggestions"] = []

    return JSONResponse(content=response)
