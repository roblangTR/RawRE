# News Rushes Edit Agent

AI-powered video editing agent for assembling broadcast-style news packages from single-camera rushes.

## Features

- **Automated shot detection** using OpenCV histogram analysis
- **Speech-to-text** with MLX-optimized Whisper for M4 Mac
- **Semantic search** using sentence transformers and FAISS
- **LLM-powered editing** via Claude (Open Arena API)
- **Editorial rule enforcement** (chronology, location consistency, quote integrity)
- **Industry-standard outputs** (CMX 3600 EDL, FCPXML)

## Architecture

The system follows a per-story working set approach:
1. **Ingest**: Process rushes into structured shot database
2. **Working Set**: Build ephemeral vector indices for story context
3. **Agent**: LLM plans beats, picks shots, verifies rules
4. **Output**: Generate EDL/FCPXML for NLE import

## Quick Start

### Installation

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Copy environment template
cp .env.example .env
# Edit .env with your Open Arena API credentials
```

### Usage

**1. Ingest rushes:**
```bash
python cli.py ingest --input ./rushes --story "city-hall-protest"
```

**2. Compile edit:**
```bash
python cli.py compile \
  --story "city-hall-protest" \
  --brief "Protesters gather at City Hall demanding transit improvements" \
  --duration 90
```

**3. Output files:**
- EDL: `./data/outputs/city-hall-protest.edl`
- FCPXML: `./data/outputs/city-hall-protest.fcpxml`

### API Server

```bash
python -m uvicorn api.server:app --reload
```

Access API docs at http://localhost:8000/docs

## Project Structure

```
RAWRE/
├── agent/               # AI editing agents
│   ├── llm_client.py    # Claude API via Open Arena
│   ├── planner.py       # Creates narrative structure
│   ├── picker.py        # Selects shots semantically
│   ├── verifier.py      # Quality control
│   └── orchestrator.py  # Manages workflow
├── ingest/              # Video processing pipeline
│   ├── video_processor.py  # Shot detection
│   ├── gemini_analyzer.py  # AI visual analysis
│   ├── transcriber.py      # Speech-to-text
│   ├── embedder.py         # Semantic embeddings
│   └── orchestrator.py     # Ingest workflow
├── storage/             # Data persistence
│   ├── database.py      # SQLite with metadata
│   └── vector_index.py  # FAISS semantic search
├── output/              # Export formats
│   ├── edl_writer.py    # CMX 3600 EDL
│   └── fcpxml_writer.py # Final Cut Pro XML
├── api/                 # REST API (future)
├── tests/               # Unit & integration tests
├── scripts/             # Test & utility scripts
├── docs/                # Complete documentation
├── cli.py               # Command-line interface
├── config.yaml          # System configuration
└── requirements.txt     # Python dependencies
```

## Documentation

Comprehensive documentation is available in the [`docs/`](docs/) directory:

- **[Getting Started](docs/CONFIGURATION_GUIDE.md)** - Setup and configuration
- **[Architecture](docs/PROJECT_SUMMARY.md)** - Technical overview
- **[Gemini Integration](docs/GEMINI_INTEGRATION.md)** - AI visual analysis
- **[Open Arena Setup](docs/OPEN_ARENA_SETUP_GUIDE.md)** - API configuration
- **[Prototype Status](docs/PROTOTYPE_COMPLETE.md)** - Current capabilities
- **[Test Scripts](scripts/README.md)** - Testing and utilities

See [`docs/README.md`](docs/README.md) for the complete documentation index.
```

## Configuration

Edit `config.yaml` to customize:
- Shot detection sensitivity
- Whisper model size
- Embedding models
- Editorial rules
- Output formats

## Editorial Rules

The agent enforces broadcast news standards:
- **Chronological spine**: Shots in temporal order (non-decreasing capture time)
- **Location consistency**: Cutaways from same location within ±10 minutes
- **Quote integrity**: Keep mouth-sync visible for key phrases
- **Shot types**: SOT (sound on tape), GV (general view), CUTAWAY

## Development

See [`docs/news_rushes_edit_agent_design_v2.md`](docs/news_rushes_edit_agent_design_v2.md) for detailed system design.

### Testing

Run the test suite:
```bash
./run_tests.sh
```

Or run specific test modules:
```bash
pytest tests/test_storage.py -v
pytest tests/test_agents.py -v
pytest tests/test_output.py -v
```

See [`tests/README.md`](tests/README.md) for test documentation.

### Test Scripts

Utility scripts for testing and development are in [`scripts/`](scripts/):

- `test_auth.py` - Verify Open Arena authentication
- `test_gemini_analysis.py` - Test AI visual analysis
- `ingest_all_rushes.py` - Batch ingest footage
- `test_2min_edit.py` - Create demo edit

See [`scripts/README.md`](scripts/README.md) for complete script documentation.

## License

MIT
