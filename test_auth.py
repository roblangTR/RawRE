#!/usr/bin/env python3
"""
Test script for Open Arena authentication and Claude client.

Run this to verify your credentials are working correctly.
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from agent.openarena_auth import get_auth_token
from agent.llm_client import ClaudeClient


def test_authentication():
    """Test Open Arena authentication."""
    print("=" * 70)
    print("Testing Open Arena Authentication")
    print("=" * 70)
    print()
    
    try:
        print("Step 1: Obtaining authentication token...")
        token = get_auth_token()
        print(f"✓ Token obtained: {token[:20]}... (truncated)")
        print()
        return True
    except Exception as e:
        print(f"✗ Authentication failed: {e}")
        print()
        print("Please check your .env file contains:")
        print("  - TR_CLIENT_ID")
        print("  - TR_CLIENT_SECRET")
        print("  - TR_AUDIENCE")
        print("OR")
        print("  - ESSO_TOKEN")
        print()
        return False


def test_claude_client():
    """Test Claude client."""
    print("=" * 70)
    print("Testing Claude Client")
    print("=" * 70)
    print()
    
    try:
        print("Step 1: Initializing Claude client...")
        client = ClaudeClient()
        print("✓ Client initialized")
        print()
        
        print("Step 2: Sending test message...")
        response = client.chat([
            {"role": "user", "content": "Say 'Hello from Claude!' and nothing else."}
        ])
        
        print(f"✓ Response received: {response['content']}")
        print(f"  Model: {response['model']}")
        print(f"  Tokens: {response['usage']}")
        print()
        
        print("Step 3: Testing JSON response...")
        json_response = client.chat_with_json([
            {"role": "user", "content": 'Respond with JSON: {"status": "ok", "test": true}'}
        ])
        
        print(f"✓ JSON parsed: {json_response}")
        print()
        
        return True
        
    except Exception as e:
        print(f"✗ Claude client test failed: {e}")
        import traceback
        traceback.print_exc()
        print()
        return False


def main():
    """Run all tests."""
    print()
    print("NEWS EDIT AGENT - Authentication Test")
    print()
    
    # Test authentication
    auth_ok = test_authentication()
    
    if not auth_ok:
        print("=" * 70)
        print("✗ Authentication failed - cannot proceed with Claude test")
        print("=" * 70)
        sys.exit(1)
    
    # Test Claude client
    claude_ok = test_claude_client()
    
    # Summary
    print("=" * 70)
    print("Test Summary")
    print("=" * 70)
    print(f"Authentication: {'✓ PASS' if auth_ok else '✗ FAIL'}")
    print(f"Claude Client:  {'✓ PASS' if claude_ok else '✗ FAIL'}")
    print()
    
    if auth_ok and claude_ok:
        print("✓ All tests passed! Your Open Arena setup is working correctly.")
        print()
        print("Next steps:")
        print("  1. Run ingest: python cli.py ingest --input ./rushes --story 'story-name'")
        print("  2. Compile edit: python cli.py compile --story 'story-name' --brief 'description'")
        sys.exit(0)
    else:
        print("✗ Some tests failed. Please fix the issues above.")
        sys.exit(1)


if __name__ == "__main__":
    main()
