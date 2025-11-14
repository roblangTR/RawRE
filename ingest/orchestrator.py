"""
Ingest Orchestrator

Coordinates the full ingest pipeline: video processing, transcription,
embedding, storage, and optional Gemini video analysis.

NOTE: This is a simplified orchestrator. Full integration requires:
1. Adapting module interfaces to work together
2. Implementing proper error handling
3. Adding progress tracking
4. Testing with real video files
"""

import logging
from pathlib import Path
from typing import Dict, Optional
import json

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class IngestOrchestrator:
    """Orchestrates the complete ingest pipeline."""
    
    def __init__(self, config: Dict):
        """
        Initialize orchestrator with configuration.
        
        Args:
            config: Configuration dictionary with paths and settings
        """
        self.config = config
        logger.info("[ORCHESTRATOR] Initialized with config")
        
        # Initialize components
        from ingest.video_processor import VideoProcessor
        from ingest.transcriber import Transcriber
        from ingest.embedder import Embedder
        from storage.database import ShotsDatabase
        
        self.video_processor = VideoProcessor(config)
        self.transcriber = Transcriber(config)
        self.embedder = Embedder(config)
        
        # Initialize database
        db_path = config.get('database', {}).get('path', './data/shots.db')
        self.database = ShotsDatabase(db_path)
        logger.info(f"[ORCHESTRATOR] ✓ Database initialized: {db_path}")
        
        # Initialize Gemini analyzer if enabled
        self.gemini_analyzer = None
        if config.get('gemini', {}).get('enabled', False):
            try:
                from ingest.gemini_analyzer import GeminiAnalyzer
                self.gemini_analyzer = GeminiAnalyzer(config)
                logger.info("[ORCHESTRATOR] ✓ Gemini analyzer enabled")
            except Exception as e:
                logger.warning(f"[ORCHESTRATOR] Failed to initialize Gemini: {e}")
                logger.warning("[ORCHESTRATOR] Continuing without Gemini analysis")
        else:
            logger.info("[ORCHESTRATOR] Gemini analysis disabled in config")
    
    def ingest_video(self, 
                     video_path: str,
                     story_id: str,
                     metadata: Optional[Dict] = None) -> Dict:
        """
        Ingest a single video file through the complete pipeline.
        
        Args:
            video_path: Path to video file
            story_id: Story identifier
            metadata: Optional metadata dict
            
        Returns:
            Dictionary with ingest results and statistics
        """
        video_path = Path(video_path)
        
        if not video_path.exists():
            raise FileNotFoundError(f"Video file not found: {video_path}")
        
        logger.info(f"[ORCHESTRATOR] Starting ingest: {video_path.name}")
        logger.info(f"[ORCHESTRATOR] Story ID: {story_id}")
        
        results = {
            'video_path': str(video_path),
            'story_id': story_id,
            'shots_processed': 0,
            'shots_stored': 0,
            'errors': [],
            'success': False,
            'shots': []
        }
        
        try:
            # Step 1: Video Processing (shot detection, keyframes, proxies)
            logger.info("[ORCHESTRATOR] Step 1: Video processing...")
            output_base_dir = Path(self.config.get('paths', {}).get('data_dir', './data'))
            shots, video_metadata = self.video_processor.process_video(video_path, output_base_dir)
            results['shots_processed'] = len(shots)
            logger.info(f"[ORCHESTRATOR] ✓ Detected {len(shots)} shots")
            
            # Step 2: Generate Gemini proxy for batch analysis
            gemini_proxy_path = None
            if self.gemini_analyzer:
                logger.info("[ORCHESTRATOR] Step 2: Generating Gemini proxy...")
                gemini_proxy_dir = output_base_dir / "gemini_proxies"
                gemini_proxy_path = self.video_processor.generate_gemini_proxy(video_path, gemini_proxy_dir)
                logger.info(f"[ORCHESTRATOR] ✓ Gemini proxy created")
            
            # Step 3: Transcription
            logger.info("[ORCHESTRATOR] Step 3: Transcribing audio...")
            transcriptions = self.transcriber.transcribe_video(video_path, shots)
            logger.info(f"[ORCHESTRATOR] ✓ Transcribed {len(transcriptions)} shots")
            
            # Step 4: Gemini Video Analysis (if enabled)
            gemini_results = []
            if self.gemini_analyzer and gemini_proxy_path:
                logger.info("[ORCHESTRATOR] Step 4: Running Gemini analysis...")
                logger.debug(f"[ORCHESTRATOR] Analyzing {len(shots)} shots")
                
                # Prepare shot data for batch analysis
                shot_data_list = []
                video_paths_list = []
                proxy_paths_list = []
                
                for shot in shots:
                    shot_data_list.append({
                        'tc_in': self.video_processor.frames_to_timecode(shot.start_frame, video_metadata['fps']),
                        'tc_out': self.video_processor.frames_to_timecode(shot.end_frame, video_metadata['fps']),
                        'duration_ms': int(shot.duration * 1000)
                    })
                    # Use the Gemini proxy for all shots
                    video_paths_list.append(str(gemini_proxy_path))
                    proxy_paths_list.append(str(gemini_proxy_path))
                
                # Run batch analysis
                gemini_results = self.gemini_analyzer.analyze_shots_batch(
                    shot_data_list,
                    video_paths_list,
                    proxy_paths_list
                )
                logger.info(f"[ORCHESTRATOR] ✓ Gemini analyzed {len(gemini_results)} shots")
                
                # Debug: Check what we got back
                for idx, result in enumerate(gemini_results):
                    if result:
                        logger.debug(f"[ORCHESTRATOR] Shot {idx}: Got Gemini result with keys: {list(result.keys())}")
                    else:
                        logger.warning(f"[ORCHESTRATOR] Shot {idx}: Gemini result is None/empty")
            
            # Step 5: Generate Embeddings
            logger.info("[ORCHESTRATOR] Step 5: Generating embeddings...")
            
            # Collect texts for embedding
            texts = []
            for i, shot in enumerate(shots):
                transcript = transcriptions[i]['text'] if i < len(transcriptions) else ""
                gemini_desc = ""
                if i < len(gemini_results) and gemini_results[i]:
                    gemini_desc = gemini_results[i].get('enhanced_description', '')
                
                # Combine transcript and Gemini description
                combined_text = f"{transcript} {gemini_desc}".strip()
                texts.append(combined_text if combined_text else " ")
            
            # Generate text embeddings
            text_embeddings = self.embedder.embed_text(texts)
            
            # Generate visual embeddings from keyframes
            keyframe_paths = [Path(shot.keyframe_path) for shot in shots if shot.keyframe_path]
            visual_embeddings = self.embedder.embed_images_batch(keyframe_paths)
            
            logger.info(f"[ORCHESTRATOR] ✓ Generated embeddings")
            
            # Step 6: Store in Database
            logger.info("[ORCHESTRATOR] Step 6: Storing in database...")
            
            for i, shot in enumerate(shots):
                # Prepare shot data
                shot_data = {
                    'story_slug': story_id,
                    'filepath': str(video_path),
                    'capture_ts': video_metadata['creation_time'].timestamp(),
                    'tc_in': self.video_processor.frames_to_timecode(shot.start_frame, video_metadata['fps']),
                    'tc_out': self.video_processor.frames_to_timecode(shot.end_frame, video_metadata['fps']),
                    'fps': video_metadata['fps'],
                    'duration_ms': int(shot.duration * 1000),
                    'asr_text': transcriptions[i]['text'] if i < len(transcriptions) else None,
                    'asr_summary': self.transcriber.summarize_transcript(transcriptions[i]['text']) if i < len(transcriptions) else None,
                    'proxy_path': video_metadata.get('proxy_path'),
                    'thumb_path': shot.keyframe_path,
                    'embedding_text': text_embeddings[i] if i < len(text_embeddings) else None,
                    'embedding_visual': visual_embeddings[i] if i < len(visual_embeddings) else None
                }
                
                # Add Gemini metadata if available
                if i < len(gemini_results) and gemini_results[i] is not None:
                    gemini = gemini_results[i]
                    logger.debug(f"[ORCHESTRATOR] Adding Gemini metadata for shot {i}: {list(gemini.keys())}")
                    shot_data.update({
                        'gemini_description': gemini.get('enhanced_description'),
                        'gemini_shot_type': gemini.get('shot_type'),
                        'gemini_shot_size': gemini.get('shot_size'),
                        'gemini_camera_movement': gemini.get('camera_movement'),
                        'gemini_composition': gemini.get('composition'),
                        'gemini_lighting': gemini.get('lighting'),
                        'gemini_subjects': gemini.get('primary_subjects'),
                        'gemini_action': gemini.get('action_description'),
                        'gemini_quality': gemini.get('visual_quality'),
                        'gemini_context': gemini.get('news_context'),
                        'gemini_tone': gemini.get('tone'),
                        'gemini_confidence': gemini.get('confidence')
                    })
                
                # Detect faces
                if shot.keyframe_path:
                    shot_data['has_face'] = 1 if self.embedder.detect_faces(Path(shot.keyframe_path)) else 0
                
                # Insert into database
                shot_id = self.database.insert_shot(shot_data)
                
                # Add to results
                shot_data['shot_id'] = shot_id
                shot_data['duration_sec'] = shot.duration
                results['shots'].append(shot_data)
            
            results['shots_stored'] = len(shots)
            logger.info(f"[ORCHESTRATOR] ✓ Stored {len(shots)} shots in database")
            
            results['success'] = True
            logger.info(f"[ORCHESTRATOR] ✓ Ingest complete for {video_path.name}")
            
        except Exception as e:
            logger.error(f"[ORCHESTRATOR] ✗ Ingest failed: {e}")
            results['errors'].append(str(e))
            import traceback
            traceback.print_exc()
            raise
        
        return results
    
    def ingest_directory(self,
                        directory: str,
                        story_id: str,
                        file_pattern: str = "*.mp4",
                        metadata: Optional[Dict] = None) -> Dict:
        """
        Ingest all videos in a directory.
        
        Args:
            directory: Directory containing video files
            story_id: Story identifier
            file_pattern: Glob pattern for video files
            metadata: Optional metadata dict
            
        Returns:
            Dictionary with overall results
        """
        directory = Path(directory)
        
        if not directory.exists():
            raise FileNotFoundError(f"Directory not found: {directory}")
        
        video_files = list(directory.glob(file_pattern))
        
        if not video_files:
            raise ValueError(f"No video files found matching {file_pattern} in {directory}")
        
        logger.info(f"[ORCHESTRATOR] Found {len(video_files)} video files")
        
        results = {
            'directory': str(directory),
            'story_id': story_id,
            'total_files': len(video_files),
            'successful': 0,
            'failed': 0,
            'file_results': []
        }
        
        for video_file in video_files:
            try:
                file_result = self.ingest_video(
                    str(video_file),
                    story_id,
                    metadata
                )
                if file_result['success']:
                    results['successful'] += 1
                else:
                    results['failed'] += 1
                results['file_results'].append(file_result)
                
            except Exception as e:
                logger.error(f"[ORCHESTRATOR] Failed to ingest {video_file.name}: {e}")
                results['failed'] += 1
                results['file_results'].append({
                    'video_path': str(video_file),
                    'success': False,
                    'error': str(e)
                })
        
        logger.info(f"[ORCHESTRATOR] Directory ingest complete: {results['successful']}/{results['total_files']} successful")
        
        return results
    
    def get_story_stats(self, story_id: str) -> Dict:
        """
        Get statistics for an ingested story.
        
        Args:
            story_id: Story identifier
            
        Returns:
            Dictionary with story statistics
        """
        try:
            shots = self.database.get_shots_by_story(story_id)
            
            if not shots:
                return {
                    'story_id': story_id,
                    'exists': False,
                    'message': 'No shots found for this story'
                }
            
            # Calculate statistics
            total_duration = sum(shot['duration_ms'] for shot in shots) / 1000.0
            
            # Count shot types
            shot_types = {}
            for shot in shots:
                shot_type = shot.get('gemini_shot_type') or shot.get('shot_type') or 'unknown'
                shot_types[shot_type] = shot_types.get(shot_type, 0) + 1
            
            # Get unique source files
            source_files = list(set(shot['filepath'] for shot in shots))
            
            return {
                'story_id': story_id,
                'exists': True,
                'total_shots': len(shots),
                'total_duration': total_duration,
                'shot_types': shot_types,
                'source_files': source_files
            }
            
        except Exception as e:
            logger.error(f"[ORCHESTRATOR] Error getting story stats: {e}")
            return {
                'story_id': story_id,
                'exists': False,
                'error': str(e)
            }
