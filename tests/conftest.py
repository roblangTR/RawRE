"""
Pytest Configuration and Fixtures

Shared fixtures for all tests.
"""

import pytest
import tempfile
import shutil
from pathlib import Path
import json
import numpy as np
from unittest.mock import Mock, MagicMock

from storage.database import ShotsDatabase
from storage.vector_index import VectorIndex


@pytest.fixture
def temp_dir():
    """Create a temporary directory for tests."""
    temp_path = tempfile.mkdtemp()
    yield temp_path
    shutil.rmtree(temp_path)


@pytest.fixture
def test_db(temp_dir):
    """Create a test database."""
    db_path = Path(temp_dir) / "test.db"
    db = ShotsDatabase(str(db_path))
    yield db
    db.close()


@pytest.fixture
def test_vector_index():
    """Create a test vector index."""
    return VectorIndex(dimension=384)


@pytest.fixture
def sample_shot_data():
    """Sample shot data for testing."""
    return {
        'shot_id': 'test_shot_001',
        'story_id': 'test_story',
        'file_path': '/path/to/video.mp4',
        'start_time': 0.0,
        'end_time': 5.0,
        'duration': 5.0,
        'shot_type': 'SOT',
        'transcript': 'This is a test transcript',
        'visual_description': 'A person speaking',
        'text_embedding': np.random.rand(384).tolist(),
        'visual_embedding': np.random.rand(384).tolist(),
        'metadata': {'camera': 'A', 'location': 'London'}
    }


@pytest.fixture
def sample_shots_list():
    """List of sample shots for testing."""
    shots = []
    for i in range(5):
        shots.append({
            'shot_id': f'test_shot_{i:03d}',
            'story_id': 'test_story',
            'file_path': f'/path/to/video_{i}.mp4',
            'start_time': float(i * 5),
            'end_time': float((i + 1) * 5),
            'duration': 5.0,
            'shot_type': ['SOT', 'GV', 'CUTAWAY'][i % 3],
            'transcript': f'Test transcript {i}',
            'visual_description': f'Visual description {i}',
            'text_embedding': np.random.rand(384).tolist(),
            'visual_embedding': np.random.rand(384).tolist(),
            'metadata': {}
        })
    return shots


@pytest.fixture
def mock_llm_client():
    """Mock LLM client for testing."""
    client = Mock()
    # Mock the chat method (ClaudeClient uses 'chat', not 'generate')
    client.chat.return_value = {
        'content': '{"test": "response"}',
        'usage': {'prompt_tokens': 100, 'completion_tokens': 50}
    }
    # Also mock generate for backward compatibility
    client.generate.return_value = {
        'response': '{"test": "response"}',
        'usage': {'prompt_tokens': 100, 'completion_tokens': 50}
    }
    return client


@pytest.fixture
def sample_plan():
    """Sample plan from planner agent."""
    return {
        'beats': [
            {
                'beat_number': 1,
                'beat_name': 'Introduction',
                'description': 'Set the scene',
                'target_duration': 10,
                'shot_requirements': ['Establishing shot', 'Wide view']
            },
            {
                'beat_number': 2,
                'beat_name': 'Main Action',
                'description': 'Show the event',
                'target_duration': 15,
                'shot_requirements': ['Action shots', 'Close-ups']
            }
        ],
        'total_duration': 25,
        'narrative_flow': 'Linear progression'
    }


@pytest.fixture
def sample_selections():
    """Sample selections from picker agent."""
    return {
        'beats': [
            {
                'beat_name': 'Introduction',
                'shots': [
                    {
                        'shot_id': 'test_shot_001',
                        'duration': 5.0,
                        'reasoning': 'Good establishing shot'
                    }
                ]
            }
        ],
        'total_duration': 5.0
    }


@pytest.fixture
def sample_verification():
    """Sample verification from verifier agent."""
    return {
        'approved': True,
        'overall_score': 8.5,
        'scores': {
            'narrative_coherence': 9.0,
            'brief_compliance': 8.5,
            'technical_quality': 8.0,
            'editorial_standards': 9.0
        },
        'feedback': 'Good edit overall',
        'issues': []
    }
