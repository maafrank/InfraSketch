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
            from app.api.routes import _generate_design_doc_background

            session_id = event.get("session_id")
            user_ip = event.get("user_ip")

            print(f"Async task invocation: Generating design doc for session {session_id}")
            _generate_design_doc_background(session_id, user_ip)

            return {"statusCode": 200, "body": "Design doc generation completed"}

        elif async_task == "generate_diagram":
            # Async invocation for diagram generation
            from app.api.routes import _generate_diagram_background

            session_id = event.get("session_id")
            prompt = event.get("prompt")
            model = event.get("model")
            user_ip = event.get("user_ip")

            print(f"Async task invocation: Generating diagram for session {session_id}")
            _generate_diagram_background(session_id, prompt, model, user_ip)

            return {"statusCode": 200, "body": "Diagram generation completed"}

        else:
            print(f"Unknown async task: {async_task}")
            return {"statusCode": 400, "body": f"Unknown async task: {async_task}"}

    # Otherwise, handle as normal API Gateway request
    # Configure text_mime_types to ensure responses aren't base64 encoded
    # Note: application/json should be handled by default, but we include it
    # explicitly to prevent any encoding issues with API Gateway
    mangum_handler = Mangum(
        app,
        lifespan="off",
        text_mime_types=[
            "application/json",
            "text/plain",
            "text/html",
            "image/svg+xml",
        ]
    )
    return mangum_handler(event, context)
