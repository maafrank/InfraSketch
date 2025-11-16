"""
Test script for tool-based diagram editing.

This script tests the new tool-based approach by simulating API calls.
"""

import requests
import json
import time

BASE_URL = "http://127.0.0.1:8000/api"


def test_tool_based_editing():
    """Test the complete tool-based editing flow."""

    print("\n" + "="*60)
    print("TESTING TOOL-BASED DIAGRAM EDITING")
    print("="*60 + "\n")

    # Step 1: Generate initial diagram
    print("Step 1: Generating initial diagram...")
    response = requests.post(
        f"{BASE_URL}/generate",
        json={
            "prompt": "Design a simple web application with a React frontend, Node.js API, and PostgreSQL database",
            "model": "claude-haiku-4-5"
        }
    )

    if response.status_code != 200:
        print(f"❌ Failed to generate diagram: {response.status_code}")
        print(response.text)
        return

    data = response.json()
    session_id = data["session_id"]
    initial_nodes = len(data["diagram"]["nodes"])
    initial_edges = len(data["diagram"]["edges"])

    print(f"✓ Generated diagram with {initial_nodes} nodes and {initial_edges} edges")
    print(f"  Session ID: {session_id}")
    print(f"  Node IDs: {[n['id'] for n in data['diagram']['nodes']]}")
    print()

    time.sleep(1)

    # Step 2: Test adding a component (Redis cache) using tool-based approach
    print("Step 2: Testing tool-based editing - Add Redis cache...")
    response = requests.post(
        f"{BASE_URL}/chat",
        json={
            "session_id": session_id,
            "message": "Add a Redis cache between the API and the database to improve performance",
            "node_id": None
        }
    )

    if response.status_code != 200:
        print(f"❌ Failed to send chat message: {response.status_code}")
        print(response.text)
        return

    data = response.json()
    print(f"✓ Chat response received")
    print(f"  Response: {data['response'][:200]}...")
    print(f"  Diagram updated: {data['diagram'] is not None}")

    if data['diagram']:
        new_nodes = len(data['diagram']['nodes'])
        new_edges = len(data['diagram']['edges'])
        print(f"  Nodes: {initial_nodes} → {new_nodes} ({new_nodes - initial_nodes:+d})")
        print(f"  Edges: {initial_edges} → {new_edges} ({new_edges - initial_edges:+d})")
        print(f"  New node IDs: {[n['id'] for n in data['diagram']['nodes']]}")

        # Check if Redis was added
        redis_nodes = [n for n in data['diagram']['nodes'] if 'redis' in n['id'].lower() or 'cache' in n['type'].lower()]
        if redis_nodes:
            print(f"  ✓ Found cache node: {redis_nodes[0]['label']} ({redis_nodes[0]['id']})")
        else:
            print(f"  ⚠️  No cache node detected (check if tool-based editing worked)")
    else:
        print(f"  ⚠️  Diagram was not updated")
    print()

    time.sleep(1)

    # Step 3: Test updating a component
    print("Step 3: Testing tool-based editing - Update database technology...")
    response = requests.post(
        f"{BASE_URL}/chat",
        json={
            "session_id": session_id,
            "message": "Change the database from PostgreSQL to MongoDB",
            "node_id": None
        }
    )

    if response.status_code != 200:
        print(f"❌ Failed to send chat message: {response.status_code}")
        print(response.text)
        return

    data = response.json()
    print(f"✓ Chat response received")
    print(f"  Response: {data['response'][:200]}...")

    if data['diagram']:
        # Check if MongoDB exists
        mongo_nodes = [n for n in data['diagram']['nodes'] if 'mongo' in n['label'].lower() or 'mongo' in n.get('metadata', {}).get('technology', '').lower()]
        if mongo_nodes:
            print(f"  ✓ Found MongoDB node: {mongo_nodes[0]['label']}")
            print(f"    Technology: {mongo_nodes[0]['metadata']['technology']}")
        else:
            print(f"  ⚠️  No MongoDB node detected")
    print()

    time.sleep(1)

    # Step 4: Test removing a component
    print("Step 4: Testing tool-based editing - Remove cache layer...")

    # First, get current state to find the cache node ID
    response = requests.get(f"{BASE_URL}/session/{session_id}")
    if response.status_code == 200:
        session = response.json()
        cache_nodes = [n for n in session['diagram']['nodes'] if 'cache' in n['type'].lower()]
        if cache_nodes:
            cache_id = cache_nodes[0]['id']
            print(f"  Found cache node: {cache_id}")

            response = requests.post(
                f"{BASE_URL}/chat",
                json={
                    "session_id": session_id,
                    "message": "Remove the Redis cache layer",
                    "node_id": None
                }
            )

            if response.status_code == 200:
                data = response.json()
                print(f"✓ Chat response received")
                print(f"  Response: {data['response'][:200]}...")

                if data['diagram']:
                    remaining_cache = [n for n in data['diagram']['nodes'] if 'cache' in n['type'].lower()]
                    if not remaining_cache:
                        print(f"  ✓ Cache successfully removed")
                    else:
                        print(f"  ⚠️  Cache still exists: {remaining_cache}")
        else:
            print(f"  ⚠️  No cache node found to remove")

    print()
    print("="*60)
    print("TEST COMPLETE")
    print("="*60)
    print()
    print("Next steps:")
    print("1. Check backend logs for tool execution messages")
    print("2. Open http://localhost:5175 to verify diagram visually")
    print(f"3. Session ID for manual testing: {session_id}")
    print()


if __name__ == "__main__":
    try:
        test_tool_based_editing()
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
