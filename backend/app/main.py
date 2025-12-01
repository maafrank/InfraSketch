from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

from app.api.routes import router
from app.middleware.rate_limit import RateLimitMiddleware
from app.middleware.auth import APIKeyMiddleware
from app.middleware.clerk_auth import ClerkAuthMiddleware
from app.middleware.logging import RequestLoggingMiddleware

app = FastAPI(title="InfraSketch API", version="1.0.0")

# CORS middleware for frontend - restrict to known origins
ALLOWED_ORIGINS = [
    "https://dr6smezctn6x0.cloudfront.net",  # Production frontend (legacy)
    "https://infrasketch.net",  # Production frontend (custom domain)
    "https://www.infrasketch.net",  # Production frontend (www subdomain)
]

# Add localhost ports 5173-5190 for local development (Vite auto-increments when ports are busy)
for port in range(5173, 5191):
    ALLOWED_ORIGINS.append(f"http://localhost:{port}")
    ALLOWED_ORIGINS.append(f"http://127.0.0.1:{port}")

# Allow environment variable override for additional origins
extra_origins = os.getenv("EXTRA_ALLOWED_ORIGINS", "").split(",")
if extra_origins and extra_origins[0]:  # Check if not empty
    ALLOWED_ORIGINS.extend([origin.strip() for origin in extra_origins])

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,  # Now safe with specific origins
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add rate limiting middleware (60 requests per minute per IP)
app.add_middleware(
    RateLimitMiddleware,
    requests_per_minute=int(os.getenv("RATE_LIMIT_PER_MINUTE", "60")),
    burst_size=int(os.getenv("RATE_LIMIT_BURST", "10")),
)

# Add Clerk JWT authentication middleware
# Validates Clerk tokens and attaches user_id to request.state
app.add_middleware(ClerkAuthMiddleware)

# Add optional API key authentication (legacy)
# Enable by setting REQUIRE_API_KEY=true in environment
app.add_middleware(APIKeyMiddleware)

# Add request logging middleware (should be last to capture all requests)
app.add_middleware(RequestLoggingMiddleware)

# Include API routes
app.include_router(router, prefix="/api")


@app.get("/")
async def root():
    return {"message": "InfraSketch API is running"}


@app.get("/health")
async def health():
    return {"status": "healthy"}
