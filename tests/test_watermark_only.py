"""
Test script to test watermark only
(Caption burning requires ffmpeg with libass support)
"""

import sys
sys.path.insert(0, 'backend')

from watermark_processor import WatermarkProcessor
from pathlib import Path

print("=" * 60)
print("Testing Watermark (Text)")
print("=" * 60)

try:
    # Use the first clip
    clip_path = "temp/clip_610.03_628.07.mp4"

    if not Path(clip_path).exists():
        print(f"ERROR: Clip not found: {clip_path}")
        sys.exit(1)

    # Test text watermark
    print("\n1. Adding text watermark...")
    watermark_config = {
        'enabled': True,
        'type': 'text',
        'text': '@YourChannel',
        'position': 'top_right',
        'gap': 50
    }

    watermark_proc = WatermarkProcessor(watermark_config)

    watermark_result = watermark_proc.add_watermark(
        video_path=clip_path,
        output_path="temp/clip_with_watermark.mp4"
    )

    if not watermark_result['success']:
        print(f"✗ ERROR adding watermark: {watermark_result['error']}")
        sys.exit(1)

    final_path = watermark_result['output_path']
    size_mb = Path(final_path).stat().st_size / (1024 * 1024)
    print(f"✓ Watermark added successfully!")
    print(f"  Output: {final_path}")
    print(f"  File size: {size_mb:.1f} MB")
    print(f"  Watermark: '@YourChannel' (top right, 50px gap)")

    print("\n" + "=" * 60)
    print("SUCCESS: Watermark test complete!")
    print("=" * 60)

    print(f"\n📺 Final video: {final_path}")
    print("   Play this video to see the watermark in the top right corner")

    print("\n⚠️  NOTE: Caption burning requires ffmpeg with libass support")
    print("   To enable caption burning, reinstall ffmpeg:")
    print("   brew reinstall ffmpeg")

except Exception as e:
    import traceback
    print("\n" + "=" * 60)
    print("ERROR:")
    print(traceback.format_exc())
    print("=" * 60)
    sys.exit(1)
