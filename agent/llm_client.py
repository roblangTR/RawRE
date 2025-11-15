"""
LLM Client for Claude via Open Arena API

Provides a simple interface for making Claude API calls through Open Arena.
"""

import json
import logging
import requests
from typing import Dict, Any, List, Optional
from .openarena_auth import get_auth_token
from .interaction_logger import get_interaction_logger

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ClaudeClient:
    """Client for Claude API via Open Arena."""
    
    def __init__(self, model: str = "claude-3-5-sonnet-20241022", temperature: float = 0.1, enable_logging: bool = True):
        """
        Initialize Claude client.
        
        Args:
            model: Claude model identifier
            temperature: Sampling temperature (0.0-1.0)
            enable_logging: Enable interaction logging
        """
        self.model = model
        self.temperature = temperature
        self.base_url = "https://aiopenarena.gcs.int.thomsonreuters.com/v1"
        self.token = None
        self.enable_logging = enable_logging
        
        logger.info(f"[CLAUDE] Initialized with model: {model}, temperature: {temperature}")
        if enable_logging:
            logger.info(f"[CLAUDE] Interaction logging enabled")
    
    def _ensure_token(self):
        """Ensure we have a valid authentication token."""
        if not self.token:
            self.token = get_auth_token()
    
    def chat(self, 
             query: str,
             workflow_id: Optional[str] = None,
             context: Optional[str] = None,
             module: Optional[str] = None) -> Dict[str, Any]:
        """
        Send an inference request to Open Arena.
        
        Args:
            query: The user query/prompt
            workflow_id: Optional workflow ID (uses default if not provided)
            context: Optional context string
            module: Optional module name ('planner', 'picker', 'verifier') to use module-specific workflow
            
        Returns:
            Response dictionary with 'content', 'usage', etc.
        
        Note:
            Model configuration (model type, temperature, max_tokens, system_prompt) should be
            configured in the Open Arena workflow itself. This keeps the workflow as the single
            source of truth for all model parameters.
        """
        self._ensure_token()
        
        # Use module-specific workflow if module is specified
        if not workflow_id:
            import os
            if module:
                # Try module-specific workflow ID first
                workflow_id = os.getenv(f'{module.upper()}_WORKFLOW_ID')
                if workflow_id:
                    logger.info(f"[CLAUDE] Using {module} workflow: {workflow_id}")
            
            # Fall back to default workflow
            if not workflow_id:
                workflow_id = os.getenv('WORKFLOW_ID')
                if not workflow_id:
                    raise Exception("No workflow_id provided and WORKFLOW_ID not set in environment")
        
        # Construct request payload per Open Arena API spec
        # Note: Model parameters (model, temperature, max_tokens, system_prompt) are
        # configured in the workflow itself, not sent in the request
        payload = {
            "workflow_id": workflow_id,
            "query": query,
            "is_persistence_allowed": False
        }
        
        # Add context if provided
        if context:
            payload["context"] = context
        
        # Make API request
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
        
        logger.debug(f"[CLAUDE] Sending inference request to workflow {workflow_id}")
        
        # Log request details
        logger.info(f"[CLAUDE] REQUEST to workflow {workflow_id}")
        logger.info(f"[CLAUDE] Query length: {len(query)} chars")
        if context:
            logger.info(f"[CLAUDE] Context length: {len(context)} chars")
        logger.debug(f"[CLAUDE] Full request payload: {json.dumps(payload, indent=2)[:500]}...")
        
        try:
            response = requests.post(
                f"{self.base_url}/inference",
                headers=headers,
                json=payload,
                timeout=120
            )
            
            response.raise_for_status()
            result = response.json()
            
            # Extract content from Open Arena response
            # Open Arena returns nested structure: result.answer.{node_id}
            content = None
            if "result" in result and "answer" in result["result"]:
                # Get the first answer from any LLM node
                answers = result["result"]["answer"]
                if answers:
                    # Get first answer value
                    content = next(iter(answers.values()))
            
            # Fallback to other possible response formats
            if not content:
                content = result.get("response") or result.get("answer") or str(result)
            
            logger.info(f"[CLAUDE] Response received ({len(str(content))} chars)")
            
            # Log interaction if enabled
            if self.enable_logging and module:
                try:
                    interaction_logger = get_interaction_logger()
                    interaction_logger.log_interaction(
                        agent=module,
                        interaction_type='chat',
                        prompt=query,
                        response=content,
                        system_prompt=None,  # System prompt is in workflow, not sent in request
                        context=context,
                        metadata={
                            'model': self.model,
                            'temperature': self.temperature,
                            'workflow_id': workflow_id
                        },
                        raw_request=payload,
                        raw_response=result
                    )
                except Exception as e:
                    logger.warning(f"[CLAUDE] Failed to log interaction: {e}")
            
            return {
                "content": content,
                "usage": result.get("usage", {}),
                "model": result.get("model", self.model),
                "raw_response": result
            }
                
        except requests.exceptions.RequestException as e:
            logger.error(f"[CLAUDE] API request failed: {e}")
            raise Exception(f"Claude API request failed: {str(e)}")
    
    def chat_with_json(self,
                      query: str,
                      workflow_id: Optional[str] = None,
                      context: Optional[str] = None) -> Dict[str, Any]:
        """
        Send a chat request and parse JSON response.
        
        Args:
            query: The user query/prompt
            workflow_id: Optional workflow ID
            context: Optional context string
            
        Returns:
            Parsed JSON object from response
        
        Note:
            The workflow should be configured to return JSON responses.
            If needed, add JSON formatting instructions to the query itself.
        """
        # Add JSON instruction to query
        json_instruction = "\n\nYou must respond with valid JSON only. Do not include any markdown formatting or explanations."
        query_with_instruction = query + json_instruction
        
        # Get response
        result = self.chat(query_with_instruction, workflow_id, context)
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
    import os
    from dotenv import load_dotenv
    
    load_dotenv()
    
    try:
        print("Testing Claude Client...")
        print()
        
        # Check for workflow ID
        workflow_id = os.getenv('WORKFLOW_ID')
        if not workflow_id:
            print("✗ WORKFLOW_ID not set in .env file")
            print("  Please add WORKFLOW_ID to your .env")
            exit(1)
        
        client = ClaudeClient()
        
        # Test simple chat
        print("Sending test message...")
        response = client.chat(
            query="Say 'Hello from Claude!' and nothing else.",
            workflow_id=workflow_id
        )
        
        print(f"✓ Response: {response['content']}")
        print(f"  Usage: {response['usage']}")
        print()
        
        # Test JSON response
        print("Testing JSON response...")
        json_response = client.chat_with_json(
            query='Respond with JSON: {"status": "ok", "message": "test"}',
            workflow_id=workflow_id
        )
        
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
