"""
FastAPI Server for News Edit Agent

Provides REST API endpoints for shot search, working set building,
and agent tool access.
"""

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import logging
import yaml
from pathlib import Path

from storage.database import ShotsDatabase
from storage.vector_index import VectorIndex
from agent.working_set import WorkingSetBuilder

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="News Edit Agent API",
    description="REST API for AI-powered news video editing",
    version="0.1.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global instances (initialized on startup)
database: Optional[ShotsDatabase] = None
vector_index: Optional[VectorIndex] = None
working_set_builder: Optional[WorkingSetBuilder] = None


# Pydantic models for request/response
class SearchRequest(BaseModel):
    """Request model for shot search."""
    story_slug: str = Field(..., description="Story identifier")
    query: str = Field(..., description="Search query")
    max_shots: int = Field(50, description="Maximum number of shots to return")
    shot_types: Optional[List[str]] = Field(None, description="Filter by shot types")
    include_neighbors: bool = Field(True, description="Include temporal neighbors")


class WorkingSetRequest(BaseModel):
    """Request model for building working set."""
    story_slug: str = Field(..., description="Story identifier")
    query: str = Field(..., description="Query describing desired content")
    max_shots: int = Field(50, description="Maximum number of shots")
    shot_types: Optional[List[str]] = Field(None, description="Filter by shot types")
    format_for_llm: bool = Field(False, description="Format output for LLM context")


class BeatWorkingSetRequest(BaseModel):
    """Request model for beat-specific working set."""
    story_slug: str = Field(..., description="Story identifier")
    beat_description: str = Field(..., description="Description of the beat")
    beat_requirements: List[str] = Field(..., description="Requirements for the beat")
    max_shots: int = Field(20, description="Maximum number of candidate shots")


class ShotResponse(BaseModel):
    """Response model for shot data."""
    shot_id: int
    story_slug: str
    filepath: str
    tc_in: str
    tc_out: str
    duration_ms: int
    shot_type: Optional[str]
    asr_text: Optional[str]
    has_face: bool
    relevance_score: Optional[float] = None


class StoryStatsResponse(BaseModel):
    """Response model for story statistics."""
    story_slug: str
    total_shots: int
    total_duration_s: float
    shot_type_counts: Dict[str, int]
    has_data: bool


# Startup/shutdown events
@app.on_event("startup")
async def startup_event():
    """Initialize database and indices on startup."""
    global database, vector_index, working_set_builder
    
    logger.info("[API] Starting up...")
    
    # Load configuration
    config_path = Path("config.yaml")
    if config_path.exists():
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
    else:
        config = {}
        logger.warning("[API] No config.yaml found, using defaults")
    
    # Initialize database
    db_path = config.get('database_path', './data/shots.db')
    database = ShotsDatabase(db_path)
    logger.info(f"[API] Database initialized: {db_path}")
    
    # Initialize vector index
    index_dir = config.get('index_dir', './data/indices')
    vector_index = VectorIndex(dimension=384)  # Default for MiniLM
    logger.info(f"[API] Vector index initialized: {index_dir}")
    
    # Initialize working set builder
    working_set_builder = WorkingSetBuilder(database, vector_index)
    logger.info("[API] Working set builder initialized")
    
    logger.info("[API] ✓ Startup complete")


@app.on_event("shutdown")
async def shutdown_event():
    """Clean up on shutdown."""
    global database
    
    logger.info("[API] Shutting down...")
    
    if database:
        database.close()
        logger.info("[API] Database closed")
    
    logger.info("[API] ✓ Shutdown complete")


# API Endpoints

@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "name": "News Edit Agent API",
        "version": "0.1.0",
        "status": "running",
        "endpoints": {
            "search": "/api/shots/search",
            "shot_details": "/api/shots/{shot_id}",
            "story_stats": "/api/stories/{story_slug}/stats",
            "working_set": "/api/working-set/build",
            "beat_working_set": "/api/working-set/beat"
        }
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "database": database is not None,
        "vector_index": vector_index is not None,
        "working_set_builder": working_set_builder is not None
    }


@app.post("/api/shots/search")
async def search_shots(request: SearchRequest):
    """
    Search for shots based on query.
    
    Returns a working set of relevant shots.
    """
    if not working_set_builder:
        raise HTTPException(status_code=500, detail="Working set builder not initialized")
    
    try:
        working_set = working_set_builder.build_for_query(
            story_slug=request.story_slug,
            query=request.query,
            max_shots=request.max_shots,
            shot_types=request.shot_types,
            include_neighbors=request.include_neighbors
        )
        
        return {
            "success": True,
            "working_set": working_set
        }
        
    except Exception as e:
        logger.error(f"[API] Search failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/shots/{shot_id}")
async def get_shot(shot_id: int):
    """Get detailed information about a specific shot."""
    if not database:
        raise HTTPException(status_code=500, detail="Database not initialized")
    
    shot = database.get_shot(shot_id)
    
    if not shot:
        raise HTTPException(status_code=404, detail=f"Shot {shot_id} not found")
    
    return {
        "success": True,
        "shot": shot
    }


@app.get("/api/shots/{shot_id}/neighbors")
async def get_shot_neighbors(
    shot_id: int,
    edge_types: Optional[List[str]] = Query(None)
):
    """Get neighboring shots via graph edges."""
    if not database:
        raise HTTPException(status_code=500, detail="Database not initialized")
    
    neighbors = database.get_neighbors(shot_id, edge_types)
    
    return {
        "success": True,
        "shot_id": shot_id,
        "neighbors": neighbors
    }


@app.get("/api/stories/{story_slug}/stats")
async def get_story_stats(story_slug: str):
    """Get statistics for a story."""
    if not database:
        raise HTTPException(status_code=500, detail="Database not initialized")
    
    shots = database.get_shots_by_story(story_slug)
    
    if not shots:
        return StoryStatsResponse(
            story_slug=story_slug,
            total_shots=0,
            total_duration_s=0.0,
            shot_type_counts={},
            has_data=False
        )
    
    # Calculate statistics
    total_duration = sum(shot['duration_ms'] for shot in shots) / 1000.0
    shot_type_counts = {}
    for shot in shots:
        shot_type = shot.get('shot_type', 'UNKNOWN')
        shot_type_counts[shot_type] = shot_type_counts.get(shot_type, 0) + 1
    
    return StoryStatsResponse(
        story_slug=story_slug,
        total_shots=len(shots),
        total_duration_s=total_duration,
        shot_type_counts=shot_type_counts,
        has_data=True
    )


@app.post("/api/working-set/build")
async def build_working_set(request: WorkingSetRequest):
    """Build a working set for agent processing."""
    if not working_set_builder:
        raise HTTPException(status_code=500, detail="Working set builder not initialized")
    
    try:
        working_set = working_set_builder.build_for_query(
            story_slug=request.story_slug,
            query=request.query,
            max_shots=request.max_shots,
            shot_types=request.shot_types,
            include_neighbors=True
        )
        
        response = {
            "success": True,
            "working_set": working_set
        }
        
        # Optionally format for LLM
        if request.format_for_llm:
            formatted = working_set_builder.format_for_llm(working_set)
            response["llm_context"] = formatted
        
        return response
        
    except Exception as e:
        logger.error(f"[API] Working set build failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/working-set/beat")
async def build_beat_working_set(request: BeatWorkingSetRequest):
    """Build a working set for a specific story beat."""
    if not working_set_builder:
        raise HTTPException(status_code=500, detail="Working set builder not initialized")
    
    try:
        working_set = working_set_builder.build_for_beat(
            story_slug=request.story_slug,
            beat_description=request.beat_description,
            beat_requirements=request.beat_requirements,
            max_shots=request.max_shots
        )
        
        return {
            "success": True,
            "working_set": working_set
        }
        
    except Exception as e:
        logger.error(f"[API] Beat working set build failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/stories")
async def list_stories():
    """List all available stories."""
    if not database:
        raise HTTPException(status_code=500, detail="Database not initialized")
    
    # Get all unique story slugs
    # Note: This requires a custom query - simplified for now
    return {
        "success": True,
        "message": "Story listing not yet implemented",
        "stories": []
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
