#!/usr/bin/env python3
"""
Test script for dual-face detection and split-screen reels conversion
Tests on test_clip2.mp4 (first 60 seconds) and outputs to tests/results/test-dual-face/
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
    output_folder = Path(__file__).parent / 'results' / f'test-dual-face-{timestamp}'
    output_folder.mkdir(parents=True, exist_ok=True)
    return output_folder


def write_verify_file(output_folder, video_path, mode, success):
    """Generate VERIFY.txt with manual check instructions"""
    verify_text = f"""# Dual-Face Detection Test Results
Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

## Test Status: {'✅ SUCCESS' if success else '❌ FAILED'}

## Output Files:
- {video_path.name if video_path else 'No output generated'}
- debug_faces_{mode.lower() if mode else 'unknown'}.mp4 (visualization with face boxes)

## Detection Mode: {mode.upper() if mode else 'UNKNOWN'}

## What to Verify:

### If DUAL-FACE mode:
1. **Split-screen layout**: Two vertical boxes stacked (9:8 each, total 9:16)
2. **Both faces visible**: Each person should be fully visible in their box
3. **Proper cropping**: Face positioned in upper portion with padding
4. **No cutoffs**: Top of head and shoulders visible
5. **Smooth transitions**: If dynamic mode, transitions should be smooth

### If SINGLE-FACE mode:
1. **Single person centered**: One person in 9:16 vertical crop
2. **Face detection**: If face detected, crop should center on face
3. **Proper padding**: Face in upper portion with good framing
4. **No cutoffs**: Full head and shoulders visible

## Manual Verification Steps:
1. Open the output video file
2. Play through the entire clip
3. Check the criteria above
4. If test passes, delete this results folder
5. If test fails, keep folder for investigation

## Debug Information:
- Input: tests/test_clip2.mp4 (first 60 seconds)
- Face detection algorithm: OpenCV Haar Cascade
- Dual-face threshold: Faces within 50% size ratio
- Dynamic mode: Checks every 8 frames

## Common Issues:
- False face detection (microphones, hands) → Should be filtered by size validation
- Single person incorrectly detected as dual → Check face size ratio validation
- Faces cut off → Check padding calculations in reels_processor.py
"""

    verify_path = output_folder / 'VERIFY.txt'
    verify_path.write_text(verify_text)
    print(f"\n📝 Generated verification instructions: {verify_path.name}")


def create_debug_visualization(video_path: Path, segments: list, output_path: Path):
    """
    Create a debug video with face detection boxes drawn
    Shows actual real-time MediaPipe face detection (orange 2px) on every frame

    Args:
        video_path: Input video path
        segments: Face segments from detect_face_segments()
        output_path: Output video path
    """
    print(f"\n4. Creating debug visualization with MediaPipe face boxes...")

    # Initialize MediaPipe FaceDetector (same as ReelsProcessor)
    import mediapipe as mp
    from mediapipe.tasks import python
    from mediapipe.tasks.python import vision

    # Load model
    model_path = Path.home() / '.cache' / 'mediapipe' / 'blaze_face_short_range.tflite'
    with open(model_path, 'rb') as f:
        model_data = f.read()

    base_options = python.BaseOptions(model_asset_buffer=model_data)
    options = vision.FaceDetectorOptions(
        base_options=base_options,
        running_mode=vision.RunningMode.VIDEO,
        min_detection_confidence=0.5,
        min_suppression_threshold=0.3
    )
    detector = vision.FaceDetector.create_from_options(options)

    cap = cv2.VideoCapture(str(video_path))
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS)

    # Create video writer
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(str(output_path), fourcc, fps, (width, height))

    frame_idx = 0
    while True:
        ret, frame = cap.read()
        if not ret:
            break

        current_time = frame_idx / fps

        # Run MediaPipe face detection on this frame
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)

        timestamp_ms = int(current_time * 1000)
        detection_result = detector.detect_for_video(mp_image, timestamp_ms)

        # Draw orange boxes for all MediaPipe detections
        raw_face_count = 0
        if detection_result.detections:
            for detection in detection_result.detections:
                bbox = detection.bounding_box
                x_min = int(bbox.origin_x)
                y_min = int(bbox.origin_y)
                x_max = x_min + int(bbox.width)
                y_max = y_min + int(bbox.height)

                # Orange box for raw MediaPipe detection
                cv2.rectangle(frame, (x_min, y_min), (x_max, y_max), (0, 165, 255), 2)  # Orange, 2px
                raw_face_count += 1

        # Find which segment this frame belongs to and show filtered faces (green)
        segment_faces = []
        for seg in segments:
            if seg['start_time'] <= current_time <= seg['end_time']:
                if 'faces' in seg and len(seg['faces']) > 0:
                    for face_list in seg['faces']:
                        if len(face_list) > 0:
                            segment_faces = face_list
                            break
                break

        # Draw green boxes for filtered segment faces
        for face in segment_faces:
            x = int(face['topLeft']['x'])
            y = int(face['topLeft']['y'])
            x2 = int(face['rightBottom']['x'])
            y2 = int(face['rightBottom']['y'])

            # Green rectangle for filtered/used face
            cv2.rectangle(frame, (x, y), (x2, y2), (0, 255, 0), 3)

            # Red dot for face center
            center_x = (x + x2) // 2
            center_y = (y + y2) // 2
            cv2.circle(frame, (center_x, center_y), 5, (0, 0, 255), -1)

        # Add frame info text
        info_text = f"Frame: {frame_idx} | Raw MP: {raw_face_count} | Filtered: {len(segment_faces)} | Time: {current_time:.2f}s"
        cv2.putText(frame, info_text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

        out.write(frame)
        frame_idx += 1

    cap.release()
    out.release()

    print(f"   ✓ Debug video created: {output_path.name}")
    print(f"   Orange (2px) = Raw MediaPipe FaceDetector | Green (3px) = Filtered faces (size + edge filtering)")


def test_face_detection(video_path: Path, output_folder: Path):
    """
    Test face detection and convert to reels

    Args:
        video_path: Path to test video
        output_folder: Path to output folder
    """
    print(f"\n{'='*60}")
    print(f"Testing: {video_path.name}")
    print(f"{'='*60}")

    processor = ReelsProcessor()

    # Detect face segments
    print("\n1. Detecting face segments (checking every 8 frames)...")
    segments = processor.detect_face_segments(str(video_path), check_every_n_frames=8)

    # Detect overall mode
    print("\n2. Detecting overall speaker position...")
    crop_params = processor.detect_speaker_position(str(video_path))

    # Display results
    mode = crop_params.get('mode', 'unknown')
    face_detected = crop_params.get('face_detected', False)

    print(f"\n   Overall Mode: {mode.upper()}")
    print(f"   Face Detected: {face_detected}")

    if mode == 'dual':
        print("\n   ✓ DUAL-FACE MODE DETECTED!")
        print(f"   Left face crop:  x={crop_params['left_face']['x']}, "
              f"y={crop_params['left_face']['y']}, "
              f"w={crop_params['left_face']['width']}, "
              f"h={crop_params['left_face']['height']}")
        print(f"   Right face crop: x={crop_params['right_face']['x']}, "
              f"y={crop_params['right_face']['y']}, "
              f"w={crop_params['right_face']['width']}, "
              f"h={crop_params['right_face']['height']}")
    elif mode == 'single':
        print("\n   ✓ Single-face mode")
        print(f"   Crop: x={crop_params.get('x')}, y={crop_params.get('y')}, "
              f"w={crop_params.get('width')}, h={crop_params.get('height')}")
        if not face_detected:
            print(f"   Position: {crop_params.get('position', 'N/A')}")

    # Convert to reels
    print("\n3. Converting to reels format...")
    output_path = output_folder / f"output_reels_{mode}.mp4"

    result = processor.convert_to_reels(
        str(video_path),
        str(output_path),
        auto_detect=True
    )

    if result['success']:
        print(f"   ✓ Conversion successful!")
        print(f"   Output: {output_path.name}")
        print(f"   Mode used: {result.get('mode', 'unknown')}")

        # Get file size
        size_mb = output_path.stat().st_size / (1024 * 1024)
        print(f"   File size: {size_mb:.2f} MB")

        # Create debug visualization
        debug_path = output_folder / f"debug_faces_{mode}.mp4"
        create_debug_visualization(video_path, segments, debug_path)

        return result, output_path, mode
    else:
        print(f"   ✗ Conversion failed: {result.get('error')}")
        return result, None, mode


def main():
    """Main test function"""
    print("\n" + "="*60)
    print("DUAL-FACE DETECTION TEST")
    print("="*60)

    # Find the test video
    test_video = Path(__file__).parent / 'test_clip2.mp4'

    if not test_video.exists():
        print(f"\n✗ Error: Test video not found at {test_video}")
        return 1

    print(f"\n✓ Found test video: {test_video.name}")

    # Create output folder
    output_folder = create_test_output_folder()
    print(f"✓ Created output folder: {output_folder.name}")

    # Extract first 60 seconds
    print(f"\n✓ Extracting first 60 seconds...")
    clipper = VideoClipper()
    one_min_clip = output_folder / "test_clip_1min.mp4"

    clip_result = clipper.create_clip(
        video_path=str(test_video),
        start_time=0,
        end_time=60,
        output_path=str(one_min_clip)
    )

    if not clip_result['success']:
        print(f"\n✗ Error extracting clip: {clip_result['error']}")
        return 1

    print(f"✓ Created 1-minute clip: {one_min_clip.name}")

    # Test face detection on the 1-minute clip
    result, output_path, mode = test_face_detection(one_min_clip, output_folder)

    # Generate verification file
    write_verify_file(output_folder, output_path, mode, result.get('success', False))

    # Summary
    print(f"\n{'='*60}")
    print("TEST SUMMARY")
    print(f"{'='*60}")
    print(f"Input: {test_video.name}")
    print(f"Output folder: {output_folder.name}")
    print(f"Mode detected: {mode.upper()}")
    print(f"Conversion: {'SUCCESS ✅' if result.get('success') else 'FAILED ❌'}")
    print(f"\n📋 Next steps:")
    print(f"   1. Review output video in: {output_folder}")
    print(f"   2. Read VERIFY.txt for manual check instructions")
    print(f"   3. Delete folder if test passes")
    print(f"{'='*60}\n")

    return 0 if result.get('success') else 1


if __name__ == '__main__':
    sys.exit(main())
