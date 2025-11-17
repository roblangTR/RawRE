"""
Unit tests for SequenceAnalyzer

Tests the grouping methods: location, temporal, visual, and hybrid.
"""

import pytest
import numpy as np
from datetime import datetime, timedelta
from agent.sequence_analyzer import SequenceAnalyzer


@pytest.fixture
def config():
    """Test configuration."""
    return {
        'sequences': {
            'temporal_window_minutes': 5,
            'visual_similarity_threshold': 0.7,
            'min_shots_per_sequence': 2,
            'max_shots_per_sequence': 8
        }
    }


@pytest.fixture
def analyzer(config):
    """Create sequence analyzer instance."""
    return SequenceAnalyzer(config)


@pytest.fixture
def sample_shots():
    """Create sample shots for testing."""
    base_time = 1000000.0
    
    # Create visual embeddings (512-dim vectors)
    embedding_1 = np.random.rand(512).astype(np.float32)
    embedding_2 = embedding_1 + np.random.rand(512).astype(np.float32) * 0.1  # Similar
    embedding_3 = np.random.rand(512).astype(np.float32)  # Different
    
    shots = [
        {
            'shot_id': 1,
            'location': 'Parliament Exterior',
            'capture_ts': base_time,
            'duration_ms': 5000,
            'shot_type': 'WIDE',
            'gemini_context': 'outdoor government building',
            'embedding_visual': embedding_1,
            'relevance_score': 0.9
        },
        {
            'shot_id': 2,
            'location': 'Parliament Exterior',
            'capture_ts': base_time + 60,  # 1 min later
            'duration_ms': 4000,
            'shot_type': 'MEDIUM',
            'gemini_context': 'outdoor government building',
            'embedding_visual': embedding_2,
            'relevance_score': 0.85
        },
        {
            'shot_id': 3,
            'location': 'Parliament Exterior',
            'capture_ts': base_time + 120,  # 2 min later
            'duration_ms': 3000,
            'shot_type': 'CLOSE',
            'gemini_context': 'outdoor government building entrance',
            'embedding_visual': embedding_1,
            'relevance_score': 0.8
        },
        {
            'shot_id': 4,
            'location': 'Interview Room',
            'capture_ts': base_time + 600,  # 10 min later (new sequence)
            'duration_ms': 6000,
            'shot_type': 'SOT',
            'gemini_context': 'indoor interview setup',
            'embedding_visual': embedding_3,
            'relevance_score': 0.95
        },
        {
            'shot_id': 5,
            'location': 'Interview Room',
            'capture_ts': base_time + 650,  # 50 sec after shot 4
            'duration_ms': 5000,
            'shot_type': 'MEDIUM',
            'gemini_context': 'indoor interview',
            'embedding_visual': embedding_3,
            'relevance_score': 0.75
        },
        {
            'shot_id': 6,
            'location': None,
            'capture_ts': base_time + 1200,  # 20 min later
            'duration_ms': 2000,
            'shot_type': 'CUTAWAY',
            'gemini_context': 'outdoor street scene',
            'embedding_visual': None,
            'relevance_score': 0.6
        }
    ]
    
    return shots


def test_group_by_location(analyzer, sample_shots):
    """Test location-based grouping."""
    sequences = analyzer._group_by_location(sample_shots)
    
    # Should have 3 groups: parliament_exterior, interview_room, outdoor_unknown
    assert len(sequences) >= 2
    assert 'parliament_exterior' in sequences
    assert 'interview_room' in sequences
    
    # Parliament exterior should have 3 shots
    assert len(sequences['parliament_exterior']) == 3
    assert all(s['shot_id'] in [1, 2, 3] for s in sequences['parliament_exterior'])
    
    # Interview room should have 2 shots
    assert len(sequences['interview_room']) == 2
    assert all(s['shot_id'] in [4, 5] for s in sequences['interview_room'])


def test_group_by_temporal_proximity(analyzer, sample_shots):
    """Test temporal proximity grouping."""
    sequences = analyzer._group_by_temporal_proximity(sample_shots)
    
    # Should create multiple sequences based on 5-minute window
    assert len(sequences) >= 2
    
    # First sequence should have shots 1, 2, 3 (all within 5 min)
    first_seq = list(sequences.values())[0]
    assert len(first_seq) == 3
    assert all(s['shot_id'] in [1, 2, 3] for s in first_seq)
    
    # Second sequence should have shots 4, 5 (within 5 min of each other)
    second_seq = list(sequences.values())[1]
    assert len(second_seq) == 2
    assert all(s['shot_id'] in [4, 5] for s in second_seq)


def test_group_by_visual_similarity(analyzer, sample_shots):
    """Test visual similarity grouping."""
    sequences = analyzer._group_by_visual_similarity(sample_shots)
    
    # Should group visually similar shots together
    assert len(sequences) >= 1
    
    # Shots with similar embeddings should be grouped
    # (This is probabilistic due to DBSCAN, so we check for reasonable output)
    total_shots = sum(len(shots) for shots in sequences.values())
    assert total_shots == len(sample_shots)


def test_hybrid_grouping(analyzer, sample_shots):
    """Test hybrid grouping strategy."""
    sequences = analyzer.group_by_sequences(sample_shots, method='hybrid')
    
    # Should create reasonable number of sequences
    assert len(sequences) >= 1
    
    # All shots should be accounted for
    total_shots = sum(len(shots) for shots in sequences.values())
    assert total_shots == len(sample_shots)
    
    # Each sequence should meet size constraints (or be in miscellaneous)
    for seq_name, shots in sequences.items():
        if seq_name != 'miscellaneous':
            assert len(shots) <= analyzer.max_shots_per_sequence


def test_filter_sequences(analyzer):
    """Test sequence filtering and trimming."""
    # Create test sequences
    sequences = {
        'too_small': [{'shot_id': 1}],  # Below min (2)
        'just_right': [
            {'shot_id': 2, 'relevance_score': 0.9},
            {'shot_id': 3, 'relevance_score': 0.8}
        ],
        'too_large': [
            {'shot_id': i, 'relevance_score': 0.9 - i*0.05}
            for i in range(4, 15)  # 11 shots, max is 8
        ]
    }
    
    filtered = analyzer._filter_sequences(sequences)
    
    # too_small should be moved to miscellaneous
    assert 'too_small' not in filtered
    assert 'miscellaneous' in filtered
    # miscellaneous should have 1 from too_small + 3 trimmed from too_large = 4 total
    assert len(filtered['miscellaneous']) == 4
    
    # just_right should remain unchanged
    assert 'just_right' in filtered
    assert len(filtered['just_right']) == 2
    
    # too_large should be trimmed to max_shots_per_sequence (8 kept, 3 moved to miscellaneous)
    assert 'too_large' in filtered
    assert len(filtered['too_large']) == analyzer.max_shots_per_sequence
    
    # Should keep highest relevance scores (top 8 out of 11)
    trimmed_scores = [s['relevance_score'] for s in filtered['too_large']]
    assert len(trimmed_scores) == 8
    # Scores should be in descending order and relatively high
    assert trimmed_scores == sorted(trimmed_scores, reverse=True)
    assert trimmed_scores[0] >= 0.7  # Best score should be high


def test_normalize_sequence_name(analyzer):
    """Test sequence name normalization."""
    assert analyzer._normalize_sequence_name('Parliament Square') == 'parliament_square'
    assert analyzer._normalize_sequence_name('St. James Park') == 'st_james_park'
    assert analyzer._normalize_sequence_name('Hyde-Park') == 'hyde_park'
    assert analyzer._normalize_sequence_name('  Spaces  ') == 'spaces'


def test_generate_temporal_sequence_name(analyzer, sample_shots):
    """Test temporal sequence name generation."""
    # With location
    parliament_shots = [s for s in sample_shots if s.get('location') == 'Parliament Exterior']
    name = analyzer._generate_temporal_sequence_name(parliament_shots, 1)
    assert 'parliament_exterior' in name
    assert 'seq_1' in name
    
    # Without location but with context
    no_location = [s for s in sample_shots if s['shot_id'] == 6]
    name = analyzer._generate_temporal_sequence_name(no_location, 2)
    assert 'outdoor' in name or 'temporal' in name
    
    # Empty list
    name = analyzer._generate_temporal_sequence_name([], 3)
    assert name == 'temporal_seq_3'


def test_get_sequence_metadata(analyzer, sample_shots):
    """Test sequence metadata extraction."""
    parliament_shots = [s for s in sample_shots if s.get('location') == 'Parliament Exterior']
    metadata = analyzer.get_sequence_metadata(parliament_shots)
    
    assert metadata['shot_count'] == 3
    assert metadata['total_duration'] == 12.0  # 5 + 4 + 3 seconds
    assert metadata['shot_types']['WIDE'] == 1
    assert metadata['shot_types']['MEDIUM'] == 1
    assert metadata['shot_types']['CLOSE'] == 1
    assert metadata['has_sot'] is False
    assert metadata['time_span_minutes'] == 2.0  # 120 seconds = 2 minutes
    
    # Test with SOT
    interview_shots = [s for s in sample_shots if s.get('location') == 'Interview Room']
    metadata = analyzer.get_sequence_metadata(interview_shots)
    assert metadata['has_sot'] is True


def test_get_sequence_metadata_empty(analyzer):
    """Test metadata extraction for empty sequence."""
    metadata = analyzer.get_sequence_metadata([])
    
    assert metadata['shot_count'] == 0
    assert metadata['total_duration'] == 0.0
    assert metadata['has_sot'] is False


def test_summarize_sequences(analyzer, sample_shots):
    """Test sequence summary generation."""
    sequences = analyzer.group_by_sequences(sample_shots, method='location')
    summary = analyzer.summarize_sequences(sequences)
    
    assert '## Sequence Summary' in summary
    assert 'Total Sequences:' in summary
    assert 'parliament_exterior' in summary.lower()
    assert 'Shots:' in summary
    assert 'Duration:' in summary


def test_method_fallback(analyzer, sample_shots):
    """Test fallback to hybrid for unknown method."""
    sequences = analyzer.group_by_sequences(sample_shots, method='unknown_method')
    
    # Should fall back to hybrid and still work
    assert len(sequences) >= 1
    total_shots = sum(len(shots) for shots in sequences.values())
    assert total_shots == len(sample_shots)


def test_empty_shots_list(analyzer):
    """Test handling of empty shots list."""
    sequences = analyzer.group_by_sequences([], method='hybrid')
    
    assert sequences == {}


def test_shots_without_embeddings(analyzer):
    """Test handling shots without visual embeddings."""
    shots = [
        {
            'shot_id': 1,
            'location': 'Test Location',
            'capture_ts': 1000000.0,
            'duration_ms': 5000,
            'shot_type': 'WIDE',
            'gemini_context': 'test',
            'embedding_visual': None,  # No embedding
            'relevance_score': 0.9
        },
        {
            'shot_id': 2,
            'location': 'Test Location',
            'capture_ts': 1000100.0,
            'duration_ms': 4000,
            'shot_type': 'MEDIUM',
            'gemini_context': 'test',
            'embedding_visual': None,  # No embedding
            'relevance_score': 0.8
        }
    ]
    
    # Should still work with location and temporal grouping
    sequences = analyzer.group_by_sequences(shots, method='hybrid')
    assert len(sequences) >= 1
    
    # Visual grouping should fall back gracefully
    visual_sequences = analyzer._group_by_visual_similarity(shots)
    assert len(visual_sequences) >= 1


def test_config_defaults():
    """Test that analyzer works with default config when sequences section missing."""
    minimal_config = {}
    analyzer = SequenceAnalyzer(minimal_config)
    
    # Should use defaults
    assert analyzer.temporal_window_minutes == 5
    assert analyzer.visual_similarity_threshold == 0.7
    assert analyzer.min_shots_per_sequence == 2
    assert analyzer.max_shots_per_sequence == 8


def test_single_shot_sequence(analyzer):
    """Test handling of single-shot sequences."""
    shots = [
        {
            'shot_id': 1,
            'location': 'Isolated Location',
            'capture_ts': 1000000.0,
            'duration_ms': 5000,
            'shot_type': 'WIDE',
            'gemini_context': 'test',
            'embedding_visual': np.random.rand(512).astype(np.float32),
            'relevance_score': 0.9
        }
    ]
    
    sequences = analyzer.group_by_sequences(shots, method='hybrid')
    
    # Single shot below min_shots should go to miscellaneous
    if 'miscellaneous' in sequences:
        assert len(sequences['miscellaneous']) == 1
    else:
        # Or might be kept if filtered differently
        total = sum(len(s) for s in sequences.values())
        assert total == 1


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
