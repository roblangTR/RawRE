"""
Working Set Builder

Builds a focused set of candidate shots for the LLM agent to work with.
Uses vector similarity search and shot graph traversal to find relevant content.
"""

import logging
from typing import Dict, List, Optional, Tuple, Any
import numpy as np
import yaml
from pathlib import Path

from storage.database import ShotsDatabase
from storage.vector_index import VectorIndex
from ingest.embedder import Embedder

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class WorkingSetBuilder:
    """Builds focused working sets of shots for agent processing."""
    
    def __init__(self, database: ShotsDatabase, vector_index: VectorIndex, config: Optional[Dict[str, Any]] = None):
        """
        Initialize working set builder.
        
        Args:
            database: Shot database instance
            vector_index: Vector index instance
            config: Configuration dictionary (optional, will load from config.yaml if not provided)
        """
        self.database = database
        self.vector_index = vector_index
        
        # Load config if not provided
        if config is None:
            config_path = Path(__file__).parent.parent / 'config.yaml'
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
        
        self.config = config
        self.embedder = Embedder(config)
        
        logger.info("[WORKING_SET] Initialized with semantic search capabilities")
    
    def build_for_query(self,
                       story_slug: str,
                       query: str,
                       max_shots: int = 50,
                       shot_types: Optional[List[str]] = None,
                       include_neighbors: bool = True) -> Dict:
        """
        Build a working set based on a text query.
        
        Args:
            story_slug: Story identifier
            query: Text query describing desired content
            max_shots: Maximum number of shots to include
            shot_types: Optional filter for shot types
            include_neighbors: Whether to include temporal neighbors
            
        Returns:
            Dictionary with working set metadata and shots
        """
        logger.info(f"[WORKING_SET] Building for query: '{query}'")
        logger.info(f"[WORKING_SET] Story: {story_slug}, max_shots: {max_shots}")
        
        working_set = {
            'story_slug': story_slug,
            'query': query,
            'max_shots': max_shots,
            'shot_types_filter': shot_types,
            'shots': [],
            'total_duration': 0.0,
            'shot_type_counts': {}
        }
        
        # Step 1: Get all shots for story
        all_shots = self.database.get_shots_by_story(
            story_slug,
            shot_types=shot_types
        )
        
        if not all_shots:
            logger.warning(f"[WORKING_SET] No shots found for story {story_slug}")
            return working_set
        
        logger.info(f"[WORKING_SET] Found {len(all_shots)} total shots")
        
        # Step 2: Perform vector similarity search with semantic embeddings
        try:
            # Generate query embedding
            query_embedding = self.embedder.embed_text([query])[0]
            
            # Search vector index (get 2x candidates for hybrid filtering)
            search_results = self.vector_index.search(
                query_vector=query_embedding,
                k=min(max_shots * 2, len(all_shots))
            )
            
            if search_results:
                logger.info(f"[WORKING_SET] Semantic search found {len(search_results)} candidates")
                
                # Get full shot details for semantic search results
                semantic_shot_ids = [r.shot_id for r in search_results]
                semantic_shots = self.database.get_shots_by_ids(semantic_shot_ids)
                
                # Create score map from search results
                semantic_score_map = {r.shot_id: r.score for r in search_results}
                
                # Add semantic scores to shots
                for shot in semantic_shots:
                    shot['semantic_score'] = semantic_score_map.get(shot['shot_id'], 0.0)
                
                # Step 3: Apply hybrid scoring (semantic + keyword + heuristics)
                scored_shots = self._apply_hybrid_scoring(semantic_shots, query)
                
            else:
                logger.warning("[WORKING_SET] Semantic search returned no results, falling back to keyword matching")
                scored_shots = self._score_shots(all_shots, query)
                
        except Exception as e:
            logger.warning(f"[WORKING_SET] Semantic search failed ({e}), falling back to keyword matching")
            scored_shots = self._score_shots(all_shots, query)
        
        # Step 4: Select top shots
        selected_shots = scored_shots[:max_shots]
        
        # Step 5: Add temporal neighbors if requested
        if include_neighbors:
            selected_shots = self._add_temporal_neighbors(
                selected_shots,
                all_shots,
                max_total=max_shots
            )
        
        # Step 6: Sort by capture time
        selected_shots.sort(key=lambda s: s['capture_ts'])
        
        # Step 7: Calculate statistics
        working_set['shots'] = selected_shots
        working_set['total_duration'] = sum(
            s['duration_ms'] / 1000.0 for s in selected_shots
        )
        
        for shot in selected_shots:
            shot_type = shot.get('shot_type', 'UNKNOWN')
            working_set['shot_type_counts'][shot_type] = \
                working_set['shot_type_counts'].get(shot_type, 0) + 1
        
        logger.info(f"[WORKING_SET] Selected {len(selected_shots)} shots")
        logger.info(f"[WORKING_SET] Total duration: {working_set['total_duration']:.1f}s")
        logger.info(f"[WORKING_SET] Shot types: {working_set['shot_type_counts']}")
        
        return working_set
    
    def build_for_beat(self,
                      story_slug: str,
                      beat_description: str,
                      beat_requirements: List[str],
                      max_shots: int = 20) -> Dict:
        """
        Build a working set for a specific story beat.
        
        Args:
            story_slug: Story identifier
            beat_description: Description of the beat
            beat_requirements: List of requirements for the beat
            max_shots: Maximum number of candidate shots
            
        Returns:
            Dictionary with working set for the beat
        """
        logger.info(f"[WORKING_SET] Building for beat: '{beat_description}'")
        
        # Combine description and requirements into query
        query = f"{beat_description}. Requirements: {', '.join(beat_requirements)}"
        
        # Build working set with stricter limits
        working_set = self.build_for_query(
            story_slug=story_slug,
            query=query,
            max_shots=max_shots,
            include_neighbors=False  # More focused for beats
        )
        
        working_set['beat_description'] = beat_description
        working_set['beat_requirements'] = beat_requirements
        
        return working_set
    
    def _apply_hybrid_scoring(self, shots: List[Dict], query: str) -> List[Dict]:
        """
        Apply hybrid scoring combining semantic similarity with keyword matching and heuristics.
        
        Args:
            shots: List of shot dictionaries (should already have semantic_score)
            query: Query string
            
        Returns:
            List of shots sorted by final combined score (descending)
        """
        query_lower = query.lower()
        query_words = set(query_lower.split())
        
        for shot in shots:
            # Get semantic score (0.0-1.0)
            semantic_score = shot.get('semantic_score', 0.0)
            
            # Calculate keyword match score (0.0-1.0)
            keyword_score = 0.0
            asr_text = shot.get('asr_text', '').lower()
            if asr_text:
                asr_words = set(asr_text.split())
                intersection = query_words & asr_words
                union = query_words | asr_words
                if union:
                    keyword_score = len(intersection) / len(union)
            
            # Heuristic bonuses (smaller weights as tiebreakers)
            heuristic_bonus = 0.0
            
            # Boost SOT shots
            if shot.get('shot_type') == 'SOT':
                heuristic_bonus += 0.15
            
            # Boost shots with faces
            if shot.get('has_face'):
                heuristic_bonus += 0.10
            
            # Prefer medium duration shots
            duration_s = shot['duration_ms'] / 1000.0
            if 3.0 <= duration_s <= 10.0:
                heuristic_bonus += 0.05
            
            # Weighted combination: semantic (70%) + keyword (20%) + heuristics (10%)
            final_score = (semantic_score * 0.7) + (keyword_score * 0.2) + (heuristic_bonus * 0.1)
            
            # Store component scores for transparency
            shot['semantic_score'] = semantic_score
            shot['keyword_score'] = keyword_score
            shot['heuristic_bonus'] = heuristic_bonus
            shot['final_score'] = final_score
            shot['relevance_score'] = final_score  # Keep for compatibility
        
        # Sort by final score descending
        shots.sort(key=lambda s: s['final_score'], reverse=True)
        
        logger.info(f"[WORKING_SET] Hybrid scoring complete. Top shot score: {shots[0]['final_score']:.3f}")
        
        return shots
    
    def _score_shots(self, shots: List[Dict], query: str) -> List[Dict]:
        """
        Score shots based on keyword matching and heuristics (fallback when semantic search unavailable).
        
        Args:
            shots: List of shot dictionaries
            query: Query string
            
        Returns:
            List of shots sorted by relevance score (descending)
        """
        query_lower = query.lower()
        query_words = set(query_lower.split())
        
        scored = []
        for shot in shots:
            score = 0.0
            
            # Score based on transcript match
            asr_text = shot.get('asr_text', '').lower()
            if asr_text:
                asr_words = set(asr_text.split())
                # Jaccard similarity
                intersection = query_words & asr_words
                union = query_words | asr_words
                if union:
                    score += len(intersection) / len(union) * 10.0
            
            # Boost SOT shots (usually more important)
            if shot.get('shot_type') == 'SOT':
                score += 2.0
            
            # Boost shots with faces
            if shot.get('has_face'):
                score += 1.0
            
            # Prefer medium duration shots (not too short, not too long)
            duration_s = shot['duration_ms'] / 1000.0
            if 3.0 <= duration_s <= 10.0:
                score += 1.0
            
            shot['relevance_score'] = score
            scored.append(shot)
        
        # Sort by score descending
        scored.sort(key=lambda s: s['relevance_score'], reverse=True)
        
        return scored
    
    def _add_temporal_neighbors(self,
                               selected_shots: List[Dict],
                               all_shots: List[Dict],
                               max_total: int) -> List[Dict]:
        """
        Add temporal neighbors (shots before/after) to provide context.
        
        Args:
            selected_shots: Currently selected shots
            all_shots: All available shots
            max_total: Maximum total shots to return
            
        Returns:
            Extended list of shots including neighbors
        """
        if len(selected_shots) >= max_total:
            return selected_shots
        
        # Create lookup by shot_id
        shot_lookup = {s['shot_id']: s for s in all_shots}
        selected_ids = {s['shot_id'] for s in selected_shots}
        
        # Sort all shots by time
        sorted_shots = sorted(all_shots, key=lambda s: s['capture_ts'])
        shot_positions = {s['shot_id']: i for i, s in enumerate(sorted_shots)}
        
        # Add neighbors
        neighbors_to_add = []
        budget = max_total - len(selected_shots)
        
        for shot in selected_shots:
            if budget <= 0:
                break
            
            pos = shot_positions[shot['shot_id']]
            
            # Add previous shot
            if pos > 0:
                prev_shot = sorted_shots[pos - 1]
                if prev_shot['shot_id'] not in selected_ids:
                    neighbors_to_add.append(prev_shot)
                    selected_ids.add(prev_shot['shot_id'])
                    budget -= 1
            
            # Add next shot
            if budget > 0 and pos < len(sorted_shots) - 1:
                next_shot = sorted_shots[pos + 1]
                if next_shot['shot_id'] not in selected_ids:
                    neighbors_to_add.append(next_shot)
                    selected_ids.add(next_shot['shot_id'])
                    budget -= 1
        
        logger.info(f"[WORKING_SET] Added {len(neighbors_to_add)} temporal neighbors")
        
        return selected_shots + neighbors_to_add
    
    def format_for_llm(self, working_set: Dict, include_transcripts: bool = True) -> str:
        """
        Format working set as text for LLM context.
        
        Args:
            working_set: Working set dictionary
            include_transcripts: Whether to include full transcripts
            
        Returns:
            Formatted string for LLM context
        """
        lines = []
        lines.append(f"# Working Set: {working_set['story_slug']}")
        lines.append(f"Query: {working_set.get('query', 'N/A')}")
        lines.append(f"Total Shots: {len(working_set['shots'])}")
        lines.append(f"Total Duration: {working_set['total_duration']:.1f}s")
        lines.append(f"Shot Types: {working_set['shot_type_counts']}")
        lines.append("")
        lines.append("## Available Shots")
        lines.append("")
        
        for i, shot in enumerate(working_set['shots'], 1):
            lines.append(f"### Shot {i}: {shot['shot_id']}")
            lines.append(f"- Type: {shot.get('shot_type', 'UNKNOWN')}")
            lines.append(f"- Duration: {shot['duration_ms'] / 1000.0:.1f}s")
            lines.append(f"- Timecode: {shot['tc_in']} - {shot['tc_out']}")
            lines.append(f"- Has Face: {shot.get('has_face', False)}")
            
            if shot.get('relevance_score'):
                lines.append(f"- Relevance Score: {shot['relevance_score']:.2f}")
            
            if include_transcripts and shot.get('asr_text'):
                lines.append(f"- Transcript: \"{shot['asr_text']}\"")
            
            if shot.get('asr_summary'):
                lines.append(f"- Summary: {shot['asr_summary']}")
            
            lines.append("")
        
        return "\n".join(lines)
    
    def get_shot_details(self, shot_id: int) -> Optional[Dict]:
        """
        Get detailed information about a specific shot.
        
        Args:
            shot_id: Shot identifier
            
        Returns:
            Shot dictionary with full details
        """
        return self.database.get_shot(shot_id)
