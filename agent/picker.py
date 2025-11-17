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
from agent.sequence_analyzer import SequenceAnalyzer
from ingest.gemini_analyzer import GeminiAnalyzer

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
                 working_set_builder: WorkingSetBuilder,
                 sequence_analyzer: Optional[SequenceAnalyzer] = None,
                 gemini_analyzer: Optional[GeminiAnalyzer] = None,
                 config: Optional[Dict] = None):
        """
        Initialize picker.
        
        Args:
            llm_client: LLM client for inference
            working_set_builder: Working set builder for candidates
            sequence_analyzer: Optional sequence analyzer for grouping shots
            gemini_analyzer: Optional Gemini analyzer for sequence visual analysis
            config: Optional configuration dictionary
        """
        self.llm_client = llm_client
        self.working_set_builder = working_set_builder
        self.sequence_analyzer = sequence_analyzer
        self.gemini_analyzer = gemini_analyzer
        self.config = config or {}
        
        # Check if sequence-based picking is enabled
        gemini_config = self.config.get('gemini', {})
        self.sequence_picking_enabled = (
            gemini_config.get('picking', {}).get('enabled', False) and
            self.sequence_analyzer is not None and
            self.gemini_analyzer is not None and
            self.gemini_analyzer.enabled
        )
        
        if self.sequence_picking_enabled:
            logger.info("[PICKER] Initialized with sequence-based visual analysis")
        else:
            logger.info("[PICKER] Initialized (sequence analysis disabled)")
    
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
        
        # Step 2: Group into sequences and analyze (if enabled)
        sequences = None
        sequence_analyses = None
        
        if self.sequence_picking_enabled and len(working_set['shots']) > 0:
            try:
                logger.info("[PICKER] Grouping shots into sequences...")
                sequences = self.sequence_analyzer.group_by_sequences(
                    working_set['shots'],
                    method=self.config.get('gemini', {}).get('picking', {}).get('sequence_grouping_method', 'hybrid')
                )
                logger.info(f"[PICKER] Grouped into {len(sequences)} sequences")
                
                # Analyze sequences with Gemini
                if sequences:
                    logger.info("[PICKER] Analyzing sequences with Gemini...")
                    
                    # Prepare video paths (we'll use the first shot's path as representative)
                    video_paths_map = {}
                    for seq_name, seq_shots in sequences.items():
                        if seq_shots:
                            # For now, we'll pass the first shot's video path
                            # In production, this would be the actual video file paths
                            video_paths_map[seq_name] = ['/path/to/video.mp4'] * len(seq_shots)
                    
                    sequence_analyses = self.gemini_analyzer.analyze_all_sequences(
                        sequences=sequences,
                        video_paths_map=video_paths_map
                    )
                    
                    successful = sum(1 for a in sequence_analyses.values() if a is not None)
                    logger.info(f"[PICKER] Analyzed {successful}/{len(sequences)} sequences")
            
            except Exception as e:
                logger.warning(f"[PICKER] Sequence analysis failed: {e}, continuing without it")
                sequences = None
                sequence_analyses = None
        
        # Step 3: Format context for LLM
        if sequences and sequence_analyses:
            context = self._format_context_with_sequences(
                beat=beat,
                working_set=working_set,
                sequences=sequences,
                sequence_analyses=sequence_analyses,
                previous_selections=previous_selections
            )
        else:
            context = self._format_picking_context(
                beat=beat,
                working_set=working_set,
                previous_selections=previous_selections
            )
        
        # Step 4: Call LLM to select shots
        logger.info("[PICKER] Calling LLM to select shots...")
        
        try:
            response = self.llm_client.chat(
                query=context,
                module='picker'
            )
            
            # Extract content from response
            response_text = response.get('content', response)
            
            # Step 5: Parse response
            selection = self._parse_selection_response(response_text, beat, working_set)
            
            # Add sequence metadata to selection
            if sequences:
                selection['sequences_analyzed'] = len(sequences)
                selection['sequence_picking_enabled'] = True
            
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
            lines.append("## Previously Selected Shots (DO NOT REUSE)")
            lines.append(f"**IMPORTANT:** The following {len(previous_selections)} shot(s) have already been used.")
            lines.append("**You MUST NOT select any of these shots again:**")
            lines.append("")
            
            # List shot IDs that are unavailable
            used_shot_ids = set()
            for prev_shot in previous_selections:
                shot_id = prev_shot.get('shot_id')
                if shot_id:
                    used_shot_ids.add(shot_id)
                    duration = prev_shot.get('duration', 0)
                    lines.append(f"- Shot {shot_id} (used for {duration:.1f}s)")
            
            lines.append("")
            lines.append(f"**Available shots:** {len(working_set['shots']) - len(used_shot_ids)} shots remaining")
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
            
            # Gemini visual metadata
            if shot.get('gemini_shot_size'):
                lines.append(f"- Shot Size: {shot['gemini_shot_size']}")
            if shot.get('gemini_camera_movement'):
                lines.append(f"- Camera Movement: {shot['gemini_camera_movement']}")
            if shot.get('gemini_composition'):
                lines.append(f"- Composition: {shot['gemini_composition']}")
            if shot.get('gemini_subjects'):
                subjects = shot['gemini_subjects']
                if isinstance(subjects, list):
                    subjects = ', '.join(subjects)
                lines.append(f"- Subjects: {subjects}")
            if shot.get('gemini_action'):
                lines.append(f"- Action: {shot['gemini_action']}")
            if shot.get('gemini_quality'):
                lines.append(f"- Quality: {shot['gemini_quality']}")
            if shot.get('gemini_description'):
                desc = shot['gemini_description'][:200]
                if len(shot.get('gemini_description', '')) > 200:
                    desc += "..."
                lines.append(f"- Visual Description: {desc}")
            
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
    
    def _format_context_with_sequences(self,
                                       beat: Dict,
                                       working_set: Dict,
                                       sequences: Dict[str, List[Dict]],
                                       sequence_analyses: Dict[str, Optional[Dict]],
                                       previous_selections: Optional[List[Dict]]) -> str:
        """
        Format context with sequence-based visual analysis for LLM shot picking.
        
        Args:
            beat: Beat dictionary
            working_set: Working set of candidate shots
            sequences: Dictionary mapping sequence names to lists of shots
            sequence_analyses: Dictionary mapping sequence names to Gemini analysis results
            previous_selections: Previously selected shots
            
        Returns:
            Formatted context string with sequence intelligence
        """
        lines = []
        
        lines.append("# Shot Selection Task with Visual Sequence Analysis")
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
            lines.append("## Previously Selected Shots (DO NOT REUSE)")
            lines.append(f"**IMPORTANT:** The following {len(previous_selections)} shot(s) have already been used.")
            lines.append("**You MUST NOT select any of these shots again:**")
            lines.append("")
            
            used_shot_ids = set()
            for prev_shot in previous_selections:
                shot_id = prev_shot.get('shot_id')
                if shot_id:
                    used_shot_ids.add(shot_id)
                    duration = prev_shot.get('duration', 0)
                    lines.append(f"- Shot {shot_id} (used for {duration:.1f}s)")
            
            lines.append("")
            lines.append(f"**Available shots:** {len(working_set['shots']) - len(used_shot_ids)} shots remaining")
            lines.append("")
        
        lines.append("## Visual Sequence Analysis")
        lines.append(f"The {len(working_set['shots'])} candidate shots have been grouped into {len(sequences)} sequences and analyzed for visual continuity:")
        lines.append("")
        
        # Present each sequence with its analysis
        for seq_name, seq_shots in sequences.items():
            analysis = sequence_analyses.get(seq_name)
            
            lines.append(f"### Sequence: {seq_name}")
            lines.append(f"**Shots in sequence:** {len(seq_shots)}")
            
            if analysis and isinstance(analysis, dict):
                # Overall assessment
                overall = analysis.get('overall_assessment', {})
                if overall:
                    quality = overall.get('sequence_quality', 'N/A')
                    variety = overall.get('shot_variety', 'N/A')
                    continuity = overall.get('continuity_score', 'N/A')
                    recommended = overall.get('recommended_for_picking', True)
                    
                    lines.append(f"**Quality Score:** {quality}/10")
                    lines.append(f"**Shot Variety:** {variety}")
                    lines.append(f"**Continuity Score:** {continuity}/10")
                    lines.append(f"**Recommended for Use:** {'Yes' if recommended else 'No'}")
                
                # Warnings
                warnings = analysis.get('warnings', [])
                if warnings:
                    lines.append(f"**⚠️ Warnings ({len(warnings)}):**")
                    for warning in warnings[:3]:  # Show first 3
                        w_type = warning.get('type', 'unknown')
                        severity = warning.get('severity', 'unknown')
                        desc = warning.get('description', '')
                        shots_involved = warning.get('shots', [])
                        lines.append(f"  - [{severity.upper()}] {w_type}: {desc}")
                        if shots_involved:
                            lines.append(f"    Shots: {', '.join(map(str, shots_involved))}")
                
                # Recommended subsequences
                recommended_subs = analysis.get('recommended_subsequences', [])
                if recommended_subs:
                    lines.append(f"**✓ Recommended Shot Progressions:**")
                    for sub in recommended_subs[:2]:  # Show top 2
                        sub_shots = sub.get('shots', [])
                        reason = sub.get('reason', '')
                        flow_score = sub.get('flow_score', 0)
                        lines.append(f"  - Shots {', '.join(map(str, sub_shots))}: {reason} (Flow: {flow_score}/10)")
                
                # Entry/exit points
                entry_points = analysis.get('entry_points', [])
                exit_points = analysis.get('exit_points', [])
                if entry_points:
                    best_entry = entry_points[0]
                    lines.append(f"**Best Entry Point:** Shot {best_entry.get('shot_id')} - {best_entry.get('reason', '')}")
                if exit_points:
                    best_exit = exit_points[0]
                    lines.append(f"**Best Exit Point:** Shot {best_exit.get('shot_id')} - {best_exit.get('reason', '')}")
            
            lines.append("")
        
        lines.append("## Candidate Shots (Grouped by Sequence)")
        lines.append("")
        
        # Show shots grouped by sequence
        for seq_name, seq_shots in sequences.items():
            lines.append(f"### {seq_name}")
            
            for shot in seq_shots:
                duration = shot['duration_ms'] / 1000.0
                shot_id = shot['shot_id']
                
                lines.append(f"**Shot {shot_id}**")
                lines.append(f"- Type: {shot.get('shot_type', 'UNKNOWN')}")
                lines.append(f"- Duration: {duration:.1f}s")
                lines.append(f"- Timecode: {shot['tc_in']} - {shot['tc_out']}")
                
                # Get shot-specific analysis if available
                analysis = sequence_analyses.get(seq_name)
                if analysis and isinstance(analysis, dict):
                    shot_analysis = analysis.get('shots', {}).get(f'shot_{shot_id}', {})
                    if shot_analysis:
                        quality = shot_analysis.get('quality_score', 'N/A')
                        works_with = shot_analysis.get('works_well_with', [])
                        avoid_with = shot_analysis.get('avoid_with', [])
                        notes = shot_analysis.get('notes', '')
                        
                        lines.append(f"- **Visual Quality:** {quality}/10")
                        if works_with:
                            lines.append(f"- **Works Well With:** Shots {', '.join(map(str, works_with))}")
                        if avoid_with:
                            lines.append(f"- **⚠️ Avoid With:** Shots {', '.join(map(str, avoid_with))}")
                        if notes:
                            lines.append(f"- **Notes:** {notes}")
                
                # Standard metadata
                if shot.get('gemini_shot_size'):
                    lines.append(f"- Shot Size: {shot['gemini_shot_size']}")
                if shot.get('gemini_composition'):
                    lines.append(f"- Composition: {shot['gemini_composition']}")
                if shot.get('gemini_description'):
                    desc = shot['gemini_description'][:150]
                    if len(shot.get('gemini_description', '')) > 150:
                        desc += "..."
                    lines.append(f"- Description: {desc}")
                if shot.get('asr_text'):
                    text = shot['asr_text'][:100]
                    if len(shot['asr_text']) > 100:
                        text += "..."
                    lines.append(f"- Transcript: \"{text}\"")
                
                lines.append("")
        
        lines.append("## Task")
        lines.append("Select the best shots for this beat, using the visual sequence analysis to:")
        lines.append("1. **Avoid jump cuts** - Don't select shots flagged as incompatible")
        lines.append("2. **Follow recommended progressions** - Use suggested shot sequences when possible")
        lines.append("3. **Consider visual quality** - Prefer shots with higher quality scores")
        lines.append("4. **Ensure smooth transitions** - Select shots that work well together")
        lines.append("5. **Meet beat requirements** - Still satisfy the editorial needs")
        lines.append("6. **Respect target duration** - Fit within the time allocation")
        lines.append("")
        lines.append("Return your selection as JSON:")
        lines.append("```json")
        lines.append("{")
        lines.append('  "shots": [')
        lines.append('    {')
        lines.append('      "shot_id": 123,')
        lines.append('      "reason": "Why this shot was selected (reference sequence analysis)",')
        lines.append('      "trim_in": "00:00:05:00",')
        lines.append('      "trim_out": "00:00:10:00",')
        lines.append('      "duration": 5.0')
        lines.append('    }')
        lines.append('  ],')
        lines.append('  "reasoning": "Overall reasoning, explaining how sequence analysis informed choices"')
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
            
            # Enrich with full shot data (excluding embeddings to reduce JSON size)
            shot_lookup = {s['shot_id']: s for s in working_set['shots']}
            for shot_sel in selection['shots']:
                shot_id = shot_sel['shot_id']
                if shot_id in shot_lookup:
                    # Create a copy without embeddings
                    full_shot = shot_lookup[shot_id].copy()
                    # Remove embedding fields to keep result JSON manageable
                    full_shot.pop('embedding_text', None)
                    full_shot.pop('embedding_visual', None)
                    shot_sel['full_data'] = full_shot
            
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
