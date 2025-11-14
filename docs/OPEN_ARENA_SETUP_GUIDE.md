# Open Arena Workflow Setup Guide

## Quick Reference: What You Need to Build

You need to create **ONE workflow** in Open Arena that will be used by all three agent modules (Planner, Picker, Verifier).

## Workflow Configuration

### Basic Settings

```yaml
Workflow Name: Reuters News Edit Agent
Model: claude-3-5-sonnet-20241022
Temperature: 0.1
Max Tokens: 4096
```

### System Prompt

Copy the **AGENT_SYSTEM_PROMPT** from `agent/system_prompts.py` (lines 1-80).

The prompt begins with:
```
You are an expert news video editor with deep knowledge of broadcast journalism, 
storytelling, and video production. You work for Reuters, creating compelling 
news packages from raw footage (rushes).
```

## Step-by-Step Setup

### 1. Create Workflow in Open Arena

1. Log into Open Arena portal at: https://open-arena.thomsonreuters.com
2. Navigate to "Workflows" section
3. Click "Create New Workflow"
4. Enter the configuration:
   - **Name:** Reuters News Edit Agent
   - **Model:** claude-3-5-sonnet-20241022
   - **Temperature:** 0.1
   - **Max Tokens:** 4096
   - **System Prompt:** Copy from `agent/system_prompts.py` (AGENT_SYSTEM_PROMPT)
5. Save the workflow
6. **Copy the Workflow ID** (you'll need this next)

### 2. Configure Environment

Add the workflow ID to your `.env` file:

```bash
# Open .env file and add:
WORKFLOW_ID=your-workflow-id-here
```

### 3. Test the Connection

```bash
# Test authentication
python test_auth.py

# Should output:
# ✓ Authentication successful
# ✓ Token retrieved
```

### 4. Test LLM Integration

```bash
# Test basic LLM call
python -c "
from agent.llm_client import ClaudeClient
from agent.system_prompts import get_system_prompt
import os

client = ClaudeClient()
response = client.chat(
    query='Describe your role as a news video editor in one sentence.',
    workflow_id=os.getenv('WORKFLOW_ID'),
    system_prompt=get_system_prompt('agent')
)
print('Response:', response['content'])
"
```

## How the System Works

### Single Workflow, Multiple Prompts

The system uses **one workflow** but dynamically switches system prompts based on the agent module:

```python
# Planner uses PLANNER_SYSTEM_PROMPT
planner = Planner(llm_client, working_set_builder)
plan = planner.create_plan(brief, target_duration)

# Picker uses PICKER_SYSTEM_PROMPT  
picker = Picker(llm_client, working_set_builder)
selections = picker.select_shots(plan, working_set)

# Verifier uses VERIFIER_SYSTEM_PROMPT
verifier = Verifier(llm_client)
verification = verifier.verify_edit(plan, selections, brief)
```

Each module automatically loads its specific system prompt via `get_system_prompt()`.

## System Prompts Overview

### 1. AGENT_SYSTEM_PROMPT (Main)
- **Used by:** General agent operations
- **Purpose:** Establishes role as expert news video editor
- **Key capabilities:** Editorial judgment, visual storytelling, technical knowledge

### 2. PLANNER_SYSTEM_PROMPT
- **Used by:** Planner module
- **Purpose:** Creates story structures from briefs
- **Output:** JSON with story beats, timing, requirements

### 3. PICKER_SYSTEM_PROMPT
- **Used by:** Picker module
- **Purpose:** Selects optimal shots for each beat
- **Output:** JSON with selected shots and reasoning

### 4. VERIFIER_SYSTEM_PROMPT
- **Used by:** Verifier module
- **Purpose:** Reviews edits for quality and compliance
- **Output:** JSON verification report with scores

## Testing Each Module

### Test Planner

```python
from agent.planner import Planner
from agent.llm_client import ClaudeClient
from agent.working_set import WorkingSetBuilder
from storage.database import ShotsDatabase
from storage.vector_index import WorkingSetIndices

# Initialize
db = ShotsDatabase('data/shots.db')
indices = WorkingSetIndices()
builder = WorkingSetBuilder(db, indices)
client = ClaudeClient()

planner = Planner(client, builder)

# Test
plan = planner.create_plan(
    brief="Create a 90-second package about climate change protests",
    target_duration=90,
    working_set={'shots': [], 'metadata': {}}
)

print("Plan:", plan)
```

### Test Picker

```python
from agent.picker import Picker

picker = Picker(client, builder)

selections = picker.select_shots(
    plan=plan,
    working_set={'shots': [...], 'metadata': {...}}
)

print("Selections:", selections)
```

### Test Verifier

```python
from agent.verifier import Verifier

verifier = Verifier(client)

verification = verifier.verify_edit(
    plan=plan,
    selections=selections,
    brief="Original brief text"
)

print("Verification:", verification)
```

## Troubleshooting

### Issue: 403 Forbidden

**Cause:** Workflow ID incorrect or authentication failed

**Solution:**
1. Verify workflow ID in `.env` is correct
2. Check authentication token: `python test_auth.py`
3. Ensure workflow has correct permissions in Open Arena

### Issue: Unexpected Response Format

**Cause:** LLM not following JSON format

**Solution:**
1. Check system prompt includes JSON format instructions
2. Verify temperature is set to 0.1 (low for consistency)
3. Review the prompt in `agent/system_prompts.py`

### Issue: Timeout Errors

**Cause:** Request taking too long

**Solution:**
1. Reduce context size (fewer shots in working set)
2. Increase timeout in `agent/llm_client.py`
3. Check network connectivity

### Issue: Module-Specific Prompt Not Working

**Cause:** System prompt not being passed correctly

**Solution:**
```python
# Verify prompt is loaded correctly
from agent.system_prompts import get_system_prompt

print("Planner prompt:", get_system_prompt('planner')[:100])
print("Picker prompt:", get_system_prompt('picker')[:100])
print("Verifier prompt:", get_system_prompt('verifier')[:100])
```

## Environment Variables Required

```bash
# .env file should contain:

# Open Arena Authentication
OPEN_ARENA_CLIENT_ID=your-client-id
OPEN_ARENA_CLIENT_SECRET=your-client-secret
OPEN_ARENA_TOKEN_URL=https://api.thomsonreuters.com/auth/oauth/v2/token
OPEN_ARENA_API_URL=https://api.thomsonreuters.com/open-arena/v1

# Workflow Configuration
WORKFLOW_ID=your-workflow-id-here

# Optional: Override defaults
# CLAUDE_MODEL=claude-3-5-sonnet-20241022
# CLAUDE_TEMPERATURE=0.1
# CLAUDE_MAX_TOKENS=4096
```

## Next Steps After Setup

1. ✅ Create workflow in Open Arena
2. ✅ Add workflow ID to `.env`
3. ✅ Test authentication
4. ✅ Test each module
5. 🔄 Run integration tests
6. 🔄 Process sample video content
7. 🔄 Generate first EDL output

## Support

- **System Prompts:** See `agent/system_prompts.py`
- **LLM Client:** See `agent/llm_client.py`
- **Full Documentation:** See `OPEN_ARENA_WORKFLOW.md`
- **Test Suite:** Run `./run_tests.sh`

---

**Last Updated:** 2025-01-14
**Version:** 1.0
