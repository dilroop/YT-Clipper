#!/usr/bin/env python3
"""
Transcribe a local video file and save transcript to JSON
"""

import os
import sys
import json
from dotenv import load_dotenv
load_dotenv()

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from transcriber import AudioTranscriber

def transcribe_local_video(video_path, output_file="transcript.json"):
    """Transcribe local video file and save to JSON"""

    print("\n" + "="*80)
    print("📝 Transcribing Local Video")
    print("="*80)

    if not os.path.exists(video_path):
        print(f"\n❌ Error: Video file not found: {video_path}")
        return

    print(f"\n📹 Video: {os.path.basename(video_path)}")
    print(f"   Size: {os.path.getsize(video_path) / (1024*1024):.1f} MB")

    # Transcribe
    print("\n🎤 Transcribing audio...")
    transcriber = AudioTranscriber(model_name="base")

    def progress(data):
        if 'percent' in data:
            print(f"   {data.get('percent', 0):.1f}% - {data.get('message', '')}")

    transcript_result = transcriber.transcribe(video_path, progress)

    if not transcript_result['success']:
        print(f"\n❌ Error: {transcript_result['error']}")
        return

    segments = transcript_result['segments']
    print(f"\n✅ Transcription complete: {len(segments)} segments")

    # Save to JSON
    data = {
        'video_info': {
            'title': os.path.basename(video_path),
            'channel': 'Local Video',
            'description': f'Transcribed from {video_path}',
            'url': f'file://{video_path}'
        },
        'segments': segments
    }

    with open(output_file, 'w') as f:
        json.dump(data, f, indent=2)

    print(f"\n💾 Saved transcript to: {output_file}")
    print(f"   Total segments: {len(segments)}")
    print("\n✅ Done! Now use: python3 test/test_ai_prompt.py")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 transcribe_local_video.py <video_file> [output.json]")
        print("\nExample:")
        print("  python3 transcribe_local_video.py ~/Downloads/video.mp4")
        sys.exit(1)

    video = sys.argv[1]
    output = sys.argv[2] if len(sys.argv) > 2 else "transcript.json"

    transcribe_local_video(video, output)
