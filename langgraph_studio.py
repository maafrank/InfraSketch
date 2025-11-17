"""
Standalone graph file for LangGraph Studio.

This file provides a clean entry point for LangGraph Studio
without requiring the 'app' module structure.
"""

import sys
import os

# Add backend directory to Python path so we can import from app.*
backend_path = os.path.join(os.path.dirname(__file__), 'backend')
sys.path.insert(0, backend_path)

# Now we can import the agent graph
from app.agent.graph import agent_graph

# Export for LangGraph Studio
__all__ = ['agent_graph']
