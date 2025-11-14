# News Rushes Edit Agent — End‑to‑End System Design (v2)

**Date:** 2025‑11‑14  
**Scope:** Build a per‑story, news‑aware vector search + LLM agent that assembles broadcast‑style edits from single‑camera rushes. Chronology is the default spine; cutaways are allowed within tight temporal/location windows. File footage is opt‑in and clearly labeled.

---

## 1) Objectives & Constraints
**Objectives**
- Index rushes at shot (or sub‑shot) granularity with multimodal signals (text/visual/audio/OCR) and precise timecodes.
- Retrieve and sequence shots with an LLM agent using strict tool APIs and deterministic verifier rules.
- Guarantee isolation via an **ephemeral per‑story working set** (“mini vector DB”).

**Constraints**
- Single camera typical; no script. Temporal order matters but can be broken for short cutaways.
- Editorial integrity: quote visibility, location consistency, provenance of FILE footage.

---

## 2) Editorial Principles (News)
1) **Chronology‑first spine** (non‑decreasing `capture_ts`), except brief cutaways (±10 min) to illustrate/cover jumps.  
2) **Location consistency**: cutaways from the same `loc_bucket` by default.  
3) **Quote integrity**: keep mouth‑sync visible for key phrases; avoid covering contentious statements.  
4) **File footage**: never by default; only when explicitly allowed and clearly noted in output (`type="FILE"`, note includes {date/source}).

---

## 3) Architecture Overview
**Global Warehouse (persistent)**
- Postgres for metadata; embeddings stored in `pgvector` (or sidecar). Object storage for proxies/thumbnails.
- Long‑term catalog; **agent never queries it directly.**

**Per‑Story Working Set (ephemeral)**
- Built for a story/time window; contains only relevant shots + a **pruned shot graph**.
- In‑memory FAISS/HNSW indices (text/visual/audio/OCR).  
- Separate, explicit **FILE working set** (opt‑in).

**Agent Layer**
- Planner → Picker → Verifier → Emitter (FCPXML/EDL/ALE).  
- Tools are hard‑scoped to the working set(s).

---

## 4) Ingest & Segment
1) **Shots**: record start/stop + hard‑cut detection; optional sub‑shot windows (2–5s).  
2) **Metadata**: `capture_ts` (UTC), SMPTE `tc_in/out`, `fps`, `camera_id`, GPS/EXIF, reel/slate.  
3) **ASR/Audio**: Whisper with word timestamps; diarization; ambience cues (applause/chant/siren).  
4) **Visual/OCR**: 1–3 keyframes; faces (anonymous clusters), podium/logo/banner detection; OCR for signage.  
5) **Shot kinds**: `GV`, `CUTAWAY`, `PTC`, `SOT`, `VOX`, `PRESSER`, `FILE`.  
6) **Embeddings**: text (ASR+OCR), visual (keyframes pooled), audio (mel/VGGish), OCR text embedding.  
7) **Proxies**: low‑res proxy + thumbnails per shot.

---

## 5) Data Model (Postgres + pgvector)
```sql
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE shots (
  shot_id           BIGSERIAL PRIMARY KEY,
  story_slug        TEXT,
  camera_id         TEXT,
  capture_ts        TIMESTAMPTZ NOT NULL,
  tc_in             TEXT NOT NULL,
  tc_out            TEXT NOT NULL,
  fps               NUMERIC NOT NULL,
  duration_ms       INT NOT NULL,
  lat               DOUBLE PRECISION,
  lon               DOUBLE PRECISION,
  loc_bucket        TEXT,               -- e.g., "City Hall"
  shot_kind         TEXT,               -- "GV","CUTAWAY","PTC","SOT","VOX","PRESSER","FILE"
  is_file           BOOLEAN DEFAULT FALSE,
  people_cluster_ids INT[],
  has_podium        BOOLEAN,
  has_logo          BOOLEAN,
  asr               TEXT,
  asr_summary       TEXT,
  entities          JSONB,              -- {"PERSON":["Mayor Khan"],"ORG":["Transit Union"]}
  embedding_text    vector(1024),
  embedding_visual  vector(1024),
  embedding_audio   vector(128),
  embedding_ocr     vector(512),
  path_proxy        TEXT,
  path_thumb        TEXT,
  created_at        TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE shot_edges (
  src_shot_id BIGINT REFERENCES shots(shot_id),
  dst_shot_id BIGINT REFERENCES shots(shot_id),
  edge_type   TEXT,     -- "adjacent","cutaway","return","contrast","file"
  weight      REAL,     -- 0..1
  PRIMARY KEY (src_shot_id, dst_shot_id, edge_type)
);

CREATE INDEX ON shots USING ivfflat (embedding_text vector_cosine) WITH (lists = 200);
CREATE INDEX ON shots USING ivfflat (embedding_visual vector_cosine) WITH (lists = 200);
```

---

## 6) Shot Graph (News‑aware)
- **Adjacent**: consecutive by `capture_ts` within same device/session (≈0.9).  
- **Cutaway**: speaking shot → nearby `GV/CUTAWAY` within ±10 min & same `loc_bucket` (0.6–0.8).  
- **Return**: back to covered speaking shot (0.7).  
- **Contrast**: signage → reaction, siren → damage (0.4–0.6).  
- **File**: edges from context to FILE (0.2); disabled unless `allow_file=true`.

---

## 7) Working Set Build (“Mini Vector DB”)
**Filters (hard gates)**: assignment window, `loc_bucket` set, `camera_id` set, `is_file=false` by default.  
**Indices**: FAISS HNSW per modality.  
**Neighbors**: precompute `adjacent`, `cutaway`, `return` for in‑set shots.  
**Append**: allow incremental updates as new rushes arrive.  
**FILE set**: separate namespace; only loaded when explicitly requested.

---

## 8) Retrieval & Ranking
Base scoring per candidate:
```
score = 0.45*text_sim + 0.25*visual_sim + 0.15*temporal_proximity
      + 0.10*same_loc_bonus + 0.05*audio_cue_match
```
- Optional cross‑encoder re‑rank (“next‑shot fitness”) using context + candidate.  
- Diversity via MMR.  
- Graph constraint: candidates must be reachable from last spine shot via `adjacent` or `cutaway` edges.

---

## 9) Tool API (Scoped to Working Set)
- `GET /search_shots?text&kinds&top_k&allow_file` → `Shot[]` (scores + summaries).  
- `GET /neighbors/{shot_id}?within_minutes=10` → `{adjacent[], cutaway[], returns[]}`.  
- `GET /asr_words/{shot_id}` → `{transcript, words[]}` with word timestamps/speaker.  
- `POST /check_rules` → chronology/location/FILE policy checks.  
- `POST /emit_fcpxml` / `POST /emit_edl` → write outputs with notes (FILE provenance).

**Hard guardrail**: any `shot_id` not in the working set is rejected by tools and the Verifier.

---

## 10) Agent Design
**Planner** (LLM): build 5–8 beats from brief + duration.  
**Picker** (LLM + tools): for each beat, fetch top‑K, pick a spine shot (PTC/SOT/PRESSER) and ≤2 cutaways; snap `tc_in/out` to ASR word boundaries.  
**Verifier** (code): enforce chronology for spine, same‑location cutaways within ±10 min, quote integrity (hook), FILE policy.  
**Emitter** (code): output FCPXML/EDL/ALE with notes, including “FILE – {date/source}” when applicable.

---

## 11) Prompts (Excerpts)

**System Prompt**
- Assemble a broadcast‑style news edit from a **per‑story working set**.  
- **Spine**: non‑decreasing `capture_ts`. **Cutaways**: same `loc_bucket`, within ±10 minutes.  
- Keep mouth‑sync visible for key phrases on speaking shots.  
- **FILE usage** only if `allow_file=true`; justify and set `type="FILE"`; add note with provenance.  
- Output strictly in the provided JSON schema; choose `tc_in/out` at ASR word boundaries.

**Planner Instruction**
- “Plan 5–8 beats for a {duration_sec}s package based on the brief. Return JSON: `{ "beats":[{"goal": "…"}] }`.”

**Picker Instruction**
- “Given beat goal, last spine shot id, and candidates, choose 1 spine shot that follows chronology and ≤2 cutaways in the same `loc_bucket` within ±10 minutes. Return `{ "beats":[{"goal":"…","picks":[…]}] }`.”

---

## 12) File Footage Policy
- Default **off**. Separate FILE working set and explicit UI/CLI toggle or user instruction.  
- Verifier blocks unauthorized FILE; if enabled, prefer same venue/event and add a note “FILE – {date/source}”.  
- Optional: apply “FILE” overlay to proxies for human review.

---

## 13) Output Formats
**CMX 3600 EDL (example)**  
```
001  AX  V  C  01:12:03:10 01:12:07:00  00:00:00:00 00:00:03:15
* FROM CLIP NAME: CAM_A_20251113_112310
* NOTE: GV City Hall exterior (establish)
```
**FCPXML fragment (25fps, simplified)**  
```xml
<asset id="r1" name="CAM_A_20251113_112310" src="file:/media/CAM_A_20251113_112310.mov" start="3600s" duration="600s" hasVideo="1"/>
<sequence duration="90s" format="r25">
  <spine>
    <clip name="GV City Hall" ref="r1" start="3615s" duration="3.6s" tcStart="01:12:03:10"/>
  </spine>
</sequence>
```

---

## 14) Training Strategy (Optional)
- **Prompt‑only** baseline works with good tools and rules.  
- Highest ROI small models:  
  1) Shot‑type head (GV/CUTAWAY/PTC/SOT/VOX/PRESSER).  
  2) Cross‑encoder re‑ranker for “next‑shot fitness”.  
  3) Audio cue classifier (applause/chant/siren).  
  4) Match‑cut scorer (optional).  
- Optional small LoRA on LLM for stricter JSON/EDL formatting or house‑style rationales.

---

## 15) Evaluation & Telemetry
- **Import success** (EDL/FCPXML syntax).  
- **Verifier violations** (should be zero in final).  
- **Editor effort** (tweaks per finished minute).  
- **Retrieval quality** (recall@K; CLIPScore vs brief).  
- **Latency** (p95 < 300 ms for top‑K search within working set).

---

## 16) Operational Notes
- Cache embeddings by asset checksum; cache `neighbors()` and `asr_words()`.  
- Security: store embeddings and thumbnails; originals in cold storage. Avoid personal identification; use anonymous face clusters.  
- Audit log: persist beats, candidate lists, chosen picks, verifier outcomes, and output paths.  
- Versioning: `embedding_version` column for upgrades.

---

## 17) Appendix

### A) Working Set Build (FAISS/HNSW sketch)
```python
# Filter candidates from Postgres by time/loc/camera and is_file=false, then:
import faiss, numpy as np

def build_index(vecs, m=32):
    d = vecs.shape[1]
    index = faiss.IndexHNSWFlat(d, m)
    index.hnsw.efConstruction = 200
    index.add(vecs.astype('float32'))
    return index

idx_text   = build_index(text_vecs)
idx_visual = build_index(visual_vecs)
idx_audio  = build_index(audio_vecs)
```

### B) Verifier Rules (pseudo)
```python
def verify(last, pick, allow_file, same_loc=True, cutaway_minutes=10):
    if pick.is_file and not allow_file: return "FILE_NOT_ALLOWED"
    if last and pick.type != "CUTAWAY" and pick.capture_ts < last.capture_ts:
        return "REVERSE_CHRONOLOGY"
    if pick.type == "CUTAWAY" and last:
        if same_loc and pick.loc_bucket != last.loc_bucket: return "CUTAWAY_WRONG_LOCATION"
        if abs(pick.capture_ts - last.capture_ts) > cutaway_minutes*60: return "CUTAWAY_TOO_FAR_IN_TIME"
    # Hook: quote integrity using ASR word spans
    return "OK"
```

### C) Re‑ranker Features
- `[text_embed(beat) ⊕ visual_embed(candidate) ⊕ text_embed(ASR) ⊕ Δtime ⊕ same_loc ⊕ one‑hot(shot_kind)] → scalar`

---

**End of Document**
