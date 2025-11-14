"""Shot classification and analysis."""

from typing import Dict, Any, List
from pathlib import Path


class ShotAnalyzer:
    """Classifies shots into types (SOT, GV, etc.)."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.sot_min_speech = config['classification']['sot_min_speech_duration']
        self.sot_requires_face = config['classification']['sot_requires_face']
        self.gv_max_speech = config['classification']['gv_max_speech_duration']
    
    def classify_shot(self, 
                     has_face: bool,
                     speech_duration: float,
                     total_duration: float,
                     transcript: str) -> str:
        """
        Classify shot type based on heuristics.
        
        Args:
            has_face: Whether faces detected in keyframe
            speech_duration: Duration of speech in seconds
            total_duration: Total shot duration in seconds
            transcript: Transcribed text
        
        Returns:
            Shot type: 'SOT', 'GV', or 'CUTAWAY'
        """
        # SOT (Sound On Tape): Person speaking
        # - Has face visible
        # - Significant speech duration
        if has_face and speech_duration >= self.sot_min_speech:
            return 'SOT'
        
        # GV (General View): Establishing shots, b-roll
        # - Minimal or no speech
        # - May or may not have faces
        if speech_duration <= self.gv_max_speech:
            return 'GV'
        
        # CUTAWAY: Default for other shots
        # - Some speech but not enough for SOT
        # - Or no face but has speech
        return 'CUTAWAY'
    
    def analyze_shots(self, 
                     shots: List[Any],
                     transcriptions: List[Dict[str, Any]],
                     has_faces: List[bool]) -> List[str]:
        """
        Classify all shots in a video.
        
        Args:
            shots: List of Shot objects
            transcriptions: List of transcription results
            has_faces: List of boolean face detection results
        
        Returns:
            List of shot types
        """
        shot_types = []
        
        for shot, transcription, has_face in zip(shots, transcriptions, has_faces):
            # Calculate speech duration
            speech_duration = 0.0
            if transcription.get('words'):
                for word in transcription['words']:
                    speech_duration += (word['end'] - word['start'])
            
            # Classify
            shot_type = self.classify_shot(
                has_face=has_face,
                speech_duration=speech_duration,
                total_duration=shot.duration,
                transcript=transcription.get('text', '')
            )
            
            shot_types.append(shot_type)
        
        return shot_types
    
    def compute_shot_graph_edges(self, 
                                 shots: List[Any],
                                 shot_types: List[str],
                                 locations: List[str]) -> List[Dict[str, Any]]:
        """
        Compute edges for shot graph.
        
        Args:
            shots: List of Shot objects
            shot_types: List of shot type classifications
            locations: List of location strings (can be None)
        
        Returns:
            List of edge dictionaries with src, dst, type, weight
        """
        edges = []
        
        for i in range(len(shots)):
            # Adjacent edges (chronological)
            if i < len(shots) - 1:
                edges.append({
                    'src': i,
                    'dst': i + 1,
                    'type': 'adjacent',
                    'weight': 0.9
                })
            
            # Cutaway edges (for SOT shots, find nearby GV/CUTAWAY)
            if shot_types[i] == 'SOT':
                # Look for cutaways within ±10 minutes
                cutaway_window = 600  # seconds
                
                for j in range(len(shots)):
                    if i == j:
                        continue
                    
                    # Check if within time window
                    time_delta = abs(shots[j].start_time - shots[i].start_time)
                    if time_delta > cutaway_window:
                        continue
                    
                    # Check if it's a cutaway type
                    if shot_types[j] not in ['GV', 'CUTAWAY']:
                        continue
                    
                    # Check location consistency (if available)
                    same_location = True
                    if locations[i] and locations[j]:
                        same_location = locations[i] == locations[j]
                    
                    if same_location:
                        # Weight based on temporal proximity
                        weight = 0.8 * (1.0 - time_delta / cutaway_window)
                        edges.append({
                            'src': i,
                            'dst': j,
                            'type': 'cutaway',
                            'weight': weight
                        })
        
        return edges
