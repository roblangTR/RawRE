# Open Arena Workflow Configuration

This document describes the recommended Open Arena workflow setup for the News Edit Agent.

## Overview

The News Edit Agent uses Claude via Open Arena to perform intelligent video editing tasks. The workflow should be configured to support the agent's three main modules:

1. **Planner** - Creates story structures from editorial briefs
2. **Picker** - Selects optimal shots for each story beat
3. **Verifier** - Reviews compiled edits for quality

## Recommended Workflow Configuration

### Basic Settings

```yaml
Workflow Name: Reuters News Edit Agent
Model: claude-3-5-sonnet-20241022
Temperature: 0.1  # Low temperature for consistent, focused responses
Max Tokens: 4096  # Sufficient for detailed analysis
```

### System Prompt

Use the main agent system prompt from `agent/system_prompts.py`:

```
You are an expert news video editor with deep knowledge of broadcast journalism, 
storytelling, and video production. You work for Reuters, creating compelling 
news packages from raw footage (rushes).

## Your Role

You help journalists and editors compile news stories by:
1. Analyzing raw video footage, transcripts, and metadata
2. Planning story structures based on editorial briefs
3. Selecting the best shots to tell the story effectively
4. Sequencing shots for maximum impact and clarity
5. Verifying edits meet broadcast standards

## Your Expertise

**Editorial Judgment:**
- Strong news sense and understanding of story hierarchy
- Ability to identify the most newsworthy elements
- Knowledge of Reuters editorial standards and ethics

**Visual Storytelling:**
- Shot selection based on composition, action, and relevance
- Pacing and rhythm for different story types
- Use of sequences: establishing shots, action, cutaways, reactions
- Visual variety and avoiding jump cuts

**Technical Knowledge:**
- Shot types: SOT (Sound on Tape), GV (General View), CUTAWAY
- Shot composition: wide, medium, close-up
- Audio considerations: nat sound, ambient audio, interview quality
- Timing and duration for broadcast standards

**Broadcast Standards:**
- Typical package lengths: 60-90 seconds for breaking news, 90-120 for features
- Shot duration guidelines: 3-5 seconds minimum
- Audio/visual sync requirements
- Legal and ethical considerations

## Your Workflow

1. Understand the Brief: Analyze story requirements and editorial angle
2. Review Available Content: Examine shots, transcripts, and metadata
3. Plan the Structure: Create beat-by-beat outline
4. Select Shots: Choose specific shots that best serve each beat
5. Sequence Carefully: Order shots for narrative flow
6. Verify Quality: Check timing, pacing, and broadcast standards

## Key Principles

1. Story First: Every shot must serve the narrative
2. Show, Don't Tell: Prefer visual storytelling
3. Accuracy: Never misrepresent what footage shows
4. Efficiency: Respect the target duration
5. Quality: Maintain high broadcast standards

You communicate professionally but conversationally, explaining your 
editorial choices clearly.
```

**See `agent/system_prompts.py` for the complete prompt text.**

## Module-Specific Configurations

### 1. Planner Module

**Purpose**: Create detailed story structures from editorial briefs

**System Prompt**: Use `PLANNER_SYSTEM_PROMPT` from `agent/system_prompts.py`

**Input Format**:
```json
{
  "task": "plan",
  "brief": "Story description and angle",
  "target_duration": 90,
  "available_shots_summary": "Brief overview of available content"
}
```

**Expected Output**: JSON structure with story beats

**Settings**:
- Temperature: 0.1 (consistent planning)
- Max Tokens: 2048 (sufficient for detailed plans)

### 2. Picker Module

**Purpose**: Select optimal shots for each story beat

**System Prompt**: Use `PICKER_SYSTEM_PROMPT` from `agent/system_prompts.py`

**Input Format**:
```json
{
  "task": "pick",
  "beat": {
    "beat_number": 1,
    "description": "Opening shot",
    "requirements": ["Wide establishing shot"]
  },
  "candidates": [
    {
      "shot_id": "shot_001",
      "description": "Wide view of city",
      "duration": 8.5,
      "similarity_score": 0.92
    }
  ]
}
```

**Expected Output**: JSON with selected shots and reasoning

**Settings**:
- Temperature: 0.1 (consistent selection)
- Max Tokens: 2048

### 3. Verifier Module

**Purpose**: Review compiled edits for quality

**System Prompt**: Use `VERIFIER_SYSTEM_PROMPT` from `agent/system_prompts.py`

**Input Format**:
```json
{
  "task": "verify",
  "edit": {
    "shots": ["shot_001", "shot_045", "shot_023"],
    "total_duration": 87.5
  },
  "original_brief": "Story requirements",
  "plan": "Original story plan"
}
```

**Expected Output**: JSON verification report

**Settings**:
- Temperature: 0.1 (consistent evaluation)
- Max Tokens: 3072 (detailed feedback)

## Usage in Code

```python
from agent.llm_client import ClaudeClient
from agent.system_prompts import get_system_prompt

# Initialize client
client = ClaudeClient(
    model="claude-3-5-sonnet-20241022",
    temperature=0.1
)

# Use for planning
response = client.chat(
    query="Plan a 90-second story about...",
    workflow_id=os.getenv('WORKFLOW_ID'),
    system_prompt=get_system_prompt('planner'),
    context="Available shots: ..."
)

# Parse JSON response
plan = client.chat_with_json(
    query="Plan a 90-second story about...",
    workflow_id=os.getenv('WORKFLOW_ID'),
    system_prompt=get_system_prompt('planner'),
    context="Available shots: ..."
)
```

## Best Practices

### Context Management

- **Keep context focused**: Only include relevant shots for each query
- **Use summaries**: For large shot libraries, provide summaries rather than full details
- **Structured data**: Format shot metadata consistently (JSON preferred)

### Prompt Engineering

- **Be specific**: Provide clear requirements and constraints
- **Include examples**: Show desired output format
- **Set expectations**: Specify response format (JSON, structured text, etc.)

### Error Handling

- **Validate JSON**: Always parse and validate JSON responses
- **Fallback logic**: Have fallback strategies if LLM response is unexpected
- **Logging**: Log all LLM interactions for debugging

### Performance Optimization

- **Batch when possible**: Group related queries
- **Cache results**: Store plans and selections to avoid re-computation
- **Parallel processing**: Run independent queries concurrently

## Testing the Workflow

### 1. Create Workflow in Open Arena

1. Log into Open Arena portal
2. Create new workflow with settings above
3. Copy the workflow ID
4. Add to `.env` as `WORKFLOW_ID=your-workflow-id`

### 2. Test Basic Functionality

```bash
# Test authentication
python test_auth.py

# Test LLM client
python -m agent.llm_client

# Test with system prompt
python -c "
from agent.llm_client import ClaudeClient
from agent.system_prompts import get_system_prompt
import os

client = ClaudeClient()
response = client.chat(
    query='Describe your role as a news video editor',
    workflow_id=os.getenv('WORKFLOW_ID'),
    system_prompt=get_system_prompt('agent')
)
print(response['content'])
"
```

### 3. Test Each Module

Test each module (planner, picker, verifier) with sample data to ensure:
- Correct JSON output format
- Appropriate reasoning and analysis
- Consistent behavior across runs

## Troubleshooting

### Common Issues

**403 Forbidden**
- Check workflow ID is correct
- Verify authentication token is valid
- Ensure workflow has correct permissions

**Unexpected Response Format**
- Review system prompt clarity
- Add explicit format instructions
- Include example outputs in prompt

**Timeout Errors**
- Reduce context size
- Increase timeout setting
- Check network connectivity

**Inconsistent Results**
- Lower temperature (try 0.0)
- Make prompts more specific
- Add constraints and requirements

## Next Steps

1. **Create the workflow** in Open Arena with the recommended settings
2. **Test thoroughly** with sample data
3. **Integrate** into the agent modules (planner, picker, verifier)
4. **Monitor performance** and adjust prompts as needed
5. **Iterate** based on real-world usage

The system prompts are designed to be production-ready but may need fine-tuning based on your specific use cases and content types.
