# LLM Client Simplification

## Overview

Simplified the LLM client to remove redundant model parameters from API requests. All model configuration (model type, temperature, max_tokens, system_prompt) is now managed in Open Arena workflows, making the workflows the single source of truth.

## Changes Made

### 1. Modified `agent/llm_client.py`

**Removed:**
- `system_prompt` parameter from `chat()` method
- `max_tokens` parameter from `chat()` method (default was 4096)
- `modelparams` section from API request payload
- System prompt logging in request details

**Simplified:**
- `chat()` method now only takes: `query`, `workflow_id`, `context`, `module`
- `chat_with_json()` method now only takes: `query`, `workflow_id`, `context`
- API payload now only includes: `workflow_id`, `query`, `is_persistence_allowed`, optional `context`

**Added:**
- Documentation explaining that model config should be in workflows
- Note that system_prompt is in workflow, not sent in request (for interaction logging)

### 2. Updated Agent Modules

Fixed all calls to `llm_client.chat()` to remove the removed parameters:

**`agent/planner.py`:**
- Removed `system_prompt` and `max_tokens` parameters
- Changed `query=prompt` to `query=context` (using the formatted context directly)
- Changed `query=prompt` to `query=refinement_context` in `refine_plan()`

**`agent/picker.py`:**
- Removed `system_prompt` and `max_tokens` parameters
- Changed `query=prompt` to `query=context`

**`agent/verifier.py`:**
- Removed `system_prompt` and `max_tokens` parameters
- Changed `query=prompt` to `query=context`

### 3. Enhanced `agent/system_prompts.py`

Added comprehensive documentation at the top of the file explaining:
- These prompts should be configured in Open Arena workflows
- This file serves as the single source of truth for prompt text
- Workflow configuration instructions for each module
- Process for updating prompts

## Benefits

1. **Cleaner API calls**: No redundant model configuration in requests
2. **Single source of truth**: Workflows control all model behavior
3. **Easier maintenance**: Update model config in one place (workflow)
4. **Version control**: Prompt text still tracked in git via `system_prompts.py`
5. **Flexibility**: Can change model settings without code changes

## Workflow Configuration

Each agent module should have its own workflow in Open Arena:

### Planner Workflow
- Environment variable: `PLANNER_WORKFLOW_ID`
- System prompt: `PLANNER_SYSTEM_PROMPT` from `system_prompts.py`
- Model: `claude-3-5-sonnet-20241022`
- Temperature: `0.1`
- Max tokens: `2000`

### Picker Workflow
- Environment variable: `PICKER_WORKFLOW_ID`
- System prompt: `PICKER_SYSTEM_PROMPT` from `system_prompts.py`
- Model: `claude-3-5-sonnet-20241022`
- Temperature: `0.1`
- Max tokens: `4096`

### Verifier Workflow
- Environment variable: `VERIFIER_WORKFLOW_ID`
- System prompt: `VERIFIER_SYSTEM_PROMPT` from `system_prompts.py`
- Model: `claude-3-5-sonnet-20241022`
- Temperature: `0.1`
- Max tokens: `4096`

## Testing

Tested the simplified LLM client:
```bash
python -m agent.llm_client
```

Results:
- ✅ Basic chat request works
- ✅ JSON response parsing works
- ✅ Authentication works
- ✅ Response extraction works

## Migration Notes

If you have existing workflows:
1. Copy the system prompts from `agent/system_prompts.py`
2. Configure them in your Open Arena workflows
3. Set the workflow IDs in your `.env` file
4. Test each workflow individually

## Related Files

- `agent/llm_client.py` - Simplified LLM client
- `agent/system_prompts.py` - System prompt reference with documentation
- `agent/planner.py` - Updated to use simplified client
- `agent/picker.py` - Updated to use simplified client
- `agent/verifier.py` - Updated to use simplified client
- `.env.example` - Should include workflow ID variables

## Date

2025-11-15
