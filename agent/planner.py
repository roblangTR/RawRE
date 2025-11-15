"""
Planner Agent Module

Takes an editorial brief and creates a beat-by-beat story structure.
Uses LLM to analyze requirements and plan the edit.
"""

import logging
from typing import Dict, List, Optional
import json

from agent.llm_client import ClaudeClient
from agent.system_prompts import get_system_prompt
from agent.working_set import WorkingSetBuilder

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class Planner:
    """Plans story structure from editorial brief."""
    
    def __init__(self, 
                 llm_client: ClaudeClient,
                 working_set_builder: WorkingSetBuilder):
        """
        Initialize planner.
        
        Args:
            llm_client: LLM client for inference
            working_set_builder: Working set builder for context
        """
        self.llm_client = llm_client
        self.working_set_builder = working_set_builder
        logger.info("[PLANNER] Initialized")
    
    def create_plan(self,
                   story_slug: str,
                   brief: str,
                   target_duration: int,
                   constraints: Optional[Dict] = None) -> Dict:
        """
        Create a beat-by-beat plan for the story.
        
        Args:
            story_slug: Story identifier
            brief: Editorial brief describing the story
            target_duration: Target duration in seconds
            constraints: Optional constraints (e.g., must include certain shots)
            
        Returns:
            Dictionary with plan structure
        """
        logger.info(f"[PLANNER] Creating plan for story: {story_slug}")
        logger.info(f"[PLANNER] Brief: {brief}")
        logger.info(f"[PLANNER] Target duration: {target_duration}s")
        
        # Step 1: Build working set for context
        logger.info("[PLANNER] Building working set for context...")
        working_set = self.working_set_builder.build_for_query(
            story_slug=story_slug,
            query=brief,
            max_shots=100,  # Larger set for planning
            include_neighbors=True
        )
        
        logger.info(f"[PLANNER] Working set: {len(working_set['shots'])} shots, "
                   f"{working_set['total_duration']:.1f}s total")
        
        # Step 2: Format context for LLM
        context = self._format_planning_context(
            working_set=working_set,
            brief=brief,
            target_duration=target_duration,
            constraints=constraints
        )
        
        # Step 3: Call LLM to create plan
        logger.info("[PLANNER] Calling LLM to create plan...")
        
        try:
            response = self.llm_client.chat(
                query=context,
                module='planner'
            )
            
            # Extract content from response
            response_text = response.get('content', response)
            
            # Step 4: Parse response
            plan = self._parse_plan_response(response_text, story_slug, brief, target_duration)
            
            logger.info(f"[PLANNER] ✓ Plan created with {len(plan['beats'])} beats")
            
            return plan
            
        except Exception as e:
            logger.error(f"[PLANNER] ✗ Planning failed: {e}")
            raise
    
    def _format_planning_context(self,
                                 working_set: Dict,
                                 brief: str,
                                 target_duration: int,
                                 constraints: Optional[Dict]) -> str:
        """
        Format context for LLM planning.
        
        Args:
            working_set: Working set dictionary
            brief: Editorial brief
            target_duration: Target duration
            constraints: Optional constraints
            
        Returns:
            Formatted context string
        """
        lines = []
        
        lines.append("# Story Planning Task")
        lines.append("")
        lines.append("## Editorial Brief")
        lines.append(brief)
        lines.append("")
        
        lines.append("## Requirements")
        lines.append(f"- Target Duration: {target_duration} seconds")
        lines.append(f"- Available Material: {len(working_set['shots'])} shots, "
                    f"{working_set['total_duration']:.1f}s total")
        lines.append(f"- Shot Types Available: {working_set['shot_type_counts']}")
        lines.append("")
        
        if constraints:
            lines.append("## Constraints")
            for key, value in constraints.items():
                lines.append(f"- {key}: {value}")
            lines.append("")
        
        lines.append("## Available Material Summary")
        lines.append("")
        
        # Group shots by type for overview
        shots_by_type = {}
        for shot in working_set['shots']:
            shot_type = shot.get('shot_type', 'UNKNOWN')
            if shot_type not in shots_by_type:
                shots_by_type[shot_type] = []
            shots_by_type[shot_type].append(shot)
        
        for shot_type, shots in shots_by_type.items():
            lines.append(f"### {shot_type} Shots ({len(shots)})")
            
            # Show ALL shots (not just top 5) sorted by relevance
            sorted_shots = sorted(shots, 
                                 key=lambda s: s.get('relevance_score', 0), 
                                 reverse=True)
            
            for shot in sorted_shots:
                duration = shot['duration_ms'] / 1000.0
                lines.append(f"\n**Shot {shot['shot_id']}** ({duration:.1f}s)")
                
                # Include Gemini visual description (CRITICAL)
                if shot.get('gemini_description'):
                    lines.append(f"Visual: {shot['gemini_description']}")
                
                # Include longer transcript (500 chars or full text)
                if shot.get('asr_text'):
                    text = shot['asr_text']
                    if len(text) > 500:
                        text = text[:500] + "..."
                    lines.append(f"Audio: \"{text}\"")
                
                # Include additional Gemini metadata if available
                metadata_parts = []
                if shot.get('gemini_shot_size'):
                    metadata_parts.append(f"Size: {shot['gemini_shot_size']}")
                if shot.get('gemini_camera_movement'):
                    metadata_parts.append(f"Movement: {shot['gemini_camera_movement']}")
                if shot.get('gemini_subjects'):
                    subjects = shot['gemini_subjects']
                    if isinstance(subjects, list):
                        subjects = ', '.join(subjects)
                    metadata_parts.append(f"Subjects: {subjects}")
                if shot.get('gemini_action'):
                    metadata_parts.append(f"Action: {shot['gemini_action']}")
                
                if metadata_parts:
                    lines.append(f"Details: {' | '.join(metadata_parts)}")
                
                # Include relevance score for context
                if shot.get('relevance_score'):
                    lines.append(f"Relevance: {shot['relevance_score']:.3f}")
            
            lines.append("")
        
        lines.append("## Task")
        lines.append("Create a beat-by-beat plan for this story that:")
        lines.append("1. Tells a clear, compelling narrative")
        lines.append("2. Meets the target duration")
        lines.append("3. Uses the available material effectively")
        lines.append("4. Follows broadcast news standards")
        lines.append("")
        lines.append("For each beat, specify:")
        lines.append("- Beat number and title")
        lines.append("- Description of what happens")
        lines.append("- Target duration (seconds)")
        lines.append("- Required shot types (SOT/GV/CUTAWAY)")
        lines.append("- Key requirements or constraints")
        lines.append("")
        lines.append("Return your plan as a JSON object with this structure:")
        lines.append("```json")
        lines.append("{")
        lines.append('  "beats": [')
        lines.append('    {')
        lines.append('      "beat_number": 1,')
        lines.append('      "title": "Opening/Establishing",')
        lines.append('      "description": "...",')
        lines.append('      "target_duration": 10,')
        lines.append('      "required_shot_types": ["GV", "CUTAWAY"],')
        lines.append('      "requirements": ["Establish location", "Set scene"]')
        lines.append('    }')
        lines.append('  ]')
        lines.append('}')
        lines.append("```")
        
        return "\n".join(lines)
    
    def _parse_plan_response(self,
                            response: str,
                            story_slug: str,
                            brief: str,
                            target_duration: int) -> Dict:
        """
        Parse LLM response into structured plan.
        
        Args:
            response: LLM response text
            story_slug: Story identifier
            brief: Original brief
            target_duration: Target duration
            
        Returns:
            Structured plan dictionary
        """
        # Try to extract JSON from response
        try:
            # Look for JSON block
            if "```json" in response:
                start = response.find("```json") + 7
                end = response.find("```", start)
                json_str = response[start:end].strip()
            elif "```" in response:
                start = response.find("```") + 3
                end = response.find("```", start)
                json_str = response[start:end].strip()
            else:
                # Try to parse entire response as JSON
                json_str = response.strip()
            
            plan_data = json.loads(json_str)
            
            # Validate structure
            if 'beats' not in plan_data:
                raise ValueError("Response missing 'beats' field")
            
            # Build complete plan
            plan = {
                'story_slug': story_slug,
                'brief': brief,
                'target_duration': target_duration,
                'beats': plan_data['beats'],
                'total_beats': len(plan_data['beats']),
                'planned_duration': sum(b.get('target_duration', 0) 
                                       for b in plan_data['beats']),
                'raw_response': response
            }
            
            # Validate beats
            for i, beat in enumerate(plan['beats'], 1):
                if 'beat_number' not in beat:
                    beat['beat_number'] = i
                if 'title' not in beat:
                    beat['title'] = f"Beat {i}"
                if 'target_duration' not in beat:
                    beat['target_duration'] = target_duration // len(plan['beats'])
                if 'required_shot_types' not in beat:
                    beat['required_shot_types'] = []
                if 'requirements' not in beat:
                    beat['requirements'] = []
            
            logger.info(f"[PLANNER] Parsed plan: {plan['total_beats']} beats, "
                       f"{plan['planned_duration']}s planned duration")
            
            return plan
            
        except json.JSONDecodeError as e:
            logger.error(f"[PLANNER] Failed to parse JSON: {e}")
            logger.error(f"[PLANNER] Response: {response[:500]}...")
            
            # Return fallback plan
            return self._create_fallback_plan(story_slug, brief, target_duration)
        
        except Exception as e:
            logger.error(f"[PLANNER] Failed to parse response: {e}")
            return self._create_fallback_plan(story_slug, brief, target_duration)
    
    def _create_fallback_plan(self,
                             story_slug: str,
                             brief: str,
                             target_duration: int) -> Dict:
        """
        Create a simple fallback plan if LLM parsing fails.
        
        Args:
            story_slug: Story identifier
            brief: Editorial brief
            target_duration: Target duration
            
        Returns:
            Simple 3-beat plan
        """
        logger.warning("[PLANNER] Creating fallback plan")
        
        # Simple 3-beat structure
        beat_duration = target_duration // 3
        
        return {
            'story_slug': story_slug,
            'brief': brief,
            'target_duration': target_duration,
            'beats': [
                {
                    'beat_number': 1,
                    'title': 'Opening',
                    'description': 'Establish the story and context',
                    'target_duration': beat_duration,
                    'required_shot_types': ['GV', 'CUTAWAY'],
                    'requirements': ['Establish location', 'Set scene']
                },
                {
                    'beat_number': 2,
                    'title': 'Development',
                    'description': 'Main content and interviews',
                    'target_duration': beat_duration,
                    'required_shot_types': ['SOT', 'GV'],
                    'requirements': ['Key interviews', 'Supporting visuals']
                },
                {
                    'beat_number': 3,
                    'title': 'Conclusion',
                    'description': 'Wrap up and closing',
                    'target_duration': beat_duration,
                    'required_shot_types': ['GV', 'CUTAWAY'],
                    'requirements': ['Closing visuals', 'Resolution']
                }
            ],
            'total_beats': 3,
            'planned_duration': target_duration,
            'fallback': True
        }
    
    def refine_plan(self,
                   plan: Dict,
                   feedback: str) -> Dict:
        """
        Refine an existing plan based on feedback.
        
        Args:
            plan: Existing plan dictionary
            feedback: Feedback on the plan
            
        Returns:
            Refined plan dictionary
        """
        logger.info("[PLANNER] Refining plan based on feedback")
        logger.info(f"[PLANNER] Feedback: {feedback}")
        
        # Format refinement context
        refinement_context = f"""# Plan Refinement Task

## Current Plan
{json.dumps(plan['beats'], indent=2)}

## Feedback
{feedback}

## Task
Refine the plan based on the feedback. Maintain the same JSON structure.
Return the updated plan as JSON.
"""
        
        try:
            response = self.llm_client.chat(
                query=refinement_context,
                module='planner'
            )
            
            # Extract content from response
            response_text = response.get('content', response)
            
            refined_plan = self._parse_plan_response(
                response_text,
                plan['story_slug'],
                plan['brief'],
                plan['target_duration']
            )
            
            refined_plan['refined'] = True
            refined_plan['original_plan'] = plan
            refined_plan['refinement_feedback'] = feedback
            
            logger.info("[PLANNER] ✓ Plan refined")
            
            return refined_plan
            
        except Exception as e:
            logger.error(f"[PLANNER] ✗ Refinement failed: {e}")
            # Return original plan if refinement fails
            return plan
