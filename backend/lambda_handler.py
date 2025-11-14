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
    if isinstance(event, dict) and event.get("async_task") == "generate_design_doc":
        # This is an async invocation for design doc generation
        from app.api.routes import _generate_design_doc_background

        session_id = event.get("session_id")
        user_ip = event.get("user_ip")

        print(f"Async task invocation: Generating design doc for session {session_id}")

        # Run the generation task directly
        _generate_design_doc_background(session_id, user_ip)

        return {"statusCode": 200, "body": "Design doc generation completed"}

    # Otherwise, handle as normal API Gateway request
    mangum_handler = Mangum(app, lifespan="off")
    return mangum_handler(event, context)
