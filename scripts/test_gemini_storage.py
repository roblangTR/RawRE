#!/usr/bin/env python3
"""
Test script to debug Gemini metadata storage
"""

import logging
import yaml
from pathlib import Path

# Set up detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

from ingest.orchestrator import IngestOrchestrator

def main():
    print("=" * 80)
    print("GEMINI METADATA STORAGE DEBUG TEST")
    print("=" * 80)
    
    # Load config
    with open('config.yaml') as f:
        config = yaml.safe_load(f)
    
    # Initialize orchestrator
    orchestrator = IngestOrchestrator(config)
    
    # Test with one small video
    test_video = 'Test_Rushes/VID_20220424_113056.mp4'
    
    print(f"\nTesting with: {test_video}")
    print("-" * 80)
    
    # Run ingest
    result = orchestrator.ingest_video(test_video, 'gemini_debug_test', {})
    
    print("\n" + "=" * 80)
    print("RESULTS")
    print("=" * 80)
    print(f"Success: {result['success']}")
    print(f"Shots processed: {result['shots_processed']}")
    print(f"Shots stored: {result['shots_stored']}")
    
    if result['shots']:
        shot = result['shots'][0]
        print(f"\nFirst shot metadata:")
        print(f"  Shot ID: {shot.get('shot_id')}")
        print(f"  Timecode: {shot.get('tc_in')} - {shot.get('tc_out')}")
        print(f"\nGemini fields:")
        gemini_fields = {k: v for k, v in shot.items() if k.startswith('gemini_')}
        if gemini_fields:
            for key, value in gemini_fields.items():
                print(f"  {key}: {value}")
        else:
            print("  NO GEMINI FIELDS FOUND!")
    
    # Query database directly
    print("\n" + "=" * 80)
    print("DATABASE VERIFICATION")
    print("=" * 80)
    
    shots = orchestrator.database.get_shots_by_story('gemini_debug_test')
    if shots:
        shot = shots[0]
        print(f"Found {len(shots)} shot(s) in database")
        print(f"\nFirst shot from DB:")
        print(f"  gemini_description: {shot.get('gemini_description')}")
        print(f"  gemini_shot_type: {shot.get('gemini_shot_type')}")
        print(f"  gemini_shot_size: {shot.get('gemini_shot_size')}")
    else:
        print("No shots found in database!")

if __name__ == '__main__':
    main()
