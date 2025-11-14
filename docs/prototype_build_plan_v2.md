# Prototype Build Plan — v2 (Rebuilt)

**Date:** 2025-11-14
**Horizon:** 3 weeks (with a user-visible demo at end of week 3)
**Objective:** Ship a working prototype that ingests news rushes, builds a per-story working set (mini vector DB), and lets a provider-agnostic LLM agent compile a short edit; allow FILE footage *only* via explicit opt-in and label it clearly.

---

## Guiding Principles
1) Working-set only: The agent sees only a per-story, ephemeral index. FILE footage lives in a separate namespace requiring explicit opt-in.
2) Rules over “learning”: Deterministic verifier enforces chronology, location, quote integrity, FILE policy.
3) Provider-agnostic LLM: Swappable adapter; JSON-only outputs; low temperature.
4) Auditability: Every pick is logged with candidates, rule checks, and rationale.

---

## Milestones & Dates
- Week 1: Ingest + Warehouse MVP ready
- Week 2: Working set (mini index) + Tool API + FILE namespace
- Week 3: Agent orchestration + Verifier + EDL/FCPXML + Demo

---

## Deliverables per Week

### Week 1 — Ingest & Warehouse (MVP)
Deliverables
- Postgres schema (`shots`, `shot_edges`) with `pgvector` enabled.
- CLI: ingest folder → shots with capture_ts, tc_in/out, fps, ASR summary (Whisper), 1–3 keyframes, basic OCR.
- Embeddings: text (ASR+OCR), visual (keyframe pooled), audio (simple mel/VGGish).
- Heuristic shot-kind tags: GV, CUTAWAY, PTC, SOT, VOX, PRESSER, FILE (if in library path).

Acceptance Criteria
- Ingest 2–3 stories (≥30 min each) populates DB and saves proxies/thumbnails.
- Random 20-shot QA: capture_ts, tc_in/out, and fps correct; ASR present with timestamps.
- CLI completes a story ingest in ≤ 20 min on dev hardware (GPU optional).

### Week 2 — Working Set (“Mini Vector DB”) + Tools
Deliverables
- Working-set builder: filters by time window, loc_bucket, camera_id; FILE excluded by default.
- In-memory FAISS/HNSW indices per modality (text/visual/audio).
- Pruned shot graph: adjacent, cutaway, return edges.
- FILE working set: built separately; tools require allow_file=true.
- FastAPI tools (scoped):
  - GET /search_shots?text&kinds&top_k&allow_file
  - GET /neighbors/{shot_id}?within_minutes=10
  - GET /asr_words/{shot_id} (basic word list)
  - POST /check_rules (chronology/location/FILE checks)
  - POST /emit_fcpxml and POST /emit_edl

Acceptance Criteria
- Top-K search in working set returns < 300 ms p95.
- neighbors() for any spine shot returns at least one adjacent and one valid cutaway if present.
- FILE shots never surface unless allow_file=true is set; Verifier blocks otherwise.

### Week 3 — Agent + Verifier + Output + Demo
Deliverables
- Planner → Picker → Verifier → Emitter orchestrator.
- Provider-agnostic LLM adapter with JSON mode.
- System prompt encoding chronology, cutaway, and FILE policy.
- FCPXML + CMX 3600 EDL output with notes (e.g., FILE – {date/source}).
- Minimal UI/CLI to run end-to-end and download outputs; thumbnail review page.

Acceptance Criteria
- End-to-end on at least one story: produces a coherent 60–90s package imported into NLE with zero syntax errors.
- Verifier blocks seeded violations: reverse-chron spine, wrong-location cutaway, unauthorized FILE.
- Editor SME sign-off: chronology respected; FILE used only when explicitly enabled and visibly labeled.

---

## Engineering Backlog (Key Tasks)
Ingest
- ffprobe parse; shot boundaries; Whisper ASR; OCR; keyframes/thumbnails; embeddings; heuristic shot-kind tags.

Working Set
- SQL filter → memory load; FAISS indices + shot graph; cutaway candidates ±10 min same loc_bucket; FILE namespace + toggle; cache neighbors/asr_words.

Tools & Orchestrator
- FastAPI endpoints; Verifier rules; prompts & JSON schema validation; FCPXML/EDL emitters; logging/audit JSON.

UI/CLI
- CLI: compile --story <slug> --brief "<text>" --duration 75 --allow-file
- Web form (optional): run, preview thumbnails, download outputs.

---

## System Prompt (Prototype Excerpt)
- Spine: non-decreasing capture_ts.
- Cutaways: same loc_bucket, within ±10 minutes; place on ASR pauses/word boundaries.
- Quote integrity: do not cover key phrases on speaking shots.
- FILE footage: only if allow_file=true; prefer same venue/context; set type="FILE" and add note "FILE – {date/source}".
- Return JSON matching the provided schema.

---

## Data & Test Protocol
- Dataset: 3 stories (30–60 min each) + a small FILE folder.
- Checks: EDL/FCPXML importability; rule-violation suite; editor qualitative notes.
- Metrics: p95 search latency; % runs with zero verifier violations; editor tweak count/min.

---

## Go/No-Go Demo Script (End of Week 3)
1) Pick a story; set duration 75s; FILE disabled.
2) Run compile; show beats, thumbnails, rationale; download FCPXML; import to NLE.
3) Re-run with --allow-file to show controlled FILE usage and labeling.
