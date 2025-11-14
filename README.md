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
news-edit-agent/
├── ingest/              # Video processing pipeline
│   ├── video_processor.py
│   ├── transcriber.py
│   ├── embedder.py
│   └── shot_analyzer.py
├── storage/             # Database and vector indices
│   ├── database.py
│   └── vector_index.py
├── agent/               # LLM orchestration
│   ├── llm_client.py
│   ├── tools.py
│   ├── planner.py
│   ├── picker.py
│   └── verifier.py
├── output/              # Format writers
│   ├── edl_writer.py
│   └── fcpxml_writer.py
├── api/                 # REST API
│   └── server.py
├── cli.py               # Command-line interface
└── config.yaml          # Configuration
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

See `news_rushes_edit_agent_design_v2.md` for detailed system design.

## License

MIT
