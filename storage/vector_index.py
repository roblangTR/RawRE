"""FAISS-based vector indices for semantic search."""

import faiss
import numpy as np
from typing import List, Tuple, Optional, Dict, Any
from dataclasses import dataclass


@dataclass
class SearchResult:
    """Result from vector search."""
    shot_id: int
    score: float
    distance: float


class VectorIndex:
    """FAISS HNSW index for fast similarity search."""
    
    def __init__(self, dimension: int, m: int = 32, ef_construction: int = 200):
        """
        Initialize HNSW index.
        
        Args:
            dimension: Vector dimension
            m: HNSW parameter (number of connections)
            ef_construction: HNSW construction parameter
        """
        self.dimension = dimension
        self.index = faiss.IndexHNSWFlat(dimension, m)
        self.index.hnsw.efConstruction = ef_construction
        self.shot_ids: List[int] = []
        self.is_trained = False
    
    def add(self, shot_ids: List[int], vectors: np.ndarray):
        """
        Add vectors to the index.
        
        Args:
            shot_ids: List of shot IDs
            vectors: Numpy array of shape (n, dimension)
        """
        if vectors.shape[1] != self.dimension:
            raise ValueError(f"Vector dimension {vectors.shape[1]} doesn't match index dimension {self.dimension}")
        
        # Ensure float32
        vectors = vectors.astype('float32')
        
        # Add to index
        self.index.add(vectors)
        self.shot_ids.extend(shot_ids)
        self.is_trained = True
    
    def search(self, query_vector: np.ndarray, k: int = 10, ef_search: int = 100) -> List[SearchResult]:
        """
        Search for k nearest neighbors.
        
        Args:
            query_vector: Query vector of shape (dimension,) or (1, dimension)
            k: Number of results to return
            ef_search: HNSW search parameter (higher = more accurate but slower)
        
        Returns:
            List of SearchResult objects
        """
        if not self.is_trained or len(self.shot_ids) == 0:
            return []
        
        # Reshape if needed
        if query_vector.ndim == 1:
            query_vector = query_vector.reshape(1, -1)
        
        # Ensure float32
        query_vector = query_vector.astype('float32')
        
        # Set search parameter
        self.index.hnsw.efSearch = ef_search
        
        # Search
        k = min(k, len(self.shot_ids))
        distances, indices = self.index.search(query_vector, k)
        
        # Convert to results
        results = []
        for dist, idx in zip(distances[0], indices[0]):
            if idx >= 0 and idx < len(self.shot_ids):
                # Convert distance to similarity score (cosine similarity)
                score = 1.0 - (dist / 2.0)  # HNSW uses L2 distance
                results.append(SearchResult(
                    shot_id=self.shot_ids[idx],
                    score=float(score),
                    distance=float(dist)
                ))
        
        return results
    
    def size(self) -> int:
        """Return number of vectors in index."""
        return len(self.shot_ids)


class WorkingSetIndices:
    """Container for multiple vector indices for a working set."""
    
    def __init__(self, text_dim: int = 384, visual_dim: int = 512):
        """
        Initialize indices for different modalities.
        
        Args:
            text_dim: Dimension of text embeddings
            visual_dim: Dimension of visual embeddings
        """
        self.text_index = VectorIndex(text_dim)
        self.visual_index = VectorIndex(visual_dim)
        self.shot_metadata: Dict[int, Dict[str, Any]] = {}
    
    def add_shots(self, shots: List[Dict[str, Any]]):
        """
        Add shots to all indices.
        
        Args:
            shots: List of shot dictionaries with embeddings
        """
        # Separate by modality
        text_shots = []
        text_vectors = []
        visual_shots = []
        visual_vectors = []
        
        for shot in shots:
            shot_id = shot['shot_id']
            self.shot_metadata[shot_id] = shot
            
            if shot.get('embedding_text') is not None:
                text_shots.append(shot_id)
                text_vectors.append(shot['embedding_text'])
            
            if shot.get('embedding_visual') is not None:
                visual_shots.append(shot_id)
                visual_vectors.append(shot['embedding_visual'])
        
        # Add to indices
        if text_vectors:
            self.text_index.add(text_shots, np.array(text_vectors))
        
        if visual_vectors:
            self.visual_index.add(visual_shots, np.array(visual_vectors))
    
    def search_multimodal(self, 
                         text_query: Optional[np.ndarray] = None,
                         visual_query: Optional[np.ndarray] = None,
                         k: int = 20,
                         text_weight: float = 0.7,
                         visual_weight: float = 0.3) -> List[Tuple[int, float]]:
        """
        Search across multiple modalities and combine scores.
        
        Args:
            text_query: Text embedding query
            visual_query: Visual embedding query
            k: Number of results
            text_weight: Weight for text similarity
            visual_weight: Weight for visual similarity
        
        Returns:
            List of (shot_id, combined_score) tuples
        """
        scores: Dict[int, float] = {}
        
        # Text search
        if text_query is not None:
            text_results = self.text_index.search(text_query, k=k*2)
            for result in text_results:
                scores[result.shot_id] = scores.get(result.shot_id, 0.0) + text_weight * result.score
        
        # Visual search
        if visual_query is not None:
            visual_results = self.visual_index.search(visual_query, k=k*2)
            for result in visual_results:
                scores[result.shot_id] = scores.get(result.shot_id, 0.0) + visual_weight * result.score
        
        # Sort by combined score
        sorted_results = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return sorted_results[:k]
    
    def get_shot(self, shot_id: int) -> Optional[Dict[str, Any]]:
        """Get shot metadata by ID."""
        return self.shot_metadata.get(shot_id)
    
    def size(self) -> int:
        """Return number of shots in working set."""
        return len(self.shot_metadata)
