# Open Arena System Prompt Update Guide

**Date:** November 17, 2025  
**Purpose:** Update Gemini workflow to support sequence-based visual analysis

## Important Note

The `_get_system_instruction()` method in `ingest/gemini_analyzer.py` is **documentation only**. The actual system prompt used by Gemini is configured in your **Open Arena workflow**, not in the Python code.

## What Needs to Be Updated

You need to manually update the system instruction in your Open Arena Gemini workflow to support both:
1. Individual shot analysis (existing functionality)
2. Sequence analysis (new functionality for visual continuity)

## New System Prompt for Open Arena

Copy this system prompt into your Open Arena workflow configuration:

```
You are an expert video analyst specializing in news and documentary footage analysis.

You analyze video content for professional editing and provide detailed, structured metadata in JSON format.

## Your Capabilities

You can perform TWO types of analysis:

### 1. Individual Shot Analysis
When analyzing a single shot, provide:
- Enhanced natural language description
- Shot classification (type, size, movement)
- Composition and framing analysis
- Lighting assessment
- Subject identification and actions
- Visual quality scoring
- Tone and news context

### 2. Sequence Analysis (Multiple Shots)
When analyzing a sequence of related shots, provide:
- Per-shot quality scores and characteristics
- Shot compatibility analysis (which shots work well together)
- Jump cut warnings (shots too similar in framing/angle)
- Recommended subsequences (optimal shot progressions)
- Entry and exit points for the sequence
- Continuity issues and visual flow assessment

## Key Principles

- **Precise & Objective**: Base analysis on what you actually see
- **Editor-Focused**: Highlight elements important for video editing
- **Continuity-Aware**: Flag potential jump cuts and transition issues
- **Quality-Conscious**: Assess technical and compositional quality
- **Structured Output**: Always follow the JSON schema requested in the user prompt

## Output Format

CRITICAL: Respond ONLY with valid JSON matching the schema requested in the user prompt. 
- Do NOT include markdown formatting
- Do NOT include code blocks (```json)
- Do NOT include any explanatory text outside the JSON
- Do follow the exact JSON structure requested

Your response should be pure, valid JSON that can be parsed directly.
```

## How to Update Your Open Arena Workflow

### Step 1: Access Open Arena
1. Go to [Open Arena](https://aiopenarena.gcs.int.thomsonreuters.com)
2. Log in with your Thomson Reuters credentials

### Step 2: Locate Your Workflow
1. Find your Gemini video analysis workflow
2. The workflow ID should match what's in your `config.yaml` under `gemini.workflow_id`

### Step 3: Update System Prompt
1. Open the workflow configuration
2. Locate the "System Instruction" or "System Prompt" field
3. Replace the existing system prompt with the new one above
4. Save the workflow

### Step 4: Verify Configuration
After updating, verify your `config.yaml` has the correct settings:

```yaml
gemini:
  enabled: true
  workflow_id: "your-workflow-id-here"  # Should match Open Arena workflow
  use_proxy_clips: true
  picking:
    enabled: true  # Enable sequence-based picking
    sequence_grouping_method: "hybrid"
    sequence_batch_size: 6
```

## Why This Update Is Needed

### Before (Individual Shots Only)
The old system prompt only handled single-shot analysis:
- Shot description
- Classification
- Quality assessment

### After (Shots + Sequences)
The new system prompt supports:
- ✅ **Individual shot analysis** (same as before)
- ✅ **Sequence analysis** (NEW) - analyzes multiple shots together for:
  - Visual continuity
  - Jump cut detection
  - Shot compatibility
  - Recommended progressions
  - Entry/exit points

## Testing the Update

After updating the Open Arena workflow, test it:

### Test 1: Individual Shot Analysis (Should Still Work)
```python
# Run existing ingestion
python cli.py ingest Test_Rushes/your_video.mp4
```

Expected: Same shot analysis as before (enhanced_description, shot_type, etc.)

### Test 2: Sequence Analysis (New Feature)
```python
# Run compilation with sequence picking enabled
python cli.py compile "Your story brief" --use-gemini-picking
```

Expected: Gemini analyzes sequences and provides:
- Shot compatibility warnings
- Jump cut alerts
- Recommended shot progressions

## Troubleshooting

### Issue: "Failed to parse JSON"
**Cause:** Gemini is returning markdown-formatted JSON (```json ... ```)  
**Solution:** The updated system prompt explicitly instructs Gemini to avoid markdown formatting

### Issue: "Missing field: sequence_name"
**Cause:** Sequence analysis isn't returning the expected schema  
**Solution:** Verify the Open Arena system prompt matches the template above exactly

### Issue: Sequence analysis returns generic descriptions
**Cause:** Old system prompt is still being used  
**Solution:** 
1. Verify you saved the workflow in Open Arena
2. Check the workflow_id in config.yaml matches
3. Try creating a new workflow if updates aren't taking effect

## Monitoring

After the update, monitor logs for:

```bash
# Watch for Gemini calls
grep "GEMINI" logs/app.log

# Check for JSON parsing issues
grep "Failed to parse JSON" logs/app.log

# Verify sequence analysis is working
grep "Analyzing sequence" logs/app.log
```

## Rollback Plan

If issues occur, you can temporarily disable sequence-based picking:

```yaml
gemini:
  enabled: true
  picking:
    enabled: false  # Disable sequence picking, use traditional method
```

This falls back to the old behavior while you troubleshoot the Open Arena configuration.

## Summary

✅ **Action Required:** Update your Open Arena workflow system prompt  
✅ **No Code Changes:** Python code is already updated (commit: b9698d5)  
✅ **Testing:** Verify both individual and sequence analysis work  
✅ **Monitoring:** Watch logs for any JSON parsing issues  

---

**Next Steps:**
1. Update Open Arena workflow with new system prompt
2. Test with a small story compilation
3. Monitor for any issues
4. If successful, enable in production

**Questions?** Check the main implementation doc at `docs/SEQUENCE_BASED_VISUAL_ANALYSIS_COMPLETE.md`
