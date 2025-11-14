#!/usr/bin/env python3
"""
Test script for Gemini batch video analysis.

This script tests analyzing multiple video clips in batch mode,
demonstrating how the system handles multiple shots from a rushes file.
"""

import json
import logging
import sys
from pathlib import Path
import yaml

from ingest.gemini_analyzer import GeminiAnalyzer
from ingest.video_processor import VideoProcessor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Test Gemini batch analysis with multiple clips."""
    
    try:
        # Load configuration
        logger.info("Loading configuration...")
        with open('config.yaml', 'r') as f:
            config = yaml.safe_load(f)
        
        # Check if Gemini is enabled
        if not config.get('gemini', {}).get('enabled', False):
            logger.error("Gemini is not enabled in config.yaml")
            sys.exit(1)
        
        # Find test videos
        test_dir = Path("Test_Rushes")
        if not test_dir.exists():
            logger.error(f"Test directory not found: {test_dir}")
            sys.exit(1)
        
        # Get all video files
        video_files = list(test_dir.glob("*.mp4")) + list(test_dir.glob("*.mov"))
        
        if not video_files:
            logger.error(f"No video files found in {test_dir}")
            sys.exit(1)
        
        # Limit to first 3 videos for testing
        video_files = video_files[:3]
        
        logger.info(f"Found {len(video_files)} test videos:")
        for i, vf in enumerate(video_files, 1):
            size_mb = vf.stat().st_size / 1024 / 1024
            logger.info(f"  {i}. {vf.name} ({size_mb:.2f} MB)")
        
        logger.info("")
        logger.info("=" * 60)
        logger.info("Initializing Gemini analyzer...")
        logger.info("=" * 60)
        
        # Initialize analyzer and video processor
        analyzer = GeminiAnalyzer(config)
        video_processor = VideoProcessor(config)
        
        if not analyzer.enabled:
            logger.error("Gemini analyzer failed to initialize")
            sys.exit(1)
        
        logger.info("✓ Gemini analyzer initialized successfully")
        logger.info("✓ Video processor initialized successfully")
        logger.info("")
        
        # Prepare shot data for each video
        shots_data = []
        video_paths = []
        
        for i, video_file in enumerate(video_files, 1):
            shot_data = {
                'shot_id': i,
                'tc_in': f'00:00:{i:02d}:00',
                'tc_out': f'00:00:{i:02d}:10',
                'duration_ms': 10000,
                'video_file': str(video_file)
            }
            shots_data.append(shot_data)
            video_paths.append(str(video_file))
        
        logger.info("=" * 60)
        logger.info(f"Analyzing {len(video_files)} videos in batch...")
        logger.info("=" * 60)
        logger.info(f"This may take {len(video_files) * 12} seconds...")
        logger.info("")
        
        # Analyze batch with video processor for Gemini proxy generation
        results = analyzer.analyze_shots_batch(
            shots_data=shots_data,
            video_paths=video_paths,
            proxy_paths=None,
            video_processor=video_processor
        )
        
        # Display results
        logger.info("")
        logger.info("=" * 60)
        logger.info("BATCH ANALYSIS COMPLETE")
        logger.info("=" * 60)
        logger.info("")
        
        successful = sum(1 for r in results if r is not None)
        failed = len(results) - successful
        
        logger.info(f"Results: {successful} successful, {failed} failed")
        logger.info("")
        
        # Display each result
        for i, (video_file, shot_data, result) in enumerate(zip(video_files, shots_data, results), 1):
            logger.info("-" * 60)
            logger.info(f"Video {i}/{len(video_files)}: {video_file.name}")
            logger.info("-" * 60)
            
            if result is None:
                logger.info("❌ Analysis failed")
                logger.info("")
                continue
            
            logger.info(f"✓ Analysis successful")
            logger.info("")
            logger.info(f"📝 Description:")
            desc = result.get('enhanced_description', 'N/A')
            # Truncate long descriptions
            if len(desc) > 200:
                desc = desc[:200] + "..."
            logger.info(f"   {desc}")
            logger.info("")
            logger.info(f"🎬 Shot Type: {result.get('shot_type', 'N/A')}")
            logger.info(f"📐 Shot Size: {result.get('shot_size', 'N/A')}")
            logger.info(f"🎥 Camera Movement: {result.get('camera_movement', 'N/A')}")
            logger.info(f"⭐ Visual Quality: {result.get('visual_quality', 'N/A')}")
            logger.info(f"📰 News Context: {result.get('news_context', 'N/A')}")
            logger.info(f"🎨 Tone: {result.get('tone', 'N/A')}")
            logger.info(f"🎯 Confidence: {result.get('confidence', 'N/A')}")
            logger.info("")
        
        # Save all results to JSON
        output_file = "gemini_batch_results.json"
        batch_output = {
            'total_videos': len(video_files),
            'successful': successful,
            'failed': failed,
            'results': [
                {
                    'video_file': str(vf),
                    'shot_data': sd,
                    'analysis': r
                }
                for vf, sd, r in zip(video_files, shots_data, results)
            ]
        }
        
        with open(output_file, 'w') as f:
            json.dump(batch_output, f, indent=2)
        
        logger.info("=" * 60)
        logger.info(f"💾 Full batch results saved to: {output_file}")
        logger.info("=" * 60)
        logger.info("")
        
        if successful == len(video_files):
            logger.info("=" * 60)
            logger.info("BATCH TEST PASSED ✓")
            logger.info("=" * 60)
            return 0
        else:
            logger.warning("=" * 60)
            logger.warning(f"BATCH TEST PARTIAL: {successful}/{len(video_files)} succeeded")
            logger.warning("=" * 60)
            return 1
        
    except Exception as e:
        logger.error(f"Batch test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
