#!/usr/bin/env python3
"""
Test AI analyzer with cached transcript (no download/transcribe needed)
Use this for fast iteration when testing different prompts
"""

import os
import sys
import json
from dotenv import load_dotenv
load_dotenv()

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from ai_analyzer import AIAnalyzer

def format_time(seconds):
    """Convert seconds to HH:MM:SS format"""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    return f"{h:02d}:{m:02d}:{s:02d}"

def test_prompt(transcript_file="transcript.json", num_clips=5):
    """Test AI analyzer with saved transcript"""

    print("\n" + "="*80)
    print("🤖 Testing AI Analyzer Prompt")
    print("="*80)

    # Check API key
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key or not api_key.startswith('sk-'):
        print("\n❌ Error: No OpenAI API key found!")
        print("Set OPENAI_API_KEY in your .env file")
        return

    # Load cached transcript
    if not os.path.exists(transcript_file):
        print(f"\n❌ Error: Transcript file not found: {transcript_file}")
        print("\nFirst run: python3 save_transcript.py <youtube_url>")
        return

    print(f"\n📂 Loading cached transcript: {transcript_file}")
    with open(transcript_file, 'r') as f:
        data = json.load(f)

    video_info = data['video_info']
    segments = data['segments']

    print(f"✅ Loaded: {video_info['title']}")
    print(f"   Channel: {video_info['channel']}")
    print(f"   Segments: {len(segments)}")

    # Test AI analyzer
    print(f"\n🤖 Running AI analyzer (requesting {num_clips} clips)...")
    print(f"   Model: {os.getenv('OPENAI_MODEL', 'gpt-4o-mini')}")
    print(f"   Temperature: {os.getenv('OPENAI_TEMPERATURE', '1.0')}")

    analyzer = AIAnalyzer(
        api_key=api_key,
        model=os.getenv('OPENAI_MODEL', 'gpt-4o-mini'),
        temperature=float(os.getenv('OPENAI_TEMPERATURE', '1.0'))
    )

    interesting_clips = analyzer.find_interesting_clips(
        segments,
        num_clips=num_clips,
        video_info=video_info
    )

    if not interesting_clips:
        print("\n❌ No clips found! Check the AI response for errors.")
        return

    print(f"\n✅ AI found {len(interesting_clips)} clips!")

    # Display results
    print("\n" + "="*80)
    print("📌 CLIPS FOUND BY AI")
    print("="*80)

    for i, clip in enumerate(interesting_clips, 1):
        duration = clip['end'] - clip['start']
        print(f"\n🎯 Clip {i}: {clip.get('title', 'Untitled')}")
        print(f"   ⏱️  Time: {format_time(clip['start'])} → {format_time(clip['end'])} ({duration:.1f}s)")
        print(f"   🔥 Reason: {clip.get('reason', 'N/A')}")
        print(f"   🏷️  Keywords: {', '.join(clip.get('keywords', []))}")

        # Show first 200 chars of text
        text_preview = clip['text'][:200]
        if len(clip['text']) > 200:
            text_preview += "..."
        print(f"   📝 Text: {text_preview}")

    print("\n" + "="*80)
    print("✅ Test complete!")
    print("="*80)
    print("\n💡 Tips:")
    print("   - Edit backend/ai_analyzer.py to modify the prompt")
    print("   - Run this script again to test changes instantly")
    print("   - Adjust OPENAI_TEMPERATURE in .env (0.0-2.0)")

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Test AI analyzer with cached transcript')
    parser.add_argument('--transcript', '-t', default='transcript.json',
                       help='Transcript JSON file (default: transcript.json)')
    parser.add_argument('--clips', '-c', type=int, default=5,
                       help='Number of clips to find (default: 5)')

    args = parser.parse_args()

    test_prompt(args.transcript, args.clips)
