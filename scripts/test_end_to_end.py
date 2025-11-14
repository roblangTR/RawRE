#!/usr/bin/env python3
"""
End-to-end test of the video news editing agent.

Tests the complete pipeline:
1. Ingest rushes (video processing, transcription, Gemini analysis)
2. Store in database with vector embeddings
3. Generate edit plan based on story brief
4. Pick shots using AI agents
5. Verify and refine selection
6. Generate EDL output

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
    """Run end-to-end test."""
    
    logger.info("=" * 80)
    logger.info("END-TO-END VIDEO NEWS EDITING AGENT TEST")
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
    
    # Target duration
    target_duration = 90  # 90 seconds
    logger.info(f"🎯 Target Duration: {target_duration} seconds")
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
    
    logger.info(f"✓ Found {len(video_files)} rushes files")
    logger.info("")
    
    # Phase 1: Ingest
    logger.info("=" * 80)
    logger.info("PHASE 1: INGEST RUSHES")
    logger.info("=" * 80)
    logger.info("")
    
    from ingest.orchestrator import IngestOrchestrator
    
    orchestrator = IngestOrchestrator(config)
    
    logger.info("Processing rushes...")
    logger.info("This will:")
    logger.info("  1. Detect shots in each video")
    logger.info("  2. Extract keyframes")
    logger.info("  3. Generate proxies")
    logger.info("  4. Transcribe audio")
    logger.info("  5. Analyze with Gemini (enhanced metadata)")
    logger.info("  6. Generate embeddings")
    logger.info("  7. Store in database")
    logger.info("")
    
    try:
        results = orchestrator.process_rushes(rushes_dir)
        
        total_shots = sum(r['shot_count'] for r in results)
        logger.info("")
        logger.info(f"✓ Ingestion complete!")
        logger.info(f"  Processed: {len(results)} videos")
        logger.info(f"  Total shots: {total_shots}")
        logger.info("")
        
    except Exception as e:
        logger.error(f"❌ Ingestion failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    # Phase 2: Plan Edit
    logger.info("=" * 80)
    logger.info("PHASE 2: PLAN EDIT")
    logger.info("=" * 80)
    logger.info("")
    
    from agent.planner import EditPlanner
    
    planner = EditPlanner(config)
    
    logger.info("Generating edit plan from story brief...")
    
    try:
        edit_plan = planner.plan_edit(
            story_brief=story_brief,
            target_duration=target_duration
        )
        
        logger.info("")
        logger.info("✓ Edit plan generated!")
        logger.info("")
        logger.info("📋 EDIT PLAN:")
        logger.info("-" * 80)
        logger.info(f"Structure: {edit_plan.get('structure', 'N/A')}")
        logger.info(f"Shot Requirements: {len(edit_plan.get('shot_requirements', []))} shots needed")
        logger.info("")
        
        for i, req in enumerate(edit_plan.get('shot_requirements', [])[:5], 1):
            logger.info(f"  {i}. {req.get('description', 'N/A')}")
            logger.info(f"     Duration: {req.get('duration', 0)}s")
            logger.info(f"     Priority: {req.get('priority', 'N/A')}")
            logger.info("")
        
        if len(edit_plan.get('shot_requirements', [])) > 5:
            logger.info(f"  ... and {len(edit_plan.get('shot_requirements', [])) - 5} more")
            logger.info("")
        
    except Exception as e:
        logger.error(f"❌ Planning failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    # Phase 3: Pick Shots
    logger.info("=" * 80)
    logger.info("PHASE 3: PICK SHOTS")
    logger.info("=" * 80)
    logger.info("")
    
    from agent.picker import ShotPicker
    from storage.database import ShotDatabase
    
    db = ShotDatabase(config)
    picker = ShotPicker(config, db)
    
    logger.info("Selecting shots based on edit plan...")
    
    try:
        selected_shots = picker.pick_shots(edit_plan)
        
        logger.info("")
        logger.info(f"✓ Shot selection complete!")
        logger.info(f"  Selected: {len(selected_shots)} shots")
        
        total_duration = sum(s.get('duration_sec', 0) for s in selected_shots)
        logger.info(f"  Total duration: {total_duration:.1f}s (target: {target_duration}s)")
        logger.info("")
        
    except Exception as e:
        logger.error(f"❌ Shot picking failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    # Phase 4: Verify Selection
    logger.info("=" * 80)
    logger.info("PHASE 4: VERIFY SELECTION")
    logger.info("=" * 80)
    logger.info("")
    
    from agent.verifier import EditVerifier
    
    verifier = EditVerifier(config)
    
    logger.info("Verifying shot selection...")
    
    try:
        verification = verifier.verify_edit(
            story_brief=story_brief,
            edit_plan=edit_plan,
            selected_shots=selected_shots
        )
        
        logger.info("")
        logger.info("✓ Verification complete!")
        logger.info("")
        logger.info("📊 VERIFICATION RESULTS:")
        logger.info("-" * 80)
        logger.info(f"Overall Quality: {verification.get('overall_quality', 'N/A')}")
        logger.info(f"Story Coverage: {verification.get('story_coverage', 'N/A')}")
        logger.info(f"Pacing: {verification.get('pacing', 'N/A')}")
        logger.info(f"Recommendations: {len(verification.get('recommendations', []))}")
        logger.info("")
        
    except Exception as e:
        logger.error(f"❌ Verification failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    # Phase 5: Generate EDL
    logger.info("=" * 80)
    logger.info("PHASE 5: GENERATE EDL")
    logger.info("=" * 80)
    logger.info("")
    
    from output.edl_writer import EDLWriter
    
    edl_writer = EDLWriter(config)
    
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)
    
    edl_path = output_dir / "gallipoli_burial_edit.edl"
    
    logger.info(f"Generating EDL: {edl_path}")
    
    try:
        edl_writer.write_edl(
            selected_shots=selected_shots,
            output_path=edl_path,
            title="Gallipoli Burial Ceremony"
        )
        
        logger.info("")
        logger.info(f"✓ EDL generated: {edl_path}")
        logger.info("")
        
    except Exception as e:
        logger.error(f"❌ EDL generation failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    # Summary
    logger.info("=" * 80)
    logger.info("END-TO-END TEST COMPLETE ✓")
    logger.info("=" * 80)
    logger.info("")
    logger.info("📊 SUMMARY:")
    logger.info(f"  Rushes processed: {len(results)} videos")
    logger.info(f"  Total shots detected: {total_shots}")
    logger.info(f"  Shots selected: {len(selected_shots)}")
    logger.info(f"  Edit duration: {total_duration:.1f}s / {target_duration}s")
    logger.info(f"  EDL output: {edl_path}")
    logger.info("")
    logger.info("🎬 The video news editing agent successfully:")
    logger.info("  ✓ Ingested and analyzed rushes with Gemini")
    logger.info("  ✓ Generated an edit plan from story brief")
    logger.info("  ✓ Selected appropriate shots using AI")
    logger.info("  ✓ Verified the edit quality")
    logger.info("  ✓ Generated EDL for editing software")
    logger.info("")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
