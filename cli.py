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
    print()
    
    print("Note: Compile functionality requires Phase 2 & 3 completion")
    print("  - Working set builder")
    print("  - Agent modules (planner, picker, verifier)")
    print("  - Output writers (EDL/FCPXML)")
    print()
    
    return 0


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
