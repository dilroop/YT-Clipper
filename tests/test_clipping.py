"""
Test script to debug clipping process
Uses the already downloaded video
"""

import sys
sys.path.insert(0, 'backend')

from transcriber import AudioTranscriber
from analyzer import SectionAnalyzer
from clipper import VideoClipper
from caption_generator import CaptionGenerator
from pathlib import Path

# Use the already downloaded video
video_path = "Downloads/-jDfA8BeOgw.mp4"

print("=" * 60)
print("Testing Clipping Process")
print("=" * 60)

try:
    # Step 1: Transcribe (or load from cache if available)
    print("\n1. Transcribing audio...")
    transcriber = AudioTranscriber(model_name="base")
    transcript_result = transcriber.transcribe(video_path)

    if not transcript_result['success']:
        print(f"ERROR: Transcription failed: {transcript_result['error']}")
        sys.exit(1)

    segments = transcript_result['segments']
    print(f"   ✓ Got {len(segments)} segments")

    # Step 2: Analyze
    print("\n2. Finding interesting clips...")
    analyzer = SectionAnalyzer()
    interesting_clips = analyzer.find_interesting_clips(segments, num_clips=2)

    print(f"   ✓ Found {len(interesting_clips)} clips")
    for i, clip in enumerate(interesting_clips):
        print(f"     Clip {i+1}: {clip['start']:.2f}s - {clip['end']:.2f}s (score: {clip['score']:.1f})")

    # Adjust timing with padding
    interesting_clips = [analyzer.adjust_clip_timing(clip) for clip in interesting_clips]

    # Step 3: Create clips
    print("\n3. Creating video clips...")
    clipper = VideoClipper()

    for i, clip in enumerate(interesting_clips):
        print(f"\n   Processing clip {i+1}/{len(interesting_clips)}...")
        print(f"   Start: {clip['start']:.2f}s, End: {clip['end']:.2f}s")

        # Create base clip
        clip_result = clipper.create_clip(
            video_path=video_path,
            start_time=clip['start'],
            end_time=clip['end']
        )

        if not clip_result['success']:
            print(f"   ✗ ERROR: {clip_result['error']}")
            continue

        print(f"   ✓ Clip created: {clip_result['clip_path']}")

        # Test caption generation
        print(f"   Testing caption generation...")
        caption_gen = CaptionGenerator({'words_per_caption': 2})

        caption_text = caption_gen.generate_clip_caption(
            clip['words'],
            clip['start'],
            clip['end']
        )

        print(f"   ✓ Caption text generated ({len(caption_text)} chars)")

        # Create ASS subtitles
        clip_path = Path(clip_result['clip_path'])
        ass_path = clip_path.parent / f"clip_{i+1}.ass"

        caption_gen.create_ass_subtitles(
            words=clip['words'],
            output_path=str(ass_path),
            clip_start_time=clip['start']
        )

        print(f"   ✓ ASS subtitles created: {ass_path}")

    print("\n" + "=" * 60)
    print("SUCCESS: All tests passed!")
    print("=" * 60)

except Exception as e:
    import traceback
    print("\n" + "=" * 60)
    print("ERROR:")
    print(traceback.format_exc())
    print("=" * 60)
    sys.exit(1)
