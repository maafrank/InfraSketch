"""
Shared test fixtures for InfraSketch backend tests.

This module provides common fixtures for:
- Test client with mocked auth
- Sample diagrams, nodes, edges
- Session fixtures
- Mocked external services (Claude, DynamoDB)
"""

import os
import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

# Set environment variables before importing app
os.environ["DISABLE_CLERK_AUTH"] = "true"
os.environ["ANTHROPIC_API_KEY"] = "test-api-key"
# Set high rate limit for tests to avoid 429 errors
os.environ["RATE_LIMIT_PER_MINUTE"] = "10000"
os.environ["RATE_LIMIT_BURST"] = "1000"

# Force reload of main module to pick up env vars
import importlib
import app.main
importlib.reload(app.main)
from app.main import app
from app.models import (
    Node, Edge, Diagram, Message, SessionState,
    NodePosition, NodeMetadata, DesignDocStatus, DiagramGenerationStatus
)
from app.session.manager import SessionManager


# ============================================================================
# Test Client Fixtures
# ============================================================================

@pytest.fixture
def client():
    """FastAPI test client with auth disabled."""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def authenticated_client(client):
    """
    Test client that simulates an authenticated user.
    Adds the user_id to request state (normally done by Clerk middleware).
    """
    # Since DISABLE_CLERK_AUTH=true, we need to mock the user_id injection
    # The middleware should skip auth and we can test endpoints directly
    return client


# ============================================================================
# Model Fixtures - Nodes
# ============================================================================

@pytest.fixture
def sample_node():
    """A basic node for testing."""
    return Node(
        id="api-gateway-1",
        type="gateway",
        label="API Gateway",
        description="Routes incoming HTTP requests to appropriate services",
        inputs=["client-requests"],
        outputs=["auth-service", "user-service"],
        metadata=NodeMetadata(technology="AWS API Gateway", notes="Rate limited"),
        position=NodePosition(x=100, y=200)
    )


@pytest.fixture
def sample_database_node():
    """A database node for testing."""
    return Node(
        id="postgres-db-1",
        type="database",
        label="PostgreSQL",
        description="Primary relational database for user data",
        inputs=["user-service"],
        outputs=[],
        metadata=NodeMetadata(technology="PostgreSQL 15", notes="Primary DB"),
        position=NodePosition(x=300, y=400)
    )


@pytest.fixture
def sample_cache_node():
    """A cache node for testing."""
    return Node(
        id="redis-cache-1",
        type="cache",
        label="Redis Cache",
        description="In-memory cache for session data",
        inputs=["auth-service"],
        outputs=[],
        metadata=NodeMetadata(technology="Redis 7", notes="Session store"),
        position=NodePosition(x=200, y=300)
    )


@pytest.fixture
def sample_group_node(sample_node, sample_database_node):
    """A group node containing other nodes."""
    return Node(
        id="backend-group-1",
        type="group",
        label="Backend Services",
        description="Group containing backend components",
        inputs=[],
        outputs=[],
        is_group=True,
        is_collapsed=False,
        child_ids=[sample_node.id, sample_database_node.id]
    )


# ============================================================================
# Model Fixtures - Edges
# ============================================================================

@pytest.fixture
def sample_edge():
    """A basic edge for testing."""
    return Edge(
        id="edge-api-to-db",
        source="api-gateway-1",
        target="postgres-db-1",
        label="SQL queries",
        type="default"
    )


@pytest.fixture
def sample_animated_edge():
    """An animated edge for testing."""
    return Edge(
        id="edge-api-to-cache",
        source="api-gateway-1",
        target="redis-cache-1",
        label="Cache lookup",
        type="animated"
    )


# ============================================================================
# Model Fixtures - Diagrams
# ============================================================================

@pytest.fixture
def empty_diagram():
    """An empty diagram."""
    return Diagram(nodes=[], edges=[])


@pytest.fixture
def simple_diagram(sample_node, sample_database_node, sample_edge):
    """A diagram with two nodes and one edge."""
    return Diagram(
        nodes=[sample_node, sample_database_node],
        edges=[sample_edge]
    )


@pytest.fixture
def complex_diagram(sample_node, sample_database_node, sample_cache_node, sample_edge, sample_animated_edge):
    """A diagram with multiple nodes and edges."""
    return Diagram(
        nodes=[sample_node, sample_database_node, sample_cache_node],
        edges=[sample_edge, sample_animated_edge]
    )


# ============================================================================
# Model Fixtures - Messages
# ============================================================================

@pytest.fixture
def sample_user_message():
    """A user message."""
    return Message(role="user", content="Add a load balancer to the system")


@pytest.fixture
def sample_assistant_message():
    """An assistant message."""
    return Message(role="assistant", content="I've added a load balancer between the API gateway and backend services.")


# ============================================================================
# Session Fixtures
# ============================================================================

@pytest.fixture
def test_user_id():
    """A test user ID (simulating Clerk user)."""
    return "user_test_123456"


@pytest.fixture
def sample_session(simple_diagram, test_user_id):
    """A complete session state for testing."""
    return SessionState(
        session_id="session-test-abc123",
        user_id=test_user_id,
        diagram=simple_diagram,
        messages=[],
        current_node=None,
        model="claude-haiku-4-5-20251001"
    )


@pytest.fixture
def session_with_messages(sample_session, sample_user_message, sample_assistant_message):
    """A session with conversation history."""
    sample_session.messages = [sample_user_message, sample_assistant_message]
    return sample_session


@pytest.fixture
def session_with_design_doc(sample_session):
    """A session with a design document."""
    sample_session.design_doc = "# System Design\n\nThis is a test design document."
    sample_session.design_doc_status = DesignDocStatus(status="completed")
    return sample_session


# ============================================================================
# Session Manager Fixtures
# ============================================================================

@pytest.fixture
def fresh_session_manager():
    """
    Create a fresh SessionManager for each test.
    Uses in-memory storage (not Lambda environment).

    IMPORTANT: We patch the global session_manager to avoid state leakage between tests.
    """
    # Save original value if it exists
    original_value = os.environ.get("AWS_LAMBDA_FUNCTION_NAME")

    # Remove the env var completely so is_lambda check returns False
    if "AWS_LAMBDA_FUNCTION_NAME" in os.environ:
        del os.environ["AWS_LAMBDA_FUNCTION_NAME"]

    try:
        # Create a completely fresh manager with empty sessions dict
        manager = SessionManager()
        manager.sessions = {}  # Ensure clean state
        manager.is_lambda = False
        manager.storage = None
        yield manager
    finally:
        # Restore original value
        if original_value is not None:
            os.environ["AWS_LAMBDA_FUNCTION_NAME"] = original_value
        elif "AWS_LAMBDA_FUNCTION_NAME" in os.environ:
            del os.environ["AWS_LAMBDA_FUNCTION_NAME"]


@pytest.fixture
def session_manager_with_session(fresh_session_manager, simple_diagram, test_user_id):
    """Session manager with a pre-created session."""
    session_id = fresh_session_manager.create_session(simple_diagram, test_user_id)
    return fresh_session_manager, session_id


@pytest.fixture(autouse=True)
def reset_global_state():
    """
    Reset global state before each test to prevent state leakage.
    This runs automatically for every test.
    """
    from app.session.manager import session_manager

    # Clear sessions for test
    if hasattr(session_manager, 'sessions'):
        session_manager.sessions = {}

    # Reset rate limiter buckets
    # The rate limiter middleware stores buckets in-memory, need to clear them
    from app.main import app
    for middleware in app.user_middleware:
        if hasattr(middleware, 'cls'):
            # Check if this is RateLimitMiddleware
            if middleware.cls.__name__ == 'RateLimitMiddleware':
                # Can't easily access middleware instance, use high burst for tests instead
                pass

    yield

    # Tests that need persistence should use their own session manager instance


# ============================================================================
# Mock Fixtures - External Services
# ============================================================================

@pytest.fixture
def mock_anthropic():
    """Mock the Anthropic client to avoid real API calls."""
    with patch("anthropic.Anthropic") as mock:
        mock_client = MagicMock()
        mock.return_value = mock_client

        # Set up a default response
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text='{"nodes": [], "edges": []}')]
        mock_response.stop_reason = "end_turn"
        mock_client.messages.create.return_value = mock_response

        yield mock_client


@pytest.fixture
def mock_dynamodb():
    """Mock DynamoDB for tests that don't need real persistence."""
    with patch("boto3.resource") as mock:
        yield mock


# ============================================================================
# Utility Fixtures
# ============================================================================

@pytest.fixture
def node_types():
    """List of valid node types."""
    return [
        "cache", "database", "api", "server", "loadbalancer",
        "queue", "cdn", "gateway", "storage", "service", "group"
    ]


@pytest.fixture
def edge_types():
    """List of valid edge types."""
    return ["default", "animated"]


# ============================================================================
# API Route Testing Fixtures
# ============================================================================

@pytest.fixture
def client_with_session(client, simple_diagram):
    """
    TestClient with a pre-created session.
    Returns tuple of (client, session_id).
    Session is created with "local-dev-user" to match the dev auth bypass.
    """
    from app.session.manager import session_manager
    # Use "local-dev-user" to match what ClerkAuthMiddleware sets when DISABLE_CLERK_AUTH=true
    session_id = session_manager.create_session(simple_diagram, user_id="local-dev-user")
    return client, session_id


@pytest.fixture
def another_user_id():
    """A different user ID for testing ownership/authorization."""
    return "user_other_789xyz"


@pytest.fixture
def mock_agent_graph(mocker):
    """
    Mock LangGraph agent to return predefined responses without LLM calls.
    Use this for chat endpoint tests.
    """
    from langchain_core.messages import AIMessage

    mock = mocker.patch("app.api.routes.agent_graph")
    mock.invoke.return_value = {
        "messages": [AIMessage(content="This is a test response from the mocked agent.")],
        "diagram": None,
        "design_doc": None,
    }
    return mock


@pytest.fixture
def mock_design_doc_generator(mocker):
    """Mock design document generator to avoid LLM calls."""
    return mocker.patch(
        "app.api.routes.generate_design_document",
        return_value="# Test Design Document\n\nThis is a mocked design document."
    )


@pytest.fixture
def mock_session_name_generator(mocker):
    """Mock session name generator to avoid LLM calls."""
    return mocker.patch(
        "app.api.routes.generate_session_name",
        return_value="Test Session Name"
    )


@pytest.fixture
def mock_subscriber_storage(mocker):
    """Mock subscriber storage for subscription endpoint tests."""
    from app.subscription.models import Subscriber
    from datetime import datetime

    mock_storage = MagicMock()

    # Default subscriber - use ISO format strings for timestamps
    now_str = datetime.now().isoformat()
    test_subscriber = Subscriber(
        user_id="local-dev-user",  # Match dev auth user
        email="test@example.com",
        subscribed=True,
        unsubscribe_token="test-token-abc123",
        created_at=now_str,
        updated_at=now_str
    )

    mock_storage.get_subscriber.return_value = test_subscriber
    mock_storage.create_subscriber.return_value = test_subscriber
    mock_storage.unsubscribe.return_value = True
    mock_storage.resubscribe.return_value = True
    mock_storage.get_subscriber_by_token.return_value = test_subscriber

    mocker.patch("app.api.routes.get_subscriber_storage", return_value=mock_storage)
    return mock_storage


# ============================================================================
# Middleware Testing Fixtures
# ============================================================================

@pytest.fixture
def rate_limit_app():
    """
    Create a test app with only rate limiting middleware for isolated testing.
    """
    from fastapi import FastAPI
    from app.middleware.rate_limit import RateLimitMiddleware

    test_app = FastAPI()
    test_app.add_middleware(RateLimitMiddleware, requests_per_minute=10, burst_size=2)

    @test_app.get("/test")
    def test_endpoint():
        return {"status": "ok"}

    @test_app.get("/health")
    def health_endpoint():
        return {"status": "healthy"}

    @test_app.get("/")
    def root_endpoint():
        return {"status": "root"}

    return test_app


@pytest.fixture
def rate_limit_client(rate_limit_app):
    """TestClient for rate limit testing."""
    with TestClient(rate_limit_app) as test_client:
        yield test_client


@pytest.fixture
def clerk_auth_test_keys():
    """
    Generate RSA key pair for testing Clerk JWT validation.
    Returns dict with private_key, public_key, kid, and jwks.
    """
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.hazmat.backends import default_backend
    import base64
    import json

    # Generate RSA key pair
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
        backend=default_backend()
    )
    public_key = private_key.public_key()

    # Get public key numbers for JWKS
    public_numbers = public_key.public_numbers()

    # Convert to base64url encoding (no padding)
    def to_base64url(num, length):
        data = num.to_bytes(length, byteorder='big')
        return base64.urlsafe_b64encode(data).rstrip(b'=').decode('utf-8')

    kid = "test-key-id-123"

    # Build JWKS
    jwks = {
        "keys": [
            {
                "kty": "RSA",
                "use": "sig",
                "kid": kid,
                "alg": "RS256",
                "n": to_base64url(public_numbers.n, 256),
                "e": to_base64url(public_numbers.e, 3),
            }
        ]
    }

    return {
        "private_key": private_key,
        "public_key": public_key,
        "kid": kid,
        "jwks": jwks,
    }


@pytest.fixture
def valid_clerk_token(clerk_auth_test_keys):
    """
    Generate a valid JWT token signed with test keys.
    """
    import jwt
    import time

    now = int(time.time())
    payload = {
        "sub": "user_test_clerk_123",
        "iss": "https://clerk.infrasketch.net",
        "iat": now,
        "exp": now + 3600,  # 1 hour from now
        "nbf": now,
    }

    token = jwt.encode(
        payload,
        clerk_auth_test_keys["private_key"],
        algorithm="RS256",
        headers={"kid": clerk_auth_test_keys["kid"]}
    )
    return token


@pytest.fixture
def expired_clerk_token(clerk_auth_test_keys):
    """
    Generate an expired JWT token.
    """
    import jwt
    import time

    now = int(time.time())
    payload = {
        "sub": "user_test_clerk_123",
        "iss": "https://clerk.infrasketch.net",
        "iat": now - 7200,  # 2 hours ago
        "exp": now - 3600,  # 1 hour ago (expired)
        "nbf": now - 7200,
    }

    token = jwt.encode(
        payload,
        clerk_auth_test_keys["private_key"],
        algorithm="RS256",
        headers={"kid": clerk_auth_test_keys["kid"]}
    )
    return token
