"""
AI Agent Interaction Logger

Captures and logs all communications between AI agents and the LLM,
including prompts, responses, context, and metadata.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List
import hashlib

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class InteractionLogger:
    """Logs all AI agent interactions with detailed context."""
    
    def __init__(self, output_dir: str = "logs/interactions"):
        """
        Initialize interaction logger.
        
        Args:
            output_dir: Directory to save interaction logs
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Session tracking
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.interaction_count = 0
        self.interactions = []
        
        logger.info(f"[INTERACTION_LOGGER] Initialized - Session: {self.session_id}")
        logger.info(f"[INTERACTION_LOGGER] Output directory: {self.output_dir}")
    
    def log_interaction(self,
                       agent: str,
                       interaction_type: str,
                       prompt: str,
                       response: Any,
                       system_prompt: Optional[str] = None,
                       context: Optional[str] = None,
                       metadata: Optional[Dict] = None,
                       raw_request: Optional[Dict] = None,
                       raw_response: Optional[Dict] = None) -> str:
        """
        Log a single AI agent interaction.
        
        Args:
            agent: Agent name (planner, picker, verifier)
            interaction_type: Type of interaction (create_plan, pick_shots, verify_edit, etc.)
            prompt: The prompt/query sent to the LLM
            response: The response from the LLM
            system_prompt: System prompt used (if any)
            context: Additional context provided
            metadata: Additional metadata
            raw_request: Raw API request payload
            raw_response: Raw API response
            
        Returns:
            Interaction ID
        """
        self.interaction_count += 1
        interaction_id = f"{self.session_id}_{self.interaction_count:04d}"
        
        timestamp = datetime.now().isoformat()
        
        # Build interaction record
        interaction = {
            'interaction_id': interaction_id,
            'session_id': self.session_id,
            'sequence_number': self.interaction_count,
            'timestamp': timestamp,
            'agent': agent,
            'interaction_type': interaction_type,
            'prompt': {
                'text': prompt,
                'length': len(prompt),
                'hash': hashlib.md5(prompt.encode()).hexdigest()
            },
            'response': {
                'text': str(response),
                'length': len(str(response)),
                'hash': hashlib.md5(str(response).encode()).hexdigest()
            },
            'system_prompt': {
                'text': system_prompt,
                'length': len(system_prompt) if system_prompt else 0
            } if system_prompt else None,
            'context': {
                'text': context,
                'length': len(context) if context else 0
            } if context else None,
            'metadata': metadata or {},
            'raw_request': raw_request,
            'raw_response': raw_response
        }
        
        # Add to session interactions
        self.interactions.append(interaction)
        
        # Log summary
        logger.info("=" * 80)
        logger.info(f"[INTERACTION_LOGGER] Logged Interaction: {interaction_id}")
        logger.info(f"  Agent: {agent}")
        logger.info(f"  Type: {interaction_type}")
        logger.info(f"  Prompt Length: {len(prompt)} chars")
        logger.info(f"  Response Length: {len(str(response))} chars")
        if system_prompt:
            logger.info(f"  System Prompt Length: {len(system_prompt)} chars")
        if context:
            logger.info(f"  Context Length: {len(context)} chars")
        logger.info("=" * 80)
        
        # Save individual interaction
        self._save_interaction(interaction)
        
        return interaction_id
    
    def _save_interaction(self, interaction: Dict):
        """
        Save individual interaction to file.
        
        Args:
            interaction: Interaction dictionary
        """
        filename = f"{interaction['interaction_id']}.json"
        filepath = self.output_dir / filename
        
        with open(filepath, 'w') as f:
            json.dump(interaction, f, indent=2)
        
        logger.debug(f"[INTERACTION_LOGGER] Saved interaction to {filepath}")
    
    def save_session_summary(self) -> str:
        """
        Save complete session summary.
        
        Returns:
            Path to summary file
        """
        summary = {
            'session_id': self.session_id,
            'total_interactions': self.interaction_count,
            'start_time': self.interactions[0]['timestamp'] if self.interactions else None,
            'end_time': self.interactions[-1]['timestamp'] if self.interactions else None,
            'interactions': self.interactions,
            'statistics': self._calculate_statistics()
        }
        
        filename = f"session_{self.session_id}_summary.json"
        filepath = self.output_dir / filename
        
        with open(filepath, 'w') as f:
            json.dump(summary, f, indent=2)
        
        logger.info(f"[INTERACTION_LOGGER] Session summary saved to {filepath}")
        
        return str(filepath)
    
    def _calculate_statistics(self) -> Dict:
        """
        Calculate statistics for the session.
        
        Returns:
            Statistics dictionary
        """
        if not self.interactions:
            return {}
        
        stats = {
            'total_interactions': len(self.interactions),
            'by_agent': {},
            'by_type': {},
            'total_prompt_chars': 0,
            'total_response_chars': 0,
            'total_context_chars': 0,
            'average_prompt_length': 0,
            'average_response_length': 0
        }
        
        for interaction in self.interactions:
            # Count by agent
            agent = interaction['agent']
            stats['by_agent'][agent] = stats['by_agent'].get(agent, 0) + 1
            
            # Count by type
            itype = interaction['interaction_type']
            stats['by_type'][itype] = stats['by_type'].get(itype, 0) + 1
            
            # Sum lengths
            stats['total_prompt_chars'] += interaction['prompt']['length']
            stats['total_response_chars'] += interaction['response']['length']
            if interaction.get('context'):
                stats['total_context_chars'] += interaction['context']['length']
        
        # Calculate averages
        stats['average_prompt_length'] = stats['total_prompt_chars'] / len(self.interactions)
        stats['average_response_length'] = stats['total_response_chars'] / len(self.interactions)
        
        return stats
    
    def get_interaction(self, interaction_id: str) -> Optional[Dict]:
        """
        Retrieve a specific interaction by ID.
        
        Args:
            interaction_id: Interaction ID
            
        Returns:
            Interaction dictionary or None
        """
        for interaction in self.interactions:
            if interaction['interaction_id'] == interaction_id:
                return interaction
        return None
    
    def get_agent_interactions(self, agent: str) -> List[Dict]:
        """
        Get all interactions for a specific agent.
        
        Args:
            agent: Agent name
            
        Returns:
            List of interactions
        """
        return [i for i in self.interactions if i['agent'] == agent]
    
    def generate_readable_report(self) -> str:
        """
        Generate a human-readable report of all interactions.
        
        Returns:
            Report text
        """
        lines = []
        
        lines.append("=" * 80)
        lines.append("AI AGENT INTERACTION LOG")
        lines.append("=" * 80)
        lines.append("")
        lines.append(f"Session ID: {self.session_id}")
        lines.append(f"Total Interactions: {self.interaction_count}")
        lines.append("")
        
        stats = self._calculate_statistics()
        
        lines.append("STATISTICS")
        lines.append("-" * 80)
        lines.append(f"Total Prompt Characters: {stats.get('total_prompt_chars', 0):,}")
        lines.append(f"Total Response Characters: {stats.get('total_response_chars', 0):,}")
        lines.append(f"Average Prompt Length: {stats.get('average_prompt_length', 0):.0f} chars")
        lines.append(f"Average Response Length: {stats.get('average_response_length', 0):.0f} chars")
        lines.append("")
        
        lines.append("BY AGENT")
        lines.append("-" * 80)
        for agent, count in stats.get('by_agent', {}).items():
            lines.append(f"  {agent}: {count} interactions")
        lines.append("")
        
        lines.append("BY TYPE")
        lines.append("-" * 80)
        for itype, count in stats.get('by_type', {}).items():
            lines.append(f"  {itype}: {count} interactions")
        lines.append("")
        
        lines.append("=" * 80)
        lines.append("DETAILED INTERACTIONS")
        lines.append("=" * 80)
        lines.append("")
        
        for i, interaction in enumerate(self.interactions, 1):
            lines.append(f"[{i}] {interaction['interaction_id']}")
            lines.append(f"    Agent: {interaction['agent']}")
            lines.append(f"    Type: {interaction['interaction_type']}")
            lines.append(f"    Timestamp: {interaction['timestamp']}")
            lines.append("")
            
            lines.append("    PROMPT:")
            lines.append("    " + "-" * 76)
            prompt_preview = interaction['prompt']['text'][:500]
            if len(interaction['prompt']['text']) > 500:
                prompt_preview += "... [truncated]"
            for line in prompt_preview.split('\n'):
                lines.append(f"    {line}")
            lines.append("")
            
            if interaction.get('system_prompt'):
                lines.append("    SYSTEM PROMPT:")
                lines.append("    " + "-" * 76)
                sys_preview = interaction['system_prompt']['text'][:300]
                if len(interaction['system_prompt']['text']) > 300:
                    sys_preview += "... [truncated]"
                for line in sys_preview.split('\n'):
                    lines.append(f"    {line}")
                lines.append("")
            
            lines.append("    RESPONSE:")
            lines.append("    " + "-" * 76)
            response_preview = interaction['response']['text'][:500]
            if len(interaction['response']['text']) > 500:
                response_preview += "... [truncated]"
            for line in response_preview.split('\n'):
                lines.append(f"    {line}")
            lines.append("")
            lines.append("=" * 80)
            lines.append("")
        
        report = "\n".join(lines)
        
        # Save report
        report_file = self.output_dir / f"session_{self.session_id}_report.txt"
        with open(report_file, 'w') as f:
            f.write(report)
        
        logger.info(f"[INTERACTION_LOGGER] Readable report saved to {report_file}")
        
        return report


# Global logger instance
_global_logger: Optional[InteractionLogger] = None


def get_interaction_logger(output_dir: str = "logs/interactions") -> InteractionLogger:
    """
    Get or create global interaction logger.
    
    Args:
        output_dir: Output directory for logs
        
    Returns:
        InteractionLogger instance
    """
    global _global_logger
    if _global_logger is None:
        _global_logger = InteractionLogger(output_dir)
    return _global_logger


def reset_interaction_logger():
    """Reset the global interaction logger (for testing)."""
    global _global_logger
    _global_logger = None
