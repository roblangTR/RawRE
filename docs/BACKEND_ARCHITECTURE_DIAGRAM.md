# RAWRE Backend Architecture: Data Flow & Embedding Usage

## 🎯 Executive Summary

**ISSUE IDENTIFIED**: Embeddings are generated and stored but **NOT being used** for semantic search. The system falls back to basic keyword matching, which significantly reduces the intelligence of shot selection.

---

## 📊 Current Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                          INGESTION PHASE                             │
│                     (ingest/orchestrator.py)                         │
└─────────────────────────────────────────────────────────────────────┘
                                  │
                    ┌─────────────┴─────────────┐
                    ▼                           ▼
         ┌──────────────────┐        ┌──────────────────┐
         │  Video Processor │        │ Gemini Analyzer  │
         │   (FFmpeg/CV2)   │        │ (Visual AI)      │
         └──────────────────┘        └──────────────────┘
                    │                           │
                    ├───► Frame Extraction     │
                    ├───► Shot Detection       │
                    └───► Timecode Mapping     │
                                               │
                    ┌──────────────────────────┘
                    │
                    ▼
         ┌──────────────────────────────┐
         │     Transcriber (Whisper)     │
         │  - Generates ASR text         │
         │  - Timestamp alignment        │
         └──────────────────────────────┘
                    │
                    ▼
         ┌──────────────────────────────┐
         │  Embedder (sentence-trans)   │
         │  ✓ Text embeddings (384d)    │
         │  ✓ Visual embeddings (512d)  │
         │  ✓ CLIP for images           │
         └──────────────────────────────┘
                    │
                    ▼
         ┌──────────────────────────────┐
         │         STORAGE              │
         ├──────────────────────────────┤
         │ SQLite Database:             │
         │  - Shot metadata             │
         │  - Transcripts               │
         │  - Gemini descriptions       │
         │  - Embeddings (BLOB)         │
         ├──────────────────────────────┤
         │ FAISS Vector Index:          │
         │  - Text embeddings index     │
         │  - Visual embeddings index   │
         │  - Fast similarity search    │
         └──────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│                        COMPILATION PHASE                             │
│                     (agent/orchestrator.py)                          │
└─────────────────────────────────────────────────────────────────────┘

    User Request: Brief + Target Duration
                    │
                    ▼
         ┌──────────────────────────┐
         │    Working Set Builder   │
         │  (agent/working_set.py)  │
         └──────────────────────────┘
                    │
        ┌───────────┴───────────┐
        ▼                       ▼
    ❌ SHOULD USE:          ✅ ACTUALLY USES:
  Vector Similarity        Keyword Matching
  (semantic search)        (Jaccard similarity)
        │                       │
        │                       │
        └───────────┬───────────┘
                    │
                    ▼
         ┌──────────────────────────┐
         │   Working Set (50-100    │
         │   shots with context)    │
         └──────────────────────────┘
                    │
                    ▼
    ┌───────────────────────────────────────┐
    │          AGENT LOOP                   │
    │  (max 3 iterations for refinement)    │
    └───────────────────────────────────────┘
                    │
        ┌───────────┼───────────┐
        ▼           ▼           ▼
    ┌──────┐   ┌──────┐   ┌──────────┐
    │ Plan │   │ Pick │   │ Verify   │
    │ Agent│──→│ Agent│──→│ Agent    │
    │      │   │      │   │          │
    │Claude│   │Claude│   │Claude    │
    └──────┘   └──────┘   └──────────┘
        │           │           │
        │           │           │
        └───────────┴───────────┘
                    │
          Score ≥ 7.0/10? ──No──┐
                    │             │
                   Yes           Loop
                    │             │
                    ▼             │
         ┌──────────────────┐    │
         │   EDL Output     │◄───┘
         └──────────────────┘
```

---

## 🔍 Detailed Component Analysis

### 1. Ingestion: What Works Well ✅

**Files**: `ingest/orchestrator.py`, `ingest/embedder.py`, `ingest/gemini_analyzer.py`

**Process**:
```python
# For each video shot:
1. Extract keyframe → CLIP visual embedding (512d)
2. Transcribe audio → Whisper ASR text
3. Embed transcript → SentenceTransformer (384d)
4. Analyze visually → Gemini description
5. Store everything in SQLite + FAISS index
```

**Data Stored Per Shot**:
- `embedding_text`: 384-dimensional vector (from transcript)
- `embedding_visual`: 512-dimensional vector (from keyframe)
- `asr_text`: Full transcript
- `gemini_description`: Visual analysis
- `gemini_shot_size`: Wide/Medium/Close
- `gemini_subjects`: People/objects in frame
- `duration_ms`, `tc_in`, `tc_out`

**✅ This part is excellent** - rich multimodal embeddings are generated.

---

### 2. Working Set Builder: THE PROBLEM ❌

**File**: `agent/working_set.py`

**What SHOULD Happen**:
```python
def build_for_query(story_slug, query, max_shots=50):
    # 1. Embed the user's query
    query_embedding = embedder.embed_text(query)
    
    # 2. Search vector index for similar shots
    results = vector_index.search(
        query_vector=query_embedding,
        k=max_shots
    )
    
    # 3. Return shots ranked by semantic similarity
    return ranked_shots
```

**What ACTUALLY Happens**:
```python
def build_for_query(story_slug, query, max_shots=50):
    # 1. Get ALL shots from database
    all_shots = database.get_shots_by_story(story_slug)
    
    # 2. Score with basic keyword matching ❌
    scored = self._score_shots(all_shots, query)
    
    # Line 125-137: Simple Jaccard similarity on words
    query_words = set(query.lower().split())
    asr_words = set(asr_text.split())
    score = len(query_words & asr_words) / len(query_words | asr_words)
    
    # 3. Return top N
    return scored[:max_shots]
```

**Why This Is Bad**:
- ❌ Ignores the 384d semantic embeddings we generated
- ❌ Ignores the 512d visual embeddings  
- ❌ Can't find semantically similar content with different wording
- ❌ Example: Query "football goal celebration" won't match "striker scores winner"
- ❌ Visual content is completely ignored (no CLIP search)

**The Comment in Code**:
```python
# Line 56-57 in working_set.py:
# Step 2: Perform vector similarity search
# TODO: Implement when embedder is integrated  ← ❌ EMBEDDER IS INTEGRATED!
```

---

### 3. Agent Processing: Works But Gets Poor Input

**Files**: `agent/planner.py`, `agent/picker.py`, `agent/verifier.py`

**Current Flow**:
```
Planner:
  1. Gets working set (50-100 shots) ← Based on keywords only
  2. Formats ALL shot details for Claude
  3. Claude sees: Gemini descriptions, transcripts, metadata
  4. Creates beat-by-beat plan
  ↓
Picker:
  1. For each beat, gets working set ← Again, keyword-based only
  2. Sends 20 shots per beat to Claude
  3. Claude selects best shots
  ↓
Verifier:
  1. Reviews selected shots
  2. Checks quality, pacing, narrative
  3. Scores 1-10, provides feedback
```

**The Issue**:
- Claude is smart and works well with what it gets
- BUT it only sees the shots that keyword matching found
- Many semantically relevant shots are never considered
- The LLM can't fix the upstream selection problem

---

## 🎯 The Solution: Proper Semantic Search

### What Needs To Change

**File**: `agent/working_set.py` - Line 44-82

**Replace This**:
```python
def build_for_query(self, story_slug, query, max_shots=50):
    # Get ALL shots
    all_shots = self.database.get_shots_by_story(story_slug)
    
    # Score with keywords ❌
    scored_shots = self._score_shots(all_shots, query)
    selected_shots = scored_shots[:max_shots]
```

**With This**:
```python
def build_for_query(self, story_slug, query, max_shots=50):
    # 1. Embed the query
    from ingest.embedder import Embedder
    embedder = Embedder(config)
    query_embedding = embedder.embed_text([query])[0]
    
    # 2. Search vector index
    results = self.vector_index.search(
        query_vector=query_embedding,
        k=max_shots * 2  # Get 2x for filtering
    )
    
    # 3. Fetch full shot details
    shot_ids = [r.shot_id for r in results]
    shots = self.database.get_shots_by_ids(shot_ids)
    
    # 4. Add semantic similarity scores
    for shot, result in zip(shots, results):
        shot['semantic_score'] = result.score
        shot['relevance_score'] = result.score * 10  # Scale to 0-10
    
    # 5. Optional: Boost with keyword overlap for hybrid search
    # ... existing keyword scoring as secondary signal
    
    return shots[:max_shots]
```

---

## 📈 Expected Improvements

### Before (Keyword Matching):
```
Query: "football goal celebration"

Results:
✓ Shot 23: "player scores goal"          (keyword: goal ✓)
✓ Shot 45: "celebration in stadium"      (keyword: celebration ✓)
✗ Shot 67: "striker nets winner"         (❌ no keyword match)
✗ Shot 89: "team jubilation"             (❌ no keyword match)
✗ Shot 102: "fans cheering wildly"       (❌ no keyword match)
```

### After (Semantic Search):
```
Query: "football goal celebration"

Results (by semantic similarity):
✓ Shot 23: "player scores goal"          (0.92 similarity)
✓ Shot 67: "striker nets winner"         (0.89 similarity)
✓ Shot 45: "celebration in stadium"      (0.87 similarity)
✓ Shot 89: "team jubilation"             (0.85 similarity)
✓ Shot 102: "fans cheering wildly"       (0.82 similarity)
```

---

## 🔧 Additional Enhancements

### 1. Multimodal Search
```python
# Combine text + visual search
text_results = vector_index.text_index.search(text_query_embedding)
visual_results = vector_index.visual_index.search(visual_query_embedding)

# Weighted combination
combined_scores = (
    0.7 * text_results.scores + 
    0.3 * visual_results.scores
)
```

### 2. Hybrid Search
```python
# Best of both worlds:
semantic_score = vector_similarity(query, shot)
keyword_score = jaccard_similarity(query, shot)

final_score = 0.8 * semantic_score + 0.2 * keyword_score
```

### 3. Contextual Re-ranking
```python
# After semantic search, use Gemini descriptions for final ranking
for shot in candidates:
    context = f"Query: {query}\nShot: {shot.gemini_description}"
    relevance = llm.score_relevance(context)
    shot.final_score = 0.6 * semantic + 0.4 * relevance
```

---

## 📝 Summary

### Current State:
- ✅ Embeddings generated correctly
- ✅ Vector index exists and works
- ✅ LLM agents are well-designed
- ❌ **Embeddings not used for search**
- ❌ Falls back to primitive keyword matching

### Impact:
- 🔴 Many relevant shots never reach the LLM
- 🔴 Agent decisions based on incomplete candidate set
- 🔴 Output quality limited by upstream selection
- 🔴 Expensive embeddings computed but wasted

### Fix Required:
1. Integrate embedder in `working_set.py`
2. Use `vector_index.search()` instead of keyword matching
3. Add hybrid scoring (semantic + keywords)
4. Consider multimodal search (text + visual)

### Expected Result:
- 🟢 Semantically similar shots surface automatically
- 🟢 Better candidate sets for LLM agents
- 🟢 Higher quality final edits
- 🟢 True intelligent video understanding
