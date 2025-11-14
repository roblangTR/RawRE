"""Video processing: shot detection, keyframe extraction, proxy generation."""

import cv2
import numpy as np
from pathlib import Path
from typing import List, Tuple, Dict, Any, Optional
from dataclasses import dataclass
import subprocess
import json
from datetime import datetime
from PIL import Image


@dataclass
class Shot:
    """Represents a detected shot."""
    start_frame: int
    end_frame: int
    start_time: float
    end_time: float
    duration: float
    keyframe_path: Optional[str] = None


class VideoProcessor:
    """Processes video files to detect shots and extract metadata."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.shot_threshold = config['video']['shot_detection']['threshold']
        self.min_shot_duration = config['video']['shot_detection']['min_shot_duration_sec']
        self.keyframe_count = config['video']['keyframes']['count']
        self.proxy_enabled = config['video']['proxy']['enabled']
    
    def get_video_metadata(self, video_path: Path) -> Dict[str, Any]:
        """Extract video metadata using ffprobe."""
        cmd = [
            'ffprobe',
            '-v', 'quiet',
            '-print_format', 'json',
            '-show_format',
            '-show_streams',
            str(video_path)
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        metadata = json.loads(result.stdout)
        
        # Find video stream
        video_stream = None
        for stream in metadata.get('streams', []):
            if stream.get('codec_type') == 'video':
                video_stream = stream
                break
        
        if not video_stream:
            raise ValueError(f"No video stream found in {video_path}")
        
        # Extract key info
        fps_parts = video_stream.get('r_frame_rate', '25/1').split('/')
        fps = float(fps_parts[0]) / float(fps_parts[1])
        
        duration = float(video_stream.get('duration', 0))
        if duration == 0 and 'format' in metadata:
            duration = float(metadata['format'].get('duration', 0))
        
        # Try to get creation time
        creation_time = None
        if 'format' in metadata and 'tags' in metadata['format']:
            creation_str = metadata['format']['tags'].get('creation_time')
            if creation_str:
                try:
                    creation_time = datetime.fromisoformat(creation_str.replace('Z', '+00:00'))
                except:
                    pass
        
        # Fallback to file modification time
        if not creation_time:
            creation_time = datetime.fromtimestamp(video_path.stat().st_mtime)
        
        return {
            'fps': fps,
            'duration': duration,
            'width': int(video_stream.get('width', 0)),
            'height': int(video_stream.get('height', 0)),
            'creation_time': creation_time,
            'codec': video_stream.get('codec_name', 'unknown')
        }
    
    def detect_shots_histogram(self, video_path: Path) -> List[Shot]:
        """
        Detect shots using histogram comparison.
        
        Uses HSV color histogram to detect hard cuts between frames.
        """
        cap = cv2.VideoCapture(str(video_path))
        
        if not cap.isOpened():
            raise ValueError(f"Cannot open video: {video_path}")
        
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        
        shots = []
        prev_hist = None
        shot_start_frame = 0
        frame_idx = 0
        
        print(f"Processing {total_frames} frames at {fps} fps...")
        
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            # Convert to HSV for better color representation
            hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
            
            # Calculate histogram
            hist = cv2.calcHist([hsv], [0, 1], None, [50, 60], [0, 180, 0, 256])
            hist = cv2.normalize(hist, hist).flatten()
            
            # Compare with previous frame
            if prev_hist is not None:
                # Use correlation coefficient
                correlation = cv2.compareHist(prev_hist, hist, cv2.HISTCMP_CORREL)
                difference = 1.0 - correlation
                
                # Detect shot boundary
                if difference > self.shot_threshold:
                    # End previous shot
                    shot_end_frame = frame_idx - 1
                    shot_start_time = shot_start_frame / fps
                    shot_end_time = shot_end_frame / fps
                    shot_duration = shot_end_time - shot_start_time
                    
                    # Only add if meets minimum duration
                    if shot_duration >= self.min_shot_duration:
                        shots.append(Shot(
                            start_frame=shot_start_frame,
                            end_frame=shot_end_frame,
                            start_time=shot_start_time,
                            end_time=shot_end_time,
                            duration=shot_duration
                        ))
                    
                    # Start new shot
                    shot_start_frame = frame_idx
            
            prev_hist = hist
            frame_idx += 1
            
            # Progress indicator
            if frame_idx % 100 == 0:
                print(f"  Processed {frame_idx}/{total_frames} frames ({len(shots)} shots detected)")
        
        # Add final shot
        if shot_start_frame < frame_idx:
            shot_end_frame = frame_idx - 1
            shot_start_time = shot_start_frame / fps
            shot_end_time = shot_end_frame / fps
            shot_duration = shot_end_time - shot_start_time
            
            if shot_duration >= self.min_shot_duration:
                shots.append(Shot(
                    start_frame=shot_start_frame,
                    end_frame=shot_end_frame,
                    start_time=shot_start_time,
                    end_time=shot_end_time,
                    duration=shot_duration
                ))
        
        cap.release()
        
        print(f"Detected {len(shots)} shots")
        return shots
    
    def extract_keyframe(self, video_path: Path, shot: Shot, output_dir: Path) -> str:
        """Extract keyframe from middle of shot."""
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Use middle frame
        middle_frame = (shot.start_frame + shot.end_frame) // 2
        middle_time = middle_frame / self.get_video_metadata(video_path)['fps']
        
        # Generate output filename
        output_path = output_dir / f"keyframe_{shot.start_frame}_{shot.end_frame}.jpg"
        
        # Extract frame using ffmpeg
        cmd = [
            'ffmpeg',
            '-ss', str(middle_time),
            '-i', str(video_path),
            '-vframes', '1',
            '-q:v', '2',
            '-y',
            str(output_path)
        ]
        
        subprocess.run(cmd, capture_output=True, check=True)
        
        return str(output_path)
    
    def generate_proxy(self, video_path: Path, output_dir: Path) -> str:
        """Generate low-res proxy video."""
        if not self.proxy_enabled:
            return str(video_path)
        
        output_dir.mkdir(parents=True, exist_ok=True)
        
        proxy_width = self.config['video']['proxy']['width']
        proxy_fps = self.config['video']['proxy']['fps']
        
        output_path = output_dir / f"proxy_{video_path.stem}.mp4"
        
        cmd = [
            'ffmpeg',
            '-i', str(video_path),
            '-vf', f'scale={proxy_width}:-2,fps={proxy_fps}',
            '-c:v', 'libx264',
            '-preset', 'fast',
            '-crf', '28',
            '-an',  # No audio for proxy
            '-y',
            str(output_path)
        ]
        
        subprocess.run(cmd, capture_output=True, check=True)
        
        return str(output_path)
    
    def generate_thumbnail(self, keyframe_path: str, output_dir: Path, max_width: int = 320) -> str:
        """Generate thumbnail from keyframe."""
        output_dir.mkdir(parents=True, exist_ok=True)
        
        img = Image.open(keyframe_path)
        
        # Calculate new height maintaining aspect ratio
        aspect_ratio = img.height / img.width
        new_height = int(max_width * aspect_ratio)
        
        # Resize
        img.thumbnail((max_width, new_height), Image.Resampling.LANCZOS)
        
        # Save
        thumb_path = output_dir / f"thumb_{Path(keyframe_path).stem}.jpg"
        img.save(thumb_path, 'JPEG', quality=85)
        
        return str(thumb_path)
    
    def frames_to_timecode(self, frame: int, fps: float) -> str:
        """Convert frame number to SMPTE timecode."""
        total_seconds = frame / fps
        hours = int(total_seconds // 3600)
        minutes = int((total_seconds % 3600) // 60)
        seconds = int(total_seconds % 60)
        frames = int((total_seconds % 1) * fps)
        
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}:{frames:02d}"
    
    def process_video(self, video_path: Path, output_base_dir: Path) -> Tuple[List[Shot], Dict[str, Any]]:
        """
        Complete video processing pipeline.
        
        Returns:
            Tuple of (shots, metadata)
        """
        print(f"\nProcessing video: {video_path.name}")
        
        # Get metadata
        metadata = self.get_video_metadata(video_path)
        print(f"  Duration: {metadata['duration']:.2f}s, FPS: {metadata['fps']:.2f}")
        
        # Detect shots
        shots = self.detect_shots_histogram(video_path)
        
        # Extract keyframes
        keyframe_dir = output_base_dir / "keyframes"
        thumb_dir = output_base_dir / "thumbnails"
        
        print("Extracting keyframes...")
        for i, shot in enumerate(shots):
            keyframe_path = self.extract_keyframe(video_path, shot, keyframe_dir)
            shot.keyframe_path = keyframe_path
            
            # Generate thumbnail
            self.generate_thumbnail(keyframe_path, thumb_dir)
            
            if (i + 1) % 10 == 0:
                print(f"  Extracted {i + 1}/{len(shots)} keyframes")
        
        # Generate proxy
        if self.proxy_enabled:
            print("Generating proxy video...")
            proxy_dir = output_base_dir / "proxies"
            proxy_path = self.generate_proxy(video_path, proxy_dir)
            metadata['proxy_path'] = proxy_path
        
        print(f"✓ Processed {len(shots)} shots from {video_path.name}")
        
        return shots, metadata
