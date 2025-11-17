# Live Plan Visualization Feature

## Overview

The Live Plan Visualization feature provides real-time visibility into the AI agent's compilation process, showing the narrative plan as it's being created and tracking progress for each story beat.

## Architecture

### Backend Components

#### 1. Status Callback System (api/server.py)
- Integrated callback mechanism in `run_compilation_task()`
- Callbacks track 5 key stages:
  - `plan_created`: When Planner agent creates the narrative structure
  - `beat_searching`: When Picker agent starts searching for a specific beat
  - `beat_complete`: When shots are selected for a beat
  - `verification`: When Verifier agent begins analysis
  - `iteration_complete`: When a full iteration finishes

#### 2. Enhanced Job Tracking
Jobs now track:
```python
{
    "status": str,                    # Overall status
    "progress": int,                   # 0-100 percentage
    "current_stage": str,              # Current processing stage
    "current_agent": str,              # Active agent (Planner/Picker/Verifier)
    "current_beat": dict,              # Currently processing beat
    "plan": dict,                      # Full narrative plan
    "beats_progress": list,            # Per-beat progress tracking
    # ... other fields
}
```

#### 3. Beats Progress Structure
Each beat tracks:
```python
{
    "beat_index": int,
    "title": str,
    "description": str,
    "target_duration": int,
    "status": str,                     # pending/searching/complete
    "shots": list                      # Selected shots
}
```

### Agent Orchestrator Updates

#### Modified compile_edit() Method
- Added `status_callback` parameter
- Invokes callback at key milestones:
  - After plan creation
  - Before/after each beat selection
  - During verification
  - After each iteration

### API Endpoints

#### GET /api/edits/{job_id}/status
Enhanced response includes:
- `plan`: Complete narrative structure with all beats
- `beats_progress`: Array of beat progress objects
- `current_stage`: What the AI is currently doing
- `current_agent`: Which agent is active
- `current_beat`: Details of beat being worked on

## Frontend Integration Points

### Data Flow
1. Frontend polls `/api/edits/{job_id}/status` every 2 seconds
2. Backend updates job status via callbacks during compilation
3. Frontend receives:
   - Overall progress percentage
   - Current stage description
   - Full plan with beats
   - Per-beat progress and selected shots

### Display Components Needed

#### 1. Plan Overview
Shows the narrative structure:
```
📋 Narrative Plan (3 beats)
├─ Beat 1: Introduction (20s) ✓
├─ Beat 2: Main Content (45s) 🔄
└─ Beat 3: Conclusion (15s) ⏳
```

#### 2. Beat Detail Cards
For each beat:
- Title and description
- Target duration
- Status indicator (pending/searching/complete)
- Selected shots (thumbnails + metadata)
- Shot count and actual duration

#### 3. Progress Indicators
- Overall progress bar (0-100%)
- Current stage message ("Searching shots for: Main Content")
- Active agent badge (Planner/Picker/Verifier)
- Per-beat status icons

## Implementation Status

### Completed ✓
- [x] Backend status callback system
- [x] Job tracking enhancements
- [x] Orchestrator callback integration
- [x] API endpoint updates
- [x] Beats progress tracking

### To Do
- [ ] Frontend plan visualization component
- [ ] Beat detail cards with shot previews
- [ ] Visual progress indicators
- [ ] Animation for state transitions
- [ ] Testing with real compilation

## Usage Example

### Backend Callback Flow
```python
# 1. Plan created
status_callback("plan_created", {
    "plan": {
        "beats": [
            {"title": "Intro", "description": "...", "target_duration": 20},
            {"title": "Main", "description": "...", "target_duration": 45}
        ]
    }
})

# 2. Starting beat selection
status_callback("beat_searching", {
    "beat_index": 0,
    "beat_title": "Intro"
})

# 3. Beat complete
status_callback("beat_complete", {
    "beat_index": 0,
    "shots": [
        {"shot_id": 123, "duration": 5.2, ...},
        {"shot_id": 124, "duration": 7.8, ...}
    ]
})
```

### Frontend Consumption
```typescript
// Poll for status
const status = await api.getCompilationStatus(jobId);

// Render plan
if (status.plan) {
    renderPlan(status.plan.beats);
}

// Show beat progress
status.beats_progress.forEach(beat => {
    renderBeatCard(beat);
});

// Update progress bar
setProgress(status.progress);
```

## Benefits

1. **Transparency**: Users see exactly what the AI is doing
2. **Progress Tracking**: Clear indication of compilation stage
3. **Early Preview**: See selected shots before completion
4. **Debugging**: Easier to identify where issues occur
5. **User Confidence**: Real-time feedback reduces perceived wait time

## Future Enhancements

- WebSocket support for true real-time updates (eliminate polling)
- Richer shot metadata in beat cards
- Edit/refine beats before verification
- Export plan as JSON for reuse
- Historical view of iteration changes

## Technical Notes

### Performance Considerations
- Status updates are lightweight (< 10KB typically)
- Polling interval: 2 seconds (adjustable)
- Beat progress arrays scale linearly with beat count
- No significant overhead on compilation process

### Error Handling
- Callback errors are logged but don't fail compilation
- Status endpoint returns last known state if job completes
- Frontend handles missing/incomplete data gracefully

### Compatibility
- Works with existing compilation workflow
- Backward compatible (callbacks are optional)
- No breaking changes to API contracts
