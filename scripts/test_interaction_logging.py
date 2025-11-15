#!/usr/bin/env python3
"""
Test script for AI Agent Interaction Logging

Runs a complete edit workflow and captures all AI agent interactions.
"""

import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import logging
from dotenv import load_dotenv

from storage.database import ShotsDatabase
from agent.llm_client import ClaudeClient
from agent.orchestrator import AgentOrchestrator
from agent.interaction_logger import get_interaction_logger, reset_interaction_logger
from ingest.embedder import Embedder

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Run test with interaction logging."""
    
    print("=" * 80)
    print("AI AGENT INTERACTION LOGGING TEST")
    print("=" * 80)
    print()
    
    # Load environment
    load_dotenv()
    
    # Check for required environment variables
    workflow_id = os.getenv('WORKFLOW_ID')
    if not workflow_id:
        print("✗ WORKFLOW_ID not set in .env file")
        print("  Please add WORKFLOW_ID to your .env")
        return 1
    
    # Reset logger for clean test
    reset_interaction_logger()
    
    # Initialize interaction logger
    interaction_logger = get_interaction_logger("logs/interactions")
    print(f"✓ Interaction logger initialized")
    print(f"  Session ID: {interaction_logger.session_id}")
    print(f"  Output directory: {interaction_logger.output_dir}")
    print()
    
    try:
        # Initialize database
        print("Initializing database...")
        db = ShotsDatabase("data/shots.db")
        
        # Check if we have data
        all_shots = db.get_shots_by_story("gallipoli_test")
        if not all_shots:
            print("✗ No shots in database for gallipoli_test")
            print("  Please run ingestion first: python scripts/test_small_ingest.py")
            return 1
        
        print(f"✓ Database loaded: {len(all_shots)} shots for gallipoli_test")
        print()
        
        # Initialize embedder (optional)
        embedder = None
        try:
            import yaml
            with open('config.yaml', 'r') as f:
                config = yaml.safe_load(f)
            
            from storage.chroma_index import ChromaIndex
            chroma = ChromaIndex(config)
            if chroma.collection.count() > 0:
                embedder = Embedder(config)
                print(f"✓ Embedder initialized with {chroma.collection.count()} embeddings")
            else:
                print("⚠ No embeddings found, using keyword search only")
        except Exception as e:
            print(f"⚠ Could not initialize embedder: {e}")
            print("  Using keyword search only")
        print()
        
        # Initialize LLM client with logging enabled
        print("Initializing LLM client with interaction logging...")
        llm_client = ClaudeClient(enable_logging=True)
        print("✓ LLM client initialized")
        print()
        
        # Initialize orchestrator
        print("Initializing agent orchestrator...")
        orchestrator = AgentOrchestrator(
            database=db,
            llm_client=llm_client,
            embedder=embedder
        )
        print("✓ Orchestrator initialized")
        print()
        
        # Define test story
        story_slug = "gallipoli_test"
        brief = "Create a short news package about the Gallipoli burial ceremony"
        target_duration = 60  # 1 minute for quick test
        
        print("=" * 80)
        print("RUNNING EDIT COMPILATION")
        print("=" * 80)
        print(f"Story: {story_slug}")
        print(f"Brief: {brief}")
        print(f"Target Duration: {target_duration}s")
        print()
        
        # Run compilation (single iteration for testing)
        result = orchestrator.compile_edit(
            story_slug=story_slug,
            brief=brief,
            target_duration=target_duration,
            max_iterations=1,  # Just one iteration for testing
            min_verification_score=5.0  # Lower threshold for testing
        )
        
        print()
        print("=" * 80)
        print("COMPILATION COMPLETE")
        print("=" * 80)
        print()
        
        # Print summary
        print(orchestrator.get_edit_summary(result))
        print()
        
        # Save session summary
        print("=" * 80)
        print("SAVING INTERACTION LOGS")
        print("=" * 80)
        print()
        
        summary_path = interaction_logger.save_session_summary()
        print(f"✓ Session summary saved: {summary_path}")
        
        # Generate readable report
        report = interaction_logger.generate_readable_report()
        print(f"✓ Readable report generated")
        print()
        
        # Print statistics
        stats = interaction_logger._calculate_statistics()
        print("INTERACTION STATISTICS")
        print("-" * 80)
        print(f"Total Interactions: {stats['total_interactions']}")
        print(f"Total Prompt Characters: {stats['total_prompt_chars']:,}")
        print(f"Total Response Characters: {stats['total_response_chars']:,}")
        print(f"Average Prompt Length: {stats['average_prompt_length']:.0f} chars")
        print(f"Average Response Length: {stats['average_response_length']:.0f} chars")
        print()
        
        print("By Agent:")
        for agent, count in stats['by_agent'].items():
            print(f"  {agent}: {count} interactions")
        print()
        
        print("By Type:")
        for itype, count in stats['by_type'].items():
            print(f"  {itype}: {count} interactions")
        print()
        
        # List all interaction files
        print("INTERACTION FILES")
        print("-" * 80)
        interaction_files = sorted(interaction_logger.output_dir.glob("*.json"))
        for f in interaction_files:
            size_kb = f.stat().st_size / 1024
            print(f"  {f.name} ({size_kb:.1f} KB)")
        print()
        
        # Show report file
        report_files = sorted(interaction_logger.output_dir.glob("*.txt"))
        for f in report_files:
            size_kb = f.stat().st_size / 1024
            print(f"  {f.name} ({size_kb:.1f} KB)")
        print()
        
        print("=" * 80)
        print("✓ TEST COMPLETE")
        print("=" * 80)
        print()
        print("You can now examine the interaction logs in:")
        print(f"  {interaction_logger.output_dir}")
        print()
        print("Files created:")
        print(f"  - Individual interaction JSONs: {interaction_logger.interaction_count} files")
        print(f"  - Session summary: session_{interaction_logger.session_id}_summary.json")
        print(f"  - Readable report: session_{interaction_logger.session_id}_report.txt")
        print()
        
        return 0
        
    except Exception as e:
        logger.error(f"Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
