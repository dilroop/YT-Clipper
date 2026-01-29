#!/usr/bin/env python3
"""
Save video transcript to JSON file for testing
Run once to cache the transcript, then use test_ai_prompt.py for fast iterations
"""

import os
import sys
import json
from dotenv import load_dotenv
load_dotenv()

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from downloader import VideoDownloader
from transcriber import AudioTranscriber

def save_transcript(url, output_file="transcript.json"):
    """Download video, transcribe, and save to JSON"""

    print("\n" + "="*80)
    print("📝 Saving Video Transcript")
    print("="*80)

    # Step 1: Download
    print("\n📥 Downloading video...")
    downloader = VideoDownloader()

    def progress(data):
        if 'percent' in data:
            print(f"   {data.get('percent', 0):.1f}% - {data.get('message', '')}", end='\r')

    download_result = downloader.download_video(url, progress)

    if not download_result['success']:
        print(f"\n❌ Error: {download_result['error']}")
        return

    video_path = download_result['video_path']
    video_info = {
        'video_id': download_result['video_id'],
        'title': download_result['title'],
        'channel': download_result['channel'],
        'description': download_result['description'],
        'url': url
    }

    print(f"\n✅ Downloaded: {video_info['title']}")

    # Step 2: Transcribe
    print("\n🎤 Transcribing audio...")
    transcriber = AudioTranscriber(model_name="base")
    transcript_result = transcriber.transcribe(video_path, progress)

    if not transcript_result['success']:
        print(f"\n❌ Error: {transcript_result['error']}")
        downloader.cleanup_video(video_path)
        return

    segments = transcript_result['segments']
    print(f"\n✅ Transcription complete: {len(segments)} segments")

    # Step 3: Save to JSON
    data = {
        'video_info': video_info,
        'segments': segments
    }

    with open(output_file, 'w') as f:
        json.dump(data, f, indent=2)

    print(f"\n💾 Saved transcript to: {output_file}")
    print(f"   Total segments: {len(segments)}")

    # Cleanup
    downloader.cleanup_video(video_path)
    print("\n✅ Done! Now use test_ai_prompt.py to test different prompts")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 save_transcript.py <youtube_url> [output_file.json]")
        print("\nExample:")
        print("  python3 save_transcript.py https://www.youtube.com/watch?v=GRqPnRcfMIY transcript.json")
        sys.exit(1)

    url = sys.argv[1]
    output = sys.argv[2] if len(sys.argv) > 2 else "transcript.json"

    save_transcript(url, output)
