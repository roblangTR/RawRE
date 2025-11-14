# News Edit Agent - Configuration Guide

## Overview

The news edit agent is fully configured and ready to use with Open Arena workflows. This guide explains the configuration and how everything works together.

## Current Configuration Status

✅ **Authentication**: OAuth2 configured and working
✅ **Workflows**: Module-specific workflows configured
✅ **LLM Client**: Properly extracting responses from Open Arena
✅ **Agent Modules**: All three agents configured to use their workflows

## Environment Variables

Your `.env` file contains:

```bash
# Open Arena API configuration (OAuth2)
TR_CLIENT_ID=HdzWdD8oaf3qqEdD5slrKGekdgajf4qm
TR_CLIENT_SECRET=EUxKIPdnA9rAIGIjjjH9z3GzeOKf1lnJt4KDKq8UYqUZOMZMTRruvySwPhAGD_Jv
TR_AUDIENCE=49d70a58-9509-48a2-ae12-4f6e00ceb270

# Open Arena Workflow IDs
WORKFLOW_ID=85d284c0-852d-4893-bcb4-1a5addb076d2              # Main/fallback
PLANNER_WORKFLOW_ID=49f87950-7584-469e-bf5c-b1cc54bc42f3      # Planner agent
PICKER_WORKFLOW_ID=60aef7b1-b2b6-46d6-9a58-947ec8926881       # Picker agent
VERIFIER_WORKFLOW_ID=c404735a-c260-4a20-9e69-896a8f61729c     # Verifier agent
```

## How It Works

### 1. Authentication Flow

```python
from agent.openarena_auth import get_auth_token

# Automatically handles OAuth2 token acquisition
token = get_auth_token()
```

- Uses client credentials from environment variables
- Obtains OAuth2 token from Open Arena
- Token is cached and reused across requests

### 2. LLM Client Usage

```python
from agent.llm_client import ClaudeClient

client = ClaudeClient()

# Automatic workflow selection based on module
response = client.chat(
    query="Your prompt here",
    system_prompt="Optional system prompt",
    module='planner'  # Uses PLANNER_WORKFLOW_ID
)

# Extract the response
content = response['content']
```

**Key Features:**
- Automatically selects workflow based on `module` parameter
- Falls back to `WORKFLOW_ID` if module-specific workflow not set
- Properly extracts content from Open Arena's nested response structure
- Logs which workflow is being used for debugging

### 3. Agent Module Integration

Each agent module automatically uses its specific workflow:

**Planner** (`agent/planner.py`):
```python
response = self.llm_client.chat(
    query=context,
    system_prompt=get_system_prompt('planner'),
    max_tokens=2000,
    module='planner'  # Uses PLANNER_WORKFLOW_ID
)
```

**Picker** (`agent/picker.py`):
```python
response = self.llm_client.chat(
    query=context,
    system_prompt=get_system_prompt('picker'),
    max_tokens=1500,
    module='picker'  # Uses PICKER_WORKFLOW_ID
)
```

**Verifier** (`agent/verifier.py`):
```python
response = self.llm_client.chat(
    query=context,
    system_prompt=get_system_prompt('verifier'),
    max_tokens=2000,
    module='verifier'  # Uses VERIFIER_WORKFLOW_ID
)
```

## Testing the Configuration

### 1. Test Authentication
```bash
python test_auth.py
```
Expected output: ✓ Token obtained successfully

### 2. Test LLM Client
```bash
python -m agent.llm_client
```
Expected output: ✓ Response received from Claude

### 3. Test Full Pipeline
```bash
# Ingest video rushes
python cli.py ingest --input ./rushes --story 'test-story'

# Compile an edit
python cli.py compile --story 'test-story' --brief 'Create a 60-second news package about...'
```

## Workflow Configuration in Open Arena

Each workflow in Open Arena should be configured with:

1. **LLM Component**: Claude 3.5 Sonnet or Claude 4.5 Sonnet
2. **System Prompt**: Role-specific prompt from `agent/system_prompts.py`
3. **Model Parameters**:
   - Temperature: 0.1 (for consistency)
   - Max tokens: 2000-4096 (depending on module)

The system prompts are automatically included when the agent modules call the LLM client.

## Response Format

Open Arena returns responses in this structure:

```json
{
  "request_id": "...",
  "workflow_asset_id": "...",
  "result": {
    "answer": {
      "llm_LLM_task": "The actual response text here"
    },
    "cost_track": {...},
    "component_log_data": {...}
  }
}
```

The LLM client automatically extracts the answer from `result.answer.{node_id}`.

## Troubleshooting

### Issue: "No workflow_id provided"
**Solution**: Ensure `.env` file has `WORKFLOW_ID` set

### Issue: "Authentication failed"
**Solution**: Check `TR_CLIENT_ID`, `TR_CLIENT_SECRET`, and `TR_AUDIENCE` in `.env`

### Issue: "Response parsing failed"
**Solution**: The LLM client now properly extracts content from Open Arena's nested structure

### Issue: Module not using correct workflow
**Solution**: Check that module-specific workflow ID is set in `.env` (e.g., `PLANNER_WORKFLOW_ID`)

## Next Steps

The system is fully configured and ready to use. You can now:

1. **Ingest video content**: Process rushes and build the shot database
2. **Compile edits**: Use the three-agent pipeline to create news packages
3. **Export outputs**: Generate EDL or FCPXML files for editing systems

For detailed usage instructions, see `README.md`.

## Configuration Summary

| Component | Status | Notes |
|-----------|--------|-------|
| Authentication | ✅ Working | OAuth2 with client credentials |
| Main Workflow | ✅ Configured | ID: 85d284c0-852d-4893-bcb4-1a5addb076d2 |
| Planner Workflow | ✅ Configured | ID: 49f87950-7584-469e-bf5c-b1cc54bc42f3 |
| Picker Workflow | ✅ Configured | ID: 60aef7b1-b2b6-46d6-9a58-947ec8926881 |
| Verifier Workflow | ✅ Configured | ID: c404735a-c260-4a20-9e69-896a8f61729c |
| LLM Client | ✅ Working | Properly extracts Open Arena responses |
| Agent Modules | ✅ Integrated | All use module-specific workflows |

**Configuration is complete and ready for production use!**
