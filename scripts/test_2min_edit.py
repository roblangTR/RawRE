#!/usr/bin/env python3
"""
Test creating a 2-minute edit from the Gallipoli rushes
"""

import yaml
from agent.orchestrator import AgentOrchestrator
from agent.llm_client import ClaudeClient
from storage.database import ShotsDatabase
from storage.vector_index import VectorIndex

def main():
    print("=" * 80)
    print("TESTING 2-MINUTE EDIT WORKFLOW")
    print("=" * 80)
    
    # Load config
    with open('config.yaml') as f:
        config = yaml.safe_load(f)
    
    # Initialize components
    print("\nInitializing components...")
    database = ShotsDatabase('./data/shots.db')
    
    # Vector index dimension (384 for all-MiniLM-L6-v2 text embeddings)
    vector_index = VectorIndex(dimension=384)
    
    # LLM client
    llm_client = ClaudeClient(
        model=config.get('llm', {}).get('model', 'claude-3-5-sonnet-20241022'),
        temperature=config.get('llm', {}).get('temperature', 0.1)
    )
    
    # Initialize agent orchestrator
    orchestrator = AgentOrchestrator(database, vector_index, llm_client)
    
    # Define edit parameters for 2-minute edit
    story_slug = 'edit_test_story'
    brief = """Create a 2-minute documentary-style edit about the Gallipoli military ceremony.
    
The edit should:
- Open with wide establishing shots showing the scale and setting of the ceremony
- Build through the ceremonial actions - wreath laying, salutes, honor guard movements
- Include close-ups of participants showing emotion and reverence
- Capture the solemn, respectful atmosphere throughout
- End with a powerful closing image that encapsulates the meaning of remembrance

The pacing should be measured and dignified, allowing moments to breathe. Use the full 2 minutes to tell a complete story of commemoration and respect."""
    
    target_duration = 120  # 2 minutes
    
    print(f"\nEdit Request:")
    print(f"  Story: {story_slug}")
    print(f"  Duration: {target_duration}s (2 minutes)")
    print(f"  Brief: {brief[:150]}...")
    print("-" * 80)
    
    # Run the agent workflow with 3 iterations for better quality
    print("\nRunning agent workflow (3 iterations max)...")
    result = orchestrator.compile_edit(
        story_slug=story_slug,
        brief=brief,
        target_duration=target_duration,
        max_iterations=3,
        min_verification_score=7.0
    )
    
    print("\n" + "=" * 80)
    print("RESULTS")
    print("=" * 80)
    
    # Print summary
    print("\n" + orchestrator.get_edit_summary(result))
    
    # Show selected shots if available
    if result.get('final_selections'):
        selections = result['final_selections']
        print("\n" + "=" * 80)
        print("SELECTED SHOTS")
        print("=" * 80)
        
        for i, shot in enumerate(selections.get('shots', []), 1):
            print(f"\n{i}. Shot {shot.get('shot_id')}")
            print(f"   Timecode: {shot.get('tc_in')} - {shot.get('tc_out')}")
            print(f"   Duration: {shot.get('duration', 0):.1f}s")
            
            if shot.get('gemini_shot_type'):
                print(f"   Type: {shot['gemini_shot_type']}, Size: {shot.get('gemini_shot_size', 'unknown')}")
            
            if shot.get('gemini_description'):
                desc = shot['gemini_description']
                if len(desc) > 150:
                    desc = desc[:150] + "..."
                print(f"   Description: {desc}")
            
            if shot.get('beat_name'):
                print(f"   Beat: {shot['beat_name']}")
    
    # Save result
    output_path = f"./data/edits/edit_2min_{story_slug}_{result['start_time'][:10]}.json"
    orchestrator.save_result(result, output_path)
    print(f"\n✓ Result saved to: {output_path}")
    
    # Summary stats
    if result.get('final_selections'):
        sel = result['final_selections']
        print(f"\n" + "=" * 80)
        print("EDIT STATISTICS")
        print("=" * 80)
        print(f"Total shots: {sel['total_shots']}")
        print(f"Total duration: {sel['total_duration']:.1f}s")
        print(f"Target duration: {target_duration}s")
        print(f"Difference: {abs(sel['total_duration'] - target_duration):.1f}s")
        print(f"Approved: {'✓ YES' if result['approved'] else '✗ NO'}")
        
        if result.get('final_verification'):
            ver = result['final_verification']
            print(f"Quality score: {ver.get('overall_score', 0)}/10")

if __name__ == '__main__':
    main()
