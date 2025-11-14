#!/usr/bin/env python3
"""
Test script for Open Arena authentication.

Run this to verify your credentials are working correctly.
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from agent.openarena_auth import get_auth_token


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
        print(f"  Token length: {len(token)} characters")
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


def main():
    """Run authentication test."""
    print()
    print("NEWS EDIT AGENT - Authentication Test")
    print()
    
    # Test authentication
    auth_ok = test_authentication()
    
    # Summary
    print("=" * 70)
    print("Test Summary")
    print("=" * 70)
    print(f"Authentication: {'✓ PASS' if auth_ok else '✗ FAIL'}")
    print()
    
    if auth_ok:
        print("✓ Authentication successful!")
        print()
        print("Note: The LLM client will need to be configured based on your")
        print("specific Open Arena setup (REST API vs WebSocket workflow).")
        print()
        print("Next steps:")
        print("  1. Configure LLM client for your Open Arena setup")
        print("  2. Run ingest: python cli.py ingest --input ./rushes --story 'story-name'")
        print("  3. Compile edit: python cli.py compile --story 'story-name' --brief 'description'")
        sys.exit(0)
    else:
        print("✗ Authentication failed. Please fix the issues above.")
        sys.exit(1)


if __name__ == "__main__":
    main()
