#!/usr/bin/env python3
"""
Test video clipping with transcription and caption generation
Outputs to tests/results/test-clipping/
"""

import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent / 'backend'))

from transcriber import AudioTranscriber
from analyzer import SectionAnalyzer
from clipper import VideoClipper
from caption_generator import CaptionGenerator


def create_test_output_folder():
    """Create timestamped output folder for test results"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_folder = Path(__file__).parent / 'results' / f'test-clipping-{timestamp}'
    output_folder.mkdir(parents=True, exist_ok=True)
    return output_folder


def write_verify_file(output_folder, clip_files, ass_files):
    """Generate VERIFY.txt with manual check instructions"""
    clips_list = "\n".join([f"- {f.name}" for f in clip_files])
    ass_list = "\n".join([f"- {f.name}" for f in ass_files])

    verify_text = f"""# Clipping Test Results
Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

## Output Files:

### Video Clips:
{clips_list}

### Caption Files (ASS format):
{ass_list}

## What to Verify:

### Clip Quality:
1. **Timing accuracy**: Clips should start/end at correct times
2. **Audio sync**: Audio should be in sync with video
3. **Quality**: No degradation from original
4. **Duration**: Each clip should be appropriate length (not too short/long)

### Caption Files:
1. **ASS format**: Files should be valid ASS subtitle format
2. **Timing**: Word-level timestamps should align with audio
3. **Text accuracy**: Captions should match spoken words
4. **Readability**: Caption text should be clear and properly formatted

### Pipeline Test:
This test verifies the full clipping pipeline:
- Transcription (Whisper)
- Analysis (keyword-based interesting moment detection)
- Clipping (FFmpeg extraction)
- Caption generation (ASS subtitle creation)

## Manual Verification Steps:
1. Open each clip video file
2. Play through and check timing
3. Open corresponding .ass file in text editor
4. Verify caption format and timing
5. Check that clips are interesting moments (not random)
6. If test passes, delete this results folder
7. If test fails, investigate which stage failed

## Debug Information:
- Input: tests/test_clip.mp4
- Transcription: Whisper 'base' model
- Analysis: SectionAnalyzer (keyword-based)
- Clipping: VideoClipper (FFmpeg)
- Captions: CaptionGenerator (ASS format, word-level timing)
- Word grouping: 2 words per caption line
"""

    verify_path = output_folder / 'VERIFY.txt'
    verify_path.write_text(verify_text)
    print(f"\n📝 Generated verification instructions")


def test_clipping_pipeline(test_video: Path, output_folder: Path):
    """Test the full clipping pipeline"""
    print("\n" + "="*60)
    print("Testing Clipping Pipeline")
    print("="*60)

    # Step 1: Transcribe
    print("\n1. Transcribing audio...")
    transcriber = AudioTranscriber(model_name="base")
    transcript_result = transcriber.transcribe(str(test_video))

    if not transcript_result['success']:
        print(f"✗ Error: Transcription failed: {transcript_result['error']}")
        return [], []

    segments = transcript_result['segments']
    print(f"   ✓ Got {len(segments)} segments")

    # Step 2: Analyze
    print("\n2. Finding interesting clips...")
    analyzer = SectionAnalyzer()
    interesting_clips = analyzer.find_interesting_clips(segments, num_clips=3)

    print(f"   ✓ Found {len(interesting_clips)} clips")
    for i, clip in enumerate(interesting_clips, 1):
        duration = clip['end'] - clip['start']
        print(f"     Clip {i}: {clip['start']:.1f}s - {clip['end']:.1f}s ({duration:.1f}s, score: {clip['score']:.1f})")

    # Adjust timing with padding
    interesting_clips = [analyzer.adjust_clip_timing(clip) for clip in interesting_clips]

    # Step 3: Create clips
    print("\n3. Creating video clips...")
    clipper = VideoClipper()
    clip_files = []
    ass_files = []

    for i, clip in enumerate(interesting_clips, 1):
        print(f"\n   Processing clip {i}/{len(interesting_clips)}...")

        # Create base clip
        output_path = output_folder / f"clip_{i}.mp4"
        clip_result = clipper.create_clip(
            video_path=str(test_video),
            start_time=clip['start'],
            end_time=clip['end'],
            output_path=str(output_path)
        )

        if not clip_result['success']:
            print(f"   ✗ Error: {clip_result['error']}")
            continue

        clip_files.append(Path(clip_result['clip_path']))
        print(f"   ✓ Clip created: {output_path.name}")

        # Generate captions
        print(f"   Generating captions...")
        caption_gen = CaptionGenerator({'words_per_caption': 2})

        # Create ASS subtitles
        ass_path = output_folder / f"clip_{i}.ass"
        caption_gen.create_ass_subtitles(
            words=clip['words'],
            output_path=str(ass_path),
            clip_start_time=clip['start']
        )

        ass_files.append(ass_path)
        print(f"   ✓ ASS subtitles created: {ass_path.name}")

    return clip_files, ass_files


def main():
    """Main test function"""
    print("\n" + "="*60)
    print("CLIPPING PIPELINE TEST")
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
        clip_files, ass_files = test_clipping_pipeline(test_video, output_folder)

        # Generate verification file
        write_verify_file(output_folder, clip_files, ass_files)

        # Summary
        print(f"\n{'='*60}")
        print("TEST SUMMARY")
        print(f"{'='*60}")
        print(f"Input: {test_video.name}")
        print(f"Output folder: {output_folder.name}")
        print(f"Clips created: {len(clip_files)}")
        print(f"Caption files: {len(ass_files)}")

        if clip_files:
            total_size = sum(f.stat().st_size for f in clip_files) / (1024 * 1024)
            print(f"Total size: {total_size:.1f} MB")

        print(f"\n📋 Next steps:")
        print(f"   1. Review clips and captions in: {output_folder}")
        print(f"   2. Read VERIFY.txt for manual check instructions")
        print(f"   3. Delete folder if test passes")
        print(f"{'='*60}\n")

        return 0 if clip_files else 1

    except Exception as e:
        import traceback
        print(f"\n✗ Error: {e}")
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
