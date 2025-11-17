"""
Gemini Video Analysis Module

Analyzes video shots using Google's Gemini via Open Arena WebSocket API
to extract rich descriptive metadata including shot type, composition,
lighting, subjects, and more.

Uses Open Arena workflow instead of direct Vertex AI access.
"""

import json
import logging
import ssl
import certifi
from pathlib import Path
from typing import Dict, Any, Optional
from websockets.sync.client import connect
import requests

from agent.openarena_auth import get_auth_token

logger = logging.getLogger(__name__)


class GeminiAnalyzer:
    """Analyzes video shots using Gemini via Open Arena WebSocket API."""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize Gemini analyzer with Open Arena.
        
        Args:
            config: Configuration dictionary with Gemini settings
        """
        self.config = config
        self.gemini_config = config.get('gemini', {})
        self.enabled = self.gemini_config.get('enabled', False)
        
        if not self.enabled:
            logger.info("[GEMINI] Gemini analysis disabled in config")
            return
        
        # Get workflow ID from config
        self.workflow_id = self.gemini_config.get('workflow_id')
        if not self.workflow_id:
            logger.error("[GEMINI] workflow_id not found in gemini config")
            self.enabled = False
            return
        
        self.use_proxy = self.gemini_config.get('use_proxy_clips', True)
        
        # Open Arena endpoints
        self.upload_endpoint = "https://aiopenarena.gcs.int.thomsonreuters.com/v1/document/file_upload"
        self.ssl_context = ssl.create_default_context(cafile=certifi.where())
        
        # Get authentication token
        try:
            self.token = get_auth_token()
            self.websocket_url = f"wss://wymocw0zke.execute-api.us-east-1.amazonaws.com/prod?Authorization={self.token}"
            logger.info(f"[GEMINI] Initialized with Open Arena workflow: {self.workflow_id}")
        except Exception as e:
            logger.error(f"[GEMINI] Failed to get auth token: {e}")
            self.enabled = False
    
    def _get_system_instruction(self) -> str:
        """Get system instruction for Gemini model (used in workflow)."""
        return """You are an expert video analyst specializing in news and documentary footage analysis.

Your task is to analyze video clips and provide detailed, structured metadata in JSON format.

For each video clip, you should:
1. Provide an enhanced natural language description of what you see
2. Classify the shot type and size
3. Describe camera movement
4. Analyze composition and lighting
5. Identify primary subjects and actions
6. Assess visual quality
7. Determine the tone and news context

Be precise, objective, and thorough in your analysis. Focus on visual elements that would be important for video editing and news production.

IMPORTANT: Respond ONLY with valid JSON. Do not include any markdown formatting, code blocks, or additional text."""
    
    def _build_analysis_prompt(self, shot_data: Dict[str, Any]) -> str:
        """
        Build analysis prompt for a shot.
        
        Args:
            shot_data: Dictionary with shot metadata (timecodes, duration, etc.)
        
        Returns:
            Formatted prompt string
        """
        tc_in = shot_data.get('tc_in', '00:00:00:00')
        tc_out = shot_data.get('tc_out', '00:00:00:00')
        duration = shot_data.get('duration_ms', 0) / 1000.0
        
        prompt = f"""Analyze this video shot and provide detailed metadata.

Shot Information:
- Timecode In: {tc_in}
- Timecode Out: {tc_out}
- Duration: {duration:.2f} seconds

Provide a JSON response with the following structure:
{{
  "enhanced_description": "Detailed natural language description of what you see in the video",
  "shot_type": "establishing|action|detail|cutaway|interview|transition|b_roll",
  "shot_size": "extreme_wide|wide|medium_wide|medium|medium_close|close_up|extreme_close_up",
  "camera_movement": "static|pan_left|pan_right|tilt_up|tilt_down|tracking|handheld|zoom_in|zoom_out|crane|dolly",
  "composition": "Description of framing, rule of thirds, symmetry, etc.",
  "lighting": "Description of lighting conditions (natural/artificial, quality, direction)",
  "primary_subjects": ["list", "of", "main", "subjects", "in", "frame"],
  "action_description": "What is happening in the shot",
  "visual_quality": "excellent|good|fair|poor",
  "news_context": "background|main_story|b_roll|interview|establishing",
  "tone": "urgent|neutral|dramatic|somber|uplifting|tense",
  "confidence": 0.95
}}

Respond ONLY with the JSON object, no additional text or markdown formatting."""
        
        return prompt
    
    def analyze_shot(self, 
                    video_path: str,
                    shot_data: Dict[str, Any],
                    proxy_path: Optional[str] = None,
                    video_processor=None) -> Optional[Dict[str, Any]]:
        """
        Analyze a single shot with Gemini via Open Arena.
        
        Args:
            video_path: Path to original video file
            shot_data: Dictionary with shot metadata
            proxy_path: Optional path to proxy video (preferred if available)
            video_processor: Optional VideoProcessor instance for generating Gemini proxies
        
        Returns:
            Dictionary with enhanced metadata, or None if analysis fails
        """
        if not self.enabled:
            logger.debug("[GEMINI] Analysis disabled, skipping")
            return None
        
        try:
            # Determine which file to analyze
            analysis_path = video_path
            
            # If we have a video processor, generate ultra-low bitrate proxy for Gemini
            if video_processor and self.use_proxy:
                try:
                    gemini_proxy_dir = Path("data/gemini_proxies")
                    gemini_proxy_path = video_processor.generate_gemini_proxy(
                        Path(video_path), 
                        gemini_proxy_dir
                    )
                    analysis_path = gemini_proxy_path
                    logger.info(f"[GEMINI] Using Gemini proxy (1 Mbit/s)")
                except Exception as e:
                    logger.warning(f"[GEMINI] Failed to generate Gemini proxy: {e}")
                    # Fall back to provided proxy or original
                    if proxy_path and Path(proxy_path).exists():
                        analysis_path = proxy_path
            elif self.use_proxy and proxy_path and Path(proxy_path).exists():
                # Use provided proxy if available
                analysis_path = proxy_path
            
            if not Path(analysis_path).exists():
                logger.warning(f"[GEMINI] Video file not found: {analysis_path}")
                return None
            
            file_size_mb = Path(analysis_path).stat().st_size / 1024 / 1024
            logger.info(f"[GEMINI] Analyzing shot ({file_size_mb:.2f} MB)")
            
            # Check file size (Open Arena has ~15MB recommended limit)
            if file_size_mb > 15:
                logger.warning(f"[GEMINI] Large file ({file_size_mb:.2f} MB), may fail")
            
            # Build prompt
            user_prompt = self._build_analysis_prompt(shot_data)
            
            # Analyze via Open Arena
            result = self._analyze_video_openarena(analysis_path, user_prompt)
            
            logger.info("[GEMINI] ✓ Successfully analyzed shot")
            return result
        
        except Exception as e:
            logger.error(f"[GEMINI] Error analyzing shot: {e}")
            return None
    
    def _analyze_video_openarena(self, video_path: str, user_prompt: str) -> Dict[str, Any]:
        """
        Analyze a video file using Open Arena WebSocket API.
        
        Args:
            video_path: Path to the video file
            user_prompt: User prompt to send
            
        Returns:
            Dict containing the analysis results
        """
        import time
        start_time = time.time()
        
        video_file = Path(video_path)
        
        try:
            # Step 1: Get pre-signed URL for file upload
            logger.info("[GEMINI] [1/4] Getting pre-signed URL...")
            presigned_data = self._get_presigned_url(video_file.name)
            
            # Step 2: Upload video to S3
            logger.info("[GEMINI] [2/4] Uploading video to S3...")
            self._upload_to_s3(video_path, presigned_data)
            
            # Step 3: Connect to WebSocket and parse video
            logger.info("[GEMINI] [3/4] Parsing video...")
            ws = connect(self.websocket_url, ssl_context=self.ssl_context)
            
            try:
                file_uuid = self._parse_file(ws, presigned_data)
                logger.info(f"[GEMINI] Video parsed. UUID: {file_uuid}")
                
                # Step 4: Send analysis request
                logger.info("[GEMINI] [4/4] Analyzing...")
                result = self._analyze_with_prompt(ws, file_uuid, user_prompt)
                
                duration = time.time() - start_time
                logger.info(f"[GEMINI] Complete in {duration:.2f}s")
                return result
                
            finally:
                ws.close()
                
        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"[GEMINI] Failed after {duration:.2f}s: {e}")
            raise
    
    def _get_presigned_url(self, filename: str) -> Dict[str, Any]:
        """Get pre-signed URL for file upload."""
        headers = {"Authorization": f"Bearer {self.token}"}
        payload = {"file_name": filename}
        
        response = requests.post(
            self.upload_endpoint,
            headers=headers,
            json=payload,
            timeout=30
        )
        response.raise_for_status()
        
        data = response.json()
        if not data.get("url"):
            raise Exception("No pre-signed URL returned from API")
        
        return data
    
    def _upload_to_s3(self, video_path: str, presigned_data: Dict[str, Any]):
        """Upload video file to S3 using pre-signed URL."""
        s3_url = presigned_data["url"]
        s3_fields = presigned_data["fields"]
        
        with open(video_path, "rb") as f:
            file_content = f.read()
        
        response = requests.post(
            s3_url,
            data=s3_fields,
            files={"file": file_content},
            timeout=120
        )
        response.raise_for_status()
    
    def _parse_file(self, ws, presigned_data: Dict[str, Any]) -> str:
        """Parse the uploaded file via WebSocket."""
        parse_payload = {
            "action": "ParseFile",
            "workflow_id": self.workflow_id,
            "presigned_url": {
                "url": presigned_data["url"],
                "fields": presigned_data["fields"],
                "file_name": presigned_data["file_name"]
            }
        }
        
        ws.send(json.dumps(parse_payload))
        
        # Wait for parse response
        raw_message = ws.recv()
        response = json.loads(raw_message)
        
        if "file_parse" in response and "file_uuid" in response["file_parse"]:
            return response["file_parse"]["file_uuid"]
        else:
            raise Exception(f"File parsing failed: {response}")
    
    def _analyze_with_prompt(self, ws, file_uuid: str, user_prompt: str) -> Dict[str, Any]:
        """Send analysis request and collect response."""
        analysis_request = {
            "action": "SendMessage",
            "workflow_id": self.workflow_id,
            "query": user_prompt,
            "is_persistence_allowed": False,
            "file_uuid": [file_uuid]
        }
        
        ws.send(json.dumps(analysis_request))
        
        # Collect the response
        full_response = ""
        end_of_response = False
        component_id = None
        
        while not end_of_response:
            raw_message = ws.recv()
            message = json.loads(raw_message)
            
            # Skip messages that only contain request_id
            if list(message.keys()) == ["request_id"]:
                continue
            
            # Check if this is a timeout/error message
            if "message" in message and "connectionId" in message:
                logger.warning(f"[GEMINI] Connection message: {message.get('message')}")
                continue
            
            # Find component with "answer" field
            for key, value in message.items():
                if isinstance(value, dict):
                    if "answer" in value:
                        if component_id is None:
                            component_id = key
                        
                        if key == component_id:
                            answer = value.get("answer", "")
                            full_response += answer
                    
                    # Check for end marker
                    if key == component_id and "cost_track" in value:
                        end_of_response = True
                        break
        
        if not full_response:
            raise Exception("No response received from model")
        
        # Parse JSON response
        try:
            # Strip markdown code fences if present
            json_text = full_response.strip()
            if json_text.startswith("```json"):
                json_text = json_text[7:]
            if json_text.startswith("```"):
                json_text = json_text[3:]
            if json_text.endswith("```"):
                json_text = json_text[:-3]
            json_text = json_text.strip()
            
            result = json.loads(json_text)
            
            # Validate required fields
            required_fields = ['enhanced_description', 'shot_type', 'shot_size']
            for field in required_fields:
                if field not in result:
                    logger.warning(f"[GEMINI] Missing field: {field}")
                    result[field] = 'unknown'
            
            # Debug: Log what we're returning
            logger.debug(f"[GEMINI] Returning result with keys: {list(result.keys())}")
            
            return result
            
        except json.JSONDecodeError as e:
            logger.error(f"[GEMINI] Failed to parse JSON: {e}")
            logger.error(f"[GEMINI] Response: {full_response[:500]}")
            
            # Return fallback with raw response
            return {
                'enhanced_description': full_response,
                'shot_type': 'unknown',
                'shot_size': 'unknown',
                'error': 'Failed to parse structured response',
                'raw_response': full_response
            }
    
    def analyze_shots_batch(self,
                           shots_data: list[Dict[str, Any]],
                           video_paths: list[str],
                           proxy_paths: Optional[list[str]] = None,
                           video_processor=None) -> list[Optional[Dict[str, Any]]]:
        """
        Analyze multiple shots in batch.
        
        Args:
            shots_data: List of shot metadata dictionaries
            video_paths: List of video file paths
            proxy_paths: Optional list of proxy video paths
            video_processor: Optional VideoProcessor instance for generating Gemini proxies
        
        Returns:
            List of analysis results (None for failed analyses)
        """
        if not self.enabled:
            logger.info("[GEMINI] Analysis disabled, returning empty results")
            return [None] * len(shots_data)
        
        results = []
        
        # Handle proxy_paths being None
        if proxy_paths is None:
            proxy_paths_list: list[Optional[str]] = [None] * len(shots_data)
        else:
            proxy_paths_list = [p for p in proxy_paths]  # Convert to list that can contain Optional[str]
        
        for i, (shot_data, video_path, proxy_path) in enumerate(zip(shots_data, video_paths, proxy_paths_list), 1):
            logger.info(f"[GEMINI] Processing shot {i}/{len(shots_data)}")
            
            result = self.analyze_shot(video_path, shot_data, proxy_path, video_processor)
            results.append(result)
            
            # Small delay to avoid rate limiting
            if i < len(shots_data):
                import time
                time.sleep(0.5)
        
        successful = sum(1 for r in results if r is not None)
        logger.info(f"[GEMINI] Batch complete: {successful}/{len(shots_data)} successful")
        
        return results
    
    def analyze_sequence_for_picking(self, 
                                    sequence_name: str,
                                    shots: list[Dict[str, Any]],
                                    video_paths: list[str],
                                    proxy_paths: Optional[list[str]] = None) -> Optional[Dict[str, Any]]:
        """
        Analyze a sequence of shots for visual continuity and transition quality.
        
        This method is used during the picking phase to understand how shots within
        a sequence work together, identify jump cuts, and recommend optimal subsequences.
        
        Args:
            sequence_name: Name of the sequence being analyzed
            shots: List of shot dictionaries with metadata
            video_paths: List of video file paths for each shot
            proxy_paths: Optional list of proxy video paths
            
        Returns:
            Dictionary with sequence analysis including:
            - Shot-level assessments (quality, characteristics, compatibility)
            - Recommended subsequences
            - Entry/exit points
            - Jump cut warnings
            - Overall sequence quality
        """
        if not self.enabled:
            logger.debug("[GEMINI] Sequence analysis disabled, skipping")
            return None
        
        if not shots:
            logger.warning("[GEMINI] No shots provided for sequence analysis")
            return None
        
        try:
            # Import here to avoid circular dependency
            from agent.system_prompts import get_sequence_analysis_prompt
            
            # Format shot information for the prompt
            shots_info_lines = []
            for i, shot in enumerate(shots, 1):
                shot_id = shot.get('shot_id', i)
                duration = shot.get('duration_ms', 0) / 1000.0
                shot_type = shot.get('shot_type', 'unknown')
                shot_size = shot.get('shot_size', 'unknown')
                gemini_desc = shot.get('gemini_context', 'No description')
                
                shots_info_lines.append(
                    f"Shot {shot_id}:\n"
                    f"  Duration: {duration:.1f}s\n"
                    f"  Type: {shot_type}\n"
                    f"  Size: {shot_size}\n"
                    f"  Description: {gemini_desc}\n"
                )
            
            shots_info = "\n".join(shots_info_lines)
            
            # Build the analysis prompt
            user_prompt = get_sequence_analysis_prompt(sequence_name, shots_info)
            
            # For sequence analysis, we'll analyze using the first shot's video
            # (Gemini can infer relationships from context + descriptions)
            video_path = video_paths[0] if video_paths else None
            proxy_path = proxy_paths[0] if proxy_paths and len(proxy_paths) > 0 else None
            
            if not video_path:
                logger.warning("[GEMINI] No video path for sequence analysis")
                return None
            
            # Determine which file to analyze
            analysis_path = video_path
            if proxy_path and Path(proxy_path).exists():
                analysis_path = proxy_path
            
            if not Path(analysis_path).exists():
                logger.warning(f"[GEMINI] Video file not found: {analysis_path}")
                return None
            
            logger.info(f"[GEMINI] Analyzing sequence '{sequence_name}' ({len(shots)} shots)")
            
            # Analyze via Open Arena
            result = self._analyze_video_openarena(analysis_path, user_prompt)
            
            # Validate sequence analysis result
            if not isinstance(result, dict):
                logger.warning("[GEMINI] Invalid sequence analysis result")
                return None
            
            # Ensure required fields exist
            if 'sequence_name' not in result:
                result['sequence_name'] = sequence_name
            
            if 'shots' not in result:
                logger.warning("[GEMINI] No shot-level analysis in result")
                result['shots'] = {}
            
            logger.info(f"[GEMINI] ✓ Sequence '{sequence_name}' analyzed successfully")
            return result
        
        except Exception as e:
            logger.error(f"[GEMINI] Error analyzing sequence '{sequence_name}': {e}")
            return None
    
    def analyze_all_sequences(self,
                             sequences: Dict[str, list[Dict[str, Any]]],
                             video_paths_map: Dict[str, list[str]],
                             proxy_paths_map: Optional[Dict[str, list[str]]] = None) -> Dict[str, Optional[Dict[str, Any]]]:
        """
        Analyze all sequences in a batch for visual continuity.
        
        Args:
            sequences: Dictionary mapping sequence names to lists of shots
            video_paths_map: Dictionary mapping sequence names to lists of video paths
            proxy_paths_map: Optional dictionary mapping sequence names to lists of proxy paths
            
        Returns:
            Dictionary mapping sequence names to analysis results
        """
        if not self.enabled:
            logger.info("[GEMINI] Sequence analysis disabled, returning empty results")
            return {name: None for name in sequences.keys()}
        
        results = {}
        sequence_count = len(sequences)
        
        # Get batch size from config (default to 6 sequences at a time)
        batch_size = self.gemini_config.get('picking', {}).get('sequence_batch_size', 6)
        
        logger.info(f"[GEMINI] Analyzing {sequence_count} sequences (batch size: {batch_size})")
        
        for i, (seq_name, shots) in enumerate(sequences.items(), 1):
            logger.info(f"[GEMINI] Processing sequence {i}/{sequence_count}: '{seq_name}'")
            
            # Get video and proxy paths for this sequence
            video_paths = video_paths_map.get(seq_name, [])
            proxy_paths = None
            if proxy_paths_map:
                proxy_paths = proxy_paths_map.get(seq_name)
            
            # Analyze the sequence
            result = self.analyze_sequence_for_picking(
                seq_name,
                shots,
                video_paths,
                proxy_paths
            )
            
            results[seq_name] = result
            
            # Small delay between sequences to avoid rate limiting
            if i < sequence_count:
                import time
                time.sleep(0.5)
        
        successful = sum(1 for r in results.values() if r is not None)
        logger.info(f"[GEMINI] Sequence analysis complete: {successful}/{sequence_count} successful")
        
        return results
