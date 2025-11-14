"""
Tests for Output Writers

Tests for EDL and FCPXML writers.
"""

import pytest
from pathlib import Path
from output.edl_writer import EDLWriter
from output.fcpxml_writer import FCPXMLWriter


class TestEDLWriter:
    """Tests for EDL Writer."""
    
    def test_create_writer(self):
        """Test EDL writer creation."""
        writer = EDLWriter(title="TEST_EDIT", frame_rate=25.0)
        assert writer.title == "TEST_EDIT"
        assert writer.frame_rate == 25.0
    
    def test_seconds_to_timecode(self):
        """Test timecode conversion."""
        writer = EDLWriter(frame_rate=25.0)
        
        # Test various times
        assert writer._seconds_to_timecode(0) == "00:00:00:00"
        assert writer._seconds_to_timecode(1) == "00:00:01:00"
        assert writer._seconds_to_timecode(60) == "00:01:00:00"
        assert writer._seconds_to_timecode(3600) == "01:00:00:00"
    
    def test_timecode_to_seconds(self):
        """Test timecode parsing."""
        writer = EDLWriter(frame_rate=25.0)
        
        assert writer._timecode_to_seconds("00:00:00:00") == 0.0
        assert writer._timecode_to_seconds("00:00:01:00") == 1.0
        assert writer._timecode_to_seconds("00:01:00:00") == 60.0
    
    def test_write_edl(self, temp_dir, sample_selections):
        """Test writing EDL file."""
        writer = EDLWriter(title="TEST")
        output_path = Path(temp_dir) / "test.edl"
        
        result = writer.write_edl(sample_selections, str(output_path))
        
        assert Path(result).exists()
        
        # Read and verify content
        with open(result, 'r') as f:
            content = f.read()
            assert "TITLE: TEST" in content
            assert "FCM: NON-DROP FRAME" in content
    
    def test_validate_edl(self, temp_dir, sample_selections):
        """Test EDL validation."""
        writer = EDLWriter()
        output_path = Path(temp_dir) / "test.edl"
        
        # Write EDL
        edl_path = writer.write_edl(sample_selections, str(output_path))
        
        # Validate
        report = writer.validate_edl(edl_path)
        assert report['valid'] is True
        assert report['event_count'] > 0


class TestFCPXMLWriter:
    """Tests for FCPXML Writer."""
    
    def test_create_writer(self):
        """Test FCPXML writer creation."""
        writer = FCPXMLWriter(project_name="Test Project", frame_rate="25p")
        assert writer.project_name == "Test Project"
        assert writer.frame_rate == "25p"
    
    def test_get_frame_duration(self):
        """Test frame duration calculation."""
        writer = FCPXMLWriter(frame_rate="25p")
        assert writer.frame_duration == "1/25s"
        
        writer = FCPXMLWriter(frame_rate="30p")
        assert writer.frame_duration == "1001/30000s"
    
    def test_seconds_to_frames(self):
        """Test frame conversion."""
        writer = FCPXMLWriter(frame_rate="25p")
        
        assert writer._seconds_to_frames(0) == 0
        assert writer._seconds_to_frames(1) == 25
        assert writer._seconds_to_frames(2.5) == 62
    
    def test_write_fcpxml(self, temp_dir, sample_selections):
        """Test writing FCPXML file."""
        writer = FCPXMLWriter(project_name="Test")
        output_path = Path(temp_dir) / "test.fcpxml"
        
        result = writer.write_fcpxml(sample_selections, str(output_path))
        
        assert Path(result).exists()
        
        # Read and verify it's valid XML
        with open(result, 'r') as f:
            content = f.read()
            assert '<?xml version' in content
            assert '<fcpxml' in content
            assert '</fcpxml>' in content
    
    def test_validate_fcpxml(self, temp_dir, sample_selections):
        """Test FCPXML validation."""
        writer = FCPXMLWriter()
        output_path = Path(temp_dir) / "test.fcpxml"
        
        # Write FCPXML
        fcpxml_path = writer.write_fcpxml(sample_selections, str(output_path))
        
        # Validate
        report = writer.validate_fcpxml(fcpxml_path)
        assert report['valid'] is True
        assert report['clip_count'] > 0
