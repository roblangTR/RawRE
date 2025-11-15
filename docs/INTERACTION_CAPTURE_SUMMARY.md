# Interaction Capture Summary

## Overview

This document summarizes the complete interaction logging system test conducted on November 15, 2025. The test captured every AI agent interaction during a full edit workflow, providing complete visibility into how the system works.

## Test Details

- **Session ID**: 20251115_165201
- **Story**: gallipoli_burial_2022
- **Target Duration**: 90 seconds
- **Available Material**: 25 shots, 842.0s total
- **Result**: Edit APPROVED on first iteration (score: 8/10)

## Complete Workflow Captured

### 10 Total Interactions

1. **PLANNER** (1 interaction)
   - Created 8-beat plan
   - Prompt: 32,649 chars (31.9 KB)
   - Response: 4,955 chars (4.8 KB)

2. **PICKER** (8 interactions - one per beat)
   - Selected shots for each beat
   - Total Prompts: 245,875 chars (240.1 KB)
   - Total Responses: 30,067 chars (29.4 KB)

3. **VERIFIER** (1 interaction)
   - Verified complete edit
   - Prompt: 15,123 chars (14.8 KB)
   - Response: 13,390 chars (13.1 KB)
   - Score: 8/10

### Overall Statistics

- **Total Prompt Data**: 293,647 chars (286.8 KB)
- **Total Response Data**: 48,412 chars (47.3 KB)
- **Combined**: 342,059 chars (334.0 KB)

## What's Captured in Each Interaction

Each interaction JSON file contains:

```json
{
  "interaction_id": "20251115_165201_0001",
  "session_id": "20251115_165201",
  "sequence_number": 1,
  "timestamp": "2025-11-15T16:52:01.123966",
  "agent": "planner",
  "interaction_type": "chat",
  "prompt": {
    "text": "...",  // Full prompt sent to AI
    "length": 32649,
    "hash": "..."
  },
  "response": {
    "text": "...",  // Complete AI response
    "length": 4955,
    "hash": "..."
  },
  "system_prompt": null,
  "context": null,
  "metadata": {
    "model": "claude-3-5-sonnet-20241022",
    "temperature": 0.1,
    "workflow_id": "49f87950-7584-469e-bf5c-b1cc54bc42f3"
  },
  "raw_request": { ... },  // Complete Open Arena API request
  "raw_response": { ... }  // Complete Open Arena API response
}
```

## Key Insights from Captured Data

### 1. Planner Has Complete Information

The planner's first interaction shows it received:
- ✅ Full Gemini visual descriptions for all 25 shots
- ✅ Complete audio transcripts (not truncated)
- ✅ Rich metadata (size, movement, subjects, actions)
- ✅ Relevance scores for shot prioritization

**Example from Shot 48:**
```
Visual: A group of approximately eight individuals, some in military uniforms 
and others in civilian attire, are gathered outdoors in what appears to be a 
military cemetery or memorial park. The scene is brightly lit by natural 
sunlight. In the foreground, a man in a dark suit with a white stole, possibly 
a priest, is speaking into a microphone while holding a document...

Audio: "The Dardanelles' combat, on the left of the Orients' expedition..."

Details: Size: medium_wide | Movement: static | Subjects: group of people, 
military personnel, priest, cemetery, monument | Action: A group of people, 
including military personnel and a priest, are gathered in a cemetery...

Relevance: 5.524
```

### 2. Picker Receives Beat-Specific Context

Each picker interaction includes:
- Beat description and requirements
- Working set of candidate shots (typically 25 shots)
- Full visual descriptions and metadata
- Semantic search relevance scores

### 3. Verifier Gets Complete Edit Context

The verifier receives:
- Full plan with all beats
- All selected shots with their assignments
- Complete metadata for verification

## File Locations

All interaction logs are stored in:
```
logs/interactions/
├── 20251115_165201_0001.json  # Planner
├── 20251115_165201_0002.json  # Picker (Beat 1)
├── 20251115_165201_0003.json  # Picker (Beat 2)
├── 20251115_165201_0004.json  # Picker (Beat 3)
├── 20251115_165201_0005.json  # Picker (Beat 4)
├── 20251115_165201_0006.json  # Picker (Beat 5)
├── 20251115_165201_0007.json  # Picker (Beat 6)
├── 20251115_165201_0008.json  # Picker (Beat 7)
├── 20251115_165201_0009.json  # Picker (Beat 8)
└── 20251115_165201_0010.json  # Verifier
```

## Analysis Tools

### View Summary
```bash
python3 scripts/analyze_interactions.py
```

### View Specific Interaction
```bash
python3 -m json.tool logs/interactions/20251115_165201_0001.json | less
```

### Search Across All Interactions
```bash
grep -r "specific_term" logs/interactions/20251115_165201_*.json
```

## Use Cases

This captured data enables:

1. **Debugging**: See exactly what each agent received and responded with
2. **Optimization**: Identify where prompts can be improved
3. **Validation**: Verify agents have all necessary information
4. **Training**: Understand how the system makes decisions
5. **Documentation**: Show stakeholders how the system works
6. **Testing**: Compare different runs to measure improvements

## Final Edit Result

The captured workflow produced:
- **15 shots** across 8 beats
- **100 seconds** total duration (vs 90s target)
- **Score**: 8/10 from verifier
- **Issues**: 4 minor issues (all low/medium severity)
- **Status**: ✅ APPROVED on first iteration

## Next Steps

With this complete capture, you can:

1. Review any specific interaction to understand decisions
2. Verify the planner has all Gemini visual data
3. Analyze how semantic search ranks shots
4. See how the verifier evaluates edits
5. Compare this run with future improvements

## Related Documentation

- [Interaction Logging](INTERACTION_LOGGING.md) - Technical implementation
- [LLM Client Simplification](LLM_CLIENT_SIMPLIFICATION.md) - Architecture changes
- [System Prompt Test Results](SYSTEM_PROMPT_TEST_RESULTS.md) - Previous testing
