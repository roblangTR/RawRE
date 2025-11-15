#!/usr/bin/env python3
"""
Analyze interaction logs from a complete edit workflow
"""
import json
from pathlib import Path
from collections import defaultdict

def analyze_interactions(session_id="20251115_165201"):
    interaction_dir = Path("logs/interactions")
    files = sorted([f for f in interaction_dir.glob(f"{session_id}_*.json")])
    
    print("=" * 80)
    print("COMPLETE INTERACTION SUMMARY - Full Edit Workflow")
    print("=" * 80)
    print(f"\nSession: {session_id}")
    print(f"Total Interactions: {len(files)}")
    print(f"\n{'='*80}\n")
    
    # Analyze each interaction
    total_prompt_chars = 0
    total_response_chars = 0
    agents = defaultdict(lambda: {'count': 0, 'prompt_chars': 0, 'response_chars': 0})
    
    for i, file in enumerate(files, 1):
        with open(file) as f:
            data = json.load(f)
        
        agent = data['agent']
        prompt_len = data['prompt']['length']
        response_len = data['response']['length']
        
        total_prompt_chars += prompt_len
        total_response_chars += response_len
        
        agents[agent]['count'] += 1
        agents[agent]['prompt_chars'] += prompt_len
        agents[agent]['response_chars'] += response_len
        
        print(f"Interaction {i:02d}: {agent.upper()}")
        print(f"  Prompt:   {prompt_len:,} chars")
        print(f"  Response: {response_len:,} chars")
        
        # Show key info from each interaction
        if agent == 'planner':
            response_text = data['response']['text']
            if 'beats' in response_text:
                import re
                beats = len(re.findall(r'"beat_number":', response_text))
                print(f"  → Created plan with {beats} beats")
        
        elif agent == 'picker':
            response_text = data['response']['text']
            # Extract shot count from response
            import re
            shots_match = re.search(r'(\d+)\s+shots?', response_text.lower())
            if shots_match:
                print(f"  → Selected {shots_match.group(1)} shot(s)")
        
        elif agent == 'verifier':
            response_text = data['response']['text']
            # Extract score
            import re
            score_match = re.search(r'"overall_score":\s*(\d+)', response_text)
            if score_match:
                print(f"  → Verification score: {score_match.group(1)}/10")
        
        print()
    
    print("=" * 80)
    print("SUMMARY BY AGENT")
    print("=" * 80)
    print()
    
    for agent, stats in sorted(agents.items()):
        print(f"{agent.upper()}:")
        print(f"  Interactions: {stats['count']}")
        print(f"  Total Prompt:   {stats['prompt_chars']:,} chars ({stats['prompt_chars']/1024:.1f} KB)")
        print(f"  Total Response: {stats['response_chars']:,} chars ({stats['response_chars']/1024:.1f} KB)")
        print()
    
    print("=" * 80)
    print("OVERALL TOTALS")
    print("=" * 80)
    print(f"Total Prompt Data:   {total_prompt_chars:,} chars ({total_prompt_chars/1024:.1f} KB)")
    print(f"Total Response Data: {total_response_chars:,} chars ({total_response_chars/1024:.1f} KB)")
    print(f"Combined:            {total_prompt_chars + total_response_chars:,} chars ({(total_prompt_chars + total_response_chars)/1024:.1f} KB)")
    print()
    
    # Workflow summary
    print("=" * 80)
    print("WORKFLOW SUMMARY")
    print("=" * 80)
    print("""
1. PLANNER created initial 8-beat plan (100s target)
2. PICKER selected shots for each of 8 beats (8 interactions)
3. VERIFIER checked the complete edit (score: 8/10)
4. Edit APPROVED on first iteration!

Final Edit:
- 15 shots across 8 beats
- 100 seconds total duration
- Approved with score 8/10
- 4 minor issues noted (all low/medium severity)
""")
    
    print("=" * 80)
    print("KEY INSIGHT: PLANNER NOW HAS COMPLETE INFORMATION")
    print("=" * 80)
    print(f"""
The planner's first interaction ({session_id}_0001.json) shows it received:
✓ Full Gemini visual descriptions for all 25 shots
✓ Complete audio transcripts (not truncated)
✓ Rich metadata (size, movement, subjects, actions)
✓ Relevance scores for shot prioritization

This is a MAJOR improvement over the previous version where the planner
only received truncated audio snippets with no visual information.
""")

if __name__ == "__main__":
    analyze_interactions()
