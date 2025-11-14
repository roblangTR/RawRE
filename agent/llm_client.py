"""
LLM Client for Claude via Open Arena API

Provides a simple interface for making Claude API calls through Open Arena.
"""

import json
import logging
import requests
from typing import Dict, Any, List, Optional
from .openarena_auth import get_auth_token

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ClaudeClient:
    """Client for Claude API via Open Arena."""
    
    def __init__(self, model: str = "claude-3-5-sonnet-20241022", temperature: float = 0.1):
        """
        Initialize Claude client.
        
        Args:
            model: Claude model identifier
            temperature: Sampling temperature (0.0-1.0)
        """
        self.model = model
        self.temperature = temperature
        self.base_url = "https://aiopenarena.gcs.int.thomsonreuters.com/v1"
        self.token = None
        
        logger.info(f"[CLAUDE] Initialized with model: {model}, temperature: {temperature}")
    
    def _ensure_token(self):
        """Ensure we have a valid authentication token."""
        if not self.token:
            self.token = get_auth_token()
    
    def chat(self, 
             messages: List[Dict[str, str]], 
             max_tokens: int = 4096,
             system: Optional[str] = None) -> Dict[str, Any]:
        """
        Send a chat completion request to Claude.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            max_tokens: Maximum tokens in response
            system: Optional system prompt
            
        Returns:
            Response dictionary with 'content', 'usage', etc.
        """
        self._ensure_token()
        
        # Construct request payload
        payload = {
            "model": self.model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": self.temperature
        }
        
        if system:
            payload["system"] = system
        
        # Make API request
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
        
        logger.debug(f"[CLAUDE] Sending request with {len(messages)} messages")
        
        try:
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
                timeout=120
            )
            
            response.raise_for_status()
            result = response.json()
            
            # Extract content from response
            if "choices" in result and len(result["choices"]) > 0:
                content = result["choices"][0]["message"]["content"]
                logger.info(f"[CLAUDE] Response received ({len(content)} chars)")
                
                return {
                    "content": content,
                    "usage": result.get("usage", {}),
                    "model": result.get("model", self.model)
                }
            else:
                raise Exception("No response content in API result")
                
        except requests.exceptions.RequestException as e:
            logger.error(f"[CLAUDE] API request failed: {e}")
            raise Exception(f"Claude API request failed: {str(e)}")
    
    def chat_with_json(self,
                      messages: List[Dict[str, str]],
                      max_tokens: int = 4096,
                      system: Optional[str] = None) -> Dict[str, Any]:
        """
        Send a chat request and parse JSON response.
        
        Args:
            messages: List of message dicts
            max_tokens: Maximum tokens in response
            system: Optional system prompt
            
        Returns:
            Parsed JSON object from response
        """
        # Add JSON instruction to system prompt
        json_instruction = "\n\nYou must respond with valid JSON only. Do not include any markdown formatting or explanations."
        
        if system:
            system = system + json_instruction
        else:
            system = json_instruction
        
        # Get response
        result = self.chat(messages, max_tokens, system)
        content = result["content"]
        
        # Parse JSON
        try:
            # Strip markdown code fences if present
            json_text = content.strip()
            if json_text.startswith("```json"):
                json_text = json_text[7:]
            if json_text.startswith("```"):
                json_text = json_text[3:]
            if json_text.endswith("```"):
                json_text = json_text[:-3]
            json_text = json_text.strip()
            
            parsed = json.loads(json_text)
            logger.info("[CLAUDE] Successfully parsed JSON response")
            return parsed
            
        except json.JSONDecodeError as e:
            logger.error(f"[CLAUDE] Failed to parse JSON: {e}")
            logger.error(f"Raw content: {content[:500]}...")
            raise Exception(f"Invalid JSON response from Claude: {str(e)}")


if __name__ == "__main__":
    # Test client when run directly
    try:
        print("Testing Claude Client...")
        print()
        
        client = ClaudeClient()
        
        # Test simple chat
        print("Sending test message...")
        response = client.chat([
            {"role": "user", "content": "Say 'Hello from Claude!' and nothing else."}
        ])
        
        print(f"✓ Response: {response['content']}")
        print(f"  Tokens used: {response['usage']}")
        print()
        
        # Test JSON response
        print("Testing JSON response...")
        json_response = client.chat_with_json([
            {"role": "user", "content": 'Respond with JSON: {"status": "ok", "message": "test"}'}
        ])
        
        print(f"✓ JSON response: {json_response}")
        print()
        
        print("=" * 70)
        print("✓ Claude client working correctly!")
        print("=" * 70)
        
    except Exception as e:
        print(f"\n✗ Client test failed: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
