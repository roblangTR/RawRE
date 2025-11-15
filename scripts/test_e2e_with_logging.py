#!/usr/bin/env python3
"""
End-to-End Test with Detailed Logging

Tests the complete RAWRE system with detailed logging of all AI interactions.
Logs are saved to a timestamped file for review.
"""

import sys
import os
import logging
from pathlib import Path
from datetime import datetime
import json
import yaml

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
from storage.database import ShotsDatabase
from ingest.embedder import Embedder
from agent.llm_client import ClaudeClient
from agent.orchestrator import AgentOrchestrator
from output.edl_writer import EDLWriter
from output.fcpxml_writer import FCPXMLWriter


def setup_detailed_logging(log_dir: str = "logs"):
    """Set up detailed logging to both console and file."""
    # Create logs directory
    Path(log_dir).mkdir(exist_ok=True)
    
    # Create timestamped log file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = Path(log_dir) / f"e2e_test_{timestamp}.log"
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    
    # Remove existing handlers
    root_logger.handlers = []
    
    # Console handler (INFO level)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)
    
    # File handler (DEBUG level - captures everything)
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    file_handler.setFormatter(file_formatter)
    root_logger.addHandler(file_handler)
    
    return log_file


def print_header(title: str):
    """Print a formatted header."""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80 + "\n")


def main():
    """Run end-to-end test with detailed logging."""
    
    # Set up logging
    log_file = setup_detailed_logging()
    
    print_header("RAWRE END-TO-END TEST WITH DETAILED LOGGING")
    print(f"📝 Detailed logs will be saved to: {log_file}")
    print()
    
    # Load environment
    load_dotenv()
    
    # Test configuration
    story_slug = "gallipoli_burial_2022"
    brief = """The remains of 17 French soldiers who fought in World War One during the
Gallipoli Campaign were laid to rest in Gallipoli on Sunday (April 24). Several members
of the French military were present during the burial ceremony alongside Turkish officials.
The remains were discovered during restoration work of a fort in the region. The ceremony
came one day before the 107th anniversary of Anzac Day."""
    target_duration = 90
    
    print(f"Story: {story_slug}")
    print(f"Target Duration: {target_duration}s")
    print()
    
    try:
        print_header("INITIALIZING SYSTEM COMPONENTS")
        
        # Load configuration
        config_path = Path("config.yaml")
        if not config_path.exists():
            print(f"✗ Configuration file not found: {config_path}")
            return 1
        
        with open(config_path) as f:
            config = yaml.safe_load(f)
        print(f"✓ Configuration loaded")
        
        # Initialize database
        print("Loading database...")
        database = ShotsDatabase("./data/shots.db")
        shots = database.get_shots_by_story(story_slug)
        print(f"✓ Found {len(shots)} shots for story '{story_slug}'")
        
        # Initialize embedder
        print("Initializing embedder...")
        embedder = Embedder(config)
        print("✓ Embedder initialized (semantic search enabled)")
        
        # Initialize LLM client
        print("Initializing LLM client...")
        llm_client = ClaudeClient()
        print("✓ LLM client initialized")
        
        # Initialize orchestrator (it will create all agents internally)
        print("Initializing orchestrator...")
        orchestrator = AgentOrchestrator(database, llm_client, embedder)
        print("✓ Orchestrator initialized")
        
        print_header("RUNNING AGENTIC EDIT WORKFLOW")
        
        # Run the workflow
        result = orchestrator.compile_edit(
            story_slug=story_slug,
            brief=brief,
            target_duration=target_duration,
            max_iterations=3,
            min_verification_score=7.0
        )
        
        print_header("WORKFLOW RESULTS")
        
        print(f"Status: {'✓ APPROVED' if result['approved'] else '✗ NOT APPROVED'}")
        print(f"Iterations: {len(result['iterations'])}")
        print(f"Total Duration: {result['final_selections']['total_duration']:.1f}s")
        print(f"Total Shots: {result['final_selections']['total_shots']}")
        print(f"Verification Score: {result['final_verification']['overall_score']}/10")
        print()
        
        # Show beat breakdown
        print("Beat Breakdown:")
        for beat_sel in result['final_selections']['beat_selections']:
            beat = beat_sel['beat']
            print(f"  Beat {beat['beat_number']}: {beat['title']}")
            print(f"    Shots: {len(beat_sel['shots'])}")
            print(f"    Duration: {beat_sel['duration']:.1f}s (target: {beat['target_duration']}s)")
        print()
        
        # Show issues
        if result['final_verification'].get('issues'):
            print(f"Issues Found: {len(result['final_verification']['issues'])}")
            for issue in result['final_verification']['issues']:
                severity_icon = "⚠️" if issue['severity'] == 'medium' else "ℹ️"
                print(f"  {severity_icon} [{issue['severity'].upper()}] {issue['description'][:80]}...")
        else:
            print("✓ No issues found")
        print()
        
        print_header("EXPORTING OUTPUTS")
        
        # Save result JSON
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = Path("./output")
        output_dir.mkdir(exist_ok=True)
        
        result_file = output_dir / f"{story_slug}_{timestamp}_result.json"
        with open(result_file, 'w') as f:
            json.dump(result, f, indent=2)
        print(f"✓ Result JSON: {result_file}")
        
        # Check file size
        file_size = result_file.stat().st_size
        print(f"  File size: {file_size / 1024:.1f} KB")
        
        # Verify no embeddings in result
        with open(result_file, 'r') as f:
            result_text = f.read()
            has_embeddings = 'embedding_text' in result_text or 'embedding_visual' in result_text
            if has_embeddings:
                print("  ⚠️  WARNING: Result file contains embedding data!")
            else:
                print("  ✓ No embeddings in result file (stored in database)")
        
        # Export EDL
        try:
            edl_file = output_dir / f"{story_slug}_{timestamp}.edl"
            edl_writer = EDLWriter()
            edl_writer.write_edl(result['final_selections'], str(edl_file))
            print(f"✓ EDL file: {edl_file}")
        except Exception as e:
            print(f"⚠️  EDL export failed: {e}")
        
        # Export FCPXML
        try:
            fcpxml_file = output_dir / f"{story_slug}_{timestamp}.fcpxml"
            fcpxml_writer = FCPXMLWriter()
            fcpxml_writer.write_fcpxml(result['final_selections'], str(fcpxml_file))
            print(f"✓ FCPXML file: {fcpxml_file}")
        except Exception as e:
            print(f"⚠️  FCPXML export failed: {e}")
        
        print()
        print_header("TEST COMPLETE")
        
        print("✓✓✓ SUCCESS ✓✓✓")
        print()
        print(f"📝 Detailed logs saved to: {log_file}")
        print(f"📁 Outputs saved to: {output_dir}")
        print()
        print("Review the log file to see all AI request/response details including:")
        print("  - Full prompts sent to Claude")
        print("  - Complete responses received")
        print("  - Token usage statistics")
        print("  - Timing information")
        
        return 0
        
    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        print(f"\n📝 Check log file for details: {log_file}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
