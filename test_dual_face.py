#!/usr/bin/env python3
"""
Test script for dual-face detection and split-screen reels conversion
Tests on video files from downloads folder
"""

import sys
import subprocess
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / 'backend'))

from reels_processor import ReelsProcessor


def create_test_clip(video_path: Path, duration: int = 30) -> Path:
    """
    Create a 30-second test clip from the video

    Args:
        video_path: Path to source video
        duration: Duration in seconds

    Returns:
        Path to test clip
    """
    output_path = video_path.parent / f"{video_path.stem}_test_clip.mp4"

    print(f"Creating {duration}s test clip from {video_path.name}...")

    cmd = [
        'ffmpeg',
        '-i', str(video_path),
        '-t', str(duration),  # Duration
        '-c:v', 'libx264',
        '-c:a', 'aac',
        '-preset', 'ultrafast',  # Fast encoding for testing
        '-y',
        str(output_path)
    ]

    try:
        subprocess.run(cmd, check=True, capture_output=True)
        print(f"✓ Test clip created: {output_path.name}")
        return output_path
    except subprocess.CalledProcessError as e:
        print(f"✗ Error creating test clip: {e.stderr.decode()}")
        return None


def test_face_detection(video_path: Path):
    """
    Test face detection and show results

    Args:
        video_path: Path to video file
    """
    print(f"\n{'='*60}")
    print(f"Testing: {video_path.name}")
    print(f"{'='*60}")

    processor = ReelsProcessor()

    # Detect faces
    print("\n1. Detecting faces...")
    crop_params = processor.detect_speaker_position(str(video_path))

    # Display results
    mode = crop_params.get('mode', 'unknown')
    face_detected = crop_params.get('face_detected', False)

    print(f"\n   Mode: {mode.upper()}")
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
    print("\n2. Converting to reels format...")
    output_path = video_path.parent / f"{video_path.stem}_reels_{mode}.mp4"

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
    else:
        print(f"   ✗ Conversion failed: {result.get('error')}")

    return result


def main():
    """Main test function"""
    print("\n" + "="*60)
    print("DUAL-FACE DETECTION TEST")
    print("="*60)

    # Find the video file
    downloads_dir = Path(__file__).parent / 'downloads'
    video_file = downloads_dir / '6g-qJ4QZ6Sk.mp4'

    if not video_file.exists():
        print(f"\n✗ Error: Video file not found at {video_file}")
        print(f"  Looking in: {downloads_dir}")
        print(f"  Available files:")
        if downloads_dir.exists():
            for f in downloads_dir.glob('*.mp4'):
                print(f"    - {f.name}")
        return 1

    print(f"\n✓ Found video: {video_file.name}")

    # Create 30-second test clip
    test_clip = create_test_clip(video_file, duration=30)

    if not test_clip:
        print("\n✗ Failed to create test clip")
        return 1

    # Test face detection on the clip
    result = test_face_detection(test_clip)

    # Summary
    print(f"\n{'='*60}")
    print("TEST SUMMARY")
    print(f"{'='*60}")
    print(f"Video: {video_file.name}")
    print(f"Test clip: {test_clip.name}")
    print(f"Mode detected: {result.get('crop_params', {}).get('mode', 'unknown').upper()}")
    print(f"Conversion: {'SUCCESS' if result.get('success') else 'FAILED'}")
    print(f"{'='*60}\n")

    return 0 if result.get('success') else 1


if __name__ == '__main__':
    sys.exit(main())
