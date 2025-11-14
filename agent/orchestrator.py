"""
Agent Orchestrator

Coordinates the three-agent workflow: Planner → Picker → Verifier
Manages state, iterations, and refinements.
"""

import logging
from typing import Dict, List, Optional
import json
from pathlib import Path
from datetime import datetime

from agent.llm_client import OpenArenaClient
from agent.planner import Planner
from agent.picker import Picker
from agent.verifier import Verifier
from agent.working_set import WorkingSetBuilder
from storage.database import ShotsDatabase
from storage.vector_index import VectorIndex

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class AgentOrchestrator:
    """Orchestrates the multi-agent editing workflow."""
    
    def __init__(self,
                 database: ShotsDatabase,
                 vector_index: VectorIndex,
                 llm_client: OpenArenaClient):
        """
        Initialize orchestrator.
        
        Args:
            database: Shot database instance
            vector_index: Vector index instance
            llm_client: LLM client instance
        """
        self.database = database
        self.vector_index = vector_index
        self.llm_client = llm_client
        
        # Initialize working set builder
        self.working_set_builder = WorkingSetBuilder(database, vector_index)
        
        # Initialize agents
        self.planner = Planner(llm_client, self.working_set_builder)
        self.picker = Picker(llm_client, self.working_set_builder)
        self.verifier = Verifier(llm_client)
        
        logger.info("[ORCHESTRATOR] Initialized with all agents")
    
    def compile_edit(self,
                    story_slug: str,
                    brief: str,
                    target_duration: int,
                    constraints: Optional[Dict] = None,
                    max_iterations: int = 3,
                    min_verification_score: float = 7.0) -> Dict:
        """
        Compile a complete edit using the three-agent workflow.
        
        Args:
            story_slug: Story identifier
            brief: Editorial brief
            target_duration: Target duration in seconds
            constraints: Optional constraints
            max_iterations: Maximum refinement iterations
            min_verification_score: Minimum acceptable verification score
            
        Returns:
            Dictionary with complete edit and metadata
        """
        logger.info("=" * 80)
        logger.info("[ORCHESTRATOR] Starting edit compilation")
        logger.info(f"[ORCHESTRATOR] Story: {story_slug}")
        logger.info(f"[ORCHESTRATOR] Brief: {brief}")
        logger.info(f"[ORCHESTRATOR] Target Duration: {target_duration}s")
        logger.info("=" * 80)
        
        start_time = datetime.now()
        
        # Initialize result structure
        result = {
            'story_slug': story_slug,
            'brief': brief,
            'target_duration': target_duration,
            'constraints': constraints,
            'iterations': [],
            'final_plan': None,
            'final_selections': None,
            'final_verification': None,
            'approved': False,
            'start_time': start_time.isoformat(),
            'end_time': None,
            'duration_seconds': None
        }
        
        plan = None
        selections = None
        verification = None
        
        # Iteration loop
        for iteration in range(1, max_iterations + 1):
            logger.info("")
            logger.info("=" * 80)
            logger.info(f"[ORCHESTRATOR] ITERATION {iteration}/{max_iterations}")
            logger.info("=" * 80)
            
            iteration_data = {
                'iteration': iteration,
                'plan': None,
                'selections': None,
                'verification': None,
                'approved': False
            }
            
            try:
                # Step 1: Planning (or refinement)
                if iteration == 1:
                    logger.info("[ORCHESTRATOR] Step 1: Creating initial plan...")
                    plan = self.planner.create_plan(
                        story_slug=story_slug,
                        brief=brief,
                        target_duration=target_duration,
                        constraints=constraints
                    )
                else:
                    logger.info("[ORCHESTRATOR] Step 1: Refining plan based on feedback...")
                    feedback = self._generate_refinement_feedback(verification)
                    plan = self.planner.refine_plan(plan, feedback)
                
                iteration_data['plan'] = plan
                logger.info(f"[ORCHESTRATOR] ✓ Plan: {len(plan['beats'])} beats, "
                           f"{plan['planned_duration']}s")
                
                # Step 2: Shot Selection
                logger.info("[ORCHESTRATOR] Step 2: Selecting shots...")
                selections = self.picker.pick_shots_for_plan(
                    plan=plan,
                    story_slug=story_slug
                )
                iteration_data['selections'] = selections
                logger.info(f"[ORCHESTRATOR] ✓ Selections: {selections['total_shots']} shots, "
                           f"{selections['total_duration']:.1f}s")
                
                # Step 3: Verification
                logger.info("[ORCHESTRATOR] Step 3: Verifying edit...")
                verification = self.verifier.verify_edit(
                    plan=plan,
                    selections=selections,
                    brief=brief
                )
                iteration_data['verification'] = verification
                
                overall_score = verification.get('overall_score', 0)
                logger.info(f"[ORCHESTRATOR] ✓ Verification: {overall_score}/10")
                
                # Check if approved
                if verification.get('approved') and overall_score >= min_verification_score:
                    logger.info("[ORCHESTRATOR] ✓✓✓ EDIT APPROVED ✓✓✓")
                    iteration_data['approved'] = True
                    result['approved'] = True
                    result['iterations'].append(iteration_data)
                    break
                else:
                    logger.info(f"[ORCHESTRATOR] Edit not approved (score: {overall_score})")
                    logger.info(f"[ORCHESTRATOR] Issues: {len(verification.get('issues', []))}")
                    
                    # Log high severity issues
                    high_issues = verification.get('high_severity_issues', [])
                    if high_issues:
                        logger.warning(f"[ORCHESTRATOR] High severity issues:")
                        for issue in high_issues:
                            logger.warning(f"  - {issue.get('description')}")
                
                result['iterations'].append(iteration_data)
                
            except Exception as e:
                logger.error(f"[ORCHESTRATOR] ✗ Iteration {iteration} failed: {e}")
                iteration_data['error'] = str(e)
                result['iterations'].append(iteration_data)
                # Continue to next iteration
        
        # Finalize result
        result['final_plan'] = plan
        result['final_selections'] = selections
        result['final_verification'] = verification
        
        end_time = datetime.now()
        result['end_time'] = end_time.isoformat()
        result['duration_seconds'] = (end_time - start_time).total_seconds()
        
        logger.info("")
        logger.info("=" * 80)
        logger.info("[ORCHESTRATOR] Compilation complete")
        logger.info(f"[ORCHESTRATOR] Iterations: {len(result['iterations'])}")
        logger.info(f"[ORCHESTRATOR] Approved: {result['approved']}")
        logger.info(f"[ORCHESTRATOR] Duration: {result['duration_seconds']:.1f}s")
        logger.info("=" * 80)
        
        return result
    
    def _generate_refinement_feedback(self, verification: Dict) -> str:
        """
        Generate feedback for plan refinement based on verification.
        
        Args:
            verification: Verification results
            
        Returns:
            Feedback string
        """
        feedback_parts = []
        
        # Overall score
        score = verification.get('overall_score', 0)
        feedback_parts.append(f"Overall score: {score}/10")
        
        # Specific scores
        scores = verification.get('scores', {})
        if scores:
            feedback_parts.append("\nScores by dimension:")
            for dimension, score in scores.items():
                feedback_parts.append(f"- {dimension}: {score}/10")
        
        # High severity issues
        high_issues = verification.get('high_severity_issues', [])
        if high_issues:
            feedback_parts.append("\nHigh priority issues to address:")
            for issue in high_issues:
                feedback_parts.append(f"- {issue.get('description')}")
                if issue.get('suggestion'):
                    feedback_parts.append(f"  Suggestion: {issue.get('suggestion')}")
        
        # Medium severity issues
        medium_issues = verification.get('medium_severity_issues', [])
        if medium_issues and len(medium_issues) <= 3:
            feedback_parts.append("\nMedium priority issues:")
            for issue in medium_issues[:3]:
                feedback_parts.append(f"- {issue.get('description')}")
        
        # Recommendations
        recommendations = verification.get('recommendations', [])
        if recommendations:
            feedback_parts.append("\nRecommendations:")
            for rec in recommendations[:3]:
                feedback_parts.append(f"- {rec}")
        
        return "\n".join(feedback_parts)
    
    def save_result(self, result: Dict, output_path: str):
        """
        Save compilation result to JSON file.
        
        Args:
            result: Compilation result dictionary
            output_path: Path to save JSON file
        """
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_file, 'w') as f:
            json.dump(result, f, indent=2)
        
        logger.info(f"[ORCHESTRATOR] Result saved to {output_path}")
    
    def get_edit_summary(self, result: Dict) -> str:
        """
        Generate a human-readable summary of the edit.
        
        Args:
            result: Compilation result
            
        Returns:
            Summary string
        """
        lines = []
        
        lines.append("=" * 80)
        lines.append("EDIT COMPILATION SUMMARY")
        lines.append("=" * 80)
        lines.append("")
        
        lines.append(f"Story: {result['story_slug']}")
        lines.append(f"Brief: {result['brief']}")
        lines.append(f"Target Duration: {result['target_duration']}s")
        lines.append("")
        
        lines.append(f"Status: {'✓ APPROVED' if result['approved'] else '✗ NOT APPROVED'}")
        lines.append(f"Iterations: {len(result['iterations'])}")
        lines.append(f"Compilation Time: {result.get('duration_seconds', 0):.1f}s")
        lines.append("")
        
        if result['final_plan']:
            plan = result['final_plan']
            lines.append(f"Plan: {len(plan['beats'])} beats, {plan['planned_duration']}s planned")
        
        if result['final_selections']:
            sel = result['final_selections']
            lines.append(f"Selections: {sel['total_shots']} shots, {sel['total_duration']:.1f}s actual")
        
        if result['final_verification']:
            ver = result['final_verification']
            lines.append(f"Verification Score: {ver.get('overall_score', 0)}/10")
            
            scores = ver.get('scores', {})
            if scores:
                lines.append("")
                lines.append("Dimension Scores:")
                for dim, score in scores.items():
                    lines.append(f"  - {dim}: {score}/10")
            
            issues = ver.get('issues', [])
            if issues:
                lines.append("")
                lines.append(f"Issues Found: {len(issues)}")
                high = len(ver.get('high_severity_issues', []))
                medium = len(ver.get('medium_severity_issues', []))
                low = len(ver.get('low_severity_issues', []))
                lines.append(f"  - High: {high}, Medium: {medium}, Low: {low}")
        
        lines.append("")
        lines.append("=" * 80)
        
        return "\n".join(lines)
    
    def quick_compile(self,
                     story_slug: str,
                     brief: str,
                     target_duration: int) -> Dict:
        """
        Quick compilation without iterations (single pass).
        
        Args:
            story_slug: Story identifier
            brief: Editorial brief
            target_duration: Target duration
            
        Returns:
            Compilation result
        """
        logger.info("[ORCHESTRATOR] Quick compile (single pass)")
        
        # Plan
        plan = self.planner.create_plan(story_slug, brief, target_duration)
        
        # Pick
        selections = self.picker.pick_shots_for_plan(plan, story_slug)
        
        # Quick check (no LLM verification)
        quick_check = self.verifier.quick_check(selections, target_duration)
        
        return {
            'story_slug': story_slug,
            'brief': brief,
            'target_duration': target_duration,
            'plan': plan,
            'selections': selections,
            'quick_check': quick_check,
            'mode': 'quick'
        }
