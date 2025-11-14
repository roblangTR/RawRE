# Editing Quality Improvements

## Overview

This document describes the improvements made to the RAWRE editing system to incorporate professional video editing principles from "Grammar of the Edit" by Roy Thompson and Christopher J. Bowen.

**Date**: 2025-01-14  
**Status**: Implemented - Phase 1 Complete

## Changes Made

### 1. Enhanced Picker Agent System Prompt

**File**: `agent/system_prompts.py` - `PICKER_SYSTEM_PROMPT`

**Key Additions**:

#### The 6 Elements of a Good Edit Framework
Integrated the professional editing framework that evaluates every transition:

1. **INFORMATION** - Does the next shot provide NEW visual or audio data?
2. **MOTIVATION** - Is there a clear reason to cut NOW?
3. **COMPOSITION** - Are the frames sufficiently different?
4. **CAMERA ANGLE** - Is there at least a 30-degree change in angle or shot size?
5. **CONTINUITY** - Do movement, position, sound, and subjects match appropriately?
6. **SOUND** - Does the audio support the visual transition?

**Scoring System**:
- ✅ Strong Edit: 4-6 elements satisfied → USE
- ⚠️ Weak Edit: 2-3 elements satisfied → RECONSIDER
- ❌ Avoid: 0-1 elements satisfied → DO NOT USE

#### Shot Duration Guidelines
- Minimum: 3 seconds (except quick action cuts)
- Maximum: 10-12 seconds (except long SOT interviews)
- Rule of thumb: "Speak the shot description aloud - when done, cut"
- Vary lengths: Mix short (3-5s), medium (5-8s), and longer (8-12s) shots for rhythm

#### News Editing Priorities
1. Factual accuracy - Never misrepresent content
2. Temporal accuracy - Maintain chronological flow
3. Speaker intent - Preserve meaning in sound bites
4. Clear information - Each shot advances the story
5. Appropriate pacing - Match urgency to story type
6. Professional sound - Clean audio throughout

#### Enhanced Output Format
Now requires the Picker to include:
- `six_elements_score`: Count of elements satisfied (0-6)
- `elements_satisfied`: List of which elements are met
- `shot_variety`: Summary of shot size mix
- Explicit reasoning for each selection

### 2. Enhanced Verifier Agent System Prompt

**File**: `agent/system_prompts.py` - `VERIFIER_SYSTEM_PROMPT`

**Key Additions**:

#### 6 Elements Validation
- Evaluates EVERY transition between shots
- Scores each transition (0-6 elements)
- Flags weak edits (2-3 elements) as issues
- Flags poor edits (0-1 elements) as critical issues

#### Comprehensive Verification Checklist

**Editorial Quality**:
- Story coherence
- Beat coverage
- Factual accuracy
- Temporal accuracy
- Speaker intent preservation

**Technical Quality**:
- Shot duration validation (3-12s range)
- Shot variety analysis (mix of sizes)
- Transition validation (straight cuts only)
- Duration target compliance (±10%)

**Continuity Checks**:
- Screen direction consistency (180-degree rule)
- Subject continuity
- Lighting consistency
- Audio perspective matching
- Complete thoughts in sound bites

**Pacing & Rhythm**:
- Shot duration variety
- Appropriate pacing for story type
- No monotonous pacing

#### Enhanced Output Format
Now includes:
- `transition_analysis`: Per-transition 6 Elements scoring
- `shot_variety_analysis`: Breakdown of shot sizes used
- `duration_analysis`: Detailed timing metrics
- `six_elements_average`: Average score across all transitions
- Issue categorization by severity (critical/major/minor)

### 3. Enhanced Picker Context Formatting

**File**: `agent/picker.py` - `_format_picking_context()`

**Key Additions**:

Now includes rich Gemini visual metadata for each candidate shot:
- `gemini_shot_size`: Shot size classification (CU/MCU/MS/LS etc)
- `gemini_camera_movement`: Camera movement description
- `gemini_composition`: Composition analysis
- `gemini_subjects`: List of subjects in frame
- `gemini_action`: Action description
- `gemini_quality`: Quality assessment
- `gemini_description`: Full visual description (truncated to 200 chars)

This provides the LLM with comprehensive visual context to make informed decisions about:
- Shot variety (mixing different shot sizes)
- Camera angle changes (for the 30-degree rule)
- Composition differences (avoiding jump cuts)
- Subject continuity (tracking who/what is in frame)
- Visual quality (avoiding poor quality shots)

## Expected Improvements

### Immediate Benefits

1. **Better Shot Selection**:
   - More varied shot sizes (avoiding monotonous framing)
   - Stronger transitions (4+ elements satisfied)
   - Better use of visual metadata

2. **Improved Pacing**:
   - Varied shot durations (3-5s, 5-8s, 8-12s mix)
   - More engaging rhythm
   - Appropriate pacing for content type

3. **Enhanced Quality Control**:
   - Systematic validation of every transition
   - Clear identification of weak edits
   - Actionable feedback for improvements

4. **Professional Standards**:
   - Adherence to broadcast editing principles
   - Consistent application of the 6 Elements framework
   - News-specific editing priorities

### Measurable Metrics

To evaluate improvements, compare before/after on:

1. **6 Elements Scores**:
   - Average score per transition (target: 4+)
   - Percentage of strong edits (target: >80%)
   - Number of weak/poor edits (target: minimize)

2. **Shot Variety**:
   - Distribution of shot sizes (target: balanced mix)
   - Consecutive similar shots (target: minimize)

3. **Duration Compliance**:
   - Shots meeting 3-12s guideline (target: >90%)
   - Shot duration variety (target: good mix)
   - Total duration accuracy (target: ±10%)

4. **Continuity**:
   - Jump cuts (target: 0)
   - Screen direction violations (target: 0)
   - Subject continuity issues (target: minimize)

## Testing Approach

### Comparison Testing

1. **Use Existing Test Data**:
   - Run same editorial brief through old vs new system
   - Compare JSON outputs
   - Analyze differences in shot selection and sequencing

2. **Metrics to Compare**:
   - Shot variety (count of each shot size)
   - Average shot duration
   - Duration accuracy
   - Number of transitions
   - Verifier scores (if available in old output)

3. **Qualitative Assessment**:
   - Review actual EDL/FCPXML output
   - Watch rendered edits (if possible)
   - Assess narrative flow and pacing

### Test Script

Use existing test scripts:
```bash
# Run test with new prompts
python scripts/test_2min_edit.py

# Compare with previous test results
# (Previous results should be saved in data/ or tests/)
```

## Future Enhancements

### Phase 2: Code-Level Improvements

1. **Shot Scoring Module** (`agent/shot_scorer.py`):
   - Multi-dimensional scoring system
   - Configurable weights for different criteria
   - Integration with Gemini metadata

2. **Pacing Analyzer** (`agent/pacing_analyzer.py`):
   - Shot duration guidelines enforcement
   - Rhythm variation analysis
   - Energy level tracking

3. **Working Set Builder Enhancements**:
   - Pre-filter by Gemini quality
   - Ensure shot size variety in candidates
   - Better semantic scoring

### Phase 3: Advanced Features

1. **Visual Continuity Validation**:
   - Automated jump cut detection
   - Screen direction analysis
   - Lighting consistency checks

2. **Narrative Structure Templates**:
   - Story arc templates (setup/conflict/resolution)
   - Emotional progression planning
   - Beat-level pacing requirements

## References

- **Grammar of the Edit** by Roy Thompson and Christopher J. Bowen
- Editing documentation: `docs/editiing/files/editing_quick_reference.md`
- AI Editor prompts: `docs/editiing/files/ai_editor_condensed_prompt.md`

## Changelog

### 2025-01-14 - Phase 1 Complete
- ✅ Enhanced Picker system prompt with 6 Elements framework
- ✅ Enhanced Verifier system prompt with 6 Elements validation
- ✅ Updated Picker context to include Gemini metadata
- ✅ Created documentation

### Next Steps
- Test improved prompts against existing test data
- Measure improvements using comparison metrics
- Iterate based on results
- Plan Phase 2 code-level improvements
