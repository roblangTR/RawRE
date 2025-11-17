"""
FastAPI Server for News Edit Agent

Provides REST API endpoints for shot search, working set building,
agent tool access, video upload, and edit generation.
"""

# Fix for PyTorch/OpenMP threading issues on macOS
import os
os.environ['OMP_NUM_THREADS'] = '1'
os.environ['MKL_NUM_THREADS'] = '1'
os.environ['OPENBLAS_NUM_THREADS'] = '1'

from fastapi import FastAPI, HTTPException, Query, UploadFile, File, WebSocket, WebSocketDisconnect, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import logging
import yaml
from pathlib import Path
import asyncio
import json
import shutil
from datetime import datetime
import uuid

from storage.database import ShotsDatabase
from storage.vector_index import VectorIndex
from agent.working_set import WorkingSetBuilder
from agent.orchestrator import AgentOrchestrator
from agent.llm_client import ClaudeClient
from ingest.orchestrator import IngestOrchestrator
from output.edl_writer import EDLWriter
from output.fcpxml_writer import FCPXMLWriter

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
ingest_orchestrator: Optional[IngestOrchestrator] = None
agent_orchestrator: Optional[AgentOrchestrator] = None
llm_client: Optional[ClaudeClient] = None
config: Optional[Dict] = None

# Track ingestion jobs
ingestion_jobs: Dict[str, Dict[str, Any]] = {}

# Track compilation jobs
compilation_jobs: Dict[str, Dict[str, Any]] = {}


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
    global database, vector_index, working_set_builder, ingest_orchestrator, agent_orchestrator, llm_client, config
    
    logger.info("[API] Starting up...")
    
    # Load configuration
    config_path = Path("config.yaml")
    if config_path.exists():
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
            if config is None:
                config = {}
                logger.warning("[API] config.yaml is empty, using defaults")
    else:
        config = {}
        logger.warning("[API] No config.yaml found, using defaults")
    
    # Initialize database
    db_path = config.get('storage', {}).get('database_path', './data/shots.db')
    database = ShotsDatabase(db_path)
    logger.info(f"[API] Database initialized: {db_path}")
    
    # Initialize vector index
    index_dir = config.get('storage', {}).get('index_dir', './data/indices')
    vector_index = VectorIndex(dimension=384)  # Default for MiniLM
    logger.info(f"[API] Vector index initialized: {index_dir}")
    
    # Initialize working set builder
    working_set_builder = WorkingSetBuilder(database, vector_index)
    logger.info("[API] Working set builder initialized")
    
    # Initialize ingest orchestrator
    ingest_orchestrator = IngestOrchestrator(config)
    logger.info("[API] Ingest orchestrator initialized")
    
    # Initialize LLM client
    llm_client = ClaudeClient()
    logger.info("[API] LLM client initialized")
    
    # Initialize agent orchestrator
    agent_orchestrator = AgentOrchestrator(database, vector_index, llm_client)
    logger.info("[API] Agent orchestrator initialized")
    
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


# New endpoints for UI integration

class VideoUploadRequest(BaseModel):
    """Request model for video upload."""
    story_slug: str = Field(..., description="Story identifier")
    
class GenerateEditRequest(BaseModel):
    """Request model for generating an edit."""
    story_slug: str = Field(..., description="Story identifier")
    brief: str = Field(..., description="Editorial brief with story context and requests")
    target_duration: int = Field(..., description="Target duration in seconds")
    max_iterations: int = Field(3, description="Maximum iterations for refinement")


def run_compilation_task(job_id: str, story_slug: str, brief: str, target_duration: int, 
                        max_iterations: int, min_verification_score: float):
    """
    Background task to run edit compilation using AI agents.
    
    Args:
        job_id: Unique job identifier
        story_slug: Story identifier
        brief: Editorial brief
        target_duration: Target duration in seconds
        max_iterations: Maximum refinement iterations
        min_verification_score: Minimum acceptable verification score
    """
    global compilation_jobs, agent_orchestrator, database
    
    try:
        compilation_jobs[job_id] = {
            "status": "processing",
            "story_slug": story_slug,
            "current_iteration": 0,
            "max_iterations": max_iterations,
            "current_agent": None,
            "current_stage": "initializing",
            "progress": 0,
            "message": "Initializing...",
            "start_time": datetime.now().isoformat(),
            "plan": None,
            "beats_progress": [],
            "current_beat": None,
            "result": None,
            "error": None
        }
        
        logger.info(f"[COMPILATION] Starting job {job_id}")
        logger.info(f"[COMPILATION] Story: {story_slug}, Target: {target_duration}s")
        
        if not agent_orchestrator:
            raise Exception("Agent orchestrator not initialized")
        
        # Update status: planning
        compilation_jobs[job_id]["status"] = "planning"
        compilation_jobs[job_id]["current_stage"] = "planning"
        compilation_jobs[job_id]["current_agent"] = "Planner"
        compilation_jobs[job_id]["message"] = "Creating narrative plan..."
        compilation_jobs[job_id]["progress"] = 10
        
        # Define callback to update status during compilation
        def status_callback(stage: str, data: Dict[str, Any]):
            """Callback to update job status during compilation"""
            try:
                if stage == "plan_created":
                    # Store the plan and update beats
                    plan = data.get("plan", {})
                    compilation_jobs[job_id]["plan"] = plan
                    compilation_jobs[job_id]["current_stage"] = "planning_complete"
                    compilation_jobs[job_id]["message"] = f"Plan created: {len(plan.get('beats', []))} beats"
                    compilation_jobs[job_id]["progress"] = 20
                    
                    # Initialize beat progress tracking
                    beats_progress = []
                    for i, beat in enumerate(plan.get('beats', [])):
                        beats_progress.append({
                            "beat_index": i,
                            "title": beat.get("title", f"Beat {i+1}"),
                            "description": beat.get("description", ""),
                            "target_duration": beat.get("target_duration", 0),
                            "status": "pending",
                            "shots": []
                        })
                    compilation_jobs[job_id]["beats_progress"] = beats_progress
                
                elif stage == "beat_searching":
                    # Update current beat being worked on
                    beat_index = data.get("beat_index", 0)
                    beat_title = data.get("beat_title", "")
                    compilation_jobs[job_id]["current_stage"] = "shot_selection"
                    compilation_jobs[job_id]["current_agent"] = "Picker"
                    compilation_jobs[job_id]["current_beat"] = {
                        "index": beat_index,
                        "title": beat_title
                    }
                    compilation_jobs[job_id]["message"] = f"Searching shots for: {beat_title}"
                    
                    # Update beat status
                    if beat_index < len(compilation_jobs[job_id]["beats_progress"]):
                        compilation_jobs[job_id]["beats_progress"][beat_index]["status"] = "searching"
                
                elif stage == "beat_complete":
                    # Mark beat as complete with selected shots
                    beat_index = data.get("beat_index", 0)
                    shots = data.get("shots", [])
                    
                    if beat_index < len(compilation_jobs[job_id]["beats_progress"]):
                        compilation_jobs[job_id]["beats_progress"][beat_index]["status"] = "complete"
                        compilation_jobs[job_id]["beats_progress"][beat_index]["shots"] = shots
                    
                    # Update progress
                    total_beats = len(compilation_jobs[job_id]["beats_progress"])
                    completed_beats = sum(1 for b in compilation_jobs[job_id]["beats_progress"] if b["status"] == "complete")
                    compilation_jobs[job_id]["progress"] = 20 + int((completed_beats / total_beats) * 50)
                
                elif stage == "verification":
                    compilation_jobs[job_id]["current_stage"] = "verification"
                    compilation_jobs[job_id]["current_agent"] = "Verifier"
                    compilation_jobs[job_id]["message"] = "Verifying edit quality..."
                    compilation_jobs[job_id]["progress"] = 75
                
                elif stage == "iteration_complete":
                    iteration = data.get("iteration", 0)
                    score = data.get("score", 0)
                    compilation_jobs[job_id]["current_iteration"] = iteration
                    compilation_jobs[job_id]["message"] = f"Iteration {iteration} complete (score: {score:.1f})"
                    compilation_jobs[job_id]["progress"] = 80
                
            except Exception as e:
                logger.error(f"[COMPILATION] Status callback error: {e}")
        
        # Run the compilation with status callback
        result = agent_orchestrator.compile_edit(
            story_slug=story_slug,
            brief=brief,
            target_duration=target_duration,
            max_iterations=max_iterations,
            min_verification_score=min_verification_score,
            status_callback=status_callback
        )
        
        # Save result to file
        output_dir = Path("./output")
        output_dir.mkdir(parents=True, exist_ok=True)
        result_file = output_dir / f"{job_id}_result.json"
        agent_orchestrator.save_result(result, str(result_file))
        
        # Generate EDL if approved
        if result.get('approved') and result.get('final_selections'):
            try:
                logger.info(f"[COMPILATION] Generating EDL for job {job_id}")
                edl_writer = EDLWriter(title=f"{story_slug}_edit")
                
                # Transform agent output format to EDL writer format
                selections_for_edl = {
                    'beats': []
                }
                
                for beat_selection in result['final_selections'].get('beat_selections', []):
                    beat_data = {
                        'beat_name': beat_selection['beat'].get('title', 'UNTITLED'),
                        'shots': []
                    }
                    
                    for shot in beat_selection.get('shots', []):
                        # Convert shot data to EDL format
                        shot_data = shot.get('full_data', shot)
                        
                        # Parse trim_in timecode to get start time in seconds
                        trim_in = shot.get('trim_in', '00:00:00:00')
                        parts = trim_in.replace(';', ':').split(':')
                        if len(parts) == 4:
                            h, m, s, f = map(int, parts)
                            start_time = h * 3600 + m * 60 + s + f / 25.0
                        else:
                            start_time = 0.0
                        
                        edl_shot = {
                            'shot_id': shot.get('shot_id'),
                            'duration': shot.get('duration', 0),
                            'start_time': start_time,
                            'file_path': shot_data.get('filepath', ''),
                            'reasoning': shot.get('reason', '')[:60] if shot.get('reason') else ''
                        }
                        beat_data['shots'].append(edl_shot)
                    
                    selections_for_edl['beats'].append(beat_data)
                
                edl_path = output_dir / f"{job_id}.edl"
                edl_writer.write_edl(
                    selections=selections_for_edl,
                    output_path=str(edl_path)
                )
                logger.info(f"[COMPILATION] ✓ EDL written to {edl_path}")
                
            except Exception as e:
                logger.error(f"[COMPILATION] Failed to generate EDL: {e}")
                import traceback
                logger.error(traceback.format_exc())
        
        # Mark as complete
        compilation_jobs[job_id]["status"] = "complete"
        compilation_jobs[job_id]["progress"] = 100
        compilation_jobs[job_id]["message"] = "Edit compilation complete!"
        compilation_jobs[job_id]["result"] = result
        compilation_jobs[job_id]["end_time"] = datetime.now().isoformat()
        
        logger.info(f"[COMPILATION] ✓ Job {job_id} completed")
        logger.info(f"[COMPILATION] Approved: {result.get('approved')}")
        logger.info(f"[COMPILATION] Iterations: {len(result.get('iterations', []))}")
        
    except Exception as e:
        logger.error(f"[COMPILATION] ✗ Job {job_id} failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        compilation_jobs[job_id]["status"] = "failed"
        compilation_jobs[job_id]["error"] = str(e)
        compilation_jobs[job_id]["end_time"] = datetime.now().isoformat()


def run_ingestion_task(job_id: str, story_slug: str, video_paths: List[str]):
    """
    Background task to run video ingestion.
    
    Args:
        job_id: Unique job identifier
        story_slug: Story identifier
        video_paths: List of paths to video files to ingest
    """
    global ingestion_jobs, ingest_orchestrator
    
    try:
        ingestion_jobs[job_id] = {
            "status": "processing",
            "story_slug": story_slug,
            "progress": 0,
            "total_files": len(video_paths),
            "processed_files": 0,
            "total_shots": 0,
            "start_time": datetime.now().isoformat(),
            "errors": []
        }
        
        logger.info(f"[INGESTION] Starting job {job_id} for {len(video_paths)} files")
        
        if not ingest_orchestrator:
            raise Exception("Ingest orchestrator not initialized")
        
        # Process each video
        for i, video_path in enumerate(video_paths):
            try:
                logger.info(f"[INGESTION] Processing {i+1}/{len(video_paths)}: {Path(video_path).name}")
                
                result = ingest_orchestrator.ingest_video(
                    video_path=video_path,
                    story_id=story_slug
                )
                
                if result['success']:
                    ingestion_jobs[job_id]['processed_files'] += 1
                    ingestion_jobs[job_id]['total_shots'] += result['shots_stored']
                    logger.info(f"[INGESTION] ✓ Processed {Path(video_path).name}: {result['shots_stored']} shots")
                else:
                    error_msg = f"Failed to process {Path(video_path).name}: {result.get('errors', ['Unknown error'])}"
                    ingestion_jobs[job_id]['errors'].append(error_msg)
                    logger.error(f"[INGESTION] ✗ {error_msg}")
                
                # Update progress
                ingestion_jobs[job_id]['progress'] = int((i + 1) / len(video_paths) * 100)
                
            except Exception as e:
                error_msg = f"Exception processing {Path(video_path).name}: {str(e)}"
                ingestion_jobs[job_id]['errors'].append(error_msg)
                logger.error(f"[INGESTION] ✗ {error_msg}")
                import traceback
                logger.error(traceback.format_exc())
        
        # Mark as complete
        ingestion_jobs[job_id]['status'] = 'completed'
        ingestion_jobs[job_id]['end_time'] = datetime.now().isoformat()
        logger.info(f"[INGESTION] ✓ Job {job_id} completed: {ingestion_jobs[job_id]['total_shots']} shots from {ingestion_jobs[job_id]['processed_files']}/{len(video_paths)} files")
        
    except Exception as e:
        logger.error(f"[INGESTION] ✗ Job {job_id} failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        ingestion_jobs[job_id]['status'] = 'failed'
        ingestion_jobs[job_id]['errors'].append(str(e))
        ingestion_jobs[job_id]['end_time'] = datetime.now().isoformat()


@app.post("/api/videos/upload")
async def upload_videos(
    background_tasks: BackgroundTasks,
    story_slug: str = Query(..., description="Story identifier"),
    files: List[UploadFile] = File(...)
):
    """
    Upload video files for ingestion.
    
    Saves videos to the appropriate directory and triggers ingestion in the background.
    """
    try:
        if not ingest_orchestrator:
            raise HTTPException(status_code=500, detail="Ingest orchestrator not initialized")
        
        # Create upload directory
        upload_dir = Path("./data/uploads") / story_slug
        upload_dir.mkdir(parents=True, exist_ok=True)
        
        uploaded_files = []
        video_paths = []
        
        for file in files:
            # Save file
            filename = file.filename or "unknown_file"
            file_path = upload_dir / filename
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            
            uploaded_files.append({
                "filename": file.filename,
                "path": str(file_path),
                "size": file_path.stat().st_size
            })
            video_paths.append(str(file_path))
            
            logger.info(f"[API] Uploaded {file.filename} for story {story_slug}")
        
        # Create job ID for tracking
        job_id = f"{story_slug}_{uuid.uuid4().hex[:8]}"
        
        # Trigger ingestion in background
        background_tasks.add_task(run_ingestion_task, job_id, story_slug, video_paths)
        
        logger.info(f"[API] Started ingestion job {job_id} for {len(uploaded_files)} files")
        
        return {
            "success": True,
            "job_id": job_id,
            "story_slug": story_slug,
            "uploaded_files": uploaded_files,
            "message": f"Uploaded {len(uploaded_files)} files. Ingestion started in background."
        }
        
    except Exception as e:
        logger.error(f"[API] Upload failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/ingestion/{job_id}/status")
async def get_ingestion_status(job_id: str):
    """
    Get the status of an ingestion job.
    
    Returns progress, shots processed, and any errors.
    """
    if job_id not in ingestion_jobs:
        raise HTTPException(status_code=404, detail=f"Ingestion job {job_id} not found")
    
    return {
        "success": True,
        "job": ingestion_jobs[job_id]
    }


@app.post("/api/edits/generate")
async def generate_edit(request: GenerateEditRequest, background_tasks: BackgroundTasks):
    """
    Generate an edit based on the brief and requirements.
    
    This endpoint initiates the edit generation process using AI agents.
    Poll the status endpoint for progress updates.
    """
    try:
        if not agent_orchestrator:
            raise HTTPException(status_code=500, detail="Agent orchestrator not initialized")
        
        # Check if story has shots
        if not database:
            raise HTTPException(status_code=500, detail="Database not initialized")
        
        shots = database.get_shots_by_story(request.story_slug)
        if not shots or len(shots) == 0:
            raise HTTPException(
                status_code=400, 
                detail=f"No shots found for story '{request.story_slug}'. Please upload and process videos first."
            )
        
        logger.info(f"[API] Generating edit for story {request.story_slug}")
        logger.info(f"[API] Brief: {request.brief[:100]}...")
        logger.info(f"[API] Target duration: {request.target_duration}s")
        logger.info(f"[API] Found {len(shots)} shots for story")
        
        # Create job ID
        job_id = f"{request.story_slug}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Default min verification score
        min_verification_score = 7.0
        
        # Trigger compilation in background
        background_tasks.add_task(
            run_compilation_task,
            job_id,
            request.story_slug,
            request.brief,
            request.target_duration,
            request.max_iterations,
            min_verification_score
        )
        
        logger.info(f"[API] Started compilation job {job_id}")
        
        return {
            "success": True,
            "job_id": job_id,
            "message": "Edit generation started. Poll /api/edits/{job_id}/status for updates.",
            "status": "processing"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[API] Edit generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/edits/{job_id}/status")
async def get_compilation_status(job_id: str):
    """
    Get the status of a compilation job.
    
    Returns progress, current iteration, and result when complete.
    """
    if job_id not in compilation_jobs:
        raise HTTPException(status_code=404, detail=f"Compilation job {job_id} not found")
    
    job = compilation_jobs[job_id]
    
    # Format response for frontend
    response = {
        "success": True,
        "job_id": job_id,
        "status": job["status"],
        "progress": job["progress"],
        "message": job["message"],
        "current_iteration": job.get("current_iteration", 0),
        "max_iterations": job.get("max_iterations", 3),
        "current_agent": job.get("current_agent"),
        "current_stage": job.get("current_stage"),
        "current_beat": job.get("current_beat"),
        "plan": job.get("plan"),
        "beats_progress": job.get("beats_progress", []),
        "start_time": job.get("start_time"),
        "end_time": job.get("end_time")
    }
    
    # Include error if failed
    if job["status"] == "failed":
        response["error"] = job.get("error")
    
    # Include result if complete
    if job["status"] == "complete" and job.get("result"):
        result = job["result"]
        response["result"] = {
            "approved": result.get("approved", False),
            "iterations": len(result.get("iterations", [])),
            "final_verification": result.get("final_verification"),
            "final_selections": result.get("final_selections")
        }
        
        # Format selected shots for frontend
        if result.get("final_selections"):
            selections = result["final_selections"]
            selected_shot_ids = []
            for beat in selections.get("beats", []):
                for shot in beat.get("shots", []):
                    selected_shot_ids.append(shot.get("shot_id"))
            
            response["result"]["selected_shot_ids"] = selected_shot_ids
    
    return response


@app.websocket("/ws/edits/{job_id}")
async def websocket_edit_progress(websocket: WebSocket, job_id: str):
    """
    WebSocket endpoint for real-time edit generation updates.
    
    Streams progress updates, AI feedback, and beat selections to the client.
    """
    await websocket.accept()
    logger.info(f"[API] WebSocket connected for job {job_id}")
    
    try:
        # Send initial connection confirmation
        await websocket.send_json({
            "type": "connected",
            "job_id": job_id,
            "timestamp": datetime.now().isoformat()
        })
        
        # TODO: This would connect to the actual edit generation process
        # For now, send simulated progress updates
        
        # Simulate progress updates
        stages = [
            {"stage": "initialization", "message": "Initializing edit generation..."},
            {"stage": "analysis", "message": "Analyzing available shots..."},
            {"stage": "planning", "message": "Planning story structure..."},
            {"stage": "beat_1", "message": "Selecting shots for beat 1..."},
            {"stage": "beat_2", "message": "Selecting shots for beat 2..."},
            {"stage": "beat_3", "message": "Selecting shots for beat 3..."},
            {"stage": "verification", "message": "Verifying edit quality..."},
            {"stage": "complete", "message": "Edit generation complete!"}
        ]
        
        for i, stage_info in enumerate(stages):
            await asyncio.sleep(1)  # Simulate processing time
            
            await websocket.send_json({
                "type": "progress",
                "stage": stage_info["stage"],
                "message": stage_info["message"],
                "progress": (i + 1) / len(stages) * 100,
                "timestamp": datetime.now().isoformat()
            })
        
        # Send final result
        await websocket.send_json({
            "type": "complete",
            "job_id": job_id,
            "result": {
                "beats": [],
                "total_duration": 0,
                "shots_selected": 0
            },
            "timestamp": datetime.now().isoformat()
        })
        
    except WebSocketDisconnect:
        logger.info(f"[API] WebSocket disconnected for job {job_id}")
    except Exception as e:
        logger.error(f"[API] WebSocket error for job {job_id}: {e}")
        await websocket.send_json({
            "type": "error",
            "message": str(e),
            "timestamp": datetime.now().isoformat()
        })
    finally:
        await websocket.close()


@app.get("/api/edits/{job_id}/export/edl")
async def export_edl(job_id: str):
    """
    Export the edit as an EDL file.
    
    Returns the EDL file for download.
    """
    try:
        # TODO: Load the edit result and generate EDL
        # For now, return a placeholder
        
        edl_path = Path("./output") / f"{job_id}.edl"
        
        if not edl_path.exists():
            raise HTTPException(status_code=404, detail=f"EDL not found for job {job_id}")
        
        return FileResponse(
            path=edl_path,
            media_type="text/plain",
            filename=f"{job_id}.edl"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[API] EDL export failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/edits/{job_id}/export/fcpxml")
async def export_fcpxml(job_id: str):
    """
    Export the edit as an FCPXML file.
    
    Returns the FCPXML file for download.
    """
    try:
        # TODO: Load the edit result and generate FCPXML
        # For now, return a placeholder
        
        fcpxml_path = Path("./output") / f"{job_id}.fcpxml"
        
        if not fcpxml_path.exists():
            raise HTTPException(status_code=404, detail=f"FCPXML not found for job {job_id}")
        
        return FileResponse(
            path=fcpxml_path,
            media_type="application/xml",
            filename=f"{job_id}.fcpxml"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[API] FCPXML export failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/stories/{story_slug}/shots")
async def get_story_shots(story_slug: str):
    """
    Get all shots for a story.
    
    Returns shot data formatted for the frontend UI.
    """
    if not database:
        raise HTTPException(status_code=500, detail="Database not initialized")
    
    try:
        shots = database.get_shots_by_story(story_slug)
        
        # Format for frontend
        formatted_shots = []
        for shot in shots:
            formatted_shots.append({
                "id": shot['shot_id'],
                "storySlug": shot['story_slug'],
                "filepath": shot['filepath'],
                "timecode": {
                    "in": shot['tc_in'],
                    "out": shot['tc_out']
                },
                "duration": shot['duration_ms'],
                "shotType": shot.get('shot_type', 'UNKNOWN'),
                "transcript": shot.get('asr_text', ''),
                "description": shot.get('description', ''),
                "hasFace": shot.get('has_face', False),
                "hasSpeech": bool(shot.get('asr_text')),
                "thumbnailUrl": f"/api/shots/{shot['shot_id']}/thumbnail"
            })
        
        return {
            "success": True,
            "story_slug": story_slug,
            "shots": formatted_shots,
            "total": len(formatted_shots)
        }
        
    except Exception as e:
        logger.error(f"[API] Failed to get story shots: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/shots/{shot_id}/thumbnail")
async def get_shot_thumbnail(shot_id: int):
    """
    Get thumbnail image for a shot.
    
    Returns the thumbnail image if available.
    """
    if not database:
        raise HTTPException(status_code=500, detail="Database not initialized")
    
    try:
        # Get shot from database
        shot = database.get_shot(shot_id)
        
        if not shot:
            raise HTTPException(status_code=404, detail=f"Shot {shot_id} not found")
        
        # Get thumbnail path
        thumb_path = shot.get('thumb_path')
        
        if not thumb_path or not Path(thumb_path).exists():
            raise HTTPException(status_code=404, detail=f"Thumbnail not found for shot {shot_id}")
        
        return FileResponse(
            path=thumb_path,
            media_type="image/jpeg",
            headers={"Cache-Control": "public, max-age=3600"}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[API] Failed to get thumbnail for shot {shot_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
