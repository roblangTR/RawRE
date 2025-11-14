#!/usr/bin/env python3
"""
Test script to generate Gemini proxy and verify file size reduction.
"""

import yaml
from pathlib import Path
from ingest.video_processor import VideoProcessor

def main():
    # Load config
    with open('config.yaml', 'r') as f:
        config = yaml.safe_load(f)
    
    # Initialize video processor
    processor = VideoProcessor(config)
    
    # Test file
    test_file = Path("Test_Rushes/VID_20220424_120853.mp4")
    
    if not test_file.exists():
        print(f"❌ Test file not found: {test_file}")
        return 1
    
    # Get original size
    original_size_mb = test_file.stat().st_size / 1024 / 1024
    print(f"📁 Original file: {test_file.name}")
    print(f"   Size: {original_size_mb:.2f} MB")
    print()
    
    # Generate Gemini proxy
    print("🔄 Generating Gemini proxy (1 Mbit/s, 480p, 12fps)...")
    output_dir = Path("data/gemini_proxies")
    
    try:
        proxy_path = processor.generate_gemini_proxy(test_file, output_dir)
        
        # Get proxy size
        proxy_size_mb = Path(proxy_path).stat().st_size / 1024 / 1024
        reduction_pct = ((original_size_mb - proxy_size_mb) / original_size_mb) * 100
        
        print()
        print("✅ Proxy generated successfully!")
        print()
        print(f"📊 Results:")
        print(f"   Original:  {original_size_mb:.2f} MB")
        print(f"   Proxy:     {proxy_size_mb:.2f} MB")
        print(f"   Reduction: {reduction_pct:.1f}%")
        print(f"   Ratio:     {original_size_mb/proxy_size_mb:.1f}x smaller")
        print()
        print(f"💾 Proxy saved to: {proxy_path}")
        
        # Check if under 15 MB limit
        if proxy_size_mb < 15:
            print(f"✓ Under 15 MB Open Arena limit")
        else:
            print(f"⚠️  Still over 15 MB limit")
        
        return 0
        
    except Exception as e:
        print(f"❌ Failed to generate proxy: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    exit(main())
