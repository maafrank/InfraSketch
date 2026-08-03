"""
Lambda handler for InfraSketch FastAPI application.
This file adapts FastAPI to work with AWS Lambda using Mangum.
Handles both API Gateway requests and async Lambda invocations.
"""
from mangum import Mangum
from app.main import app


def handler(event, context):
    """
    Main Lambda handler that routes between API Gateway requests
    and async background tasks.
    """
    # Check if this is an async task invocation (not from API Gateway)
    if isinstance(event, dict) and event.get("async_task"):
        async_task = event.get("async_task")

        if async_task == "generate_design_doc":
            # Async invocation for design doc generation
            from app.api.routes_design_docs import _generate_design_doc_background

            session_id = event.get("session_id")
            user_ip = event.get("user_ip")

            print(f"Async task invocation: Generating design doc for session {session_id}")
            _generate_design_doc_background(session_id, user_ip)

            return {"statusCode": 200, "body": "Design doc generation completed"}

        elif async_task == "generate_design_doc_preview":
            # Async invocation for free-tier design doc preview (Executive Summary only)
            from app.api.routes_design_docs import _generate_design_doc_preview_background

            session_id = event.get("session_id")
            user_ip = event.get("user_ip")

            print(f"Async task invocation: Generating design doc PREVIEW for session {session_id}")
            _generate_design_doc_preview_background(session_id, user_ip)

            return {"statusCode": 200, "body": "Design doc preview generation completed"}

        elif async_task == "generate_diagram":
            # Async invocation for diagram generation
            from app.api.routes_diagrams import _generate_diagram_background

            session_id = event.get("session_id")
            prompt = event.get("prompt")
            model = event.get("model")
            user_ip = event.get("user_ip")

            print(f"Async task invocation: Generating diagram for session {session_id}")
            _generate_diagram_background(session_id, prompt, model, user_ip)

            return {"statusCode": 200, "body": "Diagram generation completed"}

        elif async_task == "analyze_repo":
            # Async invocation for GitHub repository analysis
            from app.api.routes_diagrams import _analyze_repo_background

            session_id = event.get("session_id")
            repo_url = event.get("repo_url")
            model = event.get("model")
            user_ip = event.get("user_ip")

            print(f"Async task invocation: Analyzing repo for session {session_id}")
            _analyze_repo_background(session_id, repo_url, model, user_ip)

            return {"statusCode": 200, "body": "Repository analysis completed"}

        elif async_task == "generate_review":
            # Async invocation for architecture review
            from app.api.routes_review import _generate_review_background

            session_id = event.get("session_id")
            user_ip = event.get("user_ip")

            print(f"Async task invocation: Generating architecture review for session {session_id}")
            _generate_review_background(session_id, user_ip)

            return {"statusCode": 200, "body": "Architecture review completed"}

        elif async_task == "generate_iac":
            # Async invocation for Infrastructure-as-Code export
            from app.api.routes_iac import _generate_iac_background

            session_id = event.get("session_id")
            target = event.get("target")
            user_ip = event.get("user_ip")

            print(f"Async task invocation: Generating {target} IaC for session {session_id}")
            _generate_iac_background(session_id, target, user_ip)

            return {"statusCode": 200, "body": "IaC generation completed"}

        elif async_task == "sync_diagram_to_doc":
            from app.sync.engine import run_diagram_to_doc
            from app.session.manager import session_manager
            import time

            session_id = event.get("session_id")
            print(f"Async task invocation: sync_diagram_to_doc for session {session_id}")

            # Sleep until sync_due_at, then run. Bounded to 30s so a runaway
            # sync_due_at can't pin a Lambda forever.
            session = session_manager.get_session(session_id)
            if session and session.sync_status.sync_due_at:
                wait = max(0.0, session.sync_status.sync_due_at - time.time())
                wait = min(wait, 30.0)
                if wait > 0:
                    time.sleep(wait)
            run_diagram_to_doc(session_id)
            return {"statusCode": 200, "body": "Sync diagram_to_doc completed"}

        else:
            print(f"Unknown async task: {async_task}")
            return {"statusCode": 400, "body": f"Unknown async task: {async_task}"}

    # Otherwise, handle as normal API Gateway request
    #
    # text_mime_types is what Mangum returns verbatim; anything else it
    # base64-encodes and flags isBase64Encoded. This is a REST API (v1) with no
    # binaryMediaTypes configured, so API Gateway does NOT decode that flag and
    # the client receives literal base64. Every text content type this app
    # serves therefore has to be listed here.
    #
    # Known gap: /share/{token}/preview.png returns image/png, which genuinely
    # cannot be sent as text and needs `image/png` added to the API's
    # binaryMediaTypes to survive the round trip.
    mangum_handler = Mangum(
        app,
        lifespan="off",
        text_mime_types=[
            "application/json",
            "text/plain",
            "text/html",
            "image/svg+xml",
            # Share sitemap. Without this it reached crawlers as base64.
            "application/xml",
            "text/xml",
        ]
    )
    return mangum_handler(event, context)
