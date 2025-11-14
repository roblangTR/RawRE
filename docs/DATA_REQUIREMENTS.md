# Data Requirements for Testing

## Overview

This guide explains what data and metadata you need to test the news edit agent with your rushes (raw video footage).

## Quick Start

**Minimum Required:**
1. Video files (MP4, MOV, or similar)
2. Story identifier (e.g., "ukraine-update-2024")
3. Basic metadata (can be auto-generated from video files)

**Optional but Recommended:**
- Transcripts or subtitles
- Shot metadata (timecodes, shot types)
- Location information

## Video File Requirements

### Supported Formats
- **Video**: MP4, MOV, MXF, AVI
- **Codecs**: H.264, ProRes, DNxHD
- **Frame Rates**: 23.976, 24, 25, 29.97, 30, 50, 59.94, 60 fps

### File Organization
```
rushes/
├── story-name/
│   ├── clip001.mp4
│   ├── clip002.mp4
│   ├── clip003.mp4
│   └── metadata.json (optional)
```

## Metadata Format

### Required Fields (Per Shot)

The system expects this metadata structure for each shot:

```json
{
  "story_slug": "ukraine-update-2024",
  "filepath": "/path/to/clip001.mp4",
  "capture_ts": 1699564800.0,
  "tc_in": "01:00:00:00",
  "tc_out": "01:00:15:00",
  "fps": 25.0,
  "duration_ms": 15000
}
```

**Field Descriptions:**

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `story_slug` | string | Unique story identifier | "ukraine-update-2024" |
| `filepath` | string | Path to video file | "/rushes/clip001.mp4" |
| `capture_ts` | float | Unix timestamp of capture | 1699564800.0 |
| `tc_in` | string | In timecode (HH:MM:SS:FF) | "01:00:00:00" |
| `tc_out` | string | Out timecode (HH:MM:SS:FF) | "01:00:15:00" |
| `fps` | float | Frame rate | 25.0 |
| `duration_ms` | integer | Duration in milliseconds | 15000 |

### Optional Fields (Enhance Quality)

```json
{
  "shot_type": "medium_shot",
  "asr_text": "The president addressed the nation today...",
  "asr_summary": "Presidential address on economic policy",
  "has_face": 1,
  "location": "Washington DC",
  "proxy_path": "/proxies/clip001_proxy.mp4",
  "thumb_path": "/thumbs/clip001_thumb.jpg"
}
```

**Optional Field Descriptions:**

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `shot_type` | string | Shot classification | "wide_shot", "medium_shot", "close_up" |
| `asr_text` | string | Full transcript | "The president said..." |
| `asr_summary` | string | Brief summary | "Presidential speech" |
| `has_face` | integer | Face detected (0/1) | 1 |
| `location` | string | Shooting location | "London", "Paris" |
| `proxy_path` | string | Low-res proxy path | "/proxies/clip.mp4" |
| `thumb_path` | string | Thumbnail path | "/thumbs/clip.jpg" |

## Metadata Generation Options

### Option 1: Auto-Generate from Video Files

The system can extract basic metadata automatically:

```bash
python cli.py ingest --input ./rushes/story-name --story 'story-name'
```

**Auto-extracted:**
- Duration
- Frame rate
- Timecodes (from file timestamps)
- File paths

**Not auto-extracted (requires manual input or additional tools):**
- Transcripts
- Shot types
- Location information

### Option 2: Provide Metadata File

Create a `metadata.json` file in your rushes directory:

```json
{
  "story_slug": "ukraine-update-2024",
  "clips": [
    {
      "filename": "clip001.mp4",
      "tc_in": "01:00:00:00",
      "tc_out": "01:00:15:00",
      "shot_type": "wide_shot",
      "transcript": "The president addressed the nation...",
      "location": "Washington DC"
    },
    {
      "filename": "clip002.mp4",
      "tc_in": "01:00:15:00",
      "tc_out": "01:00:30:00",
      "shot_type": "medium_shot",
      "transcript": "Economic indicators show...",
      "location": "New York"
    }
  ]
}
```

### Option 3: Use Existing Transcripts

If you have subtitle files (SRT, VTT):

```
rushes/
├── story-name/
│   ├── clip001.mp4
│   ├── clip001.srt
│   ├── clip002.mp4
│   └── clip002.srt
```

The system will automatically associate transcripts with video files.

## Shot Type Classification

The system recognizes these shot types:

| Shot Type | Description | Use Case |
|-----------|-------------|----------|
| `wide_shot` | Establishing shot | Context, location |
| `medium_shot` | Waist up | Interviews, general coverage |
| `close_up` | Face/detail | Emotion, emphasis |
| `extreme_close_up` | Very tight detail | Dramatic emphasis |
| `over_shoulder` | OTS shot | Conversations |
| `two_shot` | Two subjects | Interactions |
| `cutaway` | Detail/B-roll | Coverage, pacing |
| `pan` | Camera movement | Following action |
| `tilt` | Vertical movement | Revealing |
| `tracking` | Moving with subject | Dynamic coverage |

## Example Test Dataset

### Minimal Test (3 clips)

```json
{
  "story_slug": "test-story",
  "clips": [
    {
      "filename": "intro.mp4",
      "duration_ms": 10000,
      "shot_type": "wide_shot",
      "transcript": "This is the introduction to our story."
    },
    {
      "filename": "interview.mp4",
      "duration_ms": 30000,
      "shot_type": "medium_shot",
      "transcript": "The expert explains the key points of the issue."
    },
    {
      "filename": "conclusion.mp4",
      "duration_ms": 8000,
      "shot_type": "close_up",
      "transcript": "In conclusion, this demonstrates the impact."
    }
  ]
}
```

### Realistic Test (10+ clips)

For a realistic test, you should have:
- **5-10 minutes** of total footage
- **10-20 clips** of varying lengths
- **Mix of shot types** (wide, medium, close-up)
- **Transcripts** for spoken content
- **Location tags** if relevant

## Testing Workflow

### Step 1: Prepare Your Rushes

```bash
# Organize your files
mkdir -p rushes/my-story
cp /path/to/your/clips/*.mp4 rushes/my-story/

# Optional: Add metadata file
cat > rushes/my-story/metadata.json << EOF
{
  "story_slug": "my-story",
  "clips": [...]
}
EOF
```

### Step 2: Ingest the Footage

```bash
# Basic ingest (auto-generates metadata)
python cli.py ingest --input rushes/my-story --story 'my-story'

# With custom metadata
python cli.py ingest --input rushes/my-story --story 'my-story' --metadata rushes/my-story/metadata.json
```

### Step 3: Compile an Edit

```bash
python cli.py compile \
  --story 'my-story' \
  --brief 'Create a 60-second news package about the economic summit, focusing on key policy announcements' \
  --duration 60
```

## What You Actually Need to Start

**Absolute Minimum:**
1. ✅ Video files in a directory
2. ✅ A story name/identifier

**The system will auto-generate:**
- Shot IDs
- Timecodes (from file metadata)
- Duration
- Frame rate
- Capture timestamps

**Recommended to Provide:**
- Transcripts (for better shot selection)
- Shot types (for better composition)
- Location info (for context)

## Example Command with Your Rushes

```bash
# If you have rushes in /path/to/rushes/ukraine-story/
python cli.py ingest \
  --input /path/to/rushes/ukraine-story \
  --story 'ukraine-story'

# Then compile an edit
python cli.py compile \
  --story 'ukraine-story' \
  --brief 'Create a 90-second package on the Ukraine peace talks, emphasizing diplomatic efforts and humanitarian impact' \
  --duration 90
```

## Metadata Enhancement Tools

If you want to enhance your metadata:

### For Transcription
- **Whisper**: `pip install openai-whisper`
- **Google Speech-to-Text**: Cloud API
- **AWS Transcribe**: Cloud API

### For Shot Classification
- **OpenCV**: Basic shot detection
- **PySceneDetect**: Scene change detection
- **Custom ML models**: Shot type classification

### For Face Detection
- **OpenCV**: Face detection
- **dlib**: Facial landmarks
- **MediaPipe**: Face mesh

## Summary

**To test with your rushes, you need:**

1. ✅ Video files (MP4, MOV, etc.)
2. ✅ Story identifier
3. ⚠️ Transcripts (optional but recommended)
4. ⚠️ Shot metadata (optional but improves quality)

**The system handles:**
- Automatic metadata extraction
- Shot database creation
- Vector embeddings
- Edit compilation

**Start simple, enhance later!**
