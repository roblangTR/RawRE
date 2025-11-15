# AI Agent Interaction Logging

This document describes the comprehensive logging system that captures all communications between AI agents and the LLM.

## Overview

The interaction logging system provides complete visibility into how the AI agents work by capturing:

- **Prompts**: The exact queries sent to the LLM
- **Responses**: The complete responses from the LLM
- **System Prompts**: The system instructions provided to each agent
- **Context**: Additional context and working set data
- **Metadata**: Model parameters, workflow IDs, timestamps, etc.
- **Raw API Data**: Complete request and response payloads

## Architecture

### Components

1. **InteractionLogger** (`agent/interaction_logger.py`)
   - Core logging class that captures and stores interactions
   - Maintains session state and interaction sequences
   - Generates both JSON and human-readable reports

2. **ClaudeClient Integration** (`agent/llm_client.py`)
   - Modified to automatically log all LLM interactions
   - Captures request/response pairs with full context
   - Optional logging can be enabled/disabled

3. **Agent Modules** (planner, picker, verifier)
   - Each agent's interactions are tagged with agent name
   - Interaction types are tracked (create_plan, pick_shots, verify_edit, etc.)

## File Structure

When logging is enabled, files are created in `logs/interactions/`:

```
logs/interactions/
├── 20251115_160301_0001.json          # Individual interaction 1
├── 20251115_160301_0002.json          # Individual interaction 2
├── 20251115_160301_0003.json          # Individual interaction 3
├── session_20251115_160301_summary.json  # Complete session summary
└── session_20251115_160301_report.txt    # Human-readable report
```

### Individual Interaction Files

Each interaction is saved as a separate JSON file with this structure:

```json
{
  "interaction_id": "20251115_160301_0001",
  "session_id": "20251115_160301",
  "sequence_number": 1,
  "timestamp": "2025-11-15T16:03:01.123456",
  "agent": "planner",
  "interaction_type": "chat",
  "prompt": {
    "text": "# Story Planning Task\n\n## Editorial Brief\n...",
    "length": 2543,
    "hash": "a1b2c3d4e5f6..."
  },
  "response": {
    "text": "{\n  \"beats\": [\n    {\n      \"beat_number\": 1,\n...",
    "length": 1876,
    "hash": "f6e5d4c3b2a1..."
  },
  "system_prompt": {
    "text": "You are an expert news editor...",
    "length": 1234
  },
  "context": {
    "text": "Available shots: 26 shots...",
    "length": 5678
  },
  "metadata": {
    "model": "claude-3-5-sonnet-20241022",
    "temperature": 0.1,
    "max_tokens": 2000,
    "workflow_id": "abc123..."
  },
  "raw_request": {
    "workflow_id": "abc123...",
    "query": "...",
    "modelparams": {...}
  },
  "raw_response": {
    "result": {...},
    "usage": {...}
  }
}
```

### Session Summary File

The session summary aggregates all interactions:

```json
{
  "session_id": "20251115_160301",
  "total_interactions": 3,
  "start_time": "2025-11-15T16:03:01.123456",
  "end_time": "2025-11-15T16:05:23.789012",
  "interactions": [
    {...},  // All individual interactions
    {...},
    {...}
  ],
  "statistics": {
    "total_interactions": 3,
    "by_agent": {
      "planner": 1,
      "picker": 1,
      "verifier": 1
    },
    "by_type": {
      "chat": 3
    },
    "total_prompt_chars": 8765,
    "total_response_chars": 5432,
    "total_context_chars": 12345,
    "average_prompt_length": 2921.67,
    "average_response_length": 1810.67
  }
}
```

### Human-Readable Report

The report file provides an easy-to-read summary:

```
================================================================================
AI AGENT INTERACTION LOG
================================================================================

Session ID: 20251115_160301
Total Interactions: 3

STATISTICS
--------------------------------------------------------------------------------
Total Prompt Characters: 8,765
Total Response Characters: 5,432
Average Prompt Length: 2922 chars
Average Response Length: 1811 chars

BY AGENT
--------------------------------------------------------------------------------
  planner: 1 interactions
  picker: 1 interactions
  verifier: 1 interactions

BY TYPE
--------------------------------------------------------------------------------
  chat: 3 interactions

================================================================================
DETAILED INTERACTIONS
================================================================================

[1] 20251115_160301_0001
    Agent: planner
    Type: chat
    Timestamp: 2025-11-15T16:03:01.123456

    PROMPT:
    ----------------------------------------------------------------------------
    # Story Planning Task
    
    ## Editorial Brief
    Create a short news package about the Gallipoli burial ceremony
    ...

    SYSTEM PROMPT:
    ----------------------------------------------------------------------------
    You are an expert news editor...

    RESPONSE:
    ----------------------------------------------------------------------------
    {
      "beats": [
        {
          "beat_number": 1,
          ...
```

## Usage

### Basic Usage

The logging system is automatically enabled when you create a `ClaudeClient`:

```python
from agent.llm_client import ClaudeClient
from agent.interaction_logger import get_interaction_logger

# Create client with logging enabled (default)
client = ClaudeClient(enable_logging=True)

# Make LLM calls - they will be automatically logged
response = client.chat(
    query="Your prompt here",
    system_prompt="System instructions",
    module='planner'  # Important: specify the agent module
)

# Access the logger to get statistics or save reports
logger = get_interaction_logger()
logger.save_session_summary()
logger.generate_readable_report()
```

### Running the Test Script

A complete test script is provided:

```bash
# Run the interaction logging test
python scripts/test_interaction_logging.py
```

This will:
1. Initialize the logging system
2. Run a complete edit workflow (planner → picker → verifier)
3. Capture all AI interactions
4. Generate summary and report files
5. Display statistics

### Disabling Logging

To disable logging:

```python
# Create client with logging disabled
client = ClaudeClient(enable_logging=False)
```

### Custom Output Directory

To specify a custom output directory:

```python
from agent.interaction_logger import get_interaction_logger

# Get logger with custom directory
logger = get_interaction_logger("custom/path/to/logs")
```

## API Reference

### InteractionLogger

#### `__init__(output_dir: str = "logs/interactions")`

Initialize the logger with an output directory.

#### `log_interaction(...) -> str`

Log a single interaction. Returns the interaction ID.

Parameters:
- `agent`: Agent name (planner, picker, verifier)
- `interaction_type`: Type of interaction
- `prompt`: The prompt sent to LLM
- `response`: The response from LLM
- `system_prompt`: System prompt (optional)
- `context`: Additional context (optional)
- `metadata`: Metadata dict (optional)
- `raw_request`: Raw API request (optional)
- `raw_response`: Raw API response (optional)

#### `save_session_summary() -> str`

Save complete session summary. Returns path to summary file.

#### `generate_readable_report() -> str`

Generate and save human-readable report. Returns report text.

#### `get_interaction(interaction_id: str) -> Optional[Dict]`

Retrieve a specific interaction by ID.

#### `get_agent_interactions(agent: str) -> List[Dict]`

Get all interactions for a specific agent.

### ClaudeClient

#### `__init__(model: str, temperature: float, enable_logging: bool = True)`

Initialize client with optional logging.

#### `chat(...) -> Dict`

Send chat request. Automatically logs if `enable_logging=True` and `module` is specified.

## Use Cases

### 1. Debugging Agent Behavior

When an agent produces unexpected results, examine the interaction logs to see:
- What context was provided
- What the exact prompt was
- How the LLM responded
- What system instructions were used

### 2. Prompt Engineering

Use the logs to:
- Analyze which prompts produce better results
- Compare different system prompt variations
- Measure response quality across iterations

### 3. Performance Analysis

Track:
- Token usage per agent
- Response times
- Context sizes
- Iteration patterns

### 4. Audit Trail

Maintain a complete record of:
- All AI decisions made
- The reasoning behind selections
- The data used for each decision

### 5. Training Data

Use logged interactions to:
- Create training datasets
- Fine-tune models
- Build evaluation benchmarks

## Best Practices

1. **Always specify the module parameter** when calling `client.chat()` to ensure proper agent tagging

2. **Review logs after each run** to understand agent behavior

3. **Archive important sessions** for future reference

4. **Use statistics** to identify patterns and optimization opportunities

5. **Clean up old logs** periodically to manage disk space

## Troubleshooting

### Logging Not Working

Check that:
1. `enable_logging=True` in ClaudeClient initialization
2. `module` parameter is specified in `chat()` calls
3. Output directory is writable

### Missing Interactions

Ensure:
1. All agent calls go through the ClaudeClient
2. The module parameter is set correctly
3. No exceptions are occurring during logging

### Large Log Files

If logs become too large:
1. Reduce the number of iterations
2. Limit context size
3. Archive and compress old sessions
4. Implement log rotation

## Example Output

After running the test script, you'll see output like:

```
================================================================================
AI AGENT INTERACTION LOGGING TEST
================================================================================

✓ Interaction logger initialized
  Session ID: 20251115_160301
  Output directory: logs/interactions

✓ Database loaded: 26 shots for test-rushes
✓ LLM client initialized
✓ Orchestrator initialized

================================================================================
RUNNING EDIT COMPILATION
================================================================================
Story: test-rushes
Brief: Create a short news package about the Gallipoli burial ceremony
Target Duration: 60s

[Planner creates plan...]
[Picker selects shots...]
[Verifier checks edit...]

================================================================================
SAVING INTERACTION LOGS
================================================================================

✓ Session summary saved: logs/interactions/session_20251115_160301_summary.json
✓ Readable report generated

INTERACTION STATISTICS
--------------------------------------------------------------------------------
Total Interactions: 3
Total Prompt Characters: 8,765
Total Response Characters: 5,432
Average Prompt Length: 2922 chars
Average Response Length: 1811 chars

By Agent:
  planner: 1 interactions
  picker: 1 interactions
  verifier: 1 interactions

INTERACTION FILES
--------------------------------------------------------------------------------
  20251115_160301_0001.json (12.3 KB)
  20251115_160301_0002.json (15.7 KB)
  20251115_160301_0003.json (8.9 KB)
  session_20251115_160301_summary.json (45.2 KB)
  session_20251115_160301_report.txt (23.1 KB)

================================================================================
✓ TEST COMPLETE
================================================================================
```

## Future Enhancements

Potential improvements:
- Real-time streaming of logs to monitoring systems
- Integration with observability platforms
- Automatic anomaly detection
- Cost tracking and optimization
- A/B testing framework for prompts
- Visual interaction timeline
- Diff tools for comparing sessions
