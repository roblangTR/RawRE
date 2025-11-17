# Sequence-Based Visual Analysis Implementation Plan

## Overview

This document outlines the complete implementation plan for enhancing the RAWRE shot picker with Gemini-powered sequence-based visual analysis. This approach addresses narrative flow, jump cuts, and visual continuity by analyzing shots in location-based sequences rather than individually.

## Objectives

1. **Eliminate Jump Cuts**: Detect and prevent jarring cuts between similar shots
2. **Improve Narrative Flow**: Ensure smooth visual transitions within and between scenes
3. **Maintain Location Continuity**: Group and analyze shots from the same location together
4. **Enable Intelligent Sequencing**: Suggest optimal shot progressions (wide → medium → close)
5. **Hybrid AI Approach**: Leverage Gemini for visual analysis, Claude for editorial decisions

## Architecture

### System Components

```
┌─────────────────────────────────────────────────────────────┐
│                    ENHANCED PICKER WORKFLOW                  │
└─────────────────────────────────────────────────────────────┘
                             ↓
                    1. Build Working Set
                    (Semantic Search + Filters)
                             ↓
                    2. Group by Sequences
                    (Location, Time, Visual Similarity)
                             ↓
                ┌────────────────────────────┐
                │  Sequence 1: Parliament    │
                │  Sequence 2: Protest March │
                │  Sequence 3: Interview     │
                │  Sequence 4: Cutaways      │
                └────────────────────────────┘
                             ↓
                    3. Gemini Visual Analysis
                    (Per-Sequence Analysis)
                             ↓
                ┌────────────────────────────┐
                │  Visual Continuity Data:   │
                │  - Transition scores       │
                │  - Jump cut warnings       │
                │  - Shot compatibility      │
                │  - Recommended subsequences│
                └────────────────────────────┘
                             ↓
                    4. Claude Editorial Selection
                    (Using Visual Intelligence)
                             ↓
                    5. Final Shot Selection
                    (With Trim Points)
```

## Implementation Phases

### Phase 1: Sequence Grouping Logic

#### 1.1 Create Sequence Analyzer

**File**: `agent/sequence_analyzer.py`

**Purpose**: Group candidate shots into location-based sequences

**Features**:
- Location-based grouping (from metadata)
- Temporal clustering (shots within time windows)
- Visual similarity clustering (using CLIP embeddings)
- Hybrid approach combining all three methods

**Key Classes**:
```python
class SequenceAnalyzer:
    """Groups shots into logical sequences based on location and context."""
    
    def group_by_sequences(
        self,
        candidates: List[Dict],
        method: str = "hybrid"  # location, temporal, visual, hybrid
    ) -> Dict[str, List[Dict]]:
        """
        Group candidates into sequences.
        
        Returns:
        {
            "parliament_exterior_morning": [shot1, shot2, shot3],
            "protest_march_street": [shot4, shot5, shot6, shot7],
            "interview_indoor": [shot8, shot9],
            "cutaways_various": [shot10, shot11]
        }
        """
```

**Methods**:
- `_group_by_location()`: Use location metadata
- `_group_by_temporal_proximity()`: Cluster shots close in time
- `_group_by_visual_similarity()`: Use CLIP embeddings
- `_hybrid_grouping()`: Combine all methods intelligently

#### 1.2 Database Schema Enhancements

Add location metadata if not already present:

```sql
-- Add location tracking (if needed)
ALTER TABLE shots ADD COLUMN location TEXT;
ALTER TABLE shots ADD COLUMN scene_id TEXT;

-- Index for efficient grouping
CREATE INDEX IF NOT EXISTS idx_shots_location ON shots(location);
CREATE INDEX IF NOT EXISTS idx_shots_scene ON shots(scene_id);
```

### Phase 2: Gemini Visual Analysis

#### 2.1 Extend GeminiAnalyzer Class

**File**: `ingest/gemini_analyzer.py` (enhance existing)

**New Methods**:

```python
class GeminiAnalyzer:
    # Existing methods...
    
    def analyze_sequence_for_picking(
        self,
        sequence_name: str,
        shots: List[Dict],
        previous_shots: List[Dict],
        beat: Dict
    ) -> Dict[str, Any]:
        """
        Analyze a sequence of shots for visual continuity.
        
        Returns detailed analysis including:
        - Individual shot quality scores
        - Intra-sequence transition scores
        - Jump cut warnings
        - Recommended shot progressions
        - Entry/exit points
        """
        
    def analyze_all_sequences(
        self,
        sequences: Dict[str, List[Dict]],
        previous_shots: List[Dict],
        beat: Dict
    ) -> Dict[str, Dict[str, Any]]:
        """
        Analyze all sequences for a beat.
        
        Returns analysis for each sequence.
        """
```

#### 2.2 Sequence Analysis Prompt

**File**: `agent/system_prompts.py` (add new prompt)

**Key Elements**:
```python
def get_sequence_analysis_prompt(
    sequence_name: str,
    shots: List[Dict],
    previous_shots: List[Dict],
    beat: Dict
) -> str:
    """
    Generate prompt for Gemini sequence analysis.
    
    Prompt focuses on:
    1. Intra-sequence flow and continuity
    2. Jump cut detection within sequence
    3. Shot quality assessment
    4. Recommended shot progressions
    5. Entry and exit points
    6. Transition compatibility
    """
```

**Output Schema**:
```json
{
  "sequence_name": "parliament_exterior_morning",
  "total_shots": 4,
  "shots": {
    "shot_123": {
      "quality_score": 8.5,
      "characteristics": {
        "shot_size": "wide",
        "camera_movement": "static",
        "subject_position": "center_left",
        "motion_direction": "left_to_right",
        "composition": "rule_of_thirds",
        "lighting": "natural_soft"
      },
      "best_for": ["sequence_start", "establishing"],
      "works_well_with": [124, 125],
      "avoid_with": [127]
    }
  },
  "recommended_subsequences": [
    {
      "shots": [123, 124, 125],
      "description": "Wide establishing → medium action → close detail",
      "flow_score": 9.2,
      "total_duration": 12.5,
      "rationale": "Classic shot progression with smooth size transitions"
    }
  ],
  "entry_points": [
    {
      "shot_id": 123,
      "transition_from_previous": 7.5,
      "rationale": "Wide shot provides good scene establishment"
    }
  ],
  "exit_points": [
    {
      "shot_id": 125,
      "next_shot_type": "cutaway or different location",
      "rationale": "Close-up provides natural break point"
    }
  ],
  "warnings": [
    {
      "type": "jump_cut",
      "shots": [124, 126],
      "severity": "high",
      "suggestion": "Insert shot 125 between them or use cutaway"
    }
  ]
}
```

### Phase 3: Enhanced Picker Integration

#### 3.1 Update Picker Class

**File**: `agent/picker.py` (enhance existing)

**Changes**:

```python
class Picker:
    def __init__(
        self,
        llm_client: ClaudeClient,
        working_set_builder: WorkingSetBuilder,
        gemini_analyzer: GeminiAnalyzer,
        sequence_analyzer: SequenceAnalyzer  # NEW
    ):
        self.llm_client = llm_client
        self.working_set_builder = working_set_builder
        self.gemini_analyzer = gemini_analyzer
        self.sequence_analyzer = sequence_analyzer  # NEW
    
    def pick_shots_for_beat(
        self,
        beat: Dict,
        story_slug: str,
        previous_selections: Optional[List[Dict]] = None
    ) -> Dict:
        """
        Enhanced picking with sequence-based visual analysis.
        
        Workflow:
        1. Build working set (existing)
        2. Group into sequences (NEW)
        3. Analyze sequences with Gemini (NEW)
        4. Format context with visual data (ENHANCED)
        5. Claude makes selection (ENHANCED)
        6. Parse and return (existing)
        """
        
        # 1. Build working set
        working_set = self.working_set_builder.build_for_beat(...)
        
        # 2. Group by sequences
        sequences = self.sequence_analyzer.group_by_sequences(
            candidates=working_set['shots'],
            method='hybrid'
        )
        
        # 3. Analyze each sequence with Gemini
        sequence_analyses = self.gemini_analyzer.analyze_all_sequences(
            sequences=sequences,
            previous_shots=previous_selections or [],
            beat=beat
        )
        
        # 4. Format enhanced context for Claude
        context = self._format_context_with_sequences(
            beat=beat,
            sequences=sequences,
            sequence_analyses=sequence_analyses,
            previous_selections=previous_selections
        )
        
        # 5. Claude makes selection
        response = self.llm_client.chat(
            query=context,
            module='picker'
        )
        
        # 6. Parse and return
        return self._parse_selection_response(...)
```

#### 3.2 Enhanced Context Formatting

**New Method**: `_format_context_with_sequences()`

**Purpose**: Provide Claude with rich sequence and visual data

**Format**:
```markdown
# Shot Selection Task

## Beat Requirements
Beat 2: "Protesters arrive at parliament"
Target Duration: 15 seconds
Required Types: establishing, action

## Previously Selected Shots
Shot 120: Wide of street (5.2s)
Shot 121: Medium tracking protesters (6.1s)

⚠️ DO NOT reuse these shot IDs

## Available Sequences

### Sequence: "parliament_exterior_morning" (4 shots, 18.5s total)

**Gemini Visual Analysis:**
- Quality: EXCELLENT (avg 8.5/10)
- Best Entry: Shot 123 (wide, transition score: 8.5/10)
- Recommended Progression: [123 → 124 → 125]
  - "Wide establishing → medium action → close detail"
  - Flow score: 9.2/10, Duration: 12.5s
- Exit Point: Shot 125 (close-up, natural break)
- ⚠️ Jump Cut Warning: Avoid shots 124 and 126 together

**Individual Shots:**

#### Shot 123 (RECOMMENDED ENTRY)
- Shot Size: Wide
- Camera: Static
- Quality: 8.5/10
- Duration: 5.2s
- Timecode: 00:10:15:00 - 00:10:20:05
- Transcript: "protesters gather outside parliament gates"
- **Visual Analysis:**
  - Subject Position: Center-left
  - Motion: Left-to-right
  - Composition: Rule of thirds
  - Works well with: 124, 125
  - Best for: Sequence start, establishing
  - Transition from previous: 8.5/10
    → "Smooth continuation from previous wide shot"

[Additional shots...]

### Sequence: "protest_march_street" (5 shots, 22.3s total)

[Similar format...]

## Task

Select shots that:
1. Meet beat requirements
2. Use Gemini's visual recommendations
3. Avoid jump cuts (heed warnings)
4. Create smooth narrative flow
5. Stay within 12-18s duration target

Consider Gemini's recommended progressions but make final editorial decisions based on story needs.
```

### Phase 4: Orchestrator Integration

#### 4.1 Update Orchestrator

**File**: `agent/orchestrator.py` (enhance existing)

**Changes**:

```python
class Orchestrator:
    def __init__(self, config):
        # Existing initializations...
        
        # NEW: Initialize sequence analyzer
        self.sequence_analyzer = SequenceAnalyzer()
        
    def _run_picker(self, plan, story_slug, previous_selections):
        """Enhanced picker with sequence analysis."""
        
        # Create picker with all components
        picker = Picker(
            llm_client=self.llm_client,
            working_set_builder=self.working_set_builder,
            gemini_analyzer=self.gemini_analyzer,  # Existing
            sequence_analyzer=self.sequence_analyzer  # NEW
        )
        
        # Run picking (now with sequence analysis)
        selections = picker.pick_shots_for_beat(...)
        
        return selections
```

### Phase 5: Configuration and Logging

#### 5.1 Configuration Updates

**File**: `config.yaml`

**Additions**:
```yaml
# Gemini video analysis
gemini:
  enabled: true
  workflow_id: "81a571bb-1096-4156-bd09-5ee7fd9047ce"
  use_proxy_clips: true
  
  # Sequence-based picking (NEW)
  picking:
    enabled: true
    sequence_grouping_method: "hybrid"  # location, temporal, visual, hybrid
    sequence_batch_size: 6  # Max shots per sequence to analyze
    analyze_in_parallel: false  # Parallel sequence analysis
    include_previous_context: true

# Sequence analysis (NEW)
sequences:
  temporal_window_minutes: 5  # Group shots within 5 min
  visual_similarity_threshold: 0.7  # CLIP similarity
  min_shots_per_sequence: 2
  max_shots_per_sequence: 8
```

#### 5.2 Enhanced Logging

**Add detailed logging throughout**:

```python
logger.info(f"[PICKER] Grouped {len(working_set['shots'])} shots into {len(sequences)} sequences")

for seq_name, seq_shots in sequences.items():
    logger.info(f"[PICKER]   - {seq_name}: {len(seq_shots)} shots")

logger.info(f"[GEMINI] Analyzing {len(sequences)} sequences...")

for seq_name in sequences:
    logger.info(f"[GEMINI]   Analyzing sequence: {seq_name}")
    
logger.info(f"[PICKER] Gemini visual analysis complete")
logger.info(f"[PICKER]   - Recommended subsequences: {total_recommendations}")
logger.info(f"[PICKER]   - Jump cut warnings: {total_warnings}")
```

### Phase 6: Testing and Validation

#### 6.1 Unit Tests

**File**: `tests/test_sequence_analyzer.py`

```python
def test_sequence_grouping_by_location():
    """Test that shots are grouped correctly by location."""
    
def test_sequence_grouping_by_temporal():
    """Test temporal clustering of shots."""
    
def test_hybrid_sequence_grouping():
    """Test hybrid approach combines methods correctly."""
```

**File**: `tests/test_gemini_sequence_analysis.py`

```python
def test_sequence_analysis_format():
    """Test Gemini returns correct JSON schema."""
    
def test_jump_cut_detection():
    """Test that jump cuts are identified."""
    
def test_transition_scoring():
    """Test transition scores are reasonable."""
```

#### 6.2 Integration Tests

**File**: `tests/test_picker_with_sequences.py`

```python
def test_picker_with_sequence_analysis():
    """Test complete picker workflow with sequences."""
    
def test_picker_uses_visual_recommendations():
    """Test that Claude incorporates Gemini recommendations."""
    
def test_picker_avoids_jump_cuts():
    """Test that flagged jump cuts are avoided."""
```

#### 6.3 Manual Testing

**Test Scenarios**:

1. **Single Location Scene**
   - Upload shots from one location
   - Verify grouping into single sequence
   - Check Gemini identifies jump cuts
   - Verify Claude follows recommendations

2. **Multi-Location Story**
   - Upload shots from 3+ locations
   - Verify correct sequence grouping
   - Check inter-sequence transitions
   - Verify smooth location changes

3. **Edge Cases**
   - Very few shots (< 5)
   - Many shots (> 50)
   - No clear location metadata
   - Mixed quality footage

### Phase 7: Documentation

#### 7.1 User Documentation

**File**: `docs/SEQUENCE_BASED_PICKING.md`

**Contents**:
- Overview of sequence-based approach
- How sequences are detected
- How visual analysis works
- Benefits for editors
- Configuration options
- Troubleshooting

#### 7.2 Developer Documentation

**File**: `docs/SEQUENCE_ANALYSIS_TECHNICAL.md`

**Contents**:
- Architecture diagrams
- API reference
- Prompt engineering details
- Performance considerations
- Extending the system

#### 7.3 Update Existing Docs

**Files to update**:
- `docs/GEMINI_INTEGRATION.md` - Add picking use case
- `docs/PROJECT_SUMMARY.md` - Add sequence analysis
- `README.md` - Update features list

## Implementation Timeline

### Week 1: Foundation
- [x] Design architecture and plan
- [ ] Create `SequenceAnalyzer` class
- [ ] Implement grouping methods
- [ ] Add unit tests for sequence grouping

### Week 2: Gemini Integration
- [ ] Extend `GeminiAnalyzer` with sequence methods
- [ ] Design and test sequence analysis prompt
- [ ] Implement batch sequence analysis
- [ ] Add Gemini analysis tests

### Week 3: Picker Enhancement
- [ ] Update `Picker` class with sequence support
- [ ] Implement enhanced context formatting
- [ ] Update orchestrator wiring
- [ ] Add integration tests

### Week 4: Testing and Refinement
- [ ] Manual testing with real footage
- [ ] Performance optimization
- [ ] Tune prompts and thresholds
- [ ] Bug fixes and refinements

### Week 5: Documentation and Deployment
- [ ] Write user documentation
- [ ] Write developer documentation
- [ ] Update configuration guide
- [ ] Deploy and monitor

## Success Metrics

### Quality Improvements
- **Jump Cut Reduction**: Target < 5% of edits have jump cuts
- **Transition Quality**: Average transition score > 7.5/10
- **Editor Satisfaction**: Qualitative feedback from users
- **Iteration Reduction**: Fewer picker iterations needed

### Performance Metrics
- **Sequence Analysis Time**: < 30s for typical beat
- **Total Picker Time**: < 60s (including all steps)
- **API Cost**: < $0.25 per compilation
- **Success Rate**: > 90% of compilations approved

### System Metrics
- **Sequence Detection Accuracy**: > 85% correctly grouped
- **Gemini Analysis Success**: > 95% valid responses
- **Claude Adoption Rate**: > 80% uses Gemini recommendations

## Rollout Strategy

### Phase 1: Alpha Testing (Week 5)
- Enable for development environment only
- Test with small dataset
- Gather initial feedback
- Fix critical bugs

### Phase 2: Beta Testing (Week 6-7)
- Enable for select users
- Monitor performance and costs
- Collect user feedback
- Refine prompts and thresholds

### Phase 3: Production (Week 8+)
- Gradual rollout to all users
- Monitor system health
- Provide user training
- Continuous improvement

## Rollback Plan

If issues arise:

1. **Quick Rollback**: Set `gemini.picking
