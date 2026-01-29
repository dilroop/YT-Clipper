#!/usr/bin/env python3
"""
Test caption burning and watermark addition
Outputs to tests/results/test-captions-watermark/
"""

import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent / 'backend'))

from clipper import VideoClipper
from caption_generator import CaptionGenerator
from watermark_processor import WatermarkProcessor
from transcriber import AudioTranscriber


def create_test_output_folder():
    """Create timestamped output folder for test results"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_folder = Path(__file__).parent / 'results' / f'test-captions-watermark-{timestamp}'
    output_folder.mkdir(parents=True, exist_ok=True)
    return output_folder


def write_verify_file(output_folder, captioned_path, final_path):
    """Generate VERIFY.txt with manual check instructions"""
    verify_text = f"""# Captions & Watermark Test Results
Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

## Output Files:
- {captioned_path.name if captioned_path else 'No captioned video generated'}
- {final_path.name if final_path else 'No final video generated'}

## What to Verify:

### Caption Quality ({captioned_path.name if captioned_path else 'N/A'}):
1. **Word-by-word animation**: Captions should highlight individual words as they're spoken
2. **Timing accuracy**: Words should appear exactly when spoken
3. **Readability**: Text should be clear and easy to read
4. **Positioning**: Captions should be centered at bottom (or configured position)
5. **No overlap**: Multiple words shouldn't overlap on screen
6. **Smooth transitions**: Word transitions should be smooth

### Watermark Quality ({final_path.name if final_path else 'N/A'}):
1. **Visibility**: Watermark text should be clearly visible
2. **Position**: Should be in top right corner with 50px gap
3. **Persistence**: Watermark should stay throughout entire video
4. **Readability**: Text should be legible over background
5. **Not intrusive**: Should not block important content
6. **Professional look**: Should look polished and intentional

### Combined Output:
- Both captions AND watermark should be present in final video
- Captions at bottom, watermark at top right
- No interference between the two elements
- Quality should be maintained (no degradation)

## Manual Verification Steps:
1. Open {captioned_path.name if captioned_path else 'captioned video'}
   - Verify captions work correctly
   - Check word-by-word animation
2. Open {final_path.name if final_path else 'final video'}
   - Verify both captions AND watermark present
   - Check watermark position and visibility
3. If test passes, delete this results folder
4. If test fails, check caption_generator.py or watermark_processor.py

## Debug Information:
- Input: tests/test_clip.mp4
- Clip extracted: 10-30 seconds (20s test clip)
- Caption format: ASS subtitles with word-level timing
- Words per line: 2
- Watermark text: '@YourChannel'
- Watermark position: top_right (50px gap)
- Caption generator: backend/caption_generator.py
- Watermark processor: backend/watermark_processor.py

## Technical Details:
- Caption style: Bold, white text with black outline
- Burn method: FFmpeg subtitles filter (libass)
- Watermark method: FFmpeg drawtext filter
"""

    verify_path = output_folder / 'VERIFY.txt'
    verify_path.write_text(verify_text)
    print(f"\n📝 Generated verification instructions")


def test_captions_and_watermark(test_video: Path, output_folder: Path):
    """Test caption burning and watermark"""
    print("\n" + "="*60)
    print("Testing Captions & Watermark")
    print("="*60)

    # Step 1: Create a test clip (10-30 seconds)
    print("\n1. Creating test clip...")
    clipper = VideoClipper()
    clip_path = output_folder / "test_clip.mp4"

    clip_result = clipper.create_clip(
        video_path=str(test_video),
        start_time=10,
        end_time=30,
        output_path=str(clip_path)
    )

    if not clip_result['success']:
        print(f"✗ Error creating clip: {clip_result['error']}")
        return None, None

    print(f"   ✓ Test clip created: {clip_path.name}")

    # Step 2: Transcribe to get word-level timing
    print("\n2. Transcribing clip for captions...")
    transcriber = AudioTranscriber(model_name="base")
    transcript_result = transcriber.transcribe(str(clip_path))

    if not transcript_result['success']:
        print(f"✗ Error transcribing: {transcript_result['error']}")
        return None, None

    # Get words from segments
    words = []
    for segment in transcript_result['segments']:
        if 'words' in segment:
            words.extend(segment['words'])

    print(f"   ✓ Got {len(words)} words for captions")

    # Step 3: Generate and burn captions
    print("\n3. Generating and burning captions...")
    caption_gen = CaptionGenerator({'words_per_caption': 2})

    # Create ASS file
    ass_path = output_folder / "captions.ass"
    caption_gen.create_ass_subtitles(
        words=words,
        output_path=str(ass_path),
        clip_start_time=0  # Clip starts at 0 (we transcribed the extracted clip)
    )
    print(f"   ✓ ASS file created: {ass_path.name}")

    # Burn captions
    captioned_path = output_folder / "clip_with_captions.mp4"
    burn_result = caption_gen.burn_captions(
        video_path=str(clip_path),
        subtitle_path=str(ass_path),
        output_path=str(captioned_path)
    )

    if not burn_result['success']:
        print(f"✗ Error burning captions: {burn_result['error']}")
        return None, None

    size_mb = captioned_path.stat().st_size / (1024 * 1024)
    print(f"   ✓ Captions burned: {captioned_path.name} ({size_mb:.1f} MB)")

    # Step 4: Add watermark
    print("\n4. Adding watermark...")
    watermark_config = {
        'enabled': True,
        'type': 'text',
        'text': '@YourChannel',
        'position': 'top_right',
        'gap': 50
    }

    watermark_proc = WatermarkProcessor(watermark_config)
    final_path = output_folder / "clip_final.mp4"

    watermark_result = watermark_proc.add_watermark(
        video_path=str(captioned_path),
        output_path=str(final_path)
    )

    if not watermark_result['success']:
        print(f"✗ Error adding watermark: {watermark_result['error']}")
        return captioned_path, None

    size_mb = final_path.stat().st_size / (1024 * 1024)
    print(f"   ✓ Watermark added: {final_path.name} ({size_mb:.1f} MB)")

    return captioned_path, final_path


def main():
    """Main test function"""
    print("\n" + "="*60)
    print("CAPTIONS & WATERMARK TEST")
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
        captioned_path, final_path = test_captions_and_watermark(test_video, output_folder)

        # Generate verification file
        write_verify_file(output_folder, captioned_path, final_path)

        # Summary
        print(f"\n{'='*60}")
        print("TEST SUMMARY")
        print(f"{'='*60}")
        print(f"Input: {test_video.name}")
        print(f"Output folder: {output_folder.name}")
        print(f"Captioned video: {captioned_path.name if captioned_path else 'Failed'}")
        print(f"Final video: {final_path.name if final_path else 'Failed'}")
        print(f"\n📋 Next steps:")
        print(f"   1. Review videos in: {output_folder}")
        print(f"   2. Read VERIFY.txt for manual check instructions")
        print(f"   3. Delete folder if test passes")
        print(f"{'='*60}\n")

        return 0 if (captioned_path and final_path) else 1

    except Exception as e:
        import traceback
        print(f"\n✗ Error: {e}")
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
