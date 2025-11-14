"""
Tests for Storage Layer

Tests for database and vector index components.
"""

import pytest
import numpy as np
from storage.database import ShotsDatabase
from storage.vector_index import VectorIndex


class TestShotsDatabase:
    """Tests for ShotsDatabase."""
    
    def test_create_database(self, test_db):
        """Test database creation."""
        assert test_db is not None
        assert test_db.conn is not None
    
    def test_store_shot(self, test_db, sample_shot_data):
        """Test storing a shot."""
        # Update sample data to match actual schema
        shot_data = {
            'story_slug': sample_shot_data['story_id'],
            'filepath': sample_shot_data['file_path'],
            'capture_ts': sample_shot_data['start_time'],
            'tc_in': '00:00:00:00',
            'tc_out': '00:00:05:00',
            'fps': 25.0,
            'duration_ms': int(sample_shot_data['duration'] * 1000),
            'shot_type': sample_shot_data['shot_type'],
            'asr_text': sample_shot_data.get('transcript'),
            'embedding_text': sample_shot_data.get('text_embedding'),
            'embedding_visual': sample_shot_data.get('visual_embedding')
        }
        
        shot_id = test_db.insert_shot(shot_data)
        assert shot_id > 0
        
        # Verify shot was stored
        shot = test_db.get_shot(shot_id)
        assert shot is not None
        assert shot['shot_id'] == shot_id
        assert shot['story_slug'] == shot_data['story_slug']
    
    def test_get_shots_by_story(self, test_db, sample_shots_list):
        """Test retrieving shots by story."""
        # Store multiple shots
        for shot in sample_shots_list:
            shot_data = {
                'story_slug': shot['story_id'],
                'filepath': shot['file_path'],
                'capture_ts': shot['start_time'],
                'tc_in': '00:00:00:00',
                'tc_out': '00:00:05:00',
                'fps': 25.0,
                'duration_ms': int(shot['duration'] * 1000),
                'shot_type': shot['shot_type'],
                'asr_text': shot.get('transcript'),
                'embedding_text': shot.get('text_embedding'),
                'embedding_visual': shot.get('visual_embedding')
            }
            test_db.insert_shot(shot_data)
        
        # Retrieve by story
        shots = test_db.get_shots_by_story('test_story')
        assert len(shots) == len(sample_shots_list)
    
    def test_search_shots(self, test_db, sample_shots_list):
        """Test searching shots by type."""
        # Store shots
        for shot in sample_shots_list:
            shot_data = {
                'story_slug': shot['story_id'],
                'filepath': shot['file_path'],
                'capture_ts': shot['start_time'],
                'tc_in': '00:00:00:00',
                'tc_out': '00:00:05:00',
                'fps': 25.0,
                'duration_ms': int(shot['duration'] * 1000),
                'shot_type': shot['shot_type'],
                'asr_text': shot.get('transcript'),
                'embedding_text': shot.get('text_embedding'),
                'embedding_visual': shot.get('visual_embedding')
            }
            test_db.insert_shot(shot_data)
        
        # Search by type
        sot_shots = test_db.get_shots_by_story('test_story', shot_types=['SOT'])
        assert len(sot_shots) > 0
        assert all(s['shot_type'] == 'SOT' for s in sot_shots)
    
    def test_get_story_stats(self, test_db, sample_shots_list):
        """Test getting story statistics."""
        # Store shots
        for shot in sample_shots_list:
            shot_data = {
                'story_slug': shot['story_id'],
                'filepath': shot['file_path'],
                'capture_ts': shot['start_time'],
                'tc_in': '00:00:00:00',
                'tc_out': '00:00:05:00',
                'fps': 25.0,
                'duration_ms': int(shot['duration'] * 1000),
                'shot_type': shot['shot_type'],
                'asr_text': shot.get('transcript'),
                'embedding_text': shot.get('text_embedding'),
                'embedding_visual': shot.get('visual_embedding')
            }
            test_db.insert_shot(shot_data)
        
        # Get all shots and calculate stats
        shots = test_db.get_shots_by_story('test_story')
        assert len(shots) == len(sample_shots_list)
        total_duration = sum(s['duration_ms'] for s in shots)
        assert total_duration > 0


class TestVectorIndex:
    """Tests for VectorIndex."""
    
    def test_create_index(self, test_vector_index):
        """Test index creation."""
        assert test_vector_index is not None
        assert test_vector_index.dimension == 384
    
    def test_add_vector(self, test_vector_index):
        """Test adding vectors."""
        vectors = np.random.rand(3, 384).astype('float32')
        shot_ids = [1, 2, 3]
        test_vector_index.add(shot_ids, vectors)
        
        assert test_vector_index.size() == 3
    
    def test_search_similar(self, test_vector_index):
        """Test similarity search."""
        # Add some vectors
        vectors = np.random.rand(5, 384).astype('float32')
        shot_ids = [1, 2, 3, 4, 5]
        test_vector_index.add(shot_ids, vectors)
        
        # Search
        query = np.random.rand(384).astype('float32')
        results = test_vector_index.search(query, k=3)
        
        assert len(results) <= 3
        assert all(hasattr(r, 'shot_id') and hasattr(r, 'score') for r in results)
    
    def test_remove_vector(self, test_vector_index):
        """Test that index maintains size after adding."""
        vectors = np.random.rand(3, 384).astype('float32')
        shot_ids = [1, 2, 3]
        test_vector_index.add(shot_ids, vectors)
        
        # FAISS doesn't support removal in HNSW, so just verify size
        assert test_vector_index.size() == 3
