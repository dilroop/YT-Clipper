#!/usr/bin/env python3
"""
Quick script to analyze a YouTube video and show interesting clips
without full processing (no clipping/captions)
"""

import os
import sys
from dotenv import load_dotenv
load_dotenv()

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from downloader import VideoDownloader
from transcriber import AudioTranscriber
from ai_analyzer import AIAnalyzer

def format_time(seconds):
    """Convert seconds to HH:MM:SS format"""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    return f"{h:02d}:{m:02d}:{s:02d}"

def analyze_video(url):
    """Analyze video and show interesting clips"""

    print("\n" + "="*80)
    print("🎬 YTClipper - AI Clip Analyzer")
    print("="*80)

    # Check API key
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key or not api_key.startswith('sk-'):
        print("\n❌ Error: No OpenAI API key found!")
        print("Please add OPENAI_API_KEY to your .env file")
        return

    print(f"\n✅ Using AI model: {os.getenv('OPENAI_MODEL', 'gpt-4o-mini')}")

    # Step 1: Download video
    print("\n📥 Step 1: Downloading video...")
    downloader = VideoDownloader()

    def progress_callback(data):
        if 'percent' in data:
            print(f"   Progress: {data.get('percent', 0)}% - {data.get('message', '')}")

    download_result = downloader.download_video(url, progress_callback)

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
    print(f"   Channel: {video_info['channel']}")

    # Step 2: Transcribe
    print("\n🎤 Step 2: Transcribing audio...")
    transcriber = AudioTranscriber(model_name="base")
    transcript_result = transcriber.transcribe(video_path, progress_callback)

    if not transcript_result['success']:
        print(f"\n❌ Error: {transcript_result['error']}")
        downloader.cleanup_video(video_path)
        return

    segments = transcript_result['segments']
    print(f"\n✅ Transcription complete: {len(segments)} segments")

    # Step 3: AI Analysis
    print("\n🤖 Step 3: AI analyzing content for interesting clips...")
    analyzer = AIAnalyzer(
        api_key=api_key,
        model=os.getenv('OPENAI_MODEL', 'gpt-4o-mini'),
        temperature=float(os.getenv('OPENAI_TEMPERATURE', '1.0'))
    )

    interesting_clips = analyzer.find_interesting_clips(
        segments,
        num_clips=5,
        video_info=video_info
    )

    print(f"\n✅ AI found {len(interesting_clips)} interesting clips!")

    # Display results
    print("\n" + "="*80)
    print("📌 INTERESTING CLIPS FOUND")
    print("="*80)

    for i, clip in enumerate(interesting_clips, 1):
        duration = clip['end'] - clip['start']
        print(f"\n🎯 Clip {i}: {clip.get('title', 'Untitled')}")
        print(f"   Time: {format_time(clip['start'])} → {format_time(clip['end'])} ({duration:.1f}s)")
        print(f"   Reason: {clip.get('reason', 'N/A')}")
        print(f"   Keywords: {', '.join(clip.get('keywords', []))}")
        print(f"   Text: {clip['text'][:150]}{'...' if len(clip['text']) > 150 else ''}")

    print("\n" + "="*80)
    print("✅ Analysis complete!")
    print("="*80)

    # Cleanup
    downloader.cleanup_video(video_path)
    print("\n🧹 Cleaned up temporary files")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 analyze_video.py <youtube_url>")
        sys.exit(1)

    video_url = sys.argv[1]
    analyze_video(video_url)
