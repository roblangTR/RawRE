#!/usr/bin/env python3
"""
Test the full agent workflow to create an edit
"""

import yaml
from agent.orchestrator import AgentOrchestrator
from agent.llm_client import ClaudeClient
from storage.database import ShotsDatabase
from storage.vector_index import VectorIndex

def main():
    print("=" * 80)
    print("TESTING AGENT EDIT WORKFLOW")
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
    
    # Define edit parameters
    story_slug = 'edit_test_story'
    brief = 'Create a 30-second edit showing the military ceremony at Gallipoli. Focus on the solemn atmosphere and the ceremonial actions.'
    target_duration = 30
    
    print(f"\nEdit Request:")
    print(f"  Story: {story_slug}")
    print(f"  Duration: {target_duration}s")
    print(f"  Brief: {brief}")
    print("-" * 80)
    
    # Run the agent workflow
    print("\nRunning agent workflow...")
    result = orchestrator.compile_edit(
        story_slug=story_slug,
        brief=brief,
        target_duration=target_duration,
        max_iterations=2
    )
    
    print("\n" + "=" * 80)
    print("RESULTS")
    print("=" * 80)
    
    # Print summary
    print("\n" + orchestrator.get_edit_summary(result))
    
    # Show selected shots if available
    if result.get('final_selections'):
        selections = result['final_selections']
        print("\nSelected Shots:")
        for i, shot in enumerate(selections.get('shots', []), 1):
            print(f"  {i}. Shot {shot.get('shot_id')}: {shot.get('tc_in')} - {shot.get('tc_out')}")
            if shot.get('gemini_shot_type'):
                print(f"     Type: {shot['gemini_shot_type']}, Size: {shot.get('gemini_shot_size', 'unknown')}")
            if shot.get('gemini_description'):
                print(f"     {shot['gemini_description'][:100]}...")
    
    # Save result
    output_path = f"./data/edits/edit_{story_slug}_{result['start_time'][:10]}.json"
    orchestrator.save_result(result, output_path)
    print(f"\n✓ Result saved to: {output_path}")

if __name__ == '__main__':
    main()
