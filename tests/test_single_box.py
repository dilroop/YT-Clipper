#!/usr/bin/env python3
"""
Test script to extract a single 9:8 face box
This helps verify the crop dimensions are correct before stacking
"""

import sys
import subprocess
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / 'backend'))

from reels_processor import ReelsProcessor


def test_single_box(video_path: Path, output_path: Path):
    """
    Extract a single 9:8 box for the LEFT face only
    """
    print(f"\n{'='*60}")
    print(f"Testing single 9:8 box extraction")
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
        print("No dual-face frames found!")
        return

    flat_frames = [faces for frame_list in dual_face_frames for faces in frame_list if len(faces) == 2]
    if not flat_frames:
        print("No valid dual-face frames!")
        return

    dual_crop_params = processor._process_dual_face_crop(flat_frames, width, height)

    # Extract LEFT face only
    left = dual_crop_params['left_face']

    print(f"\n2. Extracting LEFT face box:")
    print(f"   Position: ({left['x']}, {left['y']})")
    print(f"   Size: {left['width']}x{left['height']}")
    print(f"   Ratio: {left['width']/left['height']:.3f} (should be 1.125 for 9:8)")

    # Create FFmpeg command to extract just the left box
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
    else:
        print(f"   ✗ Error: {result.stderr.decode()}")

    return output_path if result.returncode == 0 else None


def main():
    """Main test function"""
    # Find the test clip
    downloads_dir = Path(__file__).parent.parent / 'downloads'
    video_file = downloads_dir / '6g-qJ4QZ6Sk_test_clip.mp4'

    if not video_file.exists():
        print(f"✗ Error: Test clip not found at {video_file}")
        return 1

    print(f"✓ Found video: {video_file.name}")

    # Output path
    output_file = downloads_dir / f"{video_file.stem}_single_box.mp4"

    # Test extraction
    result = test_single_box(video_file, output_file)

    if result:
        print(f"\n{'='*60}")
        print("TEST COMPLETE")
        print(f"{'='*60}")
        print(f"Open the video to check:")
        print(f"  {output_file}")
        print(f"\nVerify:")
        print(f"  - Full face visible (including top of head)")
        print(f"  - Proper padding around face")
        print(f"  - Face positioned in upper portion")
        print(f"{'='*60}\n")

        # Open the video
        subprocess.run(['open', str(output_file)])
        return 0
    else:
        return 1


if __name__ == '__main__':
    sys.exit(main())
