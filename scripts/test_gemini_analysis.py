#!/usr/bin/env python3
"""
Test script for Gemini video analysis
Analyzes a single video file from Test_Rushes folder
"""

import sys
import yaml
import json
import logging
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    """Test Gemini analysis on a single video file"""
    
    # Load config
    logger.info("Loading configuration...")
    with open('config.yaml') as f:
        config = yaml.safe_load(f)
    
    # Check if Gemini is enabled
    if not config.get('gemini', {}).get('enabled', False):
        logger.error("Gemini is not enabled in config.yaml")
        logger.info("Set gemini.enabled to true in config.yaml")
        return 1
    
    # Import after config check
    from ingest.gemini_analyzer import GeminiAnalyzer
    
    # Test video file (using smallest one for quick test)
    test_video = Path('/Users/lng3369/Documents/Claude/RAWRE/Test_Rushes/VID_20220424_103723.mp4')
    
    if not test_video.exists():
        logger.error(f"Test video not found: {test_video}")
        return 1
    
    logger.info(f"Test video: {test_video.name}")
    logger.info(f"File size: {test_video.stat().st_size / 1024 / 1024:.2f} MB")
    
    # Initialize Gemini analyzer
    logger.info("\n" + "="*60)
    logger.info("Initializing Gemini analyzer...")
    logger.info("="*60)
    
    try:
        analyzer = GeminiAnalyzer(config)
        
        if not analyzer.enabled:
            logger.error("Gemini analyzer failed to initialize")
            return 1
        
        logger.info("✓ Gemini analyzer initialized successfully")
        
    except Exception as e:
        logger.error(f"Failed to initialize Gemini analyzer: {e}")
        logger.exception("Full traceback:")
        return 1
    
    # Prepare shot data (analyzing entire video as one shot)
    shot_data = {
        'tc_in': '00:00:00:00',
        'tc_out': '00:00:10:00',  # First 10 seconds
        'duration_ms': 10000
    }
    
    # Analyze the video
    logger.info("\n" + "="*60)
    logger.info("Analyzing video with Gemini...")
    logger.info("="*60)
    logger.info("This may take 5-10 seconds...")
    
    try:
        result = analyzer.analyze_shot(
            video_path=str(test_video),
            shot_data=shot_data
        )
        
        if result:
            logger.info("\n" + "="*60)
            logger.info("✓ ANALYSIS SUCCESSFUL!")
            logger.info("="*60)
            
            # Pretty print results
            logger.info("\nGemini Analysis Results:")
            logger.info("-" * 60)
            
            # Key fields
            logger.info(f"\n📝 Description:")
            logger.info(f"   {result.get('enhanced_description', 'N/A')}")
            
            logger.info(f"\n🎬 Shot Type: {result.get('shot_type', 'N/A')}")
            logger.info(f"📐 Shot Size: {result.get('shot_size', 'N/A')}")
            logger.info(f"🎥 Camera Movement: {result.get('camera_movement', 'N/A')}")
            
            logger.info(f"\n🖼️  Composition:")
            logger.info(f"   {result.get('composition', 'N/A')}")
            
            logger.info(f"\n💡 Lighting:")
            logger.info(f"   {result.get('lighting', 'N/A')}")
            
            subjects = result.get('primary_subjects', [])
            if subjects:
                logger.info(f"\n👥 Primary Subjects:")
                for subject in subjects:
                    logger.info(f"   - {subject}")
            
            logger.info(f"\n🎭 Action:")
            logger.info(f"   {result.get('action_description', 'N/A')}")
            
            logger.info(f"\n⭐ Visual Quality: {result.get('visual_quality', 'N/A')}")
            logger.info(f"📰 News Context: {result.get('news_context', 'N/A')}")
            logger.info(f"🎨 Tone: {result.get('tone', 'N/A')}")
            logger.info(f"🎯 Confidence: {result.get('confidence', 'N/A')}")
            
            # Save full result to JSON
            output_file = Path('gemini_test_result.json')
            with open(output_file, 'w') as f:
                json.dump(result, f, indent=2)
            
            logger.info(f"\n💾 Full results saved to: {output_file}")
            logger.info("\n" + "="*60)
            logger.info("TEST PASSED ✓")
            logger.info("="*60)
            
            return 0
            
        else:
            logger.error("\n✗ Analysis returned no results")
            return 1
            
    except Exception as e:
        logger.error(f"\n✗ Analysis failed: {e}")
        logger.exception("Full traceback:")
        return 1

if __name__ == '__main__':
    sys.exit(main())
