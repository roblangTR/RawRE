"""
Picker Agent Module

Selects specific shots for each beat based on the plan.
Uses LLM to evaluate candidates and make selections.
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


class Picker:
    """Picks specific shots for story beats."""
    
    def __init__(self,
                 llm_client: ClaudeClient,
                 working_set_builder: WorkingSetBuilder):
        """
        Initialize picker.
        
        Args:
            llm_client: LLM client for inference
            working_set_builder: Working set builder for candidates
        """
        self.llm_client = llm_client
        self.working_set_builder = working_set_builder
        logger.info("[PICKER] Initialized")
    
    def pick_shots_for_beat(self,
                           beat: Dict,
                           story_slug: str,
                           previous_selections: Optional[List[Dict]] = None) -> Dict:
        """
        Pick shots for a specific beat.
        
        Args:
            beat: Beat dictionary from plan
            story_slug: Story identifier
            previous_selections: Previously selected shots for context
            
        Returns:
            Dictionary with selected shots and reasoning
        """
        logger.info(f"[PICKER] Picking shots for beat {beat['beat_number']}: {beat['title']}")
        
        # Step 1: Build working set for this beat
        working_set = self.working_set_builder.build_for_beat(
            story_slug=story_slug,
            beat_description=beat['description'],
            beat_requirements=beat.get('requirements', []),
            max_shots=30  # Focused set for picking
        )
        
        logger.info(f"[PICKER] Working set: {len(working_set['shots'])} candidate shots")
        
        # Step 2: Format context for LLM
        context = self._format_picking_context(
            beat=beat,
            working_set=working_set,
            previous_selections=previous_selections
        )
        
        # Step 3: Call LLM to select shots
        logger.info("[PICKER] Calling LLM to select shots...")
        
        system_prompt = get_system_prompt('picker')
        
        try:
            response = self.llm_client.chat(
                query=context,
                system_prompt=system_prompt,
                max_tokens=1500,
                module='picker'
            )
            
            # Extract content from response
            response_text = response.get('content', response)
            
            # Step 4: Parse response
            selection = self._parse_selection_response(response_text, beat, working_set)
            
            logger.info(f"[PICKER] ✓ Selected {len(selection['shots'])} shots")
            
            return selection
            
        except Exception as e:
            logger.error(f"[PICKER] ✗ Selection failed: {e}")
            raise
    
    def pick_shots_for_plan(self,
                           plan: Dict,
                           story_slug: str) -> Dict:
        """
        Pick shots for all beats in a plan.
        
        Args:
            plan: Complete plan dictionary
            story_slug: Story identifier
            
        Returns:
            Dictionary with selections for all beats
        """
        logger.info(f"[PICKER] Picking shots for {len(plan['beats'])} beats")
        
        selections = {
            'story_slug': story_slug,
            'plan': plan,
            'beat_selections': [],
            'total_shots': 0,
            'total_duration': 0.0
        }
        
        previous_selections = []
        
        for beat in plan['beats']:
            try:
                selection = self.pick_shots_for_beat(
                    beat=beat,
                    story_slug=story_slug,
                    previous_selections=previous_selections
                )
                
                selections['beat_selections'].append(selection)
                selections['total_shots'] += len(selection['shots'])
                selections['total_duration'] += selection['duration']
                
                # Add to previous selections for context
                previous_selections.extend(selection['shots'])
                
            except Exception as e:
                logger.error(f"[PICKER] Failed to pick shots for beat {beat['beat_number']}: {e}")
                # Continue with other beats
                selections['beat_selections'].append({
                    'beat': beat,
                    'shots': [],
                    'duration': 0.0,
                    'error': str(e)
                })
        
        logger.info(f"[PICKER] ✓ Complete: {selections['total_shots']} shots, "
                   f"{selections['total_duration']:.1f}s")
        
        return selections
    
    def _format_picking_context(self,
                                beat: Dict,
                                working_set: Dict,
                                previous_selections: Optional[List[Dict]]) -> str:
        """
        Format context for LLM shot picking.
        
        Args:
            beat: Beat dictionary
            working_set: Working set of candidate shots
            previous_selections: Previously selected shots
            
        Returns:
            Formatted context string
        """
        lines = []
        
        lines.append("# Shot Selection Task")
        lines.append("")
        lines.append(f"## Beat {beat['beat_number']}: {beat['title']}")
        lines.append(f"**Description:** {beat['description']}")
        lines.append(f"**Target Duration:** {beat['target_duration']} seconds")
        lines.append(f"**Required Shot Types:** {', '.join(beat.get('required_shot_types', []))}")
        lines.append("")
        
        if beat.get('requirements'):
            lines.append("**Requirements:**")
            for req in beat['requirements']:
                lines.append(f"- {req}")
            lines.append("")
        
        if previous_selections:
            lines.append("## Previously Selected Shots")
            lines.append(f"({len(previous_selections)} shots already selected)")
            lines.append("")
        
        lines.append("## Candidate Shots")
        lines.append(f"Total: {len(working_set['shots'])} shots available")
        lines.append("")
        
        for i, shot in enumerate(working_set['shots'], 1):
            duration = shot['duration_ms'] / 1000.0
            lines.append(f"### Shot {shot['shot_id']}")
            lines.append(f"- Type: {shot.get('shot_type', 'UNKNOWN')}")
            lines.append(f"- Duration: {duration:.1f}s")
            lines.append(f"- Timecode: {shot['tc_in']} - {shot['tc_out']}")
            
            if shot.get('relevance_score'):
                lines.append(f"- Relevance: {shot['relevance_score']:.2f}")
            
            if shot.get('asr_text'):
                text = shot['asr_text'][:150]
                if len(shot['asr_text']) > 150:
                    text += "..."
                lines.append(f"- Transcript: \"{text}\"")
            
            if shot.get('has_face'):
                lines.append(f"- Has Face: Yes")
            
            lines.append("")
        
        lines.append("## Task")
        lines.append("Select the best shots for this beat that:")
        lines.append("1. Meet the beat requirements")
        lines.append("2. Fit within the target duration")
        lines.append("3. Tell a coherent story")
        lines.append("4. Follow broadcast standards")
        lines.append("5. Don't repeat previously selected shots")
        lines.append("")
        lines.append("Return your selection as JSON:")
        lines.append("```json")
        lines.append("{")
        lines.append('  "shots": [')
        lines.append('    {')
        lines.append('      "shot_id": 123,')
        lines.append('      "reason": "Why this shot was selected",')
        lines.append('      "trim_in": "00:00:05:00",')
        lines.append('      "trim_out": "00:00:10:00",')
        lines.append('      "duration": 5.0')
        lines.append('    }')
        lines.append('  ],')
        lines.append('  "reasoning": "Overall reasoning for this selection"')
        lines.append('}')
        lines.append("```")
        
        return "\n".join(lines)
    
    def _parse_selection_response(self,
                                  response: str,
                                  beat: Dict,
                                  working_set: Dict) -> Dict:
        """
        Parse LLM response into structured selection.
        
        Args:
            response: LLM response text
            beat: Beat dictionary
            working_set: Working set used
            
        Returns:
            Structured selection dictionary
        """
        try:
            # Extract JSON
            if "```json" in response:
                start = response.find("```json") + 7
                end = response.find("```", start)
                json_str = response[start:end].strip()
            elif "```" in response:
                start = response.find("```") + 3
                end = response.find("```", start)
                json_str = response[start:end].strip()
            else:
                json_str = response.strip()
            
            selection_data = json.loads(json_str)
            
            # Validate structure
            if 'shots' not in selection_data:
                raise ValueError("Response missing 'shots' field")
            
            # Build complete selection
            selection = {
                'beat': beat,
                'shots': selection_data['shots'],
                'reasoning': selection_data.get('reasoning', ''),
                'duration': sum(s.get('duration', 0) for s in selection_data['shots']),
                'raw_response': response
            }
            
            # Enrich with full shot data
            shot_lookup = {s['shot_id']: s for s in working_set['shots']}
            for shot_sel in selection['shots']:
                shot_id = shot_sel['shot_id']
                if shot_id in shot_lookup:
                    shot_sel['full_data'] = shot_lookup[shot_id]
            
            logger.info(f"[PICKER] Parsed selection: {len(selection['shots'])} shots, "
                       f"{selection['duration']:.1f}s")
            
            return selection
            
        except json.JSONDecodeError as e:
            logger.error(f"[PICKER] Failed to parse JSON: {e}")
            logger.error(f"[PICKER] Response: {response[:500]}...")
            
            # Return empty selection
            return {
                'beat': beat,
                'shots': [],
                'reasoning': 'Failed to parse LLM response',
                'duration': 0.0,
                'error': str(e)
            }
        
        except Exception as e:
            logger.error(f"[PICKER] Failed to parse response: {e}")
            return {
                'beat': beat,
                'shots': [],
                'reasoning': 'Failed to parse LLM response',
                'duration': 0.0,
                'error': str(e)
            }
