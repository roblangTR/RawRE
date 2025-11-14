#!/usr/bin/env python3
"""
News Edit Agent CLI

Command-line interface for ingesting video rushes and compiling edits.
"""

import argparse
import sys
import json
import yaml
from pathlib import Path

from ingest.orchestrator import IngestOrchestrator
from storage.database import ShotsDatabase
from storage.vector_index import VectorIndex
from agent.llm_client import OpenArenaClient
from agent.orchestrator import AgentOrchestrator
from output.edl_writer import EDLWriter
from output.fcpxml_writer import FCPXMLWriter


def load_config(config_path: str = "config.yaml") -> dict:
    """Load configuration from YAML file."""
    config_file = Path(config_path)
    
    if not config_file.exists():
        print(f"Warning: Config file {config_path} not found, using defaults")
        return {}
    
    with open(config_file, 'r') as f:
        return yaml.safe_load(f)


def cmd_ingest(args):
    """Handle ingest command."""
    print("=" * 70)
    print("NEWS EDIT AGENT - INGEST")
    print("=" * 70)
    print()
    
    # Load configuration
    config = load_config(args.config)
    
    # Initialize orchestrator
    orchestrator = IngestOrchestrator(config)
    
    # Parse metadata if provided
    metadata = None
    if args.metadata:
        try:
            metadata = json.loads(args.metadata)
        except json.JSONDecodeError:
            print(f"Error: Invalid JSON in metadata: {args.metadata}")
            return 1
    
    try:
        # Ingest single file or directory
        if args.input:
            input_path = Path(args.input)
            
            if input_path.is_file():
                print(f"Ingesting file: {input_path}")
                result = orchestrator.ingest_video(
                    str(input_path),
                    args.story,
                    metadata
                )
                
                print()
                print("Results:")
                print(f"  Story ID: {result['story_id']}")
                print(f"  Shots Processed: {result['shots_processed']}")
                print(f"  Shots Stored: {result['shots_stored']}")
                print(f"  Success: {result['success']}")
                
                if result['errors']:
                    print(f"  Errors: {result['errors']}")
                
            elif input_path.is_dir():
                print(f"Ingesting directory: {input_path}")
                result = orchestrator.ingest_directory(
                    str(input_path),
                    args.story,
                    args.pattern,
                    metadata
                )
                
                print()
                print("Results:")
                print(f"  Story ID: {result['story_id']}")
                print(f"  Total Files: {result['total_files']}")
                print(f"  Successful: {result['successful']}")
                print(f"  Failed: {result['failed']}")
                
            else:
                print(f"Error: {input_path} is neither a file nor directory")
                return 1
        
        print()
        print("=" * 70)
        print("✓ Ingest complete")
        print("=" * 70)
        return 0
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1


def cmd_compile(args):
    """Handle compile command."""
    print("=" * 70)
    print("NEWS EDIT AGENT - COMPILE")
    print("=" * 70)
    print()
    
    print("Story:", args.story)
    print("Brief:", args.brief)
    print("Duration:", args.duration, "seconds")
    if args.output:
        print("Output:", args.output)
    print()
    
    try:
        # Load configuration
        config = load_config(args.config)
        
        # Initialize components
        print("Initializing components...")
        db_path = config.get('database', {}).get('path', './data/shots.db')
        database = ShotsDatabase(db_path)
        
        vector_dim = config.get('embeddings', {}).get('dimension', 384)
        vector_index = VectorIndex(dimension=vector_dim)
        
        llm_client = OpenArenaClient()
        
        # Create orchestrator
        orchestrator = AgentOrchestrator(database, vector_index, llm_client)
        
        # Compile edit
        print("Compiling edit...")
        result = orchestrator.compile_edit(
            story_slug=args.story,
            brief=args.brief,
            target_duration=args.duration,
            max_iterations=3,
            min_verification_score=7.0
        )
        
        # Print summary
        print()
        print(orchestrator.get_edit_summary(result))
        
        # Save result JSON
        result_path = f"./output/{args.story}_result.json"
        orchestrator.save_result(result, result_path)
        print(f"\n✓ Result saved to {result_path}")
        
        # Export to EDL/FCPXML if output specified
        if args.output:
            output_path = Path(args.output)
            ext = output_path.suffix.lower()
            
            if ext == '.edl':
                print(f"\nExporting to EDL: {output_path}")
                edl_writer = EDLWriter()
                edl_path = edl_writer.write_from_result(result, str(output_path))
                print(f"✓ EDL written to {edl_path}")
                
                # Validate
                validation = edl_writer.validate_edl(edl_path)
                if validation['valid']:
                    print(f"✓ EDL validation passed")
                else:
                    print(f"✗ EDL validation failed: {validation['errors']}")
                    
            elif ext == '.fcpxml':
                print(f"\nExporting to FCPXML: {output_path}")
                fcpxml_writer = FCPXMLWriter()
                fcpxml_path = fcpxml_writer.write_from_result(result, str(output_path))
                print(f"✓ FCPXML written to {fcpxml_path}")
                
                # Validate
                validation = fcpxml_writer.validate_fcpxml(fcpxml_path)
                if validation['valid']:
                    print(f"✓ FCPXML validation passed")
                else:
                    print(f"✗ FCPXML validation failed: {validation['errors']}")
            else:
                print(f"\nWarning: Unknown output format '{ext}', skipping export")
                print("Supported formats: .edl, .fcpxml")
        
        print()
        print("=" * 70)
        if result['approved']:
            print("✓ Edit compilation complete and approved!")
        else:
            print("✗ Edit compilation complete but not approved")
        print("=" * 70)
        
        return 0 if result['approved'] else 1
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1


def cmd_stats(args):
    """Handle stats command."""
    print("=" * 70)
    print("NEWS EDIT AGENT - STATS")
    print("=" * 70)
    print()
    
    config = load_config(args.config)
    orchestrator = IngestOrchestrator(config)
    
    stats = orchestrator.get_story_stats(args.story)
    
    print(f"Story: {stats['story_id']}")
    print(f"Exists: {stats.get('exists', False)}")
    
    if stats.get('exists'):
        print(f"Total Shots: {stats.get('total_shots', 0)}")
        print(f"Total Duration: {stats.get('total_duration', 0):.1f}s")
        print(f"Shot Types: {stats.get('shot_types', {})}")
        print(f"Source Files: {len(stats.get('source_files', []))}")
    else:
        print(f"Message: {stats.get('message', 'Story not found')}")
    
    print()
    return 0


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="News Edit Agent - AI-powered video editing for news",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Ingest a single video file
  python cli.py ingest --input ./rushes/video.mp4 --story breaking-news-001
  
  # Ingest a directory of rushes
  python cli.py ingest --input ./rushes --story breaking-news-001
  
  # Compile an edit
  python cli.py compile --story breaking-news-001 --brief "Climate protest" --duration 90
  
  # Get story statistics
  python cli.py stats --story breaking-news-001
        """
    )
    
    parser.add_argument(
        '--config',
        default='config.yaml',
        help='Path to configuration file (default: config.yaml)'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose output'
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Command to execute')
    
    # Ingest command
    ingest_parser = subparsers.add_parser(
        'ingest',
        help='Ingest video rushes into the system'
    )
    ingest_parser.add_argument(
        '--input', '-i',
        required=True,
        help='Input video file or directory'
    )
    ingest_parser.add_argument(
        '--story', '-s',
        required=True,
        help='Story identifier/slug'
    )
    ingest_parser.add_argument(
        '--pattern', '-p',
        default='*.mp4',
        help='File pattern for directory ingest (default: *.mp4)'
    )
    ingest_parser.add_argument(
        '--metadata', '-m',
        help='JSON metadata to attach to shots'
    )
    
    # Compile command
    compile_parser = subparsers.add_parser(
        'compile',
        help='Compile an edit from ingested rushes'
    )
    compile_parser.add_argument(
        '--story', '-s',
        required=True,
        help='Story identifier/slug'
    )
    compile_parser.add_argument(
        '--brief', '-b',
        required=True,
        help='Editorial brief describing the story'
    )
    compile_parser.add_argument(
        '--duration', '-d',
        type=int,
        default=90,
        help='Target duration in seconds (default: 90)'
    )
    compile_parser.add_argument(
        '--output', '-o',
        help='Output file path (EDL or FCPXML)'
    )
    
    # Stats command
    stats_parser = subparsers.add_parser(
        'stats',
        help='Get statistics for an ingested story'
    )
    stats_parser.add_argument(
        '--story', '-s',
        required=True,
        help='Story identifier/slug'
    )
    
    # Parse arguments
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    # Execute command
    if args.command == 'ingest':
        return cmd_ingest(args)
    elif args.command == 'compile':
        return cmd_compile(args)
    elif args.command == 'stats':
        return cmd_stats(args)
    else:
        print(f"Unknown command: {args.command}")
        return 1


if __name__ == '__main__':
    sys.exit(main())
