"""
ChromaDB-compatible vector index using SQLite backend.

This is a lightweight implementation that provides ChromaDB-like functionality
without the heavy dependencies (onnxruntime, etc.) that aren't available for Python 3.14.
Uses SQLite for persistent storage and numpy for vector operations.
"""

import sqlite3
import json
import logging
from pathlib import Path
from typing import List, Tuple, Optional, Dict, Any
from dataclasses import dataclass
import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    """Result from vector search."""
    shot_id: int
    score: float
    distance: float
    metadata: Dict[str, Any]


class ChromaCollection:
    """
    A collection of embeddings with metadata, similar to ChromaDB's Collection.
    Uses SQLite for persistent storage and cosine similarity for search.
    """
    
    def __init__(self, name: str, db_path: str, dimension: int):
        """
        Initialize a collection.
        
        Args:
            name: Collection name
            db_path: Path to SQLite database
            dimension: Vector dimension
        """
        self.name = name
        self.db_path = db_path
        self.dimension = dimension
        self.conn = sqlite3.connect(db_path)
        self._create_table()
    
    def _create_table(self):
        """Create the collection table if it doesn't exist."""
        cursor = self.conn.cursor()
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS {self.name} (
                id INTEGER PRIMARY KEY,
                shot_id INTEGER NOT NULL,
                embedding TEXT NOT NULL,
                metadata TEXT,
                UNIQUE(shot_id)
            )
        """)
        cursor.execute(f"""
            CREATE INDEX IF NOT EXISTS idx_{self.name}_shot_id 
            ON {self.name}(shot_id)
        """)
        self.conn.commit()
    
    def add(self, shot_ids: List[int], embeddings: np.ndarray, metadatas: Optional[List[Dict]] = None):
        """
        Add embeddings to the collection.
        
        Args:
            shot_ids: List of shot IDs
            embeddings: Numpy array of shape (n, dimension)
            metadatas: Optional list of metadata dictionaries
        """
        if embeddings.shape[1] != self.dimension:
            raise ValueError(f"Embedding dimension {embeddings.shape[1]} doesn't match collection dimension {self.dimension}")
        
        if metadatas is None:
            metadatas = [{}] * len(shot_ids)
        
        cursor = self.conn.cursor()
        for shot_id, embedding, metadata in zip(shot_ids, embeddings, metadatas):
            embedding_json = json.dumps(embedding.tolist())
            metadata_json = json.dumps(metadata)
            
            # Use INSERT OR REPLACE to handle duplicates
            cursor.execute(f"""
                INSERT OR REPLACE INTO {self.name} (shot_id, embedding, metadata)
                VALUES (?, ?, ?)
            """, (shot_id, embedding_json, metadata_json))
        
        self.conn.commit()
        logger.info(f"[CHROMA] Added {len(shot_ids)} embeddings to collection '{self.name}'")
    
    def query(self, 
              query_embeddings: np.ndarray, 
              n_results: int = 10,
              where: Optional[Dict] = None) -> Dict[str, List]:
        """
        Query the collection for similar embeddings.
        
        Args:
            query_embeddings: Query vectors of shape (n_queries, dimension)
            n_results: Number of results per query
            where: Optional metadata filter (not implemented yet)
        
        Returns:
            Dictionary with 'ids', 'distances', 'metadatas', 'embeddings'
        """
        if query_embeddings.ndim == 1:
            query_embeddings = query_embeddings.reshape(1, -1)
        
        cursor = self.conn.cursor()
        cursor.execute(f"SELECT shot_id, embedding, metadata FROM {self.name}")
        rows = cursor.fetchall()
        
        if not rows:
            return {
                'ids': [[]],
                'distances': [[]],
                'metadatas': [[]],
                'embeddings': [[]]
            }
        
        # Load all embeddings
        shot_ids = []
        embeddings = []
        metadatas = []
        
        for shot_id, embedding_json, metadata_json in rows:
            shot_ids.append(shot_id)
            embeddings.append(json.loads(embedding_json))
            metadatas.append(json.loads(metadata_json))
        
        embeddings = np.array(embeddings, dtype=np.float32)
        
        # Compute cosine similarity for each query
        all_ids = []
        all_distances = []
        all_metadatas = []
        all_embeddings = []
        
        for query_embedding in query_embeddings:
            # Normalize vectors for cosine similarity
            query_norm = query_embedding / (np.linalg.norm(query_embedding) + 1e-8)
            embeddings_norm = embeddings / (np.linalg.norm(embeddings, axis=1, keepdims=True) + 1e-8)
            
            # Compute cosine similarity (dot product of normalized vectors)
            similarities = np.dot(embeddings_norm, query_norm)
            
            # Convert to distances (1 - similarity)
            distances = 1.0 - similarities
            
            # Get top k results
            k = min(n_results, len(shot_ids))
            top_indices = np.argsort(distances)[:k]
            
            all_ids.append([shot_ids[i] for i in top_indices])
            all_distances.append([float(distances[i]) for i in top_indices])
            all_metadatas.append([metadatas[i] for i in top_indices])
            all_embeddings.append([embeddings[i].tolist() for i in top_indices])
        
        return {
            'ids': all_ids,
            'distances': all_distances,
            'metadatas': all_metadatas,
            'embeddings': all_embeddings
        }
    
    def count(self) -> int:
        """Return number of embeddings in collection."""
        cursor = self.conn.cursor()
        cursor.execute(f"SELECT COUNT(*) FROM {self.name}")
        return cursor.fetchone()[0]
    
    def delete(self, ids: Optional[List[int]] = None):
        """Delete embeddings by shot_id."""
        if ids is None:
            # Delete all
            cursor = self.conn.cursor()
            cursor.execute(f"DELETE FROM {self.name}")
            self.conn.commit()
        else:
            cursor = self.conn.cursor()
            placeholders = ','.join('?' * len(ids))
            cursor.execute(f"DELETE FROM {self.name} WHERE shot_id IN ({placeholders})", ids)
            self.conn.commit()


class ChromaClient:
    """
    ChromaDB-compatible client for managing collections.
    """
    
    def __init__(self, path: str = "./data/chroma"):
        """
        Initialize the client.
        
        Args:
            path: Directory path for storing collections
        """
        self.path = Path(path)
        self.path.mkdir(parents=True, exist_ok=True)
        self.db_path = str(self.path / "chroma.db")
        logger.info(f"[CHROMA] Initialized client at {self.db_path}")
    
    def get_or_create_collection(self, name: str, metadata: Optional[Dict] = None) -> ChromaCollection:
        """
        Get or create a collection.
        
        Args:
            name: Collection name
            metadata: Optional metadata (dimension should be specified here)
        
        Returns:
            ChromaCollection instance
        """
        dimension = 384  # Default for sentence-transformers
        if metadata and 'dimension' in metadata:
            dimension = metadata['dimension']
        
        collection = ChromaCollection(name, self.db_path, dimension)
        logger.info(f"[CHROMA] Got/created collection '{name}' with dimension {dimension}")
        return collection
    
    def delete_collection(self, name: str):
        """Delete a collection."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(f"DROP TABLE IF EXISTS {name}")
        cursor.execute(f"DROP INDEX IF EXISTS idx_{name}_shot_id")
        conn.commit()
        conn.close()
        logger.info(f"[CHROMA] Deleted collection '{name}'")
    
    def list_collections(self) -> List[str]:
        """List all collections."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        conn.close()
        return tables


class WorkingSetIndices:
    """
    Container for multiple vector indices for a working set.
    ChromaDB-compatible version.
    """
    
    def __init__(self, story_slug: str, text_dim: int = 384, visual_dim: int = 512):
        """
        Initialize indices for different modalities.
        
        Args:
            story_slug: Story identifier for collection naming
            text_dim: Dimension of text embeddings
            visual_dim: Dimension of visual embeddings
        """
        self.story_slug = story_slug
        self.client = ChromaClient()
        
        # Create collections for this story
        self.text_collection = self.client.get_or_create_collection(
            name=f"{story_slug}_text",
            metadata={'dimension': text_dim}
        )
        self.visual_collection = self.client.get_or_create_collection(
            name=f"{story_slug}_visual",
            metadata={'dimension': visual_dim}
        )
        
        self.shot_metadata: Dict[int, Dict[str, Any]] = {}
        logger.info(f"[CHROMA] Initialized working set indices for story '{story_slug}'")
    
    def add_shots(self, shots: List[Dict[str, Any]]):
        """
        Add shots to all indices.
        
        Args:
            shots: List of shot dictionaries with embeddings
        """
        # Separate by modality
        text_shots = []
        text_vectors = []
        text_metadatas = []
        
        visual_shots = []
        visual_vectors = []
        visual_metadatas = []
        
        for shot in shots:
            shot_id = shot['shot_id']
            self.shot_metadata[shot_id] = shot
            
            # Prepare metadata (without embeddings to save space)
            metadata = {
                'shot_type': shot.get('shot_type'),
                'duration_ms': shot.get('duration_ms'),
                'has_face': shot.get('has_face'),
                'capture_ts': shot.get('capture_ts')
            }
            
            if shot.get('embedding_text') is not None:
                text_shots.append(shot_id)
                text_vectors.append(shot['embedding_text'])
                text_metadatas.append(metadata)
            
            if shot.get('embedding_visual') is not None:
                visual_shots.append(shot_id)
                visual_vectors.append(shot['embedding_visual'])
                visual_metadatas.append(metadata)
        
        # Add to collections
        if text_vectors:
            self.text_collection.add(
                shot_ids=text_shots,
                embeddings=np.array(text_vectors, dtype=np.float32),
                metadatas=text_metadatas
            )
        
        if visual_vectors:
            self.visual_collection.add(
                shot_ids=visual_shots,
                embeddings=np.array(visual_vectors, dtype=np.float32),
                metadatas=visual_metadatas
            )
        
        logger.info(f"[CHROMA] Added {len(text_vectors)} text and {len(visual_vectors)} visual embeddings")
    
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
            results = self.text_collection.query(
                query_embeddings=text_query,
                n_results=k*2
            )
            
            for shot_id, distance in zip(results['ids'][0], results['distances'][0]):
                # Convert distance to similarity score (1 - distance for cosine)
                similarity = 1.0 - distance
                scores[shot_id] = scores.get(shot_id, 0.0) + text_weight * similarity
        
        # Visual search
        if visual_query is not None:
            results = self.visual_collection.query(
                query_embeddings=visual_query,
                n_results=k*2
            )
            
            for shot_id, distance in zip(results['ids'][0], results['distances'][0]):
                similarity = 1.0 - distance
                scores[shot_id] = scores.get(shot_id, 0.0) + visual_weight * similarity
        
        # Sort by combined score
        sorted_results = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return sorted_results[:k]
    
    def get_shot(self, shot_id: int) -> Optional[Dict[str, Any]]:
        """Get shot metadata by ID."""
        return self.shot_metadata.get(shot_id)
    
    def size(self) -> int:
        """Return number of shots in working set."""
        return len(self.shot_metadata)
    
    def clear(self):
        """Clear all data from collections."""
        self.text_collection.delete()
        self.visual_collection.delete()
        self.shot_metadata.clear()
        logger.info(f"[CHROMA] Cleared working set indices for story '{self.story_slug}'")
