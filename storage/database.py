"""SQLite database for shot metadata and relationships."""

import sqlite3
import pickle
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import numpy as np


class ShotsDatabase:
    """Manages shot metadata in SQLite with vector embeddings."""
    
    def __init__(self, db_path: str):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = None
        self._init_db()
    
    def _init_db(self):
        """Initialize database schema."""
        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.row_factory = sqlite3.Row
        
        cursor = self.conn.cursor()
        
        # Shots table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS shots (
                shot_id INTEGER PRIMARY KEY AUTOINCREMENT,
                story_slug TEXT NOT NULL,
                filepath TEXT NOT NULL,
                capture_ts REAL NOT NULL,
                tc_in TEXT NOT NULL,
                tc_out TEXT NOT NULL,
                fps REAL NOT NULL,
                duration_ms INTEGER NOT NULL,
                shot_type TEXT,
                asr_text TEXT,
                asr_summary TEXT,
                has_face INTEGER DEFAULT 0,
                location TEXT,
                embedding_text BLOB,
                embedding_visual BLOB,
                proxy_path TEXT,
                thumb_path TEXT,
                created_at REAL DEFAULT (julianday('now')),
                gemini_description TEXT,
                gemini_shot_type TEXT,
                gemini_shot_size TEXT,
                gemini_camera_movement TEXT,
                gemini_composition TEXT,
                gemini_lighting TEXT,
                gemini_subjects TEXT,
                gemini_action TEXT,
                gemini_quality TEXT,
                gemini_context TEXT,
                gemini_tone TEXT,
                gemini_confidence REAL
            )
        """)
        
        # Shot edges for graph relationships
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS shot_edges (
                src_shot_id INTEGER,
                dst_shot_id INTEGER,
                edge_type TEXT,
                weight REAL,
                PRIMARY KEY (src_shot_id, dst_shot_id, edge_type),
                FOREIGN KEY (src_shot_id) REFERENCES shots(shot_id),
                FOREIGN KEY (dst_shot_id) REFERENCES shots(shot_id)
            )
        """)
        
        # Indices for common queries
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_shots_story 
            ON shots(story_slug)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_shots_capture_ts 
            ON shots(capture_ts)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_shots_type 
            ON shots(shot_type)
        """)
        
        self.conn.commit()
    
    def insert_shot(self, shot_data: Dict[str, Any]) -> int:
        """Insert a new shot and return its ID."""
        cursor = self.conn.cursor()
        
        # Serialize embeddings
        embedding_text = pickle.dumps(shot_data.get('embedding_text')) if shot_data.get('embedding_text') is not None else None
        embedding_visual = pickle.dumps(shot_data.get('embedding_visual')) if shot_data.get('embedding_visual') is not None else None
        
        # Serialize Gemini subjects list if present
        gemini_subjects = None
        if shot_data.get('gemini_subjects'):
            gemini_subjects = ','.join(shot_data['gemini_subjects']) if isinstance(shot_data['gemini_subjects'], list) else shot_data['gemini_subjects']
        
        cursor.execute("""
            INSERT INTO shots (
                story_slug, filepath, capture_ts, tc_in, tc_out, fps,
                duration_ms, shot_type, asr_text, asr_summary, has_face,
                location, embedding_text, embedding_visual, proxy_path, thumb_path,
                gemini_description, gemini_shot_type, gemini_shot_size,
                gemini_camera_movement, gemini_composition, gemini_lighting,
                gemini_subjects, gemini_action, gemini_quality,
                gemini_context, gemini_tone, gemini_confidence
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            shot_data['story_slug'],
            shot_data['filepath'],
            shot_data['capture_ts'],
            shot_data['tc_in'],
            shot_data['tc_out'],
            shot_data['fps'],
            shot_data['duration_ms'],
            shot_data.get('shot_type'),
            shot_data.get('asr_text'),
            shot_data.get('asr_summary'),
            shot_data.get('has_face', 0),
            shot_data.get('location'),
            embedding_text,
            embedding_visual,
            shot_data.get('proxy_path'),
            shot_data.get('thumb_path'),
            shot_data.get('gemini_description'),
            shot_data.get('gemini_shot_type'),
            shot_data.get('gemini_shot_size'),
            shot_data.get('gemini_camera_movement'),
            shot_data.get('gemini_composition'),
            shot_data.get('gemini_lighting'),
            gemini_subjects,
            shot_data.get('gemini_action'),
            shot_data.get('gemini_quality'),
            shot_data.get('gemini_context'),
            shot_data.get('gemini_tone'),
            shot_data.get('gemini_confidence')
        ))
        
        self.conn.commit()
        return cursor.lastrowid
    
    def insert_edge(self, src_id: int, dst_id: int, edge_type: str, weight: float):
        """Insert a shot edge relationship."""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO shot_edges (src_shot_id, dst_shot_id, edge_type, weight)
            VALUES (?, ?, ?, ?)
        """, (src_id, dst_id, edge_type, weight))
        self.conn.commit()
    
    def get_shot(self, shot_id: int) -> Optional[Dict[str, Any]]:
        """Retrieve a shot by ID."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM shots WHERE shot_id = ?", (shot_id,))
        row = cursor.fetchone()
        
        if row:
            shot = dict(row)
            # Deserialize embeddings
            if shot['embedding_text']:
                shot['embedding_text'] = pickle.loads(shot['embedding_text'])
            if shot['embedding_visual']:
                shot['embedding_visual'] = pickle.loads(shot['embedding_visual'])
            # Deserialize Gemini subjects
            if shot.get('gemini_subjects'):
                shot['gemini_subjects'] = shot['gemini_subjects'].split(',')
            return shot
        return None
    
    def get_shots_by_story(self, story_slug: str, 
                          shot_types: Optional[List[str]] = None,
                          time_range: Optional[Tuple[float, float]] = None) -> List[Dict[str, Any]]:
        """Retrieve shots for a story with optional filters."""
        cursor = self.conn.cursor()
        
        query = "SELECT * FROM shots WHERE story_slug = ?"
        params = [story_slug]
        
        if shot_types:
            placeholders = ','.join('?' * len(shot_types))
            query += f" AND shot_type IN ({placeholders})"
            params.extend(shot_types)
        
        if time_range:
            query += " AND capture_ts BETWEEN ? AND ?"
            params.extend(time_range)
        
        query += " ORDER BY capture_ts ASC"
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        shots = []
        for row in rows:
            shot = dict(row)
            # Deserialize embeddings
            if shot['embedding_text']:
                shot['embedding_text'] = pickle.loads(shot['embedding_text'])
            if shot['embedding_visual']:
                shot['embedding_visual'] = pickle.loads(shot['embedding_visual'])
            # Deserialize Gemini subjects
            if shot.get('gemini_subjects'):
                shot['gemini_subjects'] = shot['gemini_subjects'].split(',')
            shots.append(shot)
        
        return shots
    
    def get_neighbors(self, shot_id: int, edge_types: Optional[List[str]] = None) -> Dict[str, List[Dict[str, Any]]]:
        """Get neighboring shots via edges."""
        cursor = self.conn.cursor()
        
        query = """
            SELECT e.edge_type, e.weight, s.*
            FROM shot_edges e
            JOIN shots s ON e.dst_shot_id = s.shot_id
            WHERE e.src_shot_id = ?
        """
        params = [shot_id]
        
        if edge_types:
            placeholders = ','.join('?' * len(edge_types))
            query += f" AND e.edge_type IN ({placeholders})"
            params.extend(edge_types)
        
        query += " ORDER BY e.weight DESC"
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        neighbors = {}
        for row in rows:
            edge_type = row['edge_type']
            shot = dict(row)
            
            # Remove edge-specific fields
            shot.pop('edge_type', None)
            shot.pop('weight', None)
            
            # Deserialize embeddings
            if shot['embedding_text']:
                shot['embedding_text'] = pickle.loads(shot['embedding_text'])
            if shot['embedding_visual']:
                shot['embedding_visual'] = pickle.loads(shot['embedding_visual'])
            # Deserialize Gemini subjects
            if shot.get('gemini_subjects'):
                shot['gemini_subjects'] = shot['gemini_subjects'].split(',')
            
            if edge_type not in neighbors:
                neighbors[edge_type] = []
            neighbors[edge_type].append(shot)
        
        return neighbors
    
    def get_all_embeddings(self, story_slug: str, 
                          embedding_type: str = 'text') -> Tuple[List[int], np.ndarray]:
        """Get all embeddings for a story as a numpy array."""
        cursor = self.conn.cursor()
        
        field = f'embedding_{embedding_type}'
        cursor.execute(f"""
            SELECT shot_id, {field}
            FROM shots
            WHERE story_slug = ? AND {field} IS NOT NULL
            ORDER BY shot_id
        """, (story_slug,))
        
        rows = cursor.fetchall()
        
        if not rows:
            return [], np.array([])
        
        shot_ids = []
        embeddings = []
        
        for row in rows:
            shot_ids.append(row['shot_id'])
            emb = pickle.loads(row[field])
            embeddings.append(emb)
        
        return shot_ids, np.array(embeddings)
    
    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
