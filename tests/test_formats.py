#!/usr/bin/env python3
"""
Test script for multi-format reels output (9:16, stacked photo, stacked video)
Tests all three format options on test_clip.mp4 (first 30 seconds)
Outputs to tests/results/test-formats/
"""

import sys
import subprocess
from pathlib import Path
from datetime import datetime
import cv2

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'backend'))

from reels_processor import ReelsProcessor, FORMAT_VERTICAL_9_16, FORMAT_STACKED_PHOTO, FORMAT_STACKED_VIDEO


def create_test_output_folder():
    """Create timestamped output folder for test results"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_folder = Path(__file__).parent / 'results' / f'test-formats-{timestamp}'
    output_folder.mkdir(parents=True, exist_ok=True)
    return output_folder


def write_verify_file(output_folder, results):
    """Generate VERIFY.txt with manual check instructions"""

    verify_text = f"""# Multi-Format Reels Test Results
Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

## Test Status: {'✅ ALL PASSED' if all(r['success'] for r in results.values()) else '❌ SOME FAILED'}

## Output Files:

### Format 1: Vertical 9:16 (Standard)
- File: format1_vertical_9x16.mp4
- Status: {'✅ SUCCESS' if results.get('format1', {}).get('success') else '❌ FAILED'}
- Mode: {results.get('format1', {}).get('mode', 'N/A')}

### Format 2: Stacked 9:8 (AI Photo)
- File: format2_stacked_photo.mp4
- Status: {'✅ SUCCESS' if results.get('format2', {}).get('success') else '❌ FAILED'}
- Mode: {results.get('format2', {}).get('mode', 'N/A')}
- Format: {results.get('format2', {}).get('format', 'N/A')}

### Format 3: Stacked 9:8 (AI Video)
- File: format3_stacked_video.mp4
- Status: {'✅ SUCCESS' if results.get('format3', {}).get('success') else '❌ FAILED'}
- Mode: {results.get('format3', {}).get('mode', 'N/A')}
- Format: {results.get('format3', {}).get('format', 'N/A')}

## What to Verify:

### Format 1 (Vertical 9:16):
1. **Full 9:16 aspect ratio** (1080x1920)
2. **Face tracking**: Should follow faces smoothly with Bezier interpolation
3. **Dual-face mode**: If 2 faces, should show split-screen
4. **Zero-face panning**: If no faces, should pan left-right smoothly

### Format 2 (Stacked Photo):
1. **Stacked layout**: Two 9:8 boxes (1080x960 each) stacked vertically
2. **Top box**: Static "AI Photo Placeholder" with dark background
3. **Bottom box**: Tracked podcast highlight with face following
4. **Audio**: Should come from bottom box (podcast audio)
5. **Captions**: Should appear at the bottom if caption_text was provided
6. **Smooth transitions**: Bottom box should have smooth face tracking

### Format 3 (Stacked Video):
1. **Stacked layout**: Two 9:8 boxes (1080x960 each) stacked vertically
2. **Top box**: Animated "AI Video Placeholder" with moving test pattern
3. **Bottom box**: Tracked podcast highlight with face following
4. **Audio**: Should come from bottom box (podcast audio)
5. **Captions**: Should appear at the bottom if caption_text was provided
6. **Animation**: Top box should show animated gradient pattern

## Manual Verification Steps:
1. Open each output video file
2. Check resolution is correct (9:16 for all)
3. Verify top/bottom box content for stacked formats
4. Verify audio quality and source (from bottom box)
5. Check face tracking smoothness in bottom box
6. If test passes, delete this results folder
7. If test fails, keep folder for investigation

## Technical Details:
- Input: tests/test_clip.mp4 (first 30 seconds)
- Face detection: MediaPipe FaceDetector
- Tracking: Bezier curve interpolation
- Box dimensions: 1080x960 (9:8 aspect ratio)
- Final output: 1080x1920 (9:16 aspect ratio)

## Errors:
"""

    # Add errors if any
    for fmt, result in results.items():
        if not result.get('success'):
            verify_text += f"\n{fmt}: {result.get('error', 'Unknown error')}"

    if all(r['success'] for r in results.values()):
        verify_text += "\nNone - all formats processed successfully!"

    verify_path = output_folder / 'VERIFY.txt'
    verify_path.write_text(verify_text)
    print(f"\n📝 Generated verification instructions: {verify_path.name}")


def main():
    print("=" * 60)
    print("MULTI-FORMAT REELS TEST")
    print("=" * 60)

    # Setup paths
    test_dir = Path(__file__).parent
    test_video = test_dir / 'test_clip.mp4'

    if not test_video.exists():
        print(f"\n✗ Test video not found: {test_video}")
        return 1

    print(f"\n✓ Found test video: {test_video.name}")

    # Create output folder
    output_folder = create_test_output_folder()
    print(f"✓ Created output folder: {output_folder.name}")

    # Extract first 30 seconds for faster testing
    print(f"\n✓ Extracting first 30 seconds...")
    test_clip = output_folder / 'test_clip_30s.mp4'
    extract_cmd = [
        'ffmpeg',
        '-i', str(test_video),
        '-t', '30',
        '-c', 'copy',
        '-y',
        str(test_clip)
    ]
    subprocess.run(extract_cmd, capture_output=True, check=True)
    print(f"✓ Created 30-second clip: {test_clip.name}")

    # Get video info
    cap = cv2.VideoCapture(str(test_clip))
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    duration = cap.get(cv2.CAP_PROP_FRAME_COUNT) / fps
    cap.release()

    print(f"\nVideo info: {width}x{height} @ {fps:.1f}fps, {duration:.1f}s")

    # Initialize processor
    processor = ReelsProcessor()

    results = {}

    # Test Format 1: Vertical 9:16
    print("\n" + "=" * 60)
    print("FORMAT 1: Vertical 9:16 (Standard)")
    print("=" * 60)
    output1 = output_folder / 'format1_vertical_9x16.mp4'
    print(f"Converting with all tracking modes (dual-face, single-face, zero-face panning)...")

    result1 = processor.convert_to_reels(
        str(test_clip),
        str(output1),
        auto_detect=True,
        dynamic_mode=True,
        output_format=FORMAT_VERTICAL_9_16
    )
    results['format1'] = result1

    if result1.get('success'):
        file_size = output1.stat().st_size / (1024 * 1024)
        print(f"✓ Format 1 complete: {output1.name} ({file_size:.2f} MB)")
        print(f"  Mode: {result1.get('mode', 'N/A')}")
    else:
        print(f"✗ Format 1 failed: {result1.get('error', 'Unknown error')}")

    # Test Format 2: Stacked Photo
    print("\n" + "=" * 60)
    print("FORMAT 2: Stacked 9:8 (AI Photo)")
    print("=" * 60)
    output2 = output_folder / 'format2_stacked_photo.mp4'
    print(f"Converting with AI photo placeholder on top...")

    result2 = processor.convert_to_reels(
        str(test_clip),
        str(output2),
        auto_detect=True,
        dynamic_mode=True,
        output_format=FORMAT_STACKED_PHOTO,
        caption_text="This is a test caption for Format 2"
    )
    results['format2'] = result2

    if result2.get('success'):
        file_size = output2.stat().st_size / (1024 * 1024)
        print(f"✓ Format 2 complete: {output2.name} ({file_size:.2f} MB)")
        print(f"  Mode: {result2.get('mode', 'N/A')}")
        print(f"  Format: {result2.get('format', 'N/A')}")
    else:
        print(f"✗ Format 2 failed: {result2.get('error', 'Unknown error')}")

    # Test Format 3: Stacked Video
    print("\n" + "=" * 60)
    print("FORMAT 3: Stacked 9:8 (AI Video)")
    print("=" * 60)
    output3 = output_folder / 'format3_stacked_video.mp4'
    print(f"Converting with AI video placeholder on top...")

    result3 = processor.convert_to_reels(
        str(test_clip),
        str(output3),
        auto_detect=True,
        dynamic_mode=True,
        output_format=FORMAT_STACKED_VIDEO,
        caption_text="This is a test caption for Format 3"
    )
    results['format3'] = result3

    if result3.get('success'):
        file_size = output3.stat().st_size / (1024 * 1024)
        print(f"✓ Format 3 complete: {output3.name} ({file_size:.2f} MB)")
        print(f"  Mode: {result3.get('mode', 'N/A')}")
        print(f"  Format: {result3.get('format', 'N/A')}")
    else:
        print(f"✗ Format 3 failed: {result3.get('error', 'Unknown error')}")

    # Write verification file
    write_verify_file(output_folder, results)

    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    print(f"Input: {test_video.name}")
    print(f"Output folder: {output_folder.name}")

    all_success = all(r.get('success') for r in results.values())
    print(f"\nOverall: {'✅ ALL TESTS PASSED' if all_success else '❌ SOME TESTS FAILED'}")
    print(f"  Format 1 (9:16): {'✅' if results.get('format1', {}).get('success') else '❌'}")
    print(f"  Format 2 (Stacked Photo): {'✅' if results.get('format2', {}).get('success') else '❌'}")
    print(f"  Format 3 (Stacked Video): {'✅' if results.get('format3', {}).get('success') else '❌'}")

    print(f"\n📋 Next steps:")
    print(f"   1. Review output videos in: {output_folder.absolute()}")
    print(f"   2. Read VERIFY.txt for detailed verification instructions")
    print(f"   3. Delete folder if all tests pass")
    print("=" * 60)

    return 0 if all_success else 1


if __name__ == '__main__':
    sys.exit(main())
