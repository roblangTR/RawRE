# Gemini Video Analysis Integration

This document describes the integration of Google's Gemini 2.5 Flash model for enhanced video metadata extraction in the RAWRE news editing agent.

## Overview

The Gemini integration adds rich, AI-generated metadata to video shots, providing detailed descriptions of visual content that significantly enhance the quality of automated video editing.

## What Gemini Adds

### Enhanced Metadata Fields

For each video shot, Gemini provides:

1. **Enhanced Description**: Natural language description of visual content
2. **Shot Type**: Classification (establishing, action, detail, cutaway, interview, transition, b_roll)
3. **Shot Size**: Framing (extreme_wide, wide, medium_wide, medium, medium_close, close_up, extreme_close_up)
4. **Camera Movement**: Movement type (static, pan, tilt, tracking, handheld, zoom, crane, dolly)
5. **Composition**: Description of framing, rule of thirds, symmetry
6. **Lighting**: Lighting conditions (natural/artificial, quality, direction)
7. **Primary Subjects**: List of main subjects in frame
8. **Action Description**: What is happening in the shot
9. **Visual Quality**: Quality assessment (excellent, good, fair, poor)
10. **News Context**: Editorial context (background, main_story, b_roll, interview, establishing)
11. **Tone**: Emotional tone (urgent, neutral, dramatic, somber, uplifting, tense)
12. **Confidence**: Analysis confidence score (0.0-1.0)

### Database Schema

The enhanced metadata is stored in the `shots` table with these additional columns:

```sql
gemini_description TEXT,
gemini_shot_type TEXT,
gemini_shot_size TEXT,
gemini_camera_movement TEXT,
gemini_composition TEXT,
gemini_lighting TEXT,
gemini_subjects TEXT,  -- Comma-separated list
gemini_action TEXT,
gemini_quality TEXT,
gemini_context TEXT,
gemini_tone TEXT,
gemini_confidence REAL
```

## Architecture

```
Video Shot (Proxy Clip)
    ↓
GeminiAnalyzer
    ↓
Vertex AI (Gemini 2.5 Flash)
    ↓
Structured JSON Metadata
    ↓
Database Storage
    ↓
Available to Edit Agents
```

## Configuration

### 1. Enable Gemini in config.yaml

```yaml
gemini:
  enabled: true  # Set to true to enable
  model: "gemini-2.5-flash"
  project_id: "tr-ai-platform"  # Optional, defaults to TR platform
  region: "us-central1"  # Optional
  use_proxy_clips: true  # Send proxy videos for faster processing
```

### 2. Authentication

**Good news!** Gemini uses the **same Thomson Reuters authentication** as Open Arena. No separate GCP credentials needed!

The Gemini analyzer automatically uses your existing TR credentials:
- Same `TR_CLIENT_ID`, `TR_CLIENT_SECRET`, `TR_AUDIENCE` from `.env`
- TR tokens provide access to both Open Arena LLMs and Vertex AI/Gemini
- No service account keys or additional setup required

Optional environment variables (usually not needed):

```bash
# Optional: Override defaults
VERTEX_PROJECT_ID=tr-ai-platform  # Defaults to TR platform
VERTEX_REGION=us-central1  # Defaults to us-central1
```

### 3. Install Dependencies

```bash
pip install google-cloud-aiplatform google-auth
```

## Setup Guide

### Step 1: Verify TR Authentication

Since Gemini uses TR authentication, just verify your existing Open Arena setup works:

```bash
python test_auth.py
```

If this succeeds, you're ready for Gemini!

### Step 2: Enable in Config

Update `config.yaml`:

```yaml
gemini:
  enabled: true
  model: "gemini-2.5-flash"
  use_proxy_clips: true
```

That's it! No additional credentials needed.

### Step 3: Test the Integration

```python
from ingest.gemini_analyzer import GeminiAnalyzer
import yaml

# Load config
with open('config.yaml') as f:
    config = yaml.safe_load(f)

# Initialize analyzer
analyzer = GeminiAnalyzer(config)

# Test with a video clip
result = analyzer.analyze_shot(
    video_path='path/to/video.mp4',
    shot_data={
        'tc_in': '00:00:10:00',
        'tc_out': '00:00:15:00',
        'duration_ms': 5000
    }
)

print(result)
```

## Usage in Pipeline

The Gemini analyzer is automatically initialized by the IngestOrchestrator when enabled:

```python
from ingest.orchestrator import IngestOrchestrator
import yaml

# Load config
with open('config.yaml') as f:
    config = yaml.safe_load(f)

# Create orchestrator (Gemini auto-initialized if enabled)
orchestrator = IngestOrchestrator(config)

# Ingest video (Gemini analysis runs automatically)
result = orchestrator.ingest_video(
    video_path='path/to/video.mp4',
    story_id='story-123'
)
```

## Integration Points

### In Ingest Pipeline

The orchestrator integrates Gemini analysis after shot detection:

```python
# Step 1: Video Processing (shot detection, keyframes, proxies)
# Step 2: Transcription
# Step 3: Shot Classification
# Step 4: Gemini Video Analysis ← NEW
# Step 5: Generate Embeddings
# Step 6: Store in Database
```

### Example Integration Code

```python
if self.gemini_analyzer:
    logger.info("Running Gemini analysis...")
    for shot in shots:
        gemini_result = self.gemini_analyzer.analyze_shot(
            video_path=shot['proxy_path'] or shot['filepath'],
            shot_data={
                'tc_in': shot['tc_in'],
                'tc_out': shot['tc_out'],
                'duration_ms': shot['duration_ms']
            }
        )
        if gemini_result:
            # Store enhanced metadata
            shot['gemini_description'] = gemini_result.get('enhanced_description')
            shot['gemini_shot_type'] = gemini_result.get('shot_type')
            shot['gemini_shot_size'] = gemini_result.get('shot_size')
            # ... etc
```

## Performance Considerations

### Processing Time

- **Per Shot**: ~5-10 seconds
- **20 Shots**: ~2-3 minutes
- **100 Shots**: ~10-15 minutes

### File Size Limits

- Gemini has a ~20MB file size limit
- Proxy clips (640px width) typically stay under this limit
- Full resolution clips may exceed the limit

### Cost

- Gemini 2.5 Flash pricing: ~$0.075 per 1M input tokens
- Video analysis: ~$0.002 per minute of video
- Typical cost: ~$0.10-0.20 per 10-minute video

### Optimization Tips

1. **Use Proxy Clips**: Enable `use_proxy_clips: true` in config
2. **Batch Processing**: Process multiple videos overnight
3. **Selective Analysis**: Only analyze key shots (SOT, establishing)
4. **Rate Limiting**: Built-in 0.5s delay between requests

## Benefits for Edit Agents

The enhanced metadata significantly improves agent performance:

### 1. Better Shot Selection

Agents can select shots based on:
- Visual quality ("excellent" vs "poor")
- Composition ("centered framing" vs "off-center")
- Lighting conditions ("well-lit" vs "dark")

### 2. Improved Cutaway Matching

Agents can find relevant cutaways by:
- Subject matching (e.g., "police officers" with "police car")
- Context matching (e.g., "establishing" with "detail")
- Tone matching (e.g., "dramatic" with "tense")

### 3. Enhanced Descriptions

Natural language descriptions help agents:
- Understand visual content without watching video
- Generate better edit rationales
- Provide context to human editors

### 4. Smarter Sequencing

Camera movement and shot size data enables:
- Better pacing (vary shot sizes)
- Smooth transitions (match movements)
- Professional composition (follow editing rules)

## Troubleshooting

### Authentication Errors

```
Error: Failed to get TR token
```

**Solution**: Verify your TR credentials in `.env`:
- `TR_CLIENT_ID`
- `TR_CLIENT_SECRET`
- `TR_AUDIENCE`

Run `python test_auth.py` to verify authentication works.

### File Size Errors

```
Error: File size exceeds 20MB limit
```

**Solution**: Enable proxy clips or reduce video resolution

### API Quota Errors

```
Error: Quota exceeded
```

**Solution**: Wait and retry, or request quota increase from GCP

### Connection Errors

```
Error: Connection reset by peer
```

**Solution**: The analyzer has built-in retry logic (3 attempts)

## Disabling Gemini

To disable Gemini analysis, set `enabled: false` in `config.yaml`:

```yaml
gemini:
  enabled: false
```

The system will continue to work without Gemini, using only basic shot classification.

## Future Enhancements

Potential improvements:

1. **Batch API**: Use batch processing for better throughput
2. **Caching**: Cache results to avoid re-analyzing same clips
3. **Selective Analysis**: Only analyze shots that need it
4. **Custom Prompts**: Allow custom analysis prompts per project
5. **Multi-modal**: Combine with audio analysis for richer metadata

## Related Documentation

- [Configuration Guide](CONFIGURATION_GUIDE.md)
- [Data Requirements](DATA_REQUIREMENTS.md)
- [Ingest Pipeline](ingest/README.md)
- [Database Schema](storage/README.md)

## Support

For issues or questions:
- Check logs in `logs/` directory
- Review Gemini analyzer code in `ingest/gemini_analyzer.py`
- Consult [Vertex AI documentation](https://cloud.google.com/vertex-ai/docs)
