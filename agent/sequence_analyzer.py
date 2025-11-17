"""
Sequence Analyzer Module

Groups candidate shots into logical sequences based on location, temporal proximity,
and visual similarity. This enables sequence-aware visual analysis for better
editorial decisions and jump cut avoidance.
"""

import logging
from typing import Dict, List, Optional, Tuple, Set
from collections import defaultdict
from datetime import datetime
import numpy as np
from sklearn.cluster import DBSCAN
import yaml
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class SequenceAnalyzer:
    """Analyzes and groups shots into logical sequences for picking."""
    
    def __init__(self, config: Optional[Dict] = None):
        """
        Initialize sequence analyzer.
        
        Args:
            config: Configuration dictionary (optional, will load from config.yaml if not provided)
        """
        # Load config if not provided
        if config is None:
            config_path = Path(__file__).parent.parent / 'config.yaml'
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
        
        self.config = config
        
        # Sequence grouping parameters (with defaults)
        seq_config = config.get('sequences', {}) if config else {}
        self.temporal_window_minutes = seq_config.get('temporal_window_minutes', 5)
        self.visual_similarity_threshold = seq_config.get('visual_similarity_threshold', 0.7)
        self.min_shots_per_sequence = seq_config.get('min_shots_per_sequence', 2)
        self.max_shots_per_sequence = seq_config.get('max_shots_per_sequence', 8)
        
        logger.info("[SEQUENCE_ANALYZER] Initialized")
        logger.info(f"[SEQUENCE_ANALYZER] Temporal window: {self.temporal_window_minutes} minutes")
        logger.info(f"[SEQUENCE_ANALYZER] Visual similarity threshold: {self.visual_similarity_threshold}")
    
    def group_by_sequences(self,
                          shots: List[Dict],
                          method: str = 'hybrid') -> Dict[str, List[Dict]]:
        """
        Group candidate shots into logical sequences.
        
        Args:
            shots: List of shot dictionaries
            method: Grouping method - 'location', 'temporal', 'visual', or 'hybrid'
            
        Returns:
            Dictionary mapping sequence names to lists of shots
            Example: {
                "parliament_exterior_morning": [shot1, shot2, shot3],
                "protest_march_street": [shot4, shot5, shot6, shot7],
                "interview_indoor": [shot8, shot9],
                "cutaways_various": [shot10, shot11]
            }
        """
        if not shots:
            logger.warning("[SEQUENCE_ANALYZER] No shots provided for grouping")
            return {}
        
        logger.info(f"[SEQUENCE_ANALYZER] Grouping {len(shots)} shots using '{method}' method")
        
        if method == 'location':
            sequences = self._group_by_location(shots)
        elif method == 'temporal':
            sequences = self._group_by_temporal_proximity(shots)
        elif method == 'visual':
            sequences = self._group_by_visual_similarity(shots)
        elif method == 'hybrid':
            sequences = self._hybrid_grouping(shots)
        else:
            logger.warning(f"[SEQUENCE_ANALYZER] Unknown method '{method}', falling back to hybrid")
            sequences = self._hybrid_grouping(shots)
        
        # Filter sequences by size constraints
        filtered_sequences = self._filter_sequences(sequences)
        
        logger.info(f"[SEQUENCE_ANALYZER] Created {len(filtered_sequences)} sequences")
        for seq_name, seq_shots in filtered_sequences.items():
            logger.info(f"[SEQUENCE_ANALYZER]   - {seq_name}: {len(seq_shots)} shots")
        
        return filtered_sequences
    
    def _group_by_location(self, shots: List[Dict]) -> Dict[str, List[Dict]]:
        """
        Group shots by location metadata.
        
        Args:
            shots: List of shot dictionaries
            
        Returns:
            Dictionary mapping location names to shots
        """
        sequences = defaultdict(list)
        
        for shot in shots:
            location = shot.get('location')
            
            if location and location.strip():
                # Use location as sequence name
                seq_name = self._normalize_sequence_name(location)
            else:
                # No location metadata - group by context if available
                context = shot.get('gemini_context', '').lower()
                if 'indoor' in context or 'interior' in context:
                    seq_name = 'indoor_unknown'
                elif 'outdoor' in context or 'exterior' in context:
                    seq_name = 'outdoor_unknown'
                else:
                    seq_name = 'location_unknown'
            
            sequences[seq_name].append(shot)
        
        logger.info(f"[SEQUENCE_ANALYZER] Location grouping: {len(sequences)} groups")
        return dict(sequences)
    
    def _group_by_temporal_proximity(self, shots: List[Dict]) -> Dict[str, List[Dict]]:
        """
        Group shots by temporal proximity (time-based clustering).
        
        Args:
            shots: List of shot dictionaries
            
        Returns:
            Dictionary mapping temporal sequence names to shots
        """
        if not shots:
            return {}
        
        # Sort by capture time
        sorted_shots = sorted(shots, key=lambda s: s['capture_ts'])
        
        sequences = {}
        current_sequence = []
        sequence_count = 1
        
        for i, shot in enumerate(sorted_shots):
            if not current_sequence:
                # Start new sequence
                current_sequence = [shot]
            else:
                # Check temporal proximity to last shot in current sequence
                last_shot = current_sequence[-1]
                time_diff_seconds = abs(shot['capture_ts'] - last_shot['capture_ts'])
                time_diff_minutes = time_diff_seconds / 60.0
                
                if time_diff_minutes <= self.temporal_window_minutes:
                    # Add to current sequence
                    current_sequence.append(shot)
                else:
                    # Save current sequence and start new one
                    seq_name = self._generate_temporal_sequence_name(
                        current_sequence,
                        sequence_count
                    )
                    sequences[seq_name] = current_sequence
                    sequence_count += 1
                    current_sequence = [shot]
        
        # Don't forget the last sequence
        if current_sequence:
            seq_name = self._generate_temporal_sequence_name(
                current_sequence,
                sequence_count
            )
            sequences[seq_name] = current_sequence
        
        logger.info(f"[SEQUENCE_ANALYZER] Temporal grouping: {len(sequences)} sequences")
        return sequences
    
    def _group_by_visual_similarity(self, shots: List[Dict]) -> Dict[str, List[Dict]]:
        """
        Group shots by visual similarity using CLIP embeddings.
        
        Args:
            shots: List of shot dictionaries
            
        Returns:
            Dictionary mapping visual sequence names to shots
        """
        # Filter shots with visual embeddings
        shots_with_embeddings = [
            s for s in shots if s.get('embedding_visual') is not None
        ]
        
        if len(shots_with_embeddings) < 2:
            logger.warning("[SEQUENCE_ANALYZER] Not enough shots with visual embeddings")
            # Fall back to single sequence
            return {'visual_sequence_1': shots}
        
        # Extract embeddings as numpy array
        embeddings = np.array([s['embedding_visual'] for s in shots_with_embeddings])
        
        # Normalize embeddings for cosine similarity
        norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
        embeddings_normalized = embeddings / (norms + 1e-8)
        
        # Compute pairwise cosine similarities
        similarity_matrix = np.dot(embeddings_normalized, embeddings_normalized.T)
        
        # Convert to distance matrix (1 - similarity)
        # Clip to handle floating point precision issues
        distance_matrix = np.clip(1 - similarity_matrix, 0.0, 2.0)
        
        # Apply DBSCAN clustering
        # eps is the maximum distance for samples to be considered neighbors
        eps = 1 - self.visual_similarity_threshold  # Convert similarity to distance
        clustering = DBSCAN(
            eps=eps,
            min_samples=self.min_shots_per_sequence,
            metric='precomputed'
        )
        
        labels = clustering.fit_predict(distance_matrix)
        
        # Group shots by cluster labels
        sequences = defaultdict(list)
        for shot, label in zip(shots_with_embeddings, labels):
            if label == -1:
                # Noise/outlier shots - group separately
                seq_name = 'visual_outliers'
            else:
                seq_name = f'visual_cluster_{label + 1}'
            
            sequences[seq_name].append(shot)
        
        # Add shots without embeddings to outliers
        shots_without_embeddings = [
            s for s in shots if s.get('embedding_visual') is None
        ]
        if shots_without_embeddings:
            if 'visual_outliers' not in sequences:
                sequences['visual_outliers'] = []
            sequences['visual_outliers'].extend(shots_without_embeddings)
        
        logger.info(f"[SEQUENCE_ANALYZER] Visual grouping: {len(sequences)} clusters")
        return dict(sequences)
    
    def _hybrid_grouping(self, shots: List[Dict]) -> Dict[str, List[Dict]]:
        """
        Hybrid approach combining location, temporal, and visual grouping.
        
        Strategy:
        1. Start with location-based grouping
        2. Within each location group, apply temporal clustering
        3. If groups are too large, further split by visual similarity
        
        Args:
            shots: List of shot dictionaries
            
        Returns:
            Dictionary mapping hybrid sequence names to shots
        """
        logger.info("[SEQUENCE_ANALYZER] Applying hybrid grouping strategy")
        
        # Step 1: Group by location
        location_groups = self._group_by_location(shots)
        
        final_sequences = {}
        
        for loc_name, loc_shots in location_groups.items():
            logger.info(f"[SEQUENCE_ANALYZER] Processing location group '{loc_name}' "
                       f"({len(loc_shots)} shots)")
            
            # Step 2: Apply temporal clustering within location
            temporal_seqs = self._group_by_temporal_proximity(loc_shots)
            
            for temp_name, temp_shots in temporal_seqs.items():
                # Check if this temporal sequence is too large
                if len(temp_shots) > self.max_shots_per_sequence:
                    logger.info(f"[SEQUENCE_ANALYZER] Temporal sequence too large "
                               f"({len(temp_shots)} shots), applying visual split")
                    
                    # Step 3: Further split by visual similarity
                    visual_seqs = self._group_by_visual_similarity(temp_shots)
                    
                    for vis_name, vis_shots in visual_seqs.items():
                        # Combine names
                        combined_name = f"{loc_name}_{vis_name}"
                        final_sequences[combined_name] = vis_shots
                else:
                    # Name the sequence
                    combined_name = f"{loc_name}_{temp_name}"
                    final_sequences[combined_name] = temp_shots
        
        logger.info(f"[SEQUENCE_ANALYZER] Hybrid grouping created {len(final_sequences)} sequences")
        return final_sequences
    
    def _filter_sequences(self, sequences: Dict[str, List[Dict]]) -> Dict[str, List[Dict]]:
        """
        Filter and trim sequences based on size constraints.
        
        Args:
            sequences: Dictionary of sequences
            
        Returns:
            Filtered sequences
        """
        filtered = {}
        small_shots = []
        
        for seq_name, shots in sequences.items():
            if len(shots) < self.min_shots_per_sequence:
                # Sequence too small - collect for "miscellaneous"
                small_shots.extend(shots)
            elif len(shots) > self.max_shots_per_sequence:
                # Sequence too large - trim to max size (keep best shots)
                logger.warning(f"[SEQUENCE_ANALYZER] Trimming '{seq_name}' from "
                             f"{len(shots)} to {self.max_shots_per_sequence} shots")
                
                # Sort by relevance score if available
                sorted_shots = sorted(
                    shots,
                    key=lambda s: s.get('relevance_score', 0),
                    reverse=True
                )
                filtered[seq_name] = sorted_shots[:self.max_shots_per_sequence]
            else:
                # Sequence is within acceptable size
                filtered[seq_name] = shots
        
        # Create miscellaneous sequence for small groups
        if small_shots:
            logger.info(f"[SEQUENCE_ANALYZER] Creating 'miscellaneous' sequence "
                       f"with {len(small_shots)} shots from small groups")
            filtered['miscellaneous'] = small_shots
        
        return filtered
    
    def _normalize_sequence_name(self, name: str) -> str:
        """
        Normalize a sequence name for consistency.
        
        Args:
            name: Raw sequence name
            
        Returns:
            Normalized name (lowercase, underscores)
        """
        # Convert to lowercase and replace spaces with underscores
        normalized = name.lower().strip()
        normalized = normalized.replace(' ', '_')
        normalized = normalized.replace('-', '_')
        
        # Remove special characters
        normalized = ''.join(c for c in normalized if c.isalnum() or c == '_')
        
        return normalized
    
    def _generate_temporal_sequence_name(self,
                                        shots: List[Dict],
                                        sequence_num: int) -> str:
        """
        Generate a descriptive name for a temporal sequence.
        
        Args:
            shots: Shots in the sequence
            sequence_num: Sequence number
            
        Returns:
            Sequence name
        """
        if not shots:
            return f"temporal_seq_{sequence_num}"
        
        # Try to use location info if available
        locations: List[str] = [s['location'] for s in shots if s.get('location')]
        if locations:
            # Use most common location
            location_counts: Dict[str, int] = defaultdict(int)
            for loc in locations:
                location_counts[loc] += 1
            most_common = max(location_counts.items(), key=lambda x: x[1])[0]
            return self._normalize_sequence_name(f"{most_common}_seq_{sequence_num}")
        
        # Try to use Gemini context info
        contexts = []
        for shot in shots:
            context = shot.get('gemini_context', '')
            if context:
                contexts.append(context)
        
        if contexts:
            # Simple heuristic: look for common keywords
            context_text = ' '.join(contexts).lower()
            if 'indoor' in context_text or 'interior' in context_text:
                return f"indoor_seq_{sequence_num}"
            elif 'outdoor' in context_text or 'exterior' in context_text:
                return f"outdoor_seq_{sequence_num}"
        
        # Fallback to generic name
        return f"temporal_seq_{sequence_num}"
    
    def get_sequence_metadata(self, sequence: List[Dict]) -> Dict:
        """
        Extract metadata about a sequence.
        
        Args:
            sequence: List of shots in the sequence
            
        Returns:
            Dictionary with sequence metadata
        """
        if not sequence:
            return {
                'shot_count': 0,
                'total_duration': 0.0,
                'shot_types': [],
                'has_sot': False,
                'time_span_minutes': 0.0
            }
        
        # Calculate statistics
        shot_types = [s.get('shot_type', 'UNKNOWN') for s in sequence]
        shot_type_counts = defaultdict(int)
        for st in shot_types:
            shot_type_counts[st] += 1
        
        total_duration = sum(s['duration_ms'] / 1000.0 for s in sequence)
        
        # Time span
        timestamps = [s['capture_ts'] for s in sequence]
        time_span_seconds = max(timestamps) - min(timestamps)
        time_span_minutes = time_span_seconds / 60.0
        
        return {
            'shot_count': len(sequence),
            'total_duration': total_duration,
            'shot_types': dict(shot_type_counts),
            'has_sot': 'SOT' in shot_type_counts,
            'time_span_minutes': time_span_minutes,
            'first_timestamp': min(timestamps),
            'last_timestamp': max(timestamps)
        }
    
    def summarize_sequences(self, sequences: Dict[str, List[Dict]]) -> str:
        """
        Create a text summary of sequences for logging or LLM context.
        
        Args:
            sequences: Dictionary of sequences
            
        Returns:
            Formatted summary string
        """
        lines = []
        lines.append(f"## Sequence Summary")
        lines.append(f"Total Sequences: {len(sequences)}")
        lines.append("")
        
        for seq_name, shots in sequences.items():
            metadata = self.get_sequence_metadata(shots)
            
            lines.append(f"### {seq_name}")
            lines.append(f"- Shots: {metadata['shot_count']}")
            lines.append(f"- Duration: {metadata['total_duration']:.1f}s")
            lines.append(f"- Time Span: {metadata['time_span_minutes']:.1f} minutes")
            lines.append(f"- Shot Types: {metadata['shot_types']}")
            lines.append(f"- Has SOT: {'Yes' if metadata['has_sot'] else 'No'}")
            lines.append("")
        
        return "\n".join(lines)
