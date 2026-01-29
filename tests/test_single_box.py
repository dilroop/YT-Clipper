#!/usr/bin/env python3
"""
Test single 9:8 box extraction for dual-face detection
Outputs to tests/results/test-single-box/
"""

import sys
import subprocess
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent / 'backend'))

from reels_processor import ReelsProcessor


def create_test_output_folder():
    """Create timestamped output folder for test results"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_folder = Path(__file__).parent / 'results' / f'test-single-box-{timestamp}'
    output_folder.mkdir(parents=True, exist_ok=True)
    return output_folder


def write_verify_file(output_folder, video_path, box_info):
    """Generate VERIFY.txt with manual check instructions"""
    verify_text = f"""# Single 9:8 Box Extraction Test Results
Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

## Output Files:
- {video_path.name if video_path else 'No output generated'}

## Box Information:
- Position: ({box_info.get('x', 0)}, {box_info.get('y', 0)})
- Size: {box_info.get('width', 0)}x{box_info.get('height', 0)}
- Ratio: {box_info.get('ratio', 0):.3f} (should be 1.125 for 9:8)

## What to Verify:

### Box Dimensions:
1. **Aspect Ratio**: Box should be exactly 9:8 (ratio 1.125)
2. **Face Coverage**: Full face visible with no cutoffs
3. **Top Padding**: Room above head (not cut off at top)
4. **Side Padding**: Face centered horizontally with padding

### Face Positioning:
1. **Upper portion**: Face should be in upper part of box, not centered vertically
2. **Head clearance**: Top of head should have space (not touching top)
3. **Shoulder visibility**: Shoulders should be visible at bottom
4. **No cutoffs**: Entire face and head visible

### Quality Checks:
1. **No distortion**: Video should not be stretched or squashed
2. **Clear crop**: Clean edges with no artifacts
3. **Proper framing**: Professional-looking crop

## Purpose of This Test:
This test extracts a SINGLE 9:8 box from a dual-face video to verify the box
dimensions are correct BEFORE stacking. This helps debug split-screen issues.

## Manual Verification Steps:
1. Open the output video file
2. Play through and check face positioning
3. Verify 9:8 aspect ratio (slightly wider than tall)
4. Check that full head is visible with padding
5. If test passes, delete this results folder
6. If test fails, check padding calculations in reels_processor.py

## Debug Information:
- Input: tests/test_clip.mp4
- Extracted: LEFT face box only (for dual-face videos)
- Algorithm: Corner-based crop with 9:8 conforming
- Used in: Dual-face split-screen stacking
"""

    verify_path = output_folder / 'VERIFY.txt'
    verify_path.write_text(verify_text)
    print(f"\n📝 Generated verification instructions")


def test_single_box(video_path: Path, output_folder: Path):
    """Extract a single 9:8 box for the LEFT face only"""
    print(f"\n{'='*60}")
    print(f"Testing Single 9:8 Box Extraction")
    print(f"{'='*60}")

    processor = ReelsProcessor()

    # Detect speaker positions
    print("\n1. Detecting faces...")
    crop_params = processor.detect_speaker_position(str(video_path))

    # Get face segments for dual face data
    segments = processor.detect_face_segments(str(video_path), check_every_n_frames=8)

    # Get video dimensions
    import cv2
    cap = cv2.VideoCapture(str(video_path))
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    cap.release()

    # Process dual face crop to get parameters
    dual_face_frames = [seg['faces'] for seg in segments if seg['face_count'] == 2 and len(seg.get('faces', [])) > 0]
    if not dual_face_frames:
        print("No dual-face frames found! Falling back to single face mode.")
        left = crop_params
    else:
        flat_frames = [faces for frame_list in dual_face_frames for faces in frame_list if len(faces) == 2]
        if not flat_frames:
            print("No valid dual-face frames! Falling back to single face mode.")
            left = crop_params
        else:
            dual_crop_params = processor._process_dual_face_crop(flat_frames, width, height)
            left = dual_crop_params['left_face']

    print(f"\n2. Extracting face box:")
    print(f"   Position: ({left['x']}, {left['y']})")
    print(f"   Size: {left['width']}x{left['height']}")
    ratio = left['width']/left['height']
    print(f"   Ratio: {ratio:.3f} (should be 1.125 for 9:8)")

    # Create FFmpeg command to extract just the box
    output_path = output_folder / "single_box_output.mp4"
    cmd = [
        'ffmpeg',
        '-i', str(video_path),
        '-vf', f"crop={left['width']}:{left['height']}:{left['x']}:{left['y']}",
        '-c:v', 'libx264',
        '-c:a', 'aac',
        '-preset', 'medium',
        '-crf', '23',
        '-y',
        str(output_path)
    ]

    print(f"\n3. Running FFmpeg...")
    result = subprocess.run(cmd, capture_output=True)

    if result.returncode == 0:
        print(f"   ✓ Success! Saved to: {output_path.name}")
        size_mb = output_path.stat().st_size / (1024 * 1024)
        print(f"   File size: {size_mb:.2f} MB")
        return True, output_path, {'x': left['x'], 'y': left['y'], 'width': left['width'], 'height': left['height'], 'ratio': ratio}
    else:
        print(f"   ✗ Error: {result.stderr.decode()}")
        return False, None, {}


def main():
    """Main test function"""
    print("\n" + "="*60)
    print("SINGLE 9:8 BOX EXTRACTION TEST")
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

    # Test extraction
    success, output_path, box_info = test_single_box(test_video, output_folder)

    # Generate verification file
    write_verify_file(output_folder, output_path, box_info)

    if success:
        print(f"\n{'='*60}")
        print("TEST COMPLETE")
        print(f"{'='*60}")
        print(f"Output folder: {output_folder.name}")
        print(f"Box ratio: {box_info.get('ratio', 0):.3f} (should be 1.125)")
        print(f"\n📋 Next steps:")
        print(f"   1. Review video in: {output_folder}")
        print(f"   2. Read VERIFY.txt for manual check instructions")
        print(f"   3. Delete folder if test passes")
        print(f"{'='*60}\n")

        # Open the video
        subprocess.run(['open', str(output_path)])
        return 0
    else:
        return 1


if __name__ == '__main__':
    sys.exit(main())
