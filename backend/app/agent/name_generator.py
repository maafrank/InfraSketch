"""
Session name generation using LLM.

Creates concise, descriptive names for sessions based on the initial prompt.
"""

from anthropic import Anthropic

NAME_GENERATION_PROMPT = """You are a technical writer creating concise session names for system design diagrams.

Given a user's initial prompt for creating a system architecture diagram, generate a short, descriptive name that captures the essence of what they're designing.

Rules:
- 2-5 words maximum
- Use title case (e.g., "E-commerce Platform with CDN")
- Focus on the system type and key technologies/components
- Be specific but concise
- Examples:
  * "Design a microservices e-commerce platform" → "E-commerce Microservices Platform"
  * "Build a real-time chat app with Redis" → "Real-time Chat with Redis"
  * "Create a video streaming service" → "Video Streaming Service"
  * "Design a serverless API with AWS Lambda" → "Serverless API Gateway"
  * "Build a data pipeline with Kafka" → "Kafka Data Pipeline"

Return ONLY the name, nothing else."""


def generate_session_name(prompt: str, anthropic_api_key: str, model: str = "claude-haiku-4-5") -> str:
    """
    Generate a concise session name based on the initial prompt.

    This is a synchronous function (uses sync Anthropic client).
    Safe to call from sync contexts like Lambda background tasks.

    Args:
        prompt: The user's initial prompt for diagram generation
        anthropic_api_key: Anthropic API key
        model: Model to use (default: claude-haiku-4-5 for speed/cost)

    Returns:
        A 2-5 word descriptive name for the session
    """
    try:
        client = Anthropic(api_key=anthropic_api_key)

        response = client.messages.create(
            model=model,
            max_tokens=50,  # Very short response needed
            temperature=0.3,  # Low temperature for consistency
            messages=[{
                "role": "user",
                "content": f"Generate a session name for this prompt:\n\n{prompt}"
            }],
            system=NAME_GENERATION_PROMPT
        )

        name = response.content[0].text.strip()

        # Fallback if something went wrong
        if not name or len(name) > 100:
            print(f"⚠️  Invalid name generated (length={len(name)}): {name}")
            return "Untitled Design"

        print(f"✓ Generated session name: {name}")
        return name

    except Exception as e:
        print(f"✗ Error generating session name: {e}")
        # Fallback to a generic name
        return "Untitled Design"
