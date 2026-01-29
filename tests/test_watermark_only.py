#!/usr/bin/env python3
"""
Test watermark addition only (without captions)
Outputs to tests/results/test-watermark/
"""

import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent / 'backend'))

from clipper import VideoClipper
from watermark_processor import WatermarkProcessor


def create_test_output_folder():
    """Create timestamped output folder for test results"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_folder = Path(__file__).parent / 'results' / f'test-watermark-{timestamp}'
    output_folder.mkdir(parents=True, exist_ok=True)
    return output_folder


def write_verify_file(output_folder, output_path, watermark_text):
    """Generate VERIFY.txt with manual check instructions"""
    verify_text = f"""# Watermark Test Results
Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

## Output Files:
- {output_path.name if output_path else 'No output generated'}

## Watermark Configuration:
- Text: {watermark_text}
- Position: top_right
- Gap from edges: 50px
- Color: White with black shadow/outline
- Font: System default, bold

## What to Verify:

### Watermark Visibility:
1. **Clearly visible**: Watermark text should be easy to read
2. **Positioned correctly**: Should be in top right corner
3. **Proper spacing**: Should have ~50px gap from top and right edges
4. **Persistent**: Should appear throughout entire video
5. **Readable contrast**: Should stand out against background

### Visual Quality:
1. **No pixelation**: Watermark should be crisp and clear
2. **No distortion**: Text should not be stretched or warped
3. **Professional look**: Should look polished, not amateur
4. **Shadow/outline**: Should have black outline for readability
5. **Consistent size**: Watermark should maintain size throughout

### Video Quality:
1. **No degradation**: Original video quality should be maintained
2. **Audio preserved**: Audio should be unchanged
3. **No artifacts**: No encoding artifacts or glitches
4. **Smooth playback**: Video should play smoothly

## Manual Verification Steps:
1. Open {output_path.name if output_path else 'output video'}
2. Play through entire clip
3. Verify watermark is visible in top right
4. Check that it doesn't block important content
5. Verify professional appearance
6. If test passes, delete this results folder
7. If test fails, check watermark_processor.py

## Debug Information:
- Input: tests/test_clip.mp4
- Clip extracted: 10-25 seconds (15s test clip)
- Watermark processor: backend/watermark_processor.py
- Method: FFmpeg drawtext filter
- Position calculation: Based on video dimensions

## Use Cases:
- Testing watermark independently from captions
- Verifying watermark positioning algorithm
- Checking watermark visibility on different backgrounds
- Debugging watermark appearance issues

## Notes:
- Captions require ffmpeg with libass support
- Watermark works with standard ffmpeg (no extra libs needed)
- This test isolates watermark functionality for easier debugging
"""

    verify_path = output_folder / 'VERIFY.txt'
    verify_path.write_text(verify_text)
    print(f"\n📝 Generated verification instructions")


def test_watermark_only(test_video: Path, output_folder: Path):
    """Test watermark addition without captions"""
    print("\n" + "="*60)
    print("Testing Watermark (Text)")
    print("="*60)

    # Step 1: Create a test clip (10-25 seconds)
    print("\n1. Creating test clip...")
    clipper = VideoClipper()
    clip_path = output_folder / "test_clip.mp4"

    clip_result = clipper.create_clip(
        video_path=str(test_video),
        start_time=10,
        end_time=25,
        output_path=str(clip_path)
    )

    if not clip_result['success']:
        print(f"✗ Error creating clip: {clip_result['error']}")
        return None

    print(f"   ✓ Test clip created: {clip_path.name}")

    # Step 2: Add watermark
    print("\n2. Adding text watermark...")
    watermark_config = {
        'enabled': True,
        'type': 'text',
        'text': '@YourChannel',
        'position': 'top_right',
        'gap': 50
    }

    watermark_proc = WatermarkProcessor(watermark_config)
    output_path = output_folder / "clip_with_watermark.mp4"

    watermark_result = watermark_proc.add_watermark(
        video_path=str(clip_path),
        output_path=str(output_path)
    )

    if not watermark_result['success']:
        print(f"✗ Error adding watermark: {watermark_result['error']}")
        return None

    size_mb = output_path.stat().st_size / (1024 * 1024)
    print(f"   ✓ Watermark added: {output_path.name}")
    print(f"   File size: {size_mb:.1f} MB")
    print(f"   Watermark: '{watermark_config['text']}' ({watermark_config['position']}, {watermark_config['gap']}px gap)")

    return output_path


def main():
    """Main test function"""
    print("\n" + "="*60)
    print("WATERMARK ONLY TEST")
    print("="*60)

    # Find test video
    test_video = Path(__file__).parent / 'test_clip.mp4'

    if not test_video.exists():
        print(f"\n✗ Error: Test video not found at {test_video}")
        return 1

    print(f"\n✓ Found test video: {test_video.name}")

    # Create output folder
    output_folder = create_test_output_folder()
    print(f"✓ Created output folder: {output_folder.name}")

    # Run test
    try:
        output_path = test_watermark_only(test_video, output_folder)

        # Generate verification file
        write_verify_file(output_folder, output_path, '@YourChannel')

        # Summary
        print(f"\n{'='*60}")
        print("TEST SUMMARY")
        print(f"{'='*60}")
        print(f"Input: {test_video.name}")
        print(f"Output folder: {output_folder.name}")
        print(f"Output video: {output_path.name if output_path else 'Failed'}")
        print(f"\n📋 Next steps:")
        print(f"   1. Review video in: {output_folder}")
        print(f"   2. Read VERIFY.txt for manual check instructions")
        print(f"   3. Delete folder if test passes")
        print(f"{'='*60}\n")

        return 0 if output_path else 1

    except Exception as e:
        import traceback
        print(f"\n✗ Error: {e}")
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
