"""
EDL Writer

Generates CMX 3600 format Edit Decision Lists from agent selections.
"""

import logging
from typing import Dict, List, Optional
from pathlib import Path
from datetime import timedelta

logger = logging.getLogger(__name__)


class EDLWriter:
    """Writes CMX 3600 format EDL files."""
    
    def __init__(self, title: str = "UNTITLED", frame_rate: float = 25.0):
        """
        Initialize EDL writer.
        
        Args:
            title: Edit title
            frame_rate: Frame rate (default 25fps for PAL)
        """
        self.title = title
        self.frame_rate = frame_rate
        self.drop_frame = False  # Non-drop frame timecode
        
        logger.info(f"[EDL] Initialized: {title} @ {frame_rate}fps")
    
    def write_edl(self,
                  selections: Dict,
                  output_path: str,
                  reel_name: str = "AX") -> str:
        """
        Write EDL file from agent selections.
        
        Args:
            selections: Agent picker selections dictionary
            output_path: Path to write EDL file
            reel_name: Reel name for source clips
            
        Returns:
            Path to written EDL file
        """
        logger.info(f"[EDL] Writing EDL to {output_path}")
        
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Build EDL content
        edl_lines = []
        
        # Header
        edl_lines.append(f"TITLE: {self.title}")
        edl_lines.append(f"FCM: {'DROP FRAME' if self.drop_frame else 'NON-DROP FRAME'}")
        edl_lines.append("")
        
        # Process beats and shots
        record_tc = 0.0  # Running record timecode in seconds
        event_num = 1
        
        for beat in selections.get('beats', []):
            beat_name = beat.get('beat_name', 'UNKNOWN')
            logger.info(f"[EDL] Processing beat: {beat_name}")
            
            for shot in beat.get('shots', []):
                shot_id = shot.get('shot_id')
                duration = shot.get('duration', 0)
                
                # Source timecodes (from shot metadata)
                source_in = shot.get('start_time', 0)
                source_out = source_in + duration
                
                # Record timecodes (running timeline)
                record_in = record_tc
                record_out = record_tc + duration
                
                # Format timecodes
                source_in_tc = self._seconds_to_timecode(source_in)
                source_out_tc = self._seconds_to_timecode(source_out)
                record_in_tc = self._seconds_to_timecode(record_in)
                record_out_tc = self._seconds_to_timecode(record_out)
                
                # EDL event line
                # Format: EVENT# REEL TRACK EDIT_TYPE [TRANSITION] SOURCE_IN SOURCE_OUT RECORD_IN RECORD_OUT
                event_line = (
                    f"{event_num:03d}  {reel_name}       V     C        "
                    f"{source_in_tc} {source_out_tc} {record_in_tc} {record_out_tc}"
                )
                edl_lines.append(event_line)
                
                # Comment with shot info
                clip_name = shot.get('file_path', shot_id)
                if isinstance(clip_name, str):
                    clip_name = Path(clip_name).stem
                edl_lines.append(f"* FROM CLIP NAME: {clip_name}")
                edl_lines.append(f"* SHOT_ID: {shot_id}")
                edl_lines.append(f"* BEAT: {beat_name}")
                
                # Add reasoning as comment if available
                reasoning = shot.get('reasoning', '')
                if reasoning:
                    # Truncate long reasoning
                    if len(reasoning) > 60:
                        reasoning = reasoning[:57] + "..."
                    edl_lines.append(f"* REASON: {reasoning}")
                
                edl_lines.append("")
                
                # Update counters
                record_tc = record_out
                event_num += 1
        
        # Write file
        with open(output_file, 'w') as f:
            f.write('\n'.join(edl_lines))
        
        logger.info(f"[EDL] ✓ Wrote {event_num - 1} events to {output_path}")
        logger.info(f"[EDL] Total duration: {self._seconds_to_timecode(record_tc)}")
        
        return str(output_file)
    
    def _seconds_to_timecode(self, seconds: float) -> str:
        """
        Convert seconds to timecode string.
        
        Args:
            seconds: Time in seconds
            
        Returns:
            Timecode string (HH:MM:SS:FF)
        """
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        frames = int((seconds % 1) * self.frame_rate)
        
        separator = ';' if self.drop_frame else ':'
        return f"{hours:02d}:{minutes:02d}:{secs:02d}{separator}{frames:02d}"
    
    def _timecode_to_seconds(self, timecode: str) -> float:
        """
        Convert timecode string to seconds.
        
        Args:
            timecode: Timecode string (HH:MM:SS:FF or HH:MM:SS;FF)
            
        Returns:
            Time in seconds
        """
        # Remove drop frame separator if present
        timecode = timecode.replace(';', ':')
        
        parts = timecode.split(':')
        if len(parts) != 4:
            raise ValueError(f"Invalid timecode format: {timecode}")
        
        hours, minutes, seconds, frames = map(int, parts)
        
        total_seconds = (
            hours * 3600 +
            minutes * 60 +
            seconds +
            frames / self.frame_rate
        )
        
        return total_seconds
    
    def write_from_result(self,
                         result: Dict,
                         output_path: str,
                         reel_name: str = "AX") -> str:
        """
        Write EDL from orchestrator result.
        
        Args:
            result: Orchestrator compile_edit result
            output_path: Path to write EDL file
            reel_name: Reel name for source clips
            
        Returns:
            Path to written EDL file
        """
        selections = result.get('final_selections')
        if not selections:
            raise ValueError("No final selections in result")
        
        # Update title from story slug
        story_slug = result.get('story_slug', 'UNTITLED')
        self.title = story_slug.upper().replace('-', '_')
        
        return self.write_edl(selections, output_path, reel_name)
    
    def validate_edl(self, edl_path: str) -> Dict:
        """
        Validate an EDL file.
        
        Args:
            edl_path: Path to EDL file
            
        Returns:
            Validation report dictionary
        """
        logger.info(f"[EDL] Validating {edl_path}")
        
        report = {
            'valid': True,
            'errors': [],
            'warnings': [],
            'event_count': 0,
            'total_duration': 0.0
        }
        
        try:
            with open(edl_path, 'r') as f:
                lines = f.readlines()
            
            event_count = 0
            last_record_out = 0.0
            
            for i, line in enumerate(lines, 1):
                line = line.strip()
                
                # Skip empty lines and comments
                if not line or line.startswith('*') or line.startswith('TITLE') or line.startswith('FCM'):
                    continue
                
                # Parse event line
                parts = line.split()
                if len(parts) >= 8:
                    try:
                        event_num = int(parts[0])
                        record_out_tc = parts[7]
                        record_out = self._timecode_to_seconds(record_out_tc)
                        
                        event_count += 1
                        last_record_out = record_out
                        
                    except (ValueError, IndexError) as e:
                        report['errors'].append(f"Line {i}: Invalid event format - {e}")
                        report['valid'] = False
            
            report['event_count'] = event_count
            report['total_duration'] = last_record_out
            
            if event_count == 0:
                report['errors'].append("No events found in EDL")
                report['valid'] = False
            
            logger.info(f"[EDL] Validation: {'✓ PASS' if report['valid'] else '✗ FAIL'}")
            logger.info(f"[EDL] Events: {event_count}, Duration: {self._seconds_to_timecode(last_record_out)}")
            
        except Exception as e:
            report['valid'] = False
            report['errors'].append(f"Failed to read EDL: {e}")
            logger.error(f"[EDL] Validation failed: {e}")
        
        return report
