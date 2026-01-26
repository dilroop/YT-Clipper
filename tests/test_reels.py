"""
Test script to test reels conversion
Uses the already created clips from temp folder
"""

import sys
sys.path.insert(0, 'backend')

from reels_processor import ReelsProcessor
from pathlib import Path

print("=" * 60)
print("Testing Reels Conversion")
print("=" * 60)

# Get the existing clips
clip_files = list(Path("temp").glob("clip_*.mp4"))

if not clip_files:
    print("ERROR: No clips found in temp folder")
    sys.exit(1)

print(f"\nFound {len(clip_files)} clips to convert")

try:
    # Initialize reels processor
    reels_proc = ReelsProcessor()

    for clip_file in clip_files:
        print(f"\n{'='*60}")
        print(f"Converting: {clip_file.name}")
        print(f"{'='*60}")

        # Convert to reels
        reels_result = reels_proc.convert_to_reels(
            str(clip_file),
            auto_detect=True  # Use face detection
        )

        if reels_result['success']:
            print(f"✓ Reels video created: {reels_result['output_path']}")

            crop_params = reels_result.get('crop_params', {})
            if crop_params.get('face_detected'):
                print(f"  Face detected: YES")
                print(f"  Crop position: x={crop_params['x']}, y={crop_params['y']}")
                print(f"  Crop size: {crop_params['width']}x{crop_params['height']}")
            else:
                print(f"  Face detected: NO (using default {crop_params.get('position', 'center')} position)")

            # Check file size
            output_path = Path(reels_result['output_path'])
            size_mb = output_path.stat().st_size / (1024 * 1024)
            print(f"  File size: {size_mb:.1f} MB")
        else:
            print(f"✗ ERROR: {reels_result.get('error', 'Unknown error')}")

    print("\n" + "=" * 60)
    print("SUCCESS: Reels conversion complete!")
    print("=" * 60)

    # Show all created reels
    print("\nCreated reels files:")
    reels_files = list(Path("temp").glob("*_reels.mp4"))
    for f in reels_files:
        size_mb = f.stat().st_size / (1024 * 1024)
        print(f"  {f.name} ({size_mb:.1f} MB)")

except Exception as e:
    import traceback
    print("\n" + "=" * 60)
    print("ERROR:")
    print(traceback.format_exc())
    print("=" * 60)
    sys.exit(1)
