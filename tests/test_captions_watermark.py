"""
Test script to test caption burning and watermark
Uses the already created clips and subtitle files
"""

import sys
sys.path.insert(0, 'backend')

from caption_generator import CaptionGenerator
from watermark_processor import WatermarkProcessor
from pathlib import Path

print("=" * 60)
print("Testing Caption Burning & Watermark")
print("=" * 60)

try:
    # Use the first clip
    clip_path = "temp/clip_610.03_628.07.mp4"
    ass_path = "temp/clip_1.ass"

    if not Path(clip_path).exists():
        print(f"ERROR: Clip not found: {clip_path}")
        sys.exit(1)

    if not Path(ass_path).exists():
        print(f"ERROR: Subtitle file not found: {ass_path}")
        sys.exit(1)

    # Step 1: Burn captions
    print("\n1. Burning captions into video...")
    caption_gen = CaptionGenerator()

    burn_result = caption_gen.burn_captions(
        video_path=clip_path,
        subtitle_path=ass_path,
        output_path="temp/clip_with_captions.mp4"
    )

    if not burn_result['success']:
        print(f"✗ ERROR burning captions: {burn_result['error']}")
        sys.exit(1)

    captioned_path = burn_result['output_path']
    size_mb = Path(captioned_path).stat().st_size / (1024 * 1024)
    print(f"✓ Captions burned successfully!")
    print(f"  Output: {captioned_path}")
    print(f"  File size: {size_mb:.1f} MB")

    # Step 2: Add text watermark
    print("\n2. Adding watermark to captioned video...")
    watermark_config = {
        'enabled': True,
        'type': 'text',
        'text': '@YourChannel',
        'position': 'top_right',
        'gap': 50
    }

    watermark_proc = WatermarkProcessor(watermark_config)

    watermark_result = watermark_proc.add_watermark(
        video_path=captioned_path,
        output_path="temp/clip_final.mp4"
    )

    if not watermark_result['success']:
        print(f"✗ ERROR adding watermark: {watermark_result['error']}")
        sys.exit(1)

    final_path = watermark_result['output_path']
    size_mb = Path(final_path).stat().st_size / (1024 * 1024)
    print(f"✓ Watermark added successfully!")
    print(f"  Output: {final_path}")
    print(f"  File size: {size_mb:.1f} MB")
    print(f"  Watermark text: '@YourChannel' (top right)")

    print("\n" + "=" * 60)
    print("SUCCESS: Caption & Watermark test complete!")
    print("=" * 60)

    print(f"\n📺 Final video ready: {final_path}")
    print("   This video has:")
    print("   ✓ Animated word-by-word captions")
    print("   ✓ Text watermark in top right corner")

except Exception as e:
    import traceback
    print("\n" + "=" * 60)
    print("ERROR:")
    print(traceback.format_exc())
    print("=" * 60)
    sys.exit(1)
