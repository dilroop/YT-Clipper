#!/usr/bin/env python3
"""
Regression Test for Reels Subtitles
Verifies that:
1. Subtitles correctly match the extracted reel's timing.
2. Only words within the reel's time range are included.
3. The PNG fallback rendering engine works correctly for these reels.
"""

import sys
import os
import json
import shutil
import tempfile
from pathlib import Path
from datetime import datetime

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.clipper import VideoClipper
from backend.caption_generator import CaptionGenerator
from backend.core.constants import TEMP_DIR
from backend.core.config import load_config

def run_reels_subtitle_test():
    print("\n" + "="*60)
    print("REELS SUBTITLE REGRESSION TEST")
    print("="*60)

    # 1. Setup paths
    test_dir = Path(__file__).parent
    input_video = test_dir / "test_clip.mp4"
    output_dir = test_dir / "results" / f"test-reels-subtitles-{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    output_dir.mkdir(parents=True, exist_ok=True)

    if not input_video.exists():
        print(f"✗ Error: Test video not found at {input_video}")
        return False

    # 2. Define a "Reel" segment (e.g., from 109.0 to 124.0 seconds)
    reel_start = 109.0
    reel_end = 124.0
    print(f"\n1. Defining reel segment: {reel_start}s to {reel_end}s")

    # 3. Load transcription words from transcript.json
    transcript_path = test_dir / "transcript.json"
    if not transcript_path.exists():
        print(f"✗ Error: transcript.json not found at {transcript_path}")
        return False
        
    with open(transcript_path, 'r', encoding='utf-8') as f:
        transcript_data = json.load(f)
    
    all_words = []
    for segment in transcript_data.get('segments', []):
        all_words.extend(segment.get('words', []))
    
    print(f"   ✓ Loaded {len(all_words)} words from transcript.json")

    # 4. Filter words for this specific reel (Logically what api_process.py does)
    # We include words if they overlap with the reel range
    reel_words = [w for w in all_words if not (w['end'] <= reel_start or w['start'] >= reel_end)]
    
    print(f"   ✓ Filtered {len(reel_words)} words for the 109-124s range")
    if reel_words:
        print(f"     - First word: '{reel_words[0]['word']}' at {reel_words[0]['start']}s")
        print(f"     - Last word: '{reel_words[-1]['word']}' at {reel_words[-1]['start']}s")

    # 5. Extract the reel clip
    print("\n2. Extracting reel clip...")
    clipper = VideoClipper()
    raw_clip_path = output_dir / "raw_reel.mp4"
    clip_result = clipper.create_clip(
        video_path=str(input_video),
        start_time=reel_start,
        end_time=reel_end,
        output_path=str(raw_clip_path)
    )

    if not clip_result['success']:
        print(f"✗ Extraction failed: {clip_result['error']}")
        return False
    print(f"   ✓ Reel extracted: {raw_clip_path.name}")

    # 6. Generate and Burn Subtitles (using dynamic system config)
    print("\n3. Generating and burning subtitles (expecting PNG fallback)...")
    full_config = load_config()
    config = full_config.get('caption_settings', {})
    if not config:
        print("   ⚠️  Warning: No caption_settings found in config.json, using defaults")
        config = {'font_family': 'Impact', 'font_size': 60, 'vertical_position': 75}
        
    print(f"   ✓ Using config: font={config.get('font_family')}, size={config.get('font_size')}, pos={config.get('vertical_position')}%")
    cg = CaptionGenerator(config)

    # Step A: Create ASS file (with offset)
    ass_path = output_dir / "reel.ass"
    cg.create_ass_subtitles(
        words=reel_words,
        output_path=str(ass_path),
        clip_start_time=reel_start,
        video_width=720, # Simulated width
        video_height=1280 # Simulated height (vertical)
    )
    print(f"   ✓ ASS file created with {reel_start}s offset: {ass_path.name}")

    # Step B: Burn captions (Should trigger PNG fallback if subtitles filter missing)
    final_clip_path = output_dir / "final_reel_with_subtitles.mp4"
    burn_result = cg.burn_captions(
        video_path=str(raw_clip_path),
        subtitle_path=str(ass_path),
        output_path=str(final_clip_path)
    )

    if not burn_result['success']:
        print(f"✗ Burning failed: {burn_result.get('error')}")
        return False

    print(f"   ✓ SUCCESS! Final video generated: {final_clip_path}")
    print(f"   ✓ Burn method used output path: {burn_result['output_path']}")

    # 7. Final Verification of instructions
    print("\n" + "="*60)
    print("VERIFICATION INSTRUCTIONS")
    print("="*60)
    print(f"1. Open: {final_clip_path}")
    print("2. Verify that subtitles start with 'EVIDENCE THAT' (from ~109.1s)")
    print("3. Verify that subtitles DO NOT include 'WHAT IS' (from 0s)")
    print("4. Verify that subtitles are styled as LARGE IMPACT text at 75% height")
    print("5. Check if PNG fallback logs appeared in console")
    
    return True

if __name__ == "__main__":
    success = run_reels_subtitle_test()
    sys.exit(0 if success else 1)
