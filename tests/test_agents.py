"""
Tests for Agent Modules

Tests for planner, picker, verifier, and orchestrator.
"""

import pytest
from unittest.mock import Mock, patch
from agent.planner import Planner
from agent.picker import Picker
from agent.verifier import Verifier
from agent.working_set import WorkingSetBuilder


class TestWorkingSetBuilder:
    """Tests for Working Set Builder."""
    
    def test_create_builder(self, test_db, test_vector_index):
        """Test builder creation."""
        builder = WorkingSetBuilder(test_db, test_vector_index)
        assert builder is not None
    
    def test_build_working_set(self, test_db, test_vector_index, sample_shots_list):
        """Test building working set."""
        # Skip this test for now - requires full integration
        pytest.skip("Requires full agent integration")


class TestPlannerAgent:
    """Tests for Planner Agent."""
    
    def test_create_planner(self, mock_llm_client, test_db, test_vector_index):
        """Test planner creation."""
        from agent.working_set import WorkingSetBuilder
        builder = WorkingSetBuilder(test_db, test_vector_index)
        planner = Planner(mock_llm_client, builder)
        assert planner is not None
    
    def test_create_plan(self, mock_llm_client, test_db, test_vector_index, sample_plan):
        """Test plan creation."""
        # Skip this test for now - requires full integration
        pytest.skip("Requires full agent integration")


class TestPickerAgent:
    """Tests for Picker Agent."""
    
    def test_create_picker(self, mock_llm_client, test_db, test_vector_index):
        """Test picker creation."""
        from agent.working_set import WorkingSetBuilder
        builder = WorkingSetBuilder(test_db, test_vector_index)
        picker = Picker(mock_llm_client, builder)
        assert picker is not None
    
    def test_select_shots(self, mock_llm_client, test_db, test_vector_index, sample_plan, sample_selections):
        """Test shot selection."""
        # Skip this test for now - requires full integration
        pytest.skip("Requires full agent integration")


class TestVerifierAgent:
    """Tests for Verifier Agent."""
    
    def test_create_verifier(self, mock_llm_client):
        """Test verifier creation."""
        verifier = Verifier(mock_llm_client)
        assert verifier is not None
    
    def test_verify_edit(self, mock_llm_client, sample_plan, sample_selections, sample_verification):
        """Test edit verification."""
        # Skip this test for now - requires full integration
        pytest.skip("Requires full agent integration")
