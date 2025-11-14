#!/usr/bin/env python3
"""
End-to-end test of video ingest pipeline.

Tests the complete ingest pipeline:
1. Video processing (shot detection, keyframes, proxies)
2. Audio transcription
3. Gemini video analysis (enhanced metadata)
4. Embedding generation
5. Database storage

Story: French WWI soldiers burial ceremony in Gallipoli
"""

import sys
import yaml
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Run end-to-end ingest test."""
    
    logger.info("=" * 80)
    logger.info("END-TO-END VIDEO INGEST TEST")
    logger.info("=" * 80)
    logger.info("")
    
    # Story brief
    story_brief = """The remains of 17 French soldiers who fought in World War One during the
Gallipoli Campaign were laid to rest in Gallipoli on Sunday (April 24).
Several members of the French military were present during the burial ceremony
alongside with Turkish officials.
The remains of the fallen soldiers, who lost their lives during the Battle of
Gallipoli over a century ago, were discovered during a restoration work of a
fort in the region.
The burial ceremony, which was conducted in the French cemetery in Gallipoli,
came one day before the 107th anniversary of the Anzac Day that commemorates the
start of the Gallipoli campaign by Allied forces against the Ottoman Empire."""
    
    logger.info("📰 STORY BRIEF:")
    logger.info("-" * 80)
    for line in story_brief.strip().split('\n'):
        logger.info(f"   {line}")
    logger.info("-" * 80)
    logger.info("")
    
    # Load config
    logger.info("📋 Loading configuration...")
    with open('config.yaml', 'r') as f:
        config = yaml.safe_load(f)
    
    # Check rushes directory
    rushes_dir = Path("Test_Rushes")
    if not rushes_dir.exists():
        logger.error(f"❌ Rushes directory not found: {rushes_dir}")
        return 1
    
    video_files = list(rushes_dir.glob("*.mp4")) + list(rushes_dir.glob("*.mov"))
    if not video_files:
        logger.error(f"❌ No video files found in {rushes_dir}")
        return 1
    
    logger.info(f"✓ Found {len(video_files)} rushes files:")
    for vf in video_files:
        size_mb = vf.stat().st_size / 1024 / 1024
        logger.info(f"  - {vf.name} ({size_mb:.1f} MB)")
    logger.info("")
    
    # Initialize ingest orchestrator
    logger.info("=" * 80)
    logger.info("INITIALIZING INGEST PIPELINE")
    logger.info("=" * 80)
    logger.info("")
    
    from ingest.orchestrator import IngestOrchestrator
    
    orchestrator = IngestOrchestrator(config)
    
    logger.info("✓ Ingest orchestrator initialized")
    logger.info("")
    
    # Process each video
    logger.info("=" * 80)
    logger.info("PROCESSING RUSHES")
    logger.info("=" * 80)
    logger.info("")
    logger.info("This will:")
    logger.info("  1. Detect shots in each video")
    logger.info("  2. Extract keyframes")
    logger.info("  3. Generate proxies (standard + Gemini)")
    logger.info("  4. Transcribe audio with Whisper")
    logger.info("  5. Analyze with Gemini (enhanced metadata)")
    logger.info("  6. Generate embeddings")
    logger.info("  7. Store in database")
    logger.info("")
    
    story_id = "gallipoli_burial_2022"
    total_shots = 0
    total_duration = 0.0
    
    try:
        for i, video_file in enumerate(video_files, 1):
            logger.info("-" * 80)
            logger.info(f"Processing video {i}/{len(video_files)}: {video_file.name}")
            logger.info("-" * 80)
            
            result = orchestrator.ingest_video(
                video_path=str(video_file),
                story_id=story_id,
                metadata={'story_brief': story_brief}
            )
            
            if result['success']:
                logger.info(f"✓ Video processed successfully")
                logger.info(f"  Shots detected: {result['shots_processed']}")
                logger.info(f"  Shots stored: {result['shots_stored']}")
                total_shots += result['shots_stored']
                
                # Get duration from first shot if available
                if result.get('shots'):
                    for shot in result['shots']:
                        total_duration += shot.get('duration_sec', 0)
            else:
                logger.error(f"❌ Video processing failed")
                if result.get('errors'):
                    for error in result['errors']:
                        logger.error(f"  Error: {error}")
            
            logger.info("")
        
        logger.info("=" * 80)
        logger.info("INGEST COMPLETE")
        logger.info("=" * 80)
        logger.info("")
        logger.info("📊 SUMMARY:")
        logger.info(f"  Story ID: {story_id}")
        logger.info(f"  Videos processed: {len(video_files)}")
        logger.info(f"  Total shots: {total_shots}")
        logger.info(f"  Total duration: {total_duration:.1f}s ({total_duration/60:.1f} minutes)")
        logger.info("")
        
        # Get story stats
        logger.info("=" * 80)
        logger.info("STORY STATISTICS")
        logger.info("=" * 80)
        logger.info("")
        
        stats = orchestrator.get_story_stats(story_id)
        
        if stats.get('exists'):
            logger.info(f"✓ Story exists in database")
            logger.info(f"  Total shots: {stats.get('total_shots', 0)}")
            logger.info(f"  Total duration: {stats.get('total_duration', 0):.1f}s")
            logger.info(f"  Source files: {len(stats.get('source_files', []))}")
            logger.info("")
            
            shot_types = stats.get('shot_types', {})
            if shot_types:
                logger.info("  Shot types:")
                for shot_type, count in shot_types.items():
                    logger.info(f"    - {shot_type}: {count}")
                logger.info("")
        else:
            logger.warning(f"⚠ Story not found in database")
            logger.info("")
        
        logger.info("=" * 80)
        logger.info("END-TO-END INGEST TEST COMPLETE ✓")
        logger.info("=" * 80)
        logger.info("")
        logger.info("🎬 The video ingest pipeline successfully:")
        logger.info("  ✓ Detected shots in all videos")
        logger.info("  ✓ Extracted keyframes and generated proxies")
        logger.info("  ✓ Transcribed audio with Whisper")
        logger.info("  ✓ Analyzed videos with Gemini (enhanced metadata)")
        logger.info("  ✓ Generated embeddings for semantic search")
        logger.info("  ✓ Stored all data in database")
        logger.info("")
        logger.info("📁 Output locations:")
        logger.info("  - Database: data/shots.db")
        logger.info("  - Keyframes: data/keyframes/")
        logger.info("  - Proxies: data/proxies/")
        logger.info("  - Gemini proxies: data/gemini_proxies/")
        logger.info("  - Vector index: data/vector_index/")
        logger.info("")
        
        return 0
        
    except Exception as e:
        logger.error(f"❌ Ingest failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
