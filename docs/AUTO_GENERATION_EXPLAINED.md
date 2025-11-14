# How Auto-Generation Works

## Overview

The system automatically extracts metadata from your video files using computer vision and FFmpeg. Here's exactly how it works.

## Auto-Generation Pipeline

### 1. Video Metadata Extraction

**Tool**: FFprobe (part of FFmpeg)

**What it extracts:**
```python
{
    'fps': 25.0,                    # Frame rate
    'duration': 120.5,              # Duration in seconds
    'width': 1920,                  # Video width
    'height': 1080,                 # Video height
    'creation_time': datetime(...), # When video was created
    'codec': 'h264'                 # Video codec
}
```

**How it works:**
```bash
# Behind the scenes, the system runs:
ffprobe -v quiet -print_format json -show_format -show_streams video.mp4
```

This extracts:
- **Frame rate**: From video stream metadata
- **Duration**: From video stream or container format
- **Creation time**: From file metadata or file modification time
- **Resolution**: Width and height from video stream
- **Codec**: Video compression format

### 2. Shot Detection

**Tool**: OpenCV with histogram comparison

**What it detects:**
- Shot boundaries (hard cuts between scenes)
- Start/end frames for each shot
- Shot duration

**How it works:**

```python
# For each frame:
1. Convert frame to HSV color space
2. Calculate color histogram
3. Compare with previous frame's histogram
4. If difference > threshold → Shot boundary detected
5. Create shot record with timecodes
```

**Algorithm:**
```
Frame 1: [histogram] ─┐
                       ├─ Compare → Similarity: 0.95 (same shot)
Frame 2: [histogram] ─┘

Frame 2: [histogram] ─┐
                       ├─ Compare → Similarity: 0.45 (NEW SHOT!)
Frame 3: [histogram] ─┘
```

**Parameters** (from config.yaml):
- `threshold`: 0.3 (30% difference triggers new shot)
- `min_shot_duration_sec`: 1.0 (ignore shots < 1 second)

**Example output:**
```python
Shot 1: frames 0-150    (0.0s - 6.0s)   duration: 6.0s
Shot 2: frames 151-300  (6.04s - 12.0s) duration: 5.96s
Shot 3: frames 301-450  (12.04s - 18.0s) duration: 5.96s
```

### 3. Timecode Generation

**What it generates:**
- SMPTE timecodes (HH:MM:SS:FF format)
- In/Out points for each shot

**How it works:**
```python
def frames_to_timecode(frame, fps):
    total_seconds = frame / fps
    hours = int(total_seconds // 3600)
    minutes = int((total_seconds % 3600) // 60)
    seconds = int(total_seconds % 60)
    frames = int((total_seconds % 1) * fps)
    
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}:{frames:02d}"
```

**Example:**
- Frame 150 at 25fps → `00:00:06:00`
- Frame 300 at 25fps → `00:00:12:00`

### 4. Keyframe Extraction

**Tool**: FFmpeg

**What it extracts:**
- One representative frame per shot (middle frame)
- High-quality JPEG image

**How it works:**
```bash
# For each shot, extract middle frame:
ffmpeg -ss 6.0 -i video.mp4 -vframes 1 -q:v 2 keyframe_0_150.jpg
```

**Parameters:**
- `-ss 6.0`: Seek to 6 seconds (middle of shot)
- `-vframes 1`: Extract 1 frame
- `-q:v 2`: High quality (2 = very high)

### 5. Thumbnail Generation

**Tool**: PIL (Python Imaging Library)

**What it creates:**
- Small preview images (320px wide)
- Maintains aspect ratio

**How it works:**
```python
1. Load keyframe image
2. Calculate new height (maintain aspect ratio)
3. Resize to 320px width
4. Save as JPEG (85% quality)
```

**Example:**
- Input: 1920x1080 keyframe
- Output: 320x180 thumbnail

### 6. Proxy Video Generation (Optional)

**Tool**: FFmpeg

**What it creates:**
- Low-resolution version for faster editing
- Smaller file size

**How it works:**
```bash
ffmpeg -i video.mp4 \
  -vf scale=640:-2,fps=12 \
  -c:v libx264 \
  -preset fast \
  -crf 28 \
  -an \
  proxy_video.mp4
```

**Parameters:**
- `scale=640:-2`: 640px wide, auto height
- `fps=12`: Reduce to 12fps
- `crf 28`: Compression (higher = smaller file)
- `-an`: No audio

### 7. Database Storage

**What gets stored:**

```python
{
    'shot_id': 1,                           # Auto-incremented
    'story_slug': 'my-story',               # From user input
    'filepath': '/path/to/video.mp4',       # Original file
    'capture_ts': 1699564800.0,             # Unix timestamp
    'tc_in': '00:00:00:00',                 # Start timecode
    'tc_out': '00:00:06:00',                # End timecode
    'fps': 25.0,                            # Frame rate
    'duration_ms': 6000,                    # Duration in ms
    'shot_type': None,                      # Not auto-detected
    'asr_text': None,                       # Requires transcription
    'asr_summary': None,                    # Requires transcription
    'has_face': 0,                          # Not auto-detected
    'location': None,                       # Not auto-detected
    'embedding_text': None,                 # Generated later
    'embedding_visual': None,               # Generated later
    'proxy_path': '/proxies/proxy.mp4',    # If enabled
    'thumb_path': '/thumbs/thumb.jpg',      # Generated
    'created_at': 1699564800.0              # Ingest timestamp
}
```

## What IS Auto-Generated

✅ **Automatically extracted:**
1. Frame rate (fps)
2. Duration (seconds/milliseconds)
3. Resolution (width/height)
4. Creation timestamp
5. Shot boundaries (start/end frames)
6. Timecodes (in/out points)
7. Keyframes (middle frame of each shot)
8. Thumbnails (small preview images)
9. Proxy videos (optional, low-res versions)
10. File paths

## What is NOT Auto-Generated

❌ **Requires additional processing or manual input:**
1. **Transcripts** (`asr_text`) - Requires speech-to-text
2. **Shot types** (`shot_type`) - Requires ML classification
3. **Face detection** (`has_face`) - Requires face detection
4. **Location** (`location`) - Requires manual input or GPS metadata
5. **Embeddings** (`embedding_text`, `embedding_visual`) - Generated in separate step
6. **Shot summaries** (`asr_summary`) - Requires LLM processing

## Complete Processing Flow

```
Input: video.mp4
    ↓
[1] FFprobe → Extract metadata (fps, duration, etc.)
    ↓
[2] OpenCV → Detect shots (histogram comparison)
    ↓
[3] Calculate → Generate timecodes for each shot
    ↓
[4] FFmpeg → Extract keyframes (middle of each shot)
    ↓
[5] PIL → Generate thumbnails from keyframes
    ↓
[6] FFmpeg → Generate proxy video (optional)
    ↓
[7] SQLite → Store all metadata in database
    ↓
Output: Structured shot database ready for editing
```

## Example: Processing a 2-minute video

**Input:**
- `news_clip.mp4` (2 minutes, 25fps, 1920x1080)

**Auto-generated output:**

```
Shots detected: 15 shots
├── Shot 1: 00:00:00:00 - 00:00:08:12 (8.5s)
│   ├── Keyframe: keyframe_0_212.jpg
│   └── Thumbnail: thumb_0_212.jpg
├── Shot 2: 00:00:08:13 - 00:00:15:20 (7.3s)
│   ├── Keyframe: keyframe_213_395.jpg
│   └── Thumbnail: thumb_213_395.jpg
├── Shot 3: 00:00:15:21 - 00:00:22:10 (6.8s)
│   ├── Keyframe: keyframe_396_565.jpg
│   └── Thumbnail: thumb_396_565.jpg
└── ... (12 more shots)

Proxy video: proxy_news_clip.mp4 (640x360, 12fps)

Database records: 15 shots with complete metadata
```

## Performance

**Processing speed** (approximate):
- Shot detection: ~2-5x realtime (2min video = 24-60 seconds)
- Keyframe extraction: ~1 second per shot
- Thumbnail generation: ~0.1 seconds per shot
- Proxy generation: ~0.5x realtime (2min video = 4 minutes)

**Total time for 2-minute video:**
- Without proxy: ~1-2 minutes
- With proxy: ~5-6 minutes

## Configuration

All auto-generation parameters are in `config.yaml`:

```yaml
video:
  shot_detection:
    threshold: 0.3              # Sensitivity (lower = more shots)
    min_shot_duration_sec: 1.0  # Minimum shot length
  
  keyframes:
    count: 1                    # Frames per shot
  
  proxy:
    enabled: true               # Generate proxies?
    width: 640                  # Proxy width
    fps: 12                     # Proxy frame rate
```

## Dependencies

**Required tools:**
- **FFmpeg/FFprobe**: Video metadata and frame extraction
- **OpenCV**: Shot detection and image processing
- **PIL/Pillow**: Thumbnail generation
- **NumPy**: Numerical operations

**Install:**
```bash
# FFmpeg (system)
brew install ffmpeg  # macOS
apt install ffmpeg   # Linux

# Python packages
pip install opencv-python pillow numpy
```

## Summary

**The system automatically generates:**
1. ✅ Shot boundaries from video analysis
2. ✅ Timecodes for each shot
3. ✅ Keyframes and thumbnails
4. ✅ Video metadata (fps, duration, etc.)
5. ✅ Proxy videos (optional)
6. ✅ Database records

**You only need to provide:**
1. Video files
2. Story identifier

**Everything else is automatic!**
