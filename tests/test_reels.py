#!/usr/bin/env python3
"""
Test reels conversion on test video clip
Outputs to tests/results/test-reels/
"""

import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent / 'backend'))

from reels_processor import ReelsProcessor
from clipper import VideoClipper


def create_test_output_folder():
    """Create timestamped output folder for test results"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_folder = Path(__file__).parent / 'results' / f'test-reels-{timestamp}'
    output_folder.mkdir(parents=True, exist_ok=True)
    return output_folder


def write_verify_file(output_folder, reels_files):
    """Generate VERIFY.txt with manual check instructions"""
    files_list = "\n".join([f"- {f.name}" for f in reels_files])
    verify_text = f"""# Reels Conversion Test Results
Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

## Output Files:
{files_list}

## What to Verify:

### Video Format:
1. **Aspect Ratio**: All videos should be 9:16 (vertical/portrait)
2. **Resolution**: Should be 1080px width (or scaled appropriately)
3. **Audio**: Audio should be preserved from original

### Face Detection & Cropping:
1. **Face centered**: If face detected, person should be centered in frame
2. **No cutoffs**: Full head and shoulders visible
3. **Proper padding**: Comfortable space around subject
4. **Dynamic crop**: For videos with face detection, crop should follow speaker

### Quality Checks:
1. **No pixelation**: Video should maintain quality
2. **No black bars**: Crop should fill the 9:16 frame
3. **Smooth playback**: No stuttering or artifacts
4. **Color accuracy**: Colors should match original

## Manual Verification Steps:
1. Open each reel video file
2. Play through entire clip
3. Check aspect ratio (should be tall/vertical)
4. Verify face detection worked correctly
5. Check for any visual artifacts
6. If test passes, delete this results folder
7. If test fails, keep folder for debugging

## Debug Information:
- Input: tests/test_clip.mp4
- Processor: ReelsProcessor from backend/reels_processor.py
- Face detection: OpenCV Haar Cascade (auto-detect mode)
- Output format: MP4 (H.264 + AAC)
"""

    verify_path = output_folder / 'VERIFY.txt'
    verify_path.write_text(verify_text)
    print(f"\n📝 Generated verification instructions")


def test_reels_conversion(test_video: Path, output_folder: Path):
    """Test reels conversion"""
    print("\n" + "="*60)
    print("Testing Reels Conversion")
    print("="*60)

    # First create a couple of test clips from the video
    print("\n1. Creating test clips...")
    clipper = VideoClipper()

    # Create 3 short clips at different times
    test_times = [
        (10, 25),  # 15 second clip
        (30, 50),  # 20 second clip
        (60, 80),  # 20 second clip
    ]

    clip_files = []
    for i, (start, end) in enumerate(test_times, 1):
        clip_result = clipper.create_clip(
            video_path=str(test_video),
            start_time=start,
            end_time=end,
            output_path=str(output_folder / f"clip_{i}.mp4")
        )

        if clip_result['success']:
            clip_files.append(Path(clip_result['clip_path']))
            print(f"   ✓ Created clip {i}: {start}s - {end}s")
        else:
            print(f"   ✗ Failed to create clip {i}: {clip_result.get('error')}")

    if not clip_files:
        print("\n✗ No clips created, aborting test")
        return []

    # Convert each clip to reels
    print("\n2. Converting clips to reels format...")
    reels_proc = ReelsProcessor()
    reels_files = []

    for i, clip_file in enumerate(clip_files, 1):
        print(f"\n   Converting clip {i}/{len(clip_files)}: {clip_file.name}")

        reels_result = reels_proc.convert_to_reels(
            str(clip_file),
            str(output_folder / f"clip_{i}_reels.mp4"),
            auto_detect=True
        )

        if reels_result['success']:
            reels_path = Path(reels_result['output_path'])
            reels_files.append(reels_path)
            size_mb = reels_path.stat().st_size / (1024 * 1024)

            crop_params = reels_result.get('crop_params', {})
            face_detected = crop_params.get('face_detected', False)
            mode = crop_params.get('mode', 'single')

            print(f"   ✓ Success: {reels_path.name}")
            print(f"     Size: {size_mb:.1f} MB")
            print(f"     Mode: {mode}")
            print(f"     Face detected: {face_detected}")
        else:
            print(f"   ✗ Error: {reels_result.get('error')}")

    return reels_files


def main():
    """Main test function"""
    print("\n" + "="*60)
    print("REELS CONVERSION TEST")
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
    reels_files = test_reels_conversion(test_video, output_folder)

    # Generate verification file
    write_verify_file(output_folder, reels_files)

    # Summary
    print(f"\n{'='*60}")
    print("TEST SUMMARY")
    print(f"{'='*60}")
    print(f"Input: {test_video.name}")
    print(f"Output folder: {output_folder.name}")
    print(f"Reels created: {len(reels_files)}")

    if reels_files:
        total_size = sum(f.stat().st_size for f in reels_files) / (1024 * 1024)
        print(f"Total size: {total_size:.1f} MB")

    print(f"\n📋 Next steps:")
    print(f"   1. Review reel videos in: {output_folder}")
    print(f"   2. Read VERIFY.txt for manual check instructions")
    print(f"   3. Delete folder if test passes")
    print(f"{'='*60}\n")

    return 0 if reels_files else 1


if __name__ == '__main__':
    sys.exit(main())
