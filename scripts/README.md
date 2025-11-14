# RAWRE Test & Utility Scripts

This directory contains test scripts and utilities for the RAWRE prototype.

## Test Scripts

### Ingest Pipeline Tests

#### `test_auth.py`
Tests Open Arena OAuth2 authentication.
```bash
python scripts/test_auth.py
```
- Verifies TR authentication credentials
- Tests token acquisition
- Validates API connectivity

#### `test_gemini_analysis.py`
Tests Gemini AI analysis on a single video.
```bash
python scripts/test_gemini_analysis.py
```
- Processes one test video
- Runs Gemini visual analysis
- Displays comprehensive metadata results

#### `test_gemini_batch.py`
Tests batch Gemini analysis on multiple videos.
```bash
python scripts/test_gemini_batch.py
```
- Processes 3 test videos
- Demonstrates batch processing
- Shows performance metrics

#### `test_proxy_generation.py`
Tests ultra-low bitrate proxy generation for Gemini.
```bash
python scripts/test_proxy_generation.py
```
- Creates 1 Mbit/s proxy videos
- Validates proxy specifications
- Tests Gemini compatibility

#### `test_gemini_storage.py`
Tests Gemini metadata storage in database.
```bash
python scripts/test_gemini_storage.py
```
- Verifies database schema
- Checks metadata persistence
- Validates field storage

#### `test_end_to_end_ingest.py`
Tests complete ingest pipeline end-to-end.
```bash
python scripts/test_end_to_end_ingest.py
```
- Full pipeline: video → shots → Gemini → embeddings → database
- Comprehensive integration test
- Performance benchmarking

### Agent Workflow Tests

#### `test_agent_edit.py`
Tests the complete agent editing workflow.
```bash
python scripts/test_agent_edit.py
```
- Tests Planner, Picker, and Verifier agents
- Demonstrates iterative refinement
- Shows edit compilation process

#### `test_2min_edit.py`
Tests 2-minute edit compilation with full dataset.
```bash
python scripts/test_2min_edit.py
```
- Uses complete ingested footage
- Creates 2-minute documentary edit
- Generates EDL/FCPXML output
- **This is the main demo script**

### Legacy/Deprecated

#### `test_end_to_end.py`
Early end-to-end test (superseded by `test_end_to_end_ingest.py`).

## Utility Scripts

### `ingest_all_rushes.py`
Batch ingest script for processing all test footage.
```bash
python scripts/ingest_all_rushes.py
```
- Processes all videos in `./data/rushes/`
- Creates shots with Gemini metadata
- Stores in database for agent use
- **Run this before testing agents**

## Usage Workflow

### Initial Setup
1. Configure environment variables (`.env`)
2. Test authentication: `python scripts/test_auth.py`
3. Test single video: `python scripts/test_gemini_analysis.py`

### Full Ingest
1. Place videos in `./data/rushes/`
2. Run batch ingest: `python scripts/ingest_all_rushes.py`
3. Verify storage: `python scripts/test_gemini_storage.py`

### Agent Testing
1. Ensure footage is ingested (see above)
2. Test agent workflow: `python scripts/test_agent_edit.py`
3. Create 2-minute edit: `python scripts/test_2min_edit.py`

## Script Categories

### Authentication & Setup
- `test_auth.py` - Verify API credentials

### Ingest Pipeline
- `test_gemini_analysis.py` - Single video analysis
- `test_gemini_batch.py` - Batch processing
- `test_proxy_generation.py` - Proxy creation
- `test_gemini_storage.py` - Database verification
- `test_end_to_end_ingest.py` - Full pipeline
- `ingest_all_rushes.py` - Batch ingest utility

### Agent Workflow
- `test_agent_edit.py` - Agent system test
- `test_2min_edit.py` - Complete edit demo

## Output Locations

Scripts generate output in various locations:

- **Processed shots**: `./data/shots/`
- **Keyframes**: `./data/keyframes/`
- **Proxies**: `./data/proxies/`
- **Gemini proxies**: `./data/gemini_proxies/`
- **Database**: `./data/shots.db`
- **Vector index**: `./data/vector_index/`
- **Edit outputs**: `./data/edits/`

## Requirements

All scripts require:
- Python 3.8+
- Dependencies from `requirements.txt`
- Configured `.env` file
- Test footage in `./data/rushes/`

## Troubleshooting

### Authentication Errors
- Verify `.env` credentials
- Run `test_auth.py` to diagnose
- Check Open Arena token expiry

### Gemini Analysis Failures
- Check proxy file size (<20MB recommended)
- Verify Open Arena workflow ID
- Review logs for timeout issues

### Database Issues
- Ensure `./data/` directory exists
- Check SQLite permissions
- Verify schema with `test_gemini_storage.py`

## Performance Notes

- **Single video ingest**: ~30 seconds
- **Batch ingest (26 videos)**: ~8 minutes
- **Agent workflow (3 iterations)**: ~5-6 minutes
- **Gemini analysis**: ~10-15 seconds per shot

## See Also

- [Test Suite Documentation](../tests/README.md) - Unit and integration tests
- [Main Documentation](../docs/README.md) - Complete documentation index
- [Configuration Guide](../docs/CONFIGURATION_GUIDE.md) - Setup instructions

---

*Last updated: 14 November 2025*
