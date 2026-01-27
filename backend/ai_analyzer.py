"""
AI-Based Clip Analyzer
Uses GPT to detect interesting sections from video transcripts
"""

import json
import re
import os
from pathlib import Path
from typing import List, Dict, Optional
from openai import OpenAI


class AIAnalyzer:
    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4o-mini",
        temperature: float = 1.0,
        min_clip_duration: int = 15,
        max_clip_duration: int = 60
    ):
        """
        Initialize AI-based analyzer

        Args:
            api_key: OpenAI API key
            model: GPT model to use (gpt-4o-mini, gpt-4, gpt-3.5-turbo)
            temperature: AI creativity (0.0-2.0)
            min_clip_duration: Minimum clip length in seconds
            max_clip_duration: Maximum clip length in seconds
        """
        self.client = OpenAI(api_key=api_key)
        self.model = model
        self.temperature = temperature
        self.min_clip_duration = min_clip_duration
        self.max_clip_duration = max_clip_duration

    def get_system_prompt(self, num_clips: int, video_info: Dict = None) -> str:
        """
        Generate system prompt for GPT by reading from InterestFetchingPrompt.txt

        Args:
            num_clips: Number of clips to find
            video_info: Optional video metadata (title, description, etc.)

        Returns:
            Formatted prompt string
        """
        # Get project root directory (parent of backend)
        project_root = Path(__file__).parent.parent
        prompt_file = project_root / "InterestFetchingPrompt.txt"

        # Read prompt from file
        try:
            with open(prompt_file, 'r', encoding='utf-8') as f:
                prompt_template = f.read()
        except FileNotFoundError:
            print(f"Warning: {prompt_file} not found, using fallback prompt")
            prompt_template = """You are a viral content editor. Find the most interesting moments.
Return JSON array with start_time, end_time, title, reason, keywords."""

        # Add video context if provided
        video_context = ""
        if video_info:
            video_context = f"""VIDEO INFO:
- Title: {video_info.get('title', 'Unknown')}
- Description: {video_info.get('description', '')[:500]}

"""

        # Calculate target duration
        target_duration = (self.min_clip_duration + self.max_clip_duration) // 2

        # Format the prompt with variables
        formatted_prompt = prompt_template.format(
            min_duration=self.min_clip_duration,
            max_duration=self.max_clip_duration,
            target_duration=target_duration
        )

        # Insert video context at the beginning if available
        if video_context:
            formatted_prompt = formatted_prompt.replace(
                "🔥 PRIORITY SELECTION CRITERIA",
                f"{video_context}🔥 PRIORITY SELECTION CRITERIA"
            )

        return formatted_prompt

    def find_interesting_clips(
        self,
        segments: List[Dict],
        num_clips: int = 5,
        video_info: Dict = None
    ) -> List[Dict]:
        """
        Use AI to find the most interesting clips from transcript

        Args:
            segments: List of transcript segments with text and timestamps
            num_clips: Number of clips to extract
            video_info: Optional video metadata

        Returns:
            List of clip metadata (start, end, text, score, title, reason)
        """
        # Format transcript with timestamps
        transcript_lines = []
        for segment in segments:
            start_time = self._format_timestamp(segment['start'])
            end_time = self._format_timestamp(segment['end'])
            text = segment['text'].strip()
            transcript_lines.append(f"[{start_time} - {end_time}] {text}")

        transcript = "\n".join(transcript_lines)

        # Request extra clips to ensure we get enough valid ones
        request_clips = num_clips + 3

        # Generate prompt
        system_prompt = self.get_system_prompt(request_clips, video_info)

        # Format full prompt
        full_prompt = f"{system_prompt}\n\nTranscript:\n{transcript}"

        try:
            # Call GPT API
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": full_prompt}],
                temperature=self.temperature,
            )

            result = response.choices[0].message.content.strip()

            # Log the raw OpenAI response
            print(f"\n📝 Raw OpenAI Response:")
            print("="*80)
            print(result)
            print("="*80)

            # Clean response if it has markdown code blocks
            if result.startswith("```"):
                result = re.sub(r"```json?\n?", "", result)
                result = re.sub(r"```\n?", "", result)

            # Remove any leading/trailing whitespace and newlines
            result = result.strip()

            # Try to find JSON array by looking for [ and matching ]
            # This is more robust than regex for nested structures
            start_idx = result.find('[')
            if start_idx != -1:
                # Find the matching closing bracket
                bracket_count = 0
                for i in range(start_idx, len(result)):
                    if result[i] == '[':
                        bracket_count += 1
                    elif result[i] == ']':
                        bracket_count -= 1
                        if bracket_count == 0:
                            result = result[start_idx:i+1]
                            break

            # Parse JSON response
            try:
                highlights = json.loads(result)
            except json.JSONDecodeError as e:
                print(f"\n❌ JSON Parse Error: {e}")
                print(f"\n📄 Raw Response (first 1000 chars):")
                print("="*80)
                print(result[:1000])
                print("="*80)
                # Return empty list instead of raising to be more robust
                return []

            # Validate that we got a list
            if not isinstance(highlights, list):
                print(f"\n❌ GPT Response Error: Expected a list but got {type(highlights)}")
                print(f"\n📄 Parsed JSON:")
                print("="*80)
                print(highlights)
                print("="*80)
                return []

            # Log what AI suggested before filtering
            print(f"\n🤖 AI Suggested {len(highlights)} clips before filtering:")
            for i, clip in enumerate(highlights, 1):
                if isinstance(clip, dict) and 'start_time' in clip and 'end_time' in clip:
                    start = self._parse_timestamp(clip['start_time'])
                    end = self._parse_timestamp(clip['end_time'])
                    duration = end - start
                    print(f"   Clip {i}: {clip['start_time']} - {clip['end_time']} ({duration:.1f}s) | {clip.get('title', 'N/A')}")
                else:
                    print(f"   Clip {i}: Invalid format")
            print()

            # Filter by duration
            valid_clips = []
            for i, highlight in enumerate(highlights):
                # Validate that each item is a dictionary with required fields
                if not isinstance(highlight, dict):
                    print(f"\n⚠️  Skipping clip {i+1}: Expected dict but got {type(highlight)}")
                    print(f"   Value: {str(highlight)[:200]}")
                    continue

                if 'start_time' not in highlight or 'end_time' not in highlight:
                    print(f"\n⚠️  Skipping clip {i+1}: Missing start_time or end_time")
                    print(f"   Keys: {list(highlight.keys())}")
                    continue
                start = self._parse_timestamp(highlight['start_time'])
                end = self._parse_timestamp(highlight['end_time'])
                duration = end - start

                # Check duration requirements
                if self.min_clip_duration <= duration <= self.max_clip_duration:
                    # Find matching segments and words for this time range
                    clip_segments = [
                        seg for seg in segments
                        if not (seg['end'] < start or seg['start'] > end)
                    ]

                    # Collect all words in this time range
                    all_words = []
                    for seg in clip_segments:
                        all_words.extend(seg.get('words', []))

                    # Filter words to only those within the clip timerange
                    clip_words = [
                        w for w in all_words
                        if w['start'] >= start and w['end'] <= end
                    ]

                    # Combine text from all segments
                    clip_text = ' '.join([seg['text'] for seg in clip_segments])

                    valid_clips.append({
                        'start': start,
                        'end': end,
                        'text': clip_text,
                        'words': clip_words,
                        'score': 90,  # AI-selected clips get high score
                        'title': highlight.get('title', 'Interesting Clip'),
                        'reason': highlight.get('reason', ''),
                        'keywords': highlight.get('keywords', []),
                        'duration': duration
                    })

                    if len(valid_clips) >= num_clips:
                        break
                else:
                    # Log duration violations
                    if duration < self.min_clip_duration:
                        print(f"\n⚠️  Skipping clip {i+1}: Duration {duration:.1f}s is too short (minimum: {self.min_clip_duration}s)")
                    else:
                        print(f"\n⚠️  Skipping clip {i+1}: Duration {duration:.1f}s is too long (maximum: {self.max_clip_duration}s)")
                    print(f"   Title: {highlight.get('title', 'N/A')}")
                    print(f"   Time: {highlight['start_time']} - {highlight['end_time']}")

            # Log filtering summary
            filtered_count = len(highlights) - len(valid_clips)
            if filtered_count > 0:
                print(f"\n✅ Kept {len(valid_clips)} clips, filtered out {filtered_count} clips due to duration constraints")
            else:
                print(f"\n✅ Kept all {len(valid_clips)} clips")

            # Sort by timestamp
            valid_clips.sort(key=lambda x: x['start'])

            # Assign clip numbers
            for i, clip in enumerate(valid_clips):
                clip['clip_number'] = i + 1

            return valid_clips[:num_clips]

        except json.JSONDecodeError as e:
            print(f"\n❌ Error parsing GPT response: {e}")
            print(f"\n📄 Raw GPT Response:")
            print("="*80)
            print(result)
            print("="*80)
            # Fall back to empty list
            return []
        except Exception as e:
            error_message = str(e).lower()

            # Check for OpenAI credit/quota errors
            if any(keyword in error_message for keyword in [
                'insufficient_quota',
                'rate_limit',
                'quota_exceeded',
                'billing',
                'credit',
                'exceeded your current quota'
            ]):
                print(f"\n❌ OpenAI API Error: {e}")
                # Raise a specific exception that can be caught by the server
                raise Exception("OPENAI_QUOTA_ERROR: Insufficient OpenAI credits. Please add credits to your OpenAI account.")

            print(f"\n❌ Error calling GPT API: {e}")
            import traceback
            print(traceback.format_exc())
            # Fall back to empty list
            return []

    def _format_timestamp(self, seconds: float) -> str:
        """Convert seconds to HH:MM:SS.mmm format"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        milliseconds = int((seconds % 1) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d}.{milliseconds:03d}"

    def _parse_timestamp(self, timestamp: str) -> float:
        """Convert HH:MM:SS.mmm or HH:MM:SS,mmm format to seconds"""
        # Handle both . and , as decimal separator
        timestamp = timestamp.replace(',', '.')

        parts = timestamp.split(':')
        if len(parts) == 3:
            hours = int(parts[0])
            minutes = int(parts[1])
            seconds = float(parts[2])
            return hours * 3600 + minutes * 60 + seconds
        else:
            return 0.0
