"""
Lambda handler for InfraSketch FastAPI application.
This file adapts FastAPI to work with AWS Lambda using Mangum.
"""
from mangum import Mangum
from app.main import app

# Create the Lambda handler
handler = Mangum(app, lifespan="off")
