#!/usr/bin/env python3
"""
Ingest all test rushes from Test_Rushes folder
"""

import yaml
import glob
from pathlib import Path
from ingest.orchestrator import IngestOrchestrator

def main():
    print("=" * 80)
    print("INGESTING ALL TEST RUSHES")
    print("=" * 80)
    
    # Load config
    with open('config.yaml') as f:
        config = yaml.safe_load(f)
    
    # Initialize orchestrator
    orchestrator = IngestOrchestrator(config)
    
    # Find all videos
    video_files = sorted(glob.glob('Test_Rushes/*.mp4'))
    
    print(f"\nFound {len(video_files)} videos to ingest")
    print("-" * 80)
    
    story_slug = 'edit_test_story'
    
    # Process each video
    for i, video_path in enumerate(video_files, 1):
        video_name = Path(video_path).name
        print(f"\n[{i}/{len(video_files)}] Processing: {video_name}")
        print("-" * 80)
        
        try:
            result = orchestrator.ingest_video(
                video_path=video_path,
                story_id=story_slug,
                metadata={'source': 'Test_Rushes', 'filename': video_name}
            )
            
            print(f"✓ Success: {result['shots_stored']} shots created")
            
        except Exception as e:
            print(f"✗ Error: {e}")
            continue
    
    print("\n" + "=" * 80)
    print("INGEST COMPLETE")
    print("=" * 80)
    
    # Check total shots
    from storage.database import ShotsDatabase
    db = ShotsDatabase('./data/shots.db')
    shots = db.get_shots_by_story(story_slug)
    print(f"\nTotal shots in database: {len(shots)}")
    
    # Show duration stats
    total_duration = sum(s.get('duration', 0) for s in shots)
    print(f"Total footage duration: {total_duration:.1f}s ({total_duration/60:.1f} minutes)")

if __name__ == '__main__':
    main()
