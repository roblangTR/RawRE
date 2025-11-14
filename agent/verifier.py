"""
Verifier Agent Module

Reviews compiled edits for quality, standards compliance, and narrative flow.
Provides feedback and suggestions for improvement.
"""

import logging
from typing import Dict, List, Optional
import json

from agent.llm_client import OpenArenaClient
from agent.system_prompts import get_system_prompt

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class Verifier:
    """Verifies edit quality and compliance."""
    
    def __init__(self, llm_client: OpenArenaClient):
        """
        Initialize verifier.
        
        Args:
            llm_client: LLM client for inference
        """
        self.llm_client = llm_client
        logger.info("[VERIFIER] Initialized")
    
    def verify_edit(self,
                   plan: Dict,
                   selections: Dict,
                   brief: str) -> Dict:
        """
        Verify a compiled edit for quality and compliance.
        
        Args:
            plan: Story plan dictionary
            selections: Shot selections dictionary
            brief: Original editorial brief
            
        Returns:
            Dictionary with verification results
        """
        logger.info("[VERIFIER] Verifying edit...")
        logger.info(f"[VERIFIER] Plan: {len(plan['beats'])} beats")
        logger.info(f"[VERIFIER] Selections: {selections['total_shots']} shots, "
                   f"{selections['total_duration']:.1f}s")
        
        # Format context for LLM
        context = self._format_verification_context(plan, selections, brief)
        
        # Call LLM to verify
        logger.info("[VERIFIER] Calling LLM to verify edit...")
        
        system_prompt = get_system_prompt('verifier')
        
        try:
            response = self.llm_client.generate(
                prompt=context,
                system_prompt=system_prompt,
                max_tokens=2000,
                temperature=0.3  # Low temperature for consistent evaluation
            )
            
            # Parse response
            verification = self._parse_verification_response(response, plan, selections)
            
            logger.info(f"[VERIFIER] ✓ Verification complete")
            logger.info(f"[VERIFIER] Overall Score: {verification.get('overall_score', 'N/A')}/10")
            logger.info(f"[VERIFIER] Issues Found: {len(verification.get('issues', []))}")
            
            return verification
            
        except Exception as e:
            logger.error(f"[VERIFIER] ✗ Verification failed: {e}")
            raise
    
    def _format_verification_context(self,
                                    plan: Dict,
                                    selections: Dict,
                                    brief: str) -> str:
        """
        Format context for LLM verification.
        
        Args:
            plan: Story plan
            selections: Shot selections
            brief: Editorial brief
            
        Returns:
            Formatted context string
        """
        lines = []
        
        lines.append("# Edit Verification Task")
        lines.append("")
        lines.append("## Editorial Brief")
        lines.append(brief)
        lines.append("")
        
        lines.append("## Story Plan")
        lines.append(f"Target Duration: {plan['target_duration']}s")
        lines.append(f"Planned Duration: {plan['planned_duration']}s")
        lines.append(f"Total Beats: {len(plan['beats'])}")
        lines.append("")
        
        for beat in plan['beats']:
            lines.append(f"### Beat {beat['beat_number']}: {beat['title']}")
            lines.append(f"- Description: {beat['description']}")
            lines.append(f"- Target Duration: {beat['target_duration']}s")
            lines.append("")
        
        lines.append("## Compiled Edit")
        lines.append(f"Total Shots: {selections['total_shots']}")
        lines.append(f"Total Duration: {selections['total_duration']:.1f}s")
        lines.append("")
        
        for beat_sel in selections['beat_selections']:
            beat = beat_sel['beat']
            lines.append(f"### Beat {beat['beat_number']}: {beat['title']}")
            lines.append(f"- Shots Selected: {len(beat_sel['shots'])}")
            lines.append(f"- Duration: {beat_sel['duration']:.1f}s")
            
            if beat_sel.get('reasoning'):
                lines.append(f"- Reasoning: {beat_sel['reasoning']}")
            
            lines.append("")
            
            for shot in beat_sel['shots']:
                lines.append(f"  * Shot {shot['shot_id']}: {shot.get('duration', 0):.1f}s")
                if shot.get('reason'):
                    lines.append(f"    Reason: {shot['reason']}")
            
            lines.append("")
        
        lines.append("## Verification Criteria")
        lines.append("")
        lines.append("Evaluate the edit on these dimensions:")
        lines.append("")
        lines.append("1. **Narrative Flow** (1-10)")
        lines.append("   - Does the story flow logically?")
        lines.append("   - Are transitions smooth?")
        lines.append("   - Is the pacing appropriate?")
        lines.append("")
        lines.append("2. **Brief Compliance** (1-10)")
        lines.append("   - Does it match the editorial brief?")
        lines.append("   - Are key points covered?")
        lines.append("   - Is the tone appropriate?")
        lines.append("")
        lines.append("3. **Technical Quality** (1-10)")
        lines.append("   - Are shot types used appropriately?")
        lines.append("   - Is duration within target?")
        lines.append("   - Are there technical issues?")
        lines.append("")
        lines.append("4. **Broadcast Standards** (1-10)")
        lines.append("   - Does it meet broadcast standards?")
        lines.append("   - Is it balanced and fair?")
        lines.append("   - Are there any compliance issues?")
        lines.append("")
        lines.append("## Task")
        lines.append("Provide a comprehensive verification report as JSON:")
        lines.append("```json")
        lines.append("{")
        lines.append('  "overall_score": 8,')
        lines.append('  "scores": {')
        lines.append('    "narrative_flow": 8,')
        lines.append('    "brief_compliance": 9,')
        lines.append('    "technical_quality": 7,')
        lines.append('    "broadcast_standards": 8')
        lines.append('  },')
        lines.append('  "strengths": ["List of strengths"],')
        lines.append('  "issues": [')
        lines.append('    {')
        lines.append('      "severity": "high|medium|low",')
        lines.append('      "category": "narrative|technical|compliance",')
        lines.append('      "description": "Issue description",')
        lines.append('      "suggestion": "How to fix"')
        lines.append('    }')
        lines.append('  ],')
        lines.append('  "recommendations": ["List of recommendations"],')
        lines.append('  "approved": true')
        lines.append('}')
        lines.append("```")
        
        return "\n".join(lines)
    
    def _parse_verification_response(self,
                                    response: str,
                                    plan: Dict,
                                    selections: Dict) -> Dict:
        """
        Parse LLM verification response.
        
        Args:
            response: LLM response text
            plan: Story plan
            selections: Shot selections
            
        Returns:
            Structured verification dictionary
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
            
            verification_data = json.loads(json_str)
            
            # Build complete verification
            verification = {
                'plan': plan,
                'selections': selections,
                'overall_score': verification_data.get('overall_score', 0),
                'scores': verification_data.get('scores', {}),
                'strengths': verification_data.get('strengths', []),
                'issues': verification_data.get('issues', []),
                'recommendations': verification_data.get('recommendations', []),
                'approved': verification_data.get('approved', False),
                'raw_response': response
            }
            
            # Categorize issues by severity
            verification['high_severity_issues'] = [
                i for i in verification['issues'] 
                if i.get('severity') == 'high'
            ]
            verification['medium_severity_issues'] = [
                i for i in verification['issues'] 
                if i.get('severity') == 'medium'
            ]
            verification['low_severity_issues'] = [
                i for i in verification['issues'] 
                if i.get('severity') == 'low'
            ]
            
            return verification
            
        except json.JSONDecodeError as e:
            logger.error(f"[VERIFIER] Failed to parse JSON: {e}")
            logger.error(f"[VERIFIER] Response: {response[:500]}...")
            
            # Return basic verification
            return {
                'plan': plan,
                'selections': selections,
                'overall_score': 0,
                'scores': {},
                'strengths': [],
                'issues': [{
                    'severity': 'high',
                    'category': 'technical',
                    'description': 'Failed to parse verification response',
                    'suggestion': 'Review manually'
                }],
                'recommendations': [],
                'approved': False,
                'error': str(e)
            }
        
        except Exception as e:
            logger.error(f"[VERIFIER] Failed to parse response: {e}")
            return {
                'plan': plan,
                'selections': selections,
                'overall_score': 0,
                'scores': {},
                'strengths': [],
                'issues': [{
                    'severity': 'high',
                    'category': 'technical',
                    'description': f'Verification error: {str(e)}',
                    'suggestion': 'Review manually'
                }],
                'recommendations': [],
                'approved': False,
                'error': str(e)
            }
    
    def quick_check(self, selections: Dict, target_duration: int) -> Dict:
        """
        Perform quick automated checks without LLM.
        
        Args:
            selections: Shot selections
            target_duration: Target duration in seconds
            
        Returns:
            Dictionary with quick check results
        """
        logger.info("[VERIFIER] Performing quick checks...")
        
        issues = []
        
        # Check duration
        duration_diff = abs(selections['total_duration'] - target_duration)
        duration_tolerance = target_duration * 0.1  # 10% tolerance
        
        if duration_diff > duration_tolerance:
            issues.append({
                'severity': 'high' if duration_diff > target_duration * 0.2 else 'medium',
                'category': 'technical',
                'description': f"Duration mismatch: {selections['total_duration']:.1f}s vs target {target_duration}s",
                'suggestion': 'Adjust shot selections to meet target duration'
            })
        
        # Check for empty beats
        for beat_sel in selections['beat_selections']:
            if not beat_sel['shots']:
                issues.append({
                    'severity': 'high',
                    'category': 'technical',
                    'description': f"Beat {beat_sel['beat']['beat_number']} has no shots selected",
                    'suggestion': 'Select shots for this beat'
                })
        
        # Check for very short/long shots
        for beat_sel in selections['beat_selections']:
            for shot in beat_sel['shots']:
                duration = shot.get('duration', 0)
                if duration < 2.0:
                    issues.append({
                        'severity': 'low',
                        'category': 'technical',
                        'description': f"Shot {shot['shot_id']} is very short ({duration:.1f}s)",
                        'suggestion': 'Consider using a longer shot'
                    })
                elif duration > 15.0:
                    issues.append({
                        'severity': 'medium',
                        'category': 'technical',
                        'description': f"Shot {shot['shot_id']} is very long ({duration:.1f}s)",
                        'suggestion': 'Consider trimming or splitting'
                    })
        
        logger.info(f"[VERIFIER] Quick check found {len(issues)} issues")
        
        return {
            'issues': issues,
            'passed': len([i for i in issues if i['severity'] == 'high']) == 0
        }
