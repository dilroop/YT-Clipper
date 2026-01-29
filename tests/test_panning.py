#!/usr/bin/env python3
"""
Test script for zero-face panning and mixed face scenarios
Tests on test_clip.mp4 (first 60 seconds) with varied face counts
Outputs to tests/results/test-panning/
"""

import sys
import subprocess
from pathlib import Path
from datetime import datetime
import cv2

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'backend'))

from reels_processor import ReelsProcessor
from clipper import VideoClipper


def create_test_output_folder():
    """Create timestamped output folder for test results"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_folder = Path(__file__).parent / 'results' / f'test-panning-{timestamp}'
    output_folder.mkdir(parents=True, exist_ok=True)
    return output_folder


def write_verify_file(output_folder, video_path, segments, success):
    """Generate VERIFY.txt with manual check instructions"""

    # Count segment types
    zero_face = sum(1 for s in segments if s['face_count'] == 0)
    single_face = sum(1 for s in segments if s['face_count'] == 1)
    dual_face = sum(1 for s in segments if s['face_count'] == 2)

    verify_text = f"""# Zero-Face Panning Test Results
Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

## Test Status: {'✅ SUCCESS' if success else '❌ FAILED'}

## Output Files:
- {video_path.name if video_path else 'No output generated'}
- debug_faces.mp4 (visualization with face boxes)

## Detected Segments:
- Zero-face segments: {zero_face} (should show smooth panning)
- Single-face segments: {single_face} (should follow face with Bezier curves)
- Dual-face segments: {dual_face} (should show split-screen)

## What to Verify:

### Zero-Face Segments (No faces detected):
1. **Smooth panning**: Camera should pan left-to-right smoothly
2. **Boundary respect**: Should stay within 15%-85% of frame width
3. **Continuous motion**: Sine wave motion, not sudden jumps
4. **Cycle timing**: Should complete one pan cycle every 8 seconds

### Single-Face Segments:
1. **Face tracking**: Crop should follow face smoothly
2. **Bezier interpolation**: Motion should be fluid, no jank
3. **Proper centering**: Face centered in crop window

### Dual-Face Segments:
1. **Split-screen layout**: Two 9:8 boxes stacked vertically
2. **Both faces visible**: Each person fully visible in their box
3. **Proper framing**: Faces in upper portion with good padding

## Manual Verification Steps:
1. Open the output video file
2. Play through the entire clip
3. Check the criteria above for each segment type
4. Verify smooth transitions between segment types
5. If test passes, delete this results folder
6. If test fails, keep folder for investigation

## Debug Information:
- Input: tests/test_clip.mp4 (first 60 seconds)
- Face detection: MediaPipe FaceDetector
- Panning boundaries: 15% to 85% (hiding edges)
- Pan cycle duration: 8 seconds
- Smoothing: Bezier curves with Gaussian filter

## Settings:
- FACE_CHECK_INTERVAL_FRAMES: 4
- USE_SMOOTH_INTERPOLATION: True
- ENABLE_ZERO_FACE_PANNING: True
- PAN_LEFT_BOUNDARY: 0.15 (15%)
- PAN_RIGHT_BOUNDARY: 0.85 (85%)
- PAN_CYCLE_DURATION: 8.0 seconds

## Common Issues:
- Panning too fast → Increase PAN_CYCLE_DURATION
- Not reaching edges → Check boundary calculations
- Sudden transitions → Check interpolation is enabled
"""

    verify_path = output_folder / 'VERIFY.txt'
    verify_path.write_text(verify_text)
    print(f"\n📝 Generated verification instructions: {verify_path.name}")


def create_debug_visualization(video_path: Path, segments: list, output_path: Path):
    """Create debug video with face detection boxes overlaid"""
    from reels_processor import ReelsProcessor
    processor = ReelsProcessor()

    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        print(f"   ✗ Cannot open video: {video_path}")
        return

    # Get video properties
    fps = cap.get(cv2.CAP_PROP_FPS)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')

    out = cv2.VideoWriter(str(output_path), fourcc, fps, (width, height))

    # Process frames
    frame_idx = 0
    while True:
        ret, frame = cap.read()
        if not ret:
            break

        timestamp = frame_idx / fps

        # Find current segment
        current_seg = None
        for seg in segments:
            if seg['start_time'] <= timestamp < seg['end_time']:
                current_seg = seg
                break

        # Draw face boxes if available
        if current_seg and 'faces' in current_seg and current_seg['faces']:
            # Get face data for closest frame in segment
            seg_progress = (timestamp - current_seg['start_time']) / (current_seg['end_time'] - current_seg['start_time'])
            face_idx = int(seg_progress * len(current_seg['faces']))
            face_idx = min(face_idx, len(current_seg['faces']) - 1)

            if face_idx >= 0 and current_seg['faces'][face_idx]:
                for face in current_seg['faces'][face_idx]:
                    # Draw face box
                    tl = (face['topLeft']['x'], face['topLeft']['y'])
                    rb = (face['rightBottom']['x'], face['rightBottom']['y'])
                    cv2.rectangle(frame, tl, rb, (0, 255, 0), 3)

        # Draw segment info
        if current_seg:
            face_count = current_seg['face_count']
            if face_count == 0:
                mode_text = "PANNING (0 faces)"
                color = (255, 165, 0)  # Orange
            elif face_count == 1:
                mode_text = "TRACKING (1 face)"
                color = (0, 255, 0)  # Green
            elif face_count == 2:
                mode_text = "SPLIT-SCREEN (2 faces)"
                color = (0, 0, 255)  # Red
            else:
                mode_text = f"{face_count} faces"
                color = (255, 255, 255)

            cv2.putText(frame, mode_text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, color, 2)

        out.write(frame)
        frame_idx += 1

    cap.release()
    out.release()
    print(f"   ✓ Debug video created: {output_path.name}")
    print(f"   Orange = Panning | Green = Face tracking | Red = Split-screen")


def main():
    print("=" * 60)
    print("ZERO-FACE PANNING TEST")
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

    # Extract first 60 seconds
    print(f"\n✓ Extracting first 60 seconds...")
    test_clip = output_folder / 'test_clip_1min.mp4'
    extract_cmd = [
        'ffmpeg',
        '-i', str(test_video),
        '-t', '60',
        '-c', 'copy',
        '-y',
        str(test_clip)
    ]
    subprocess.run(extract_cmd, capture_output=True, check=True)
    print(f"✓ Created 1-minute clip: {test_clip.name}")

    print("\n" + "=" * 60)
    print(f"Testing: {test_clip.name}")
    print("=" * 60)

    # Initialize processor
    processor = ReelsProcessor()

    # Step 1: Detect face segments
    print(f"\n1. Detecting face segments (checking every 4 frames)...")
    segments = processor.detect_face_segments(str(test_clip), check_every_n_frames=4)

    # Step 2: Convert to reels
    print(f"\n2. Converting to reels format...")
    output_reels = output_folder / 'output_reels.mp4'
    result = processor.convert_to_reels(
        str(test_clip),
        str(output_reels),
        auto_detect=True,
        dynamic_mode=True
    )

    success = result.get('success', False)

    if success:
        file_size = output_reels.stat().st_size / (1024 * 1024)  # MB
        print(f"   ✓ Conversion successful!")
        print(f"   Output: {output_reels.name}")
        print(f"   Mode used: {result.get('mode', 'unknown')}")
        print(f"   File size: {file_size:.2f} MB")
    else:
        print(f"   ✗ Conversion failed: {result.get('error', 'Unknown error')}")

    # Step 3: Create debug visualization
    print(f"\n3. Creating debug visualization with face boxes...")
    debug_video = output_folder / 'debug_faces.mp4'
    create_debug_visualization(test_clip, segments, debug_video)

    # Write verification file
    write_verify_file(output_folder, output_reels if success else None, segments, success)

    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    print(f"Input: {test_video.name}")
    print(f"Output folder: {output_folder.name}")
    print(f"Segments detected: {len(segments)}")
    zero_face = sum(1 for s in segments if s['face_count'] == 0)
    single_face = sum(1 for s in segments if s['face_count'] == 1)
    dual_face = sum(1 for s in segments if s['face_count'] == 2)
    print(f"  - Zero-face: {zero_face} (panning)")
    print(f"  - Single-face: {single_face} (tracking)")
    print(f"  - Dual-face: {dual_face} (split-screen)")
    print(f"Conversion: {'SUCCESS ✅' if success else 'FAILED ❌'}")
    print(f"\n📋 Next steps:")
    print(f"   1. Review output video in: {output_folder.absolute()}")
    print(f"   2. Read VERIFY.txt for manual check instructions")
    print(f"   3. Delete folder if test passes")
    print("=" * 60)

    return 0 if success else 1


if __name__ == '__main__':
    sys.exit(main())
