# Agent Context Reference

**Document:** What context is sent to each agent in the RAWRE system  
**Date:** 14 November 2025

---

## Overview

Each agent in the RAWRE system receives:
1. **System Prompt** - Defines the agent's role and output format
2. **Context** - Task-specific information formatted as the user query

This document details exactly what context each agent receives.

---

## 1. Planner Agent

**Purpose:** Creates beat-by-beat story structure from editorial brief

### System Prompt
- Loaded from `agent/system_prompts.py` via `get_system_prompt('planner')`
- Defines role as story planner
- Specifies JSON output format for beats

### Context Sent (as query parameter)

```markdown
# Story Planning Task

## Editorial Brief
[The story brief text]

## Requirements
- Target Duration: [X] seconds
- Available Material: [N] shots, [X]s total
- Shot Types Available: {SOT: X, GV: Y, CUTAWAY: Z}

## Constraints (if any)
- [constraint 1]
- [constraint 2]

## Available Material Summary

### SOT Shots (N)
- Shot [ID]: [duration]s
  "[transcript excerpt]"
- Shot [ID]: [duration]s
  "[transcript excerpt]"
[Top 5 most relevant SOT shots]

### GV Shots (N)
- Shot [ID]: [duration]s
  "[transcript excerpt if available]"
[Top 5 most relevant GV shots]

### CUTAWAY Shots (N)
- Shot [ID]: [duration]s
[Top 5 most relevant cutaway shots]

## Task
Create a beat-by-beat plan for this story that:
1. Tells a clear, compelling narrative
2. Meets the target duration
3. Uses the available material effectively
4. Follows broadcast news standards

For each beat, specify:
- Beat number and title
- Description of what happens
- Target duration (seconds)
- Required shot types (SOT/GV/CUTAWAY)
- Key requirements or constraints

Return your plan as a JSON object with this structure:
[JSON schema example]
```

**Key Information Included:**
- Editorial brief (full text)
- Target duration
- Available material statistics
- Top 5 most relevant shots per shot type
- Shot transcripts (truncated to 100 chars)
- Relevance scores
- JSON output format specification

**Working Set:** Built using `working_set_builder.build_for_query()` with:
- `max_shots=100` (larger set for planning)
- `include_neighbors=True`
- Semantic search based on the brief text

---

## 2. Picker Agent

**Purpose:** Selects specific shots for each beat based on the plan

### System Prompt
- Loaded from `agent/system_prompts.py` via `get_system_prompt('picker')`
- Defines role as shot selector
- Specifies JSON output format for selections

### Context Sent (as query parameter)

```markdown
# Shot Selection Task

## Beat [N]: [Beat Title]
**Description:** [Beat description from plan]
**Target Duration:** [X] seconds
**Required Shot Types:** [SOT, GV, etc.]

**Requirements:**
- [requirement 1]
- [requirement 2]

## Previously Selected Shots
([N] shots already selected)

## Candidate Shots
Total: [N] shots available

### Shot [ID]
- Type: [SOT/GV/CUTAWAY]
- Duration: [X]s
- Timecode: [TC_IN] - [TC_OUT]
- Shot Size: [Close-up/Medium/Wide/etc.]
- Camera Movement: [Static/Pan/Tilt/etc.]
- Composition: [Description]
- Subjects: [List of subjects]
- Action: [What's happening]
- Quality: [Good/Fair/Poor]
- Visual Description: [Gemini description, truncated to 200 chars]
- Relevance: [X.XX]
- Transcript: "[ASR text, truncated to 150 chars]"
- Has Face: [Yes/No]

[Repeated for each candidate shot]

## Task
Select the best shots for this beat that:
1. Meet the beat requirements
2. Fit within the target duration
3. Tell a coherent story
4. Follow broadcast standards
5. Don't repeat previously selected shots

Return your selection as JSON:
[JSON schema example]
```

**Key Information Included:**
- Beat details (title, description, target duration, requirements)
- Previously selected shots (to avoid repetition)
- Candidate shots with FULL metadata:
  - Basic info (type, duration, timecode)
  - Gemini visual analysis (shot size, movement, composition, subjects, action, quality, description)
  - Relevance score from semantic search
  - ASR transcript (if available)
  - Face detection results
- JSON output format specification

**Working Set:** Built using `working_set_builder.build_for_beat()` with:
- `max_shots=30` (focused set for picking)
- Semantic search based on beat description and requirements
- Beat-specific filtering

---

## 3. Verifier Agent

**Purpose:** Reviews compiled edit for quality and compliance

### System Prompt
- Loaded from `agent/system_prompts.py` via `get_system_prompt('verifier')`
- Defines role as quality verifier
- Specifies JSON output format for verification results

### Context Sent (as query parameter)

```markdown
# Edit Verification Task

## Editorial Brief
[The story brief text]

## Story Plan
Target Duration: [X]s
Planned Duration: [X]s
Total Beats: [N]

### Beat [N]: [Title]
- Description: [Description]
- Target Duration: [X]s

[Repeated for each beat]

## Compiled Edit
Total Shots: [N]
Total Duration: [X]s

### Beat [N]: [Title]
- Shots Selected: [N]
- Duration: [X]s
- Reasoning: [Picker's reasoning]

  * Shot [ID]: [X]s
    Reason: [Why this shot was selected]
  * Shot [ID]: [X]s
    Reason: [Why this shot was selected]

[Repeated for each beat]

## Verification Criteria

Evaluate the edit on these dimensions:

1. **Narrative Flow** (1-10)
   - Does the story flow logically?
   - Are transitions smooth?
   - Is the pacing appropriate?

2. **Brief Compliance** (1-10)
   - Does it match the editorial brief?
   - Are key points covered?
   - Is the tone appropriate?

3. **Technical Quality** (1-10)
   - Are shot types used appropriately?
   - Is duration within target?
   - Are there technical issues?

4. **Broadcast Standards** (1-10)
   - Does it meet broadcast standards?
   - Is it balanced and fair?
   - Are there any compliance issues?

## Task
Provide a comprehensive verification report as JSON:
[JSON schema example with scores, strengths, issues, recommendations, approved flag]
```

**Key Information Included:**
- Original editorial brief
- Complete story plan with all beats
- Complete compiled edit with:
  - All selected shots per beat
  - Shot durations
  - Picker's reasoning for each selection
  - Beat-level reasoning
- Verification criteria (4 dimensions)
- JSON output format specification

**No Working Set:** Verifier doesn't use semantic search - it evaluates the complete plan and selections provided.

---

## Context Flow Summary

```
USER INPUT (Story Brief)
    ↓
PLANNER receives:
    - Brief text
    - Target duration
    - Working set: 100 shots (semantic search on brief)
    - Shot metadata (type, duration, transcript excerpts)
    ↓
PLANNER outputs: Beat-by-beat plan
    ↓
PICKER receives (for each beat):
    - Beat details (title, description, requirements)
    - Working set: 30 shots (semantic search on beat description)
    - FULL shot metadata (Gemini analysis, transcripts, etc.)
    - Previously selected shots
    ↓
PICKER outputs: Selected shots per beat
    ↓
VERIFIER receives:
    - Original brief
    - Complete plan
    - Complete selections with reasoning
    - Verification criteria
    ↓
VERIFIER outputs: Quality scores, issues, approval decision
```

---

## Key Differences Between Agents

### Planner
- **Focus:** Strategic planning
- **Working Set Size:** 100 shots (broad overview)
- **Shot Detail:** Summary level (type, duration, transcript excerpts)
- **Search Query:** Story brief text

### Picker
- **Focus:** Tactical selection
- **Working Set Size:** 30 shots (focused candidates)
- **Shot Detail:** Full detail (Gemini analysis, complete metadata)
- **Search Query:** Beat description + requirements

### Verifier
- **Focus:** Quality assessment
- **Working Set Size:** N/A (no search)
- **Shot Detail:** Selected shots only with reasoning
- **Input:** Complete plan + selections

---

## Semantic Search Integration

### How Working Sets Are Built

1. **Query Formulation:**
   - Planner: Uses story brief text
   - Picker: Uses beat description + requirements

2. **Vector Search:**
   - Queries ChromaDB with sentence-transformers embeddings
   - Returns shots ranked by semantic similarity
   - Relevance scores included in results

3. **Enrichment:**
   - Adds full shot metadata from database
   - Includes Gemini visual analysis
   - Includes ASR transcripts
   - Calculates statistics (shot type counts, total duration)

4. **Context Formatting:**
   - Organizes shots by type
   - Shows top N most relevant per type
   - Truncates long text fields
   - Formats for LLM consumption

---

## LLM API Call Structure

For all agents, the call structure is:

```python
response = llm_client.chat(
    query=context,                    # Formatted context (see above)
    system_prompt=system_prompt,      # Agent-specific system prompt
    max_tokens=max_tokens,            # 2000 for Planner/Verifier, 1500 for Picker
    module='agent_name'               # 'planner', 'picker', or 'verifier'
)
```

The `llm_client` then constructs the Open Arena API payload:

```python
payload = {
    "workflow_id": workflow_id,
    "query": query,                   # The formatted context
    "is_persistence_allowed": False,
    "modelparams": {
        model: {
            "temperature": "0.1",
            "max_tokens": str(max_tokens),
            "system_prompt": system_prompt  # Agent-specific system prompt
        }
    }
}
```

---

## Summary

**Yes, system prompts ARE being sent to the LLM** via the `modelparams[model]["system_prompt"]` field.

**Context sent as query includes:**
- **Planner:** Brief + working set summary (100 shots)
- **Picker:** Beat details + full shot metadata (30 shots per beat)
- **Verifier:** Brief + complete plan + complete selections

**Each agent receives specialized context** tailored to its specific task, with the appropriate level of detail and the right working set size for effective decision-making.
