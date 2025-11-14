"""
Open Arena Authentication Module

Handles authentication with Open Arena API for Claude access.
Supports both OAuth2 and direct ESSO token authentication.
"""

import os
import time
import logging
import requests
from typing import Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Authentication configuration
AUTH_TOKEN_BASE_PATH = "https://auth.thomsonreuters.com"
AUTH_TOKEN_URL_PATH = "/oauth/token"


class TokenCache:
    """Simple token cache with expiration tracking"""
    def __init__(self):
        self.token: Optional[str] = None
        self.expires_at: float = 0


_token_cache = TokenCache()


def get_auth_token() -> str:
    """
    Retrieves an authentication token for Open Arena API.
    
    Priority:
    1. OAuth2 client credentials (TR_CLIENT_ID, TR_CLIENT_SECRET, TR_AUDIENCE)
    2. ESSO_TOKEN environment variable (direct token fallback)
    
    Returns:
        str: The access token
        
    Raises:
        Exception: If authentication fails
    """
    # Try OAuth2 first (primary method)
    try:
        return get_oauth2_token()
    except Exception as e:
        logger.warning(f"[AUTH] OAuth2 failed: {str(e)}")
        
        # Fall back to ESSO token if OAuth2 fails
        esso_token = os.getenv("ESSO_TOKEN")
        if esso_token:
            logger.info("[AUTH] Falling back to ESSO token from environment")
            return esso_token
        
        # No authentication available
        raise Exception(
            "Authentication failed. Please provide either:\n"
            "1. OAuth2 credentials (TR_CLIENT_ID, TR_CLIENT_SECRET, TR_AUDIENCE), or\n"
            "2. ESSO_TOKEN from D&A Portal"
        )


def get_oauth2_token() -> str:
    """
    Retrieves an OAuth2 access token using client credentials flow.
    Implements token caching with a 5-minute buffer before expiration.
    
    Returns:
        str: The access token
        
    Raises:
        Exception: If authentication fails
    """
    # Check if we have a valid cached token (with 5-minute buffer)
    now = time.time()
    buffer_seconds = 5 * 60  # 5 minutes
    
    if _token_cache.token and _token_cache.expires_at > now + buffer_seconds:
        logger.debug("[AUTH] Using cached OAuth2 token")
        return _token_cache.token

    # Get credentials from environment variables
    client_id = os.getenv("TR_CLIENT_ID")
    client_secret = os.getenv("TR_CLIENT_SECRET")
    audience = os.getenv("TR_AUDIENCE")

    # Validate that all required credentials are present
    if not client_id or not client_secret or not audience:
        raise Exception(
            "Authentication configuration missing. Required environment variables: "
            "TR_CLIENT_ID, TR_CLIENT_SECRET, TR_AUDIENCE (OAuth2) OR ESSO_TOKEN (direct token)"
        )

    auth_token_body = {
        "client_id": client_id,
        "client_secret": client_secret,
        "audience": audience,
        "grant_type": "client_credentials",
    }

    logger.info("[AUTH] Requesting OAuth2 token...")
    
    try:
        auth_token_response = requests.post(
            AUTH_TOKEN_BASE_PATH + AUTH_TOKEN_URL_PATH,
            headers={"Content-Type": "application/json"},
            json=auth_token_body,
            timeout=30
        )

        if not auth_token_response.ok:
            error_text = auth_token_response.text
            raise Exception(
                f"Authentication failed: {auth_token_response.status_code}. {error_text}"
            )

        response_data = auth_token_response.json()
        access_token = response_data.get("access_token")
        
        if not access_token or not isinstance(access_token, str):
            raise Exception("Authentication failed: No access token in response")

        # Cache the token with expiration
        # Default to 1 hour if expires_in is not provided
        expires_in = response_data.get("expires_in", 3600)
        _token_cache.token = access_token
        _token_cache.expires_at = now + expires_in

        logger.info("[AUTH] ✓ OAuth2 token obtained successfully")
        return access_token
        
    except requests.exceptions.RequestException as e:
        raise Exception(f"Authentication request failed: {str(e)}")


def clear_token_cache():
    """Clears the cached authentication token."""
    _token_cache.token = None
    _token_cache.expires_at = 0
    logger.debug("[AUTH] Token cache cleared")


if __name__ == "__main__":
    # Test authentication when run directly
    try:
        print("Testing Open Arena Authentication...")
        print()
        
        token = get_auth_token()
        print(f"✓ Authentication successful!")
        print(f"  Token: {token[:20]}... (truncated)")
        print()
        
    except Exception as e:
        print(f"\n✗ Authentication failed: {e}")
        exit(1)
