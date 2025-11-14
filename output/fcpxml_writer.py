"""
FCPXML Writer

Generates Final Cut Pro X XML files from agent selections.
"""

import logging
from typing import Dict, List, Optional
from pathlib import Path
from xml.etree import ElementTree as ET
from xml.dom import minidom

logger = logging.getLogger(__name__)


class FCPXMLWriter:
    """Writes Final Cut Pro X XML files."""
    
    def __init__(self, project_name: str = "Untitled Project", frame_rate: str = "25p"):
        """
        Initialize FCPXML writer.
        
        Args:
            project_name: Project name
            frame_rate: Frame rate (e.g., "25p", "30p", "24p")
        """
        self.project_name = project_name
        self.frame_rate = frame_rate
        self.frame_duration = self._get_frame_duration(frame_rate)
        
        logger.info(f"[FCPXML] Initialized: {project_name} @ {frame_rate}")
    
    def _get_frame_duration(self, frame_rate: str) -> str:
        """Get frame duration for given frame rate."""
        rate_map = {
            "24p": "1001/24000s",
            "25p": "1/25s",
            "30p": "1001/30000s",
            "50p": "1/50s",
            "60p": "1001/60000s"
        }
        return rate_map.get(frame_rate, "1/25s")
    
    def write_fcpxml(self,
                     selections: Dict,
                     output_path: str,
                     media_path: Optional[str] = None) -> str:
        """
        Write FCPXML file from agent selections.
        
        Args:
            selections: Agent picker selections dictionary
            output_path: Path to write FCPXML file
            media_path: Optional base path for media files
            
        Returns:
            Path to written FCPXML file
        """
        logger.info(f"[FCPXML] Writing FCPXML to {output_path}")
        
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Create root element
        fcpxml = ET.Element('fcpxml', version="1.9")
        
        # Add resources
        resources = ET.SubElement(fcpxml, 'resources')
        
        # Add format
        format_elem = ET.SubElement(
            resources,
            'format',
            id="r1",
            name="FFVideoFormat1080p25",
            frameDuration=self.frame_duration,
            width="1920",
            height="1080"
        )
        
        # Track unique clips for resources
        clip_resources = {}
        resource_id = 2
        
        # Create library and event
        library = ET.SubElement(fcpxml, 'library')
        event = ET.SubElement(library, 'event', name=self.project_name)
        
        # Create project
        project = ET.SubElement(
            event,
            'project',
            name=self.project_name
        )
        
        # Create sequence
        sequence = ET.SubElement(
            project,
            'sequence',
            format="r1",
            duration=f"{self._seconds_to_frames(selections.get('total_duration', 0))}/25s"
        )
        
        # Create spine (main timeline)
        spine = ET.SubElement(sequence, 'spine')
        
        # Process beats and shots
        for beat in selections.get('beats', []):
            beat_name = beat.get('beat_name', 'UNKNOWN')
            logger.info(f"[FCPXML] Processing beat: {beat_name}")
            
            for shot in beat.get('shots', []):
                shot_id = shot.get('shot_id')
                duration = shot.get('duration', 0)
                file_path = shot.get('file_path', '')
                
                # Add clip resource if not already added
                if shot_id not in clip_resources:
                    clip_resource_id = f"r{resource_id}"
                    resource_id += 1
                    
                    # Determine media path
                    if media_path:
                        full_path = str(Path(media_path) / file_path)
                    else:
                        full_path = file_path
                    
                    # Add asset resource
                    asset = ET.SubElement(
                        resources,
                        'asset',
                        id=clip_resource_id,
                        name=Path(file_path).stem if file_path else shot_id,
                        src=f"file://{full_path}",
                        duration=f"{self._seconds_to_frames(duration)}/25s",
                        format="r1"
                    )
                    
                    # Add metadata
                    metadata = ET.SubElement(asset, 'metadata')
                    md_shot_id = ET.SubElement(
                        metadata,
                        'md',
                        key="com.apple.proapps.studio.shotID",
                        value=shot_id
                    )
                    md_beat = ET.SubElement(
                        metadata,
                        'md',
                        key="com.apple.proapps.studio.beat",
                        value=beat_name
                    )
                    
                    clip_resources[shot_id] = clip_resource_id
                
                # Add clip to spine
                clip_ref = clip_resources[shot_id]
                start_time = shot.get('start_time', 0)
                
                clip_elem = ET.SubElement(
                    spine,
                    'asset-clip',
                    ref=clip_ref,
                    offset=f"{self._seconds_to_frames(start_time)}/25s",
                    name=Path(file_path).stem if file_path else shot_id,
                    duration=f"{self._seconds_to_frames(duration)}/25s",
                    format="r1"
                )
                
                # Add note with reasoning
                reasoning = shot.get('reasoning', '')
                if reasoning:
                    note = ET.SubElement(clip_elem, 'note')
                    note.text = reasoning
        
        # Pretty print XML
        xml_str = self._prettify_xml(fcpxml)
        
        # Write file
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(xml_str)
        
        logger.info(f"[FCPXML] ✓ Wrote FCPXML to {output_path}")
        logger.info(f"[FCPXML] Total clips: {len(clip_resources)}")
        
        return str(output_file)
    
    def _seconds_to_frames(self, seconds: float) -> int:
        """Convert seconds to frame count."""
        # Extract frame rate number from string like "25p"
        fps = int(self.frame_rate.rstrip('p'))
        return int(seconds * fps)
    
    def _prettify_xml(self, elem: ET.Element) -> str:
        """Return a pretty-printed XML string."""
        rough_string = ET.tostring(elem, encoding='unicode')
        reparsed = minidom.parseString(rough_string)
        return reparsed.toprettyxml(indent="  ")
    
    def write_from_result(self,
                         result: Dict,
                         output_path: str,
                         media_path: Optional[str] = None) -> str:
        """
        Write FCPXML from orchestrator result.
        
        Args:
            result: Orchestrator compile_edit result
            output_path: Path to write FCPXML file
            media_path: Optional base path for media files
            
        Returns:
            Path to written FCPXML file
        """
        selections = result.get('final_selections')
        if not selections:
            raise ValueError("No final selections in result")
        
        # Update project name from story slug
        story_slug = result.get('story_slug', 'Untitled Project')
        self.project_name = story_slug.replace('-', ' ').title()
        
        return self.write_fcpxml(selections, output_path, media_path)
    
    def validate_fcpxml(self, fcpxml_path: str) -> Dict:
        """
        Validate an FCPXML file.
        
        Args:
            fcpxml_path: Path to FCPXML file
            
        Returns:
            Validation report dictionary
        """
        logger.info(f"[FCPXML] Validating {fcpxml_path}")
        
        report = {
            'valid': True,
            'errors': [],
            'warnings': [],
            'clip_count': 0,
            'resource_count': 0
        }
        
        try:
            tree = ET.parse(fcpxml_path)
            root = tree.getroot()
            
            # Check root element
            if root.tag != 'fcpxml':
                report['errors'].append("Root element is not 'fcpxml'")
                report['valid'] = False
            
            # Count resources
            resources = root.find('resources')
            if resources is not None:
                report['resource_count'] = len(list(resources))
            else:
                report['warnings'].append("No resources section found")
            
            # Count clips in spine
            spine = root.find('.//spine')
            if spine is not None:
                clips = spine.findall('.//*[@ref]')
                report['clip_count'] = len(clips)
            else:
                report['errors'].append("No spine found in project")
                report['valid'] = False
            
            if report['clip_count'] == 0:
                report['warnings'].append("No clips found in timeline")
            
            logger.info(f"[FCPXML] Validation: {'✓ PASS' if report['valid'] else '✗ FAIL'}")
            logger.info(f"[FCPXML] Resources: {report['resource_count']}, Clips: {report['clip_count']}")
            
        except ET.ParseError as e:
            report['valid'] = False
            report['errors'].append(f"XML parse error: {e}")
            logger.error(f"[FCPXML] Validation failed: {e}")
        except Exception as e:
            report['valid'] = False
            report['errors'].append(f"Validation error: {e}")
            logger.error(f"[FCPXML] Validation failed: {e}")
        
        return report
