"""
Integration Test for Sequence-Based Visual Analysis

Tests the complete workflow:
1. Build working set
2. Group into sequences
3. Analyze sequences with Gemini (mocked)
4. Pick shots with enhanced context
"""

import pytest
import yaml
from pathlib import Path
from unittest.mock import Mock, patch
import json

from storage.database import ShotsDatabase
from storage.chroma_index import WorkingSetIndices
from agent.llm_client import ClaudeClient
from agent.orchestrator import AgentOrchestrator
from agent.sequence_analyzer import SequenceAnalyzer
from agent.working_set import WorkingSetBuilder


@pytest.fixture
def config():
    """Load configuration."""
    config_path = Path(__file__).parent.parent / 'config.yaml'
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)


@pytest.fixture
def database(config):
    """Initialize database."""
    return ShotsDatabase(config['storage']['database_path'])


@pytest.fixture
def chroma_index(database, config):
    """Initialize ChromaDB working set indices."""
    # Use WorkingSetIndices for testing - it manages text and visual collections
    return WorkingSetIndices(
        story_slug='test_integration',
        text_dim=384,
        visual_dim=512
    )


@pytest.fixture
def sequence_analyzer(config):
    """Initialize sequence analyzer."""
    return SequenceAnalyzer(config)


@pytest.fixture
def working_set_builder(database, chroma_index, config):
    """Initialize working set builder."""
    return WorkingSetBuilder(database, chroma_index, config)


class TestSequenceAnalysisIntegration:
    """Integration tests for sequence-based picking."""
    
    def test_sequence_grouping_with_real_data(self, sequence_analyzer, database):
        """Test sequence grouping with real database shots."""
        # Get shots from a story
        shots = database.get_shots_by_story('edit_test_story')
        
        assert len(shots) > 0, "No shots found for test story"
        print(f"\n✓ Loaded {len(shots)} shots from database")
        
        # Group into sequences
        sequences = sequence_analyzer.group_by_sequences(
            shots,
            method='hybrid'
        )
        
        assert len(sequences) > 0, "No sequences created"
        print(f"✓ Grouped into {len(sequences)} sequences")
        
        # Verify sequence structure
        total_shots = 0
        for seq_name, seq_shots in sequences.items():
            assert len(seq_shots) > 0, f"Empty sequence: {seq_name}"
            total_shots += len(seq_shots)
            print(f"  - {seq_name}: {len(seq_shots)} shots")
        
        assert total_shots == len(shots), "Some shots lost in grouping"
        print(f"✓ All {total_shots} shots accounted for")
    
    def test_working_set_to_sequences_workflow(self, working_set_builder, sequence_analyzer):
        """Test the workflow from working set to sequences."""
        # Build working set
        working_set = working_set_builder.build_for_beat(
            story_slug='edit_test_story',
            beat_description='Opening shots showing the story location and context',
            beat_requirements=['establishing shots', 'location context'],
            max_shots=20
        )
        
        assert len(working_set['shots']) > 0, "No shots in working set"
        print(f"\n✓ Built working set: {len(working_set['shots'])} shots")
        
        # Group into sequences
        sequences = sequence_analyzer.group_by_sequences(
            working_set['shots'],
            method='hybrid'
        )
        
        assert len(sequences) > 0, "No sequences created from working set"
        print(f"✓ Grouped into {len(sequences)} sequences")
        
        for seq_name, seq_shots in sequences.items():
            print(f"  - {seq_name}: {len(seq_shots)} shots")
    
    @patch('agent.picker.GeminiAnalyzer')
    def test_picker_with_mocked_gemini(self, mock_gemini_class, database, chroma_index, config):
        """Test picker with mocked Gemini analysis."""
        from agent.picker import Picker
        from agent.llm_client import ClaudeClient
        
        # Setup mocks
        mock_gemini = Mock()
        mock_gemini.enabled = True
        mock_gemini.analyze_all_sequences.return_value = {
            'test_sequence': {
                'overall_assessment': {
                    'sequence_quality': 8.5,
                    'shot_variety': 'good',
                    'continuity_score': 9.0,
                    'recommended_for_picking': True
                },
                'shots': {
                    'shot_1': {
                        'quality_score': 8.0,
                        'works_well_with': [2, 3],
                        'avoid_with': [],
                        'notes': 'Strong establishing shot'
                    }
                },
                'warnings': [],
                'recommended_subsequences': []
            }
        }
        mock_gemini_class.return_value = mock_gemini
        
        # Initialize components
        llm_client = ClaudeClient(config)
        working_set_builder = WorkingSetBuilder(database, chroma_index, config)
        sequence_analyzer = SequenceAnalyzer(config)
        
        picker = Picker(
            llm_client=llm_client,
            working_set_builder=working_set_builder,
            sequence_analyzer=sequence_analyzer,
            gemini_analyzer=mock_gemini,
            config=config
        )
        
        assert picker.sequence_picking_enabled, "Sequence picking should be enabled"
        print("\n✓ Picker initialized with sequence analysis")
    
    def test_sequence_metadata_in_shots(self, database):
        """Test that shots have necessary metadata for sequencing."""
        shots = database.get_shots_by_story('edit_test_story')
        
        assert len(shots) > 0, "No shots found"
        
        # Check metadata availability
        has_location = sum(1 for s in shots if s.get('location'))
        has_tc_in = sum(1 for s in shots if s.get('tc_in'))
        has_embeddings = sum(1 for s in shots if s.get('embedding_visual') is not None)
        
        print(f"\n✓ Shot metadata:")
        print(f"  - Location: {has_location}/{len(shots)} shots")
        print(f"  - Timecode: {has_tc_in}/{len(shots)} shots")
        print(f"  - Visual embeddings: {has_embeddings}/{len(shots)} shots")
        
        # At least some shots should have metadata
        assert has_tc_in > 0, "No shots have timecode data"
    
    def test_sequence_config_values(self, config):
        """Test that sequence configuration is properly set."""
        assert 'sequences' in config, "Missing sequences config"
        assert 'gemini' in config, "Missing gemini config"
        
        seq_config = config['sequences']
        assert seq_config['temporal_window_minutes'] == 5
        assert seq_config['visual_similarity_threshold'] == 0.7
        assert seq_config['min_shots_per_sequence'] == 2
        assert seq_config['max_shots_per_sequence'] == 8
        
        gemini_config = config['gemini']
        assert gemini_config['picking']['enabled'] == True
        assert gemini_config['picking']['sequence_grouping_method'] == 'hybrid'
        
        print("\n✓ Configuration validated:")
        print(f"  - Sequence picking enabled: {gemini_config['picking']['enabled']}")
        print(f"  - Grouping method: {gemini_config['picking']['sequence_grouping_method']}")
        print(f"  - Temporal window: {seq_config['temporal_window_minutes']} minutes")


def test_full_compilation_dry_run(config, database, chroma_index):
    """
    Dry run of full compilation with logging only.
    Does not call LLM or Gemini APIs to avoid costs.
    """
    from agent.working_set import WorkingSetBuilder
    from agent.sequence_analyzer import SequenceAnalyzer
    
    print("\n" + "="*80)
    print("SEQUENCE-BASED PICKING DRY RUN")
    print("="*80)
    
    # Initialize components
    working_set_builder = WorkingSetBuilder(database, chroma_index, config)
    sequence_analyzer = SequenceAnalyzer(config)
    
    # Build working set
    print("\n1. Building working set...")
    working_set = working_set_builder.build_for_beat(
        story_slug='edit_test_story',
        beat_description='Opening shots showing the story location',
        beat_requirements=['establishing shots'],
        max_shots=20
    )
    print(f"   ✓ Working set: {len(working_set['shots'])} shots")
    
    # Group into sequences
    print("\n2. Grouping into sequences...")
    sequences = sequence_analyzer.group_by_sequences(
        working_set['shots'],
        method='hybrid'
    )
    print(f"   ✓ Sequences: {len(sequences)}")
    for seq_name, seq_shots in sequences.items():
        print(f"     - {seq_name}: {len(seq_shots)} shots")
    
    # Show what would be sent to Gemini
    print("\n3. Sequences ready for Gemini analysis:")
    for seq_name, seq_shots in sequences.items():
        print(f"\n   Sequence: {seq_name}")
        for shot in seq_shots[:3]:  # Show first 3 shots
            print(f"     - Shot {shot['shot_id']}: {shot.get('shot_type', 'UNKNOWN')}")
            if shot.get('gemini_description'):
                desc = shot['gemini_description'][:100]
                print(f"       {desc}...")
    
    print("\n" + "="*80)
    print("DRY RUN COMPLETE")
    print("="*80)
    print("\nTo run with real APIs, ensure:")
    print("  1. Gemini API credentials are configured")
    print("  2. Claude API credentials are configured")
    print("  3. Set gemini.picking.enabled: true in config.yaml")


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])
