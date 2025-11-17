#!/usr/bin/env python3
"""
Export FCPXML and EDL from test result JSON

This script reads the JSON result from the integrated test and properly
exports FCPXML and EDL files.
"""

import sys
import json
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from output.fcpxml_writer import FCPXMLWriter
from output.edl_writer import EDLWriter


def convert_result_to_selections(result: dict) -> dict:
    """
    Convert orchestrator result format to the format expected by writers.
    
    The orchestrator result has:
    - final_selections with beat_selections
    - Each beat has shots with full_data nested
    
    Writers expect:
    - beats with shots at top level
    - Fields like file_path, duration, start_time directly accessible
    """
    final_selections = result.get('final_selections', {})
    beat_selections = final_selections.get('beat_selections', [])
    
    converted_beats = []
    cumulative_time = 0.0
    
    for beat_sel in beat_selections:
        beat_info = beat_sel.get('beat', {})
        shots = beat_sel.get('shots', [])
        
        converted_shots = []
        for shot in shots:
            # Get full data
            full_data = shot.get('full_data', {})
            
            # Calculate duration in seconds
            duration_ms = full_data.get('duration_ms', 0)
            duration_s = duration_ms / 1000.0
            
            # Build converted shot
            converted_shot = {
                'shot_id': str(full_data.get('shot_id', 'unknown')),
                'file_path': full_data.get('filepath', ''),
                'duration': duration_s,
                'start_time': cumulative_time,
                'trim_in': shot.get('trim_in', full_data.get('tc_in', '00:00:00:00')),
                'trim_out': shot.get('trim_out', full_data.get('tc_out', '00:00:00:00')),
                'reasoning': shot.get('reason', ''),
                'beat_name': beat_info.get('title', 'Unknown Beat')
            }
            
            converted_shots.append(converted_shot)
            cumulative_time += duration_s
        
        converted_beat = {
            'beat_number': beat_info.get('beat_number', 0),
            'beat_name': beat_info.get('title', 'Unknown Beat'),
            'shots': converted_shots
        }
        
        converted_beats.append(converted_beat)
    
    return {
        'story_slug': result.get('story_slug', 'unknown'),
        'total_duration': final_selections.get('total_duration', 0),
        'total_shots': final_selections.get('total_shots', 0),
        'beats': converted_beats
    }


def main():
    """Export FCPXML and EDL from result JSON."""
    
    # Use the working result file (not the one with numpy arrays)
    output_dir = Path("./output")
    result_file = output_dir / "gallipoli_burial_2022_result.json"
    
    if not result_file.exists():
        print(f"✗ Result file not found: {result_file}")
        return 1
    
    print(f"Reading result from: {result_file}")
    
    # Load result
    with open(result_file) as f:
        result = json.load(f)
    
    print(f"Story: {result.get('story_slug')}")
    print(f"Iterations: {len(result.get('iterations', []))}")
    print(f"Approved: {result.get('approved', False)}")
    
    # Convert to format expected by writers
    print("\nConverting result format...")
    selections = convert_result_to_selections(result)
    
    print(f"Converted {len(selections['beats'])} beats")
    print(f"Total shots: {selections['total_shots']}")
    print(f"Total duration: {selections['total_duration']:.1f}s")
    
    # Generate timestamp for output files
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    story_slug = result.get('story_slug', 'unknown')
    
    # Export FCPXML
    print("\n" + "=" * 60)
    print("EXPORTING FCPXML")
    print("=" * 60)
    
    try:
        fcpxml_writer = FCPXMLWriter(
            project_name=story_slug.replace('_', ' ').title(),
            frame_rate="25p"
        )
        
        fcpxml_path = output_dir / f"{story_slug}_{timestamp}.fcpxml"
        
        # Use the converted selections
        fcpxml_writer.write_fcpxml(
            selections=selections,
            output_path=str(fcpxml_path),
            media_path=str(Path.cwd() / "Test_Rushes")
        )
        
        print(f"✓ FCPXML exported: {fcpxml_path}")
        
        # Validate
        validation = fcpxml_writer.validate_fcpxml(str(fcpxml_path))
        if validation['valid']:
            print(f"✓ FCPXML validation passed")
            print(f"  - Resources: {validation['resource_count']}")
            print(f"  - Clips: {validation['clip_count']}")
        else:
            print(f"⚠ FCPXML validation issues:")
            for error in validation['errors']:
                print(f"  - ERROR: {error}")
            for warning in validation['warnings']:
                print(f"  - WARNING: {warning}")
        
    except Exception as e:
        print(f"✗ FCPXML export failed: {e}")
        import traceback
        traceback.print_exc()
    
    # Export EDL
    print("\n" + "=" * 60)
    print("EXPORTING EDL")
    print("=" * 60)
    
    try:
        edl_writer = EDLWriter(
            title=story_slug.replace('_', ' ').title(),
            frame_rate=25.0
        )
        
        edl_path = output_dir / f"{story_slug}_{timestamp}.edl"
        
        # Use the converted selections
        edl_writer.write_edl(
            selections=selections,
            output_path=str(edl_path)
        )
        
        print(f"✓ EDL exported: {edl_path}")
        
        # Validate
        validation = edl_writer.validate_edl(str(edl_path))
        if validation['valid']:
            print(f"✓ EDL validation passed")
            print(f"  - Events: {validation['event_count']}")
        else:
            print(f"⚠ EDL validation issues:")
            for error in validation['errors']:
                print(f"  - ERROR: {error}")
            for warning in validation['warnings']:
                print(f"  - WARNING: {warning}")
        
    except Exception as e:
        print(f"✗ EDL export failed: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 60)
    print("EXPORT COMPLETE")
    print("=" * 60)
    print(f"\nFiles exported to: {output_dir}")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
