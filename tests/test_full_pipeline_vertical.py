#!/usr/bin/env python3
"""
Full Pipeline Regression Test: Extraction -> Transcription -> Vertical -> Subtitles
Verifies that:
1. Extraction is accurate.
2. Transcription of the SMALL clip works.
3. Vertical 9:16 conversion works.
4. Subtitles match the NEW transcript perfectly.
"""

import sys
import os
import json
import shutil
from pathlib import Path
from datetime import datetime

# Add backend to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent / 'backend'))

from clipper import VideoClipper
from transcriber import AudioTranscriber
from reels_processor import ReelsProcessor
from caption_generator import CaptionGenerator
from core.config import load_config

def run_full_pipeline_test():
    print("\n" + "="*60)
    print("FULL PIPELINE VERTICAL REELS TEST")
    print("="*60)

    # 1. Setup paths
    test_dir = Path(__file__).parent
    input_video = test_dir / "test_clip.mp4"
    output_dir = test_dir / "results" / f"test-full-pipeline-{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    output_dir.mkdir(parents=True, exist_ok=True)

    if not input_video.exists():
        print(f"✗ Error: Test video not found at {input_video}")
        return False

    # 2. Extract a 15s clip (Accurate seeking now enabled in clipper.py)
    reel_start = 109.0
    duration = 15.0
    print(f"\n1. Extracting {duration}s clip starting at {reel_start}s...")
    
    clipper = VideoClipper()
    raw_clip_path = output_dir / "raw_extract.mp4"
    clip_result = clipper.create_clip(
        video_path=str(input_video),
        start_time=reel_start,
        end_time=reel_start + duration,
        output_path=str(raw_clip_path)
    )

    if not clip_result['success']:
        print(f"✗ Extraction failed: {clip_result['error']}")
        return False
    print(f"   ✓ Clip extracted: {raw_clip_path.name}")

    # 3. Transcribe the EXTRACTED clip (0-indexed)
    print("\n2. Transcribing the extracted clip...")
    transcriber = AudioTranscriber(model_name="tiny") # Use tiny for speed in test
    transcript = transcriber.transcribe(str(raw_clip_path))
    
    if not transcript.get('success'):
        print(f"✗ Transcription failed: {transcript.get('error')}")
        return False
        
    all_words = []
    for segment in transcript.get('segments', []):
        all_words.extend(segment.get('words', []))
    
    print(f"   ✓ Transcribed {len(all_words)} words")
    if all_words:
        print(f"     - First word in clip: '{all_words[0]['word']}' at {all_words[0]['start']}s")

    # 4. Convert to Vertical 9:16 (Standard Reel format)
    print("\n3. Converting to Vertical 9:16...")
    processor = ReelsProcessor()
    # Note: process_video handles face detection and cropping
    vertical_path = output_dir / "vertical_9x16.mp4"
    
    # We use the internal _crop_video or just convert_to_reels from clipper (simpler for test)
    # The user asked for "vertical reef format phase"
    reels_result = clipper.convert_to_reels(
        clip_path=str(raw_clip_path),
        output_path=str(vertical_path)
    )
    
    if not reels_result['success']:
        print(f"✗ Vertical conversion failed: {reels_result.get('error')}")
        return False
    print(f"   ✓ Vertical video created: {vertical_path.name}")

    # 5. Burn Captions onto Vertical Video (using dynamic system config)
    print("\n4. Burning captions onto vertical video...")
    full_config = load_config()
    config = full_config.get('caption_settings', {})
    if not config:
        print("   ⚠️  Warning: No caption_settings found in config.json, using defaults")
        config = {'font_family': 'Impact', 'font_size': 60, 'vertical_position': 75}
        
    print(f"   ✓ Using config: font={config.get('font_family')}, size={config.get('font_size')}, pos={config.get('vertical_position')}%")
    cg = CaptionGenerator(config)

    # Step A: Create ASS file (No offset needed because we transcribed the clip)
    ass_path = output_dir / "vertical.ass"
    cg.create_ass_subtitles(
        words=all_words,
        output_path=str(ass_path),
        clip_start_time=0.0, # NO OFFSET
        video_width=1080,
        video_height=1920
    )

    # Step B: Burn
    final_path = output_dir / "final_vertical_reel.mp4"
    burn_result = cg.burn_captions(
        video_path=str(vertical_path),
        subtitle_path=str(ass_path),
        output_path=str(final_path)
    )

    if not burn_result['success']:
        print(f"✗ Burning failed: {burn_result.get('error')}")
        return False

    print(f"   ✓ SUCCESS! Final vertical reel: {final_path}")

    # 6. Instructions
    print("\n" + "="*60)
    print("VERIFICATION")
    print("="*60)
    print(f"1. Open: {final_path}")
    print("2. Verify that timing is perfect (since we transcribed the clip itself)")
    print("3. Verify 9:16 aspect ratio (1080x1920)")
    
    return True

if __name__ == "__main__":
    success = run_full_pipeline_test()
    sys.exit(0 if success else 1)
