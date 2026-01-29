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

    def get_system_prompt(self, num_clips: int, video_info: Dict = None, strategy: str = "viral-moments") -> str:
        """
        Generate system prompt for GPT by reading from ai-prompt-strategy folder

        Args:
            num_clips: Number of clips to find
            video_info: Optional video metadata (title, description, etc.)
            strategy: Strategy name (filename without .txt extension)

        Returns:
            Formatted prompt string
        """
        # Get project root directory (parent of backend)
        project_root = Path(__file__).parent.parent
        strategy_folder = project_root / "ai-prompt-strategy"
        prompt_file = strategy_folder / f"{strategy}.txt"

        # Fallback to old location if strategy file not found
        if not prompt_file.exists():
            old_prompt_file = project_root / "InterestFetchingPrompt.txt"
            if old_prompt_file.exists():
                prompt_file = old_prompt_file
                print(f"⚠️ Strategy '{strategy}' not found, using legacy InterestFetchingPrompt.txt")

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
        video_info: Dict = None,
        strategy: str = "viral-moments"
    ) -> List[Dict]:
        """
        Use AI to find the most interesting clips from transcript

        Args:
            segments: List of transcript segments with text and timestamps
            num_clips: Number of clips to extract
            video_info: Optional video metadata
            strategy: AI strategy to use (viral-moments, context-rich, educational)

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

        # Generate prompt with selected strategy
        system_prompt = self.get_system_prompt(request_clips, video_info, strategy)
        print(f"\n🎯 Using AI Strategy: {strategy}")

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
                if isinstance(clip, dict):
                    if self._is_multipart_format(clip):
                        # Multi-part clip - show all parts
                        parts = clip.get('parts', [])
                        print(f"   Clip {i}: Multi-part reel with {len(parts)} parts | {clip.get('title', 'N/A')}")
                        for part_idx, part in enumerate(parts, 1):
                            if 'start_time' in part and 'end_time' in part:
                                start = self._parse_timestamp(part['start_time'])
                                end = self._parse_timestamp(part['end_time'])
                                duration = end - start
                                print(f"      Part {part_idx}: {part['start_time']} - {part['end_time']} ({duration:.1f}s)")
                    elif 'start_time' in clip and 'end_time' in clip:
                        # Single-part clip (legacy)
                        start = self._parse_timestamp(clip['start_time'])
                        end = self._parse_timestamp(clip['end_time'])
                        duration = end - start
                        print(f"   Clip {i}: {clip['start_time']} - {clip['end_time']} ({duration:.1f}s) | {clip.get('title', 'N/A')}")
                    else:
                        print(f"   Clip {i}: Invalid format - missing required fields")
                else:
                    print(f"   Clip {i}: Invalid format - not a dict")
            print()

            # Process and validate clips
            valid_clips = []
            for i, highlight in enumerate(highlights):
                # Validate that each item is a dictionary
                if not isinstance(highlight, dict):
                    print(f"\n⚠️  Skipping clip {i+1}: Expected dict but got {type(highlight)}")
                    print(f"   Value: {str(highlight)[:200]}")
                    continue

                # Detect format and validate
                is_multipart = self._is_multipart_format(highlight)

                if is_multipart:
                    # Multi-part clip validation
                    validation_error = self._validate_multipart_clip(highlight, i+1)
                    if validation_error:
                        print(f"\n⚠️  {validation_error}")
                        continue

                    # Convert to normalized format
                    try:
                        normalized_clip = self._convert_multipart_to_normalized_format(highlight, segments)
                        valid_clips.append(normalized_clip)

                        # Log success
                        parts_count = len(normalized_clip['parts'])
                        total_duration = sum(part['duration'] for part in normalized_clip['parts'])
                        print(f"\n✅ Clip {i+1}: Multi-part reel with {parts_count} parts (total: {total_duration:.1f}s)")
                        print(f"   Title: {normalized_clip['title']}")

                    except Exception as e:
                        print(f"\n⚠️  Skipping clip {i+1}: Error converting multi-part clip: {e}")
                        continue

                else:
                    # Single-part clip validation (backward compatibility)
                    if 'start_time' not in highlight or 'end_time' not in highlight:
                        print(f"\n⚠️  Skipping clip {i+1}: Missing start_time or end_time")
                        print(f"   Keys: {list(highlight.keys())}")
                        continue

                    start = self._parse_timestamp(highlight['start_time'])
                    end = self._parse_timestamp(highlight['end_time'])
                    duration = end - start

                    # Check duration requirements
                    if duration < self.min_clip_duration:
                        print(f"\n⚠️  Skipping clip {i+1}: Duration {duration:.1f}s is too short (minimum: {self.min_clip_duration}s)")
                        print(f"   Title: {highlight.get('title', 'N/A')}")
                        print(f"   Time: {highlight['start_time']} - {highlight['end_time']}")
                        continue
                    elif duration > self.max_clip_duration:
                        print(f"\n⚠️  Skipping clip {i+1}: Duration {duration:.1f}s is too long (maximum: {self.max_clip_duration}s)")
                        print(f"   Title: {highlight.get('title', 'N/A')}")
                        print(f"   Time: {highlight['start_time']} - {highlight['end_time']}")
                        continue

                    # Convert to normalized format (1-part multi-part)
                    try:
                        normalized_clip = self._convert_singlepart_to_normalized_format(highlight, segments)
                        valid_clips.append(normalized_clip)

                        # Log success
                        print(f"\n✅ Clip {i+1}: Single-part clip ({duration:.1f}s)")
                        print(f"   Title: {normalized_clip['title']}")

                    except Exception as e:
                        print(f"\n⚠️  Skipping clip {i+1}: Error converting single-part clip: {e}")
                        continue

                # Stop if we have enough clips
                if len(valid_clips) >= num_clips:
                    break

            # Log filtering summary
            filtered_count = len(highlights) - len(valid_clips)
            if filtered_count > 0:
                print(f"\n✅ Kept {len(valid_clips)} clips, filtered out {filtered_count} clips")
            else:
                print(f"\n✅ Kept all {len(valid_clips)} clips")

            # Sort by timestamp of first part
            valid_clips.sort(key=lambda x: x['parts'][0]['start'])

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

    def _is_multipart_format(self, clip_data: Dict) -> bool:
        """
        Detect if clip data is in multi-part format
        Multi-part format has a 'parts' array instead of direct start_time/end_time
        """
        return isinstance(clip_data, dict) and 'parts' in clip_data

    def _validate_multipart_clip(self, clip_data: Dict, clip_index: int) -> Optional[str]:
        """
        Validate multi-part clip data structure and constraints
        Returns error message if invalid, None if valid
        """
        # Check for required fields
        if 'title' not in clip_data:
            return f"Clip {clip_index}: Missing 'title' field"

        if 'parts' not in clip_data:
            return f"Clip {clip_index}: Missing 'parts' array"

        parts = clip_data['parts']

        # Validate parts array
        if not isinstance(parts, list):
            return f"Clip {clip_index}: 'parts' must be an array"

        # Check part count (3-7 parts per reel)
        if len(parts) < 1:
            return f"Clip {clip_index}: Must have at least 1 part"

        if len(parts) > 7:
            return f"Clip {clip_index}: Too many parts ({len(parts)}). Maximum is 7 parts per reel"

        # Validate each part and calculate total duration
        prev_end = None
        total_duration = 0.0

        for part_idx, part in enumerate(parts):
            if not isinstance(part, dict):
                return f"Clip {clip_index}, Part {part_idx+1}: Part must be a dict"

            if 'start_time' not in part or 'end_time' not in part:
                return f"Clip {clip_index}, Part {part_idx+1}: Missing start_time or end_time"

            start = self._parse_timestamp(part['start_time'])
            end = self._parse_timestamp(part['end_time'])

            # Check chronological order
            if prev_end is not None and start < prev_end:
                return f"Clip {clip_index}, Part {part_idx+1}: Parts must be in chronological order"

            # Check minimum gap between parts (5 seconds)
            if prev_end is not None and (start - prev_end) < 5.0:
                return f"Clip {clip_index}, Part {part_idx+1}: Parts must be at least 5 seconds apart (gap: {start - prev_end:.1f}s)"

            # Check individual part duration (allow short segments for multi-part)
            duration = end - start
            if duration < 2.0:  # Minimum 2s per part to avoid extremely short segments
                return f"Clip {clip_index}, Part {part_idx+1}: Duration {duration:.1f}s is too short (minimum 2s per part)"

            if duration > self.max_clip_duration:  # Still enforce max per part
                return f"Clip {clip_index}, Part {part_idx+1}: Duration {duration:.1f}s exceeds maximum ({self.max_clip_duration}s per part)"

            total_duration += duration
            prev_end = end

        # Validate total combined duration
        if total_duration < self.min_clip_duration:
            return f"Clip {clip_index}: Total duration {total_duration:.1f}s is too short (minimum: {self.min_clip_duration}s)"

        if total_duration > self.max_clip_duration:
            return f"Clip {clip_index}: Total duration {total_duration:.1f}s is too long (maximum: {self.max_clip_duration}s)"

        return None  # Valid

    def _convert_multipart_to_normalized_format(self, clip_data: Dict, segments: List[Dict]) -> Dict:
        """
        Convert multi-part clip data to normalized internal format

        Multi-part format:
        {
            "title": "...",
            "reason": "...",
            "keywords": [...],
            "parts": [
                {"start_time": "00:01:00.000", "end_time": "00:01:15.000", ...},
                {"start_time": "00:03:20.000", "end_time": "00:03:40.000", ...}
            ]
        }

        Normalized format:
        {
            "title": "...",
            "reason": "...",
            "keywords": [...],
            "parts": [
                {"start": 60.0, "end": 75.0, "text": "...", "words": [...]},
                {"start": 200.0, "end": 220.0, "text": "...", "words": [...]}
            ]
        }
        """
        parts = clip_data['parts']
        normalized_parts = []

        for part_data in parts:
            start = self._parse_timestamp(part_data['start_time'])
            end = self._parse_timestamp(part_data['end_time'])

            # Find matching segments for this part
            part_segments = [
                seg for seg in segments
                if not (seg['end'] < start or seg['start'] > end)
            ]

            # Collect words for this part
            all_words = []
            for seg in part_segments:
                all_words.extend(seg.get('words', []))

            # Filter words to only those within this part's timerange
            part_words = [
                w for w in all_words
                if w['start'] >= start and w['end'] <= end
            ]

            # Combine text from all segments in this part
            part_text = ' '.join([seg['text'] for seg in part_segments])

            normalized_parts.append({
                'start': start,
                'end': end,
                'text': part_text,
                'words': part_words,
                'duration': end - start
            })

        return {
            'title': clip_data.get('title', 'Multi-Part Reel'),
            'reason': clip_data.get('reason', ''),
            'keywords': clip_data.get('keywords', []),
            'parts': normalized_parts,
            'score': 90,  # AI-selected clips get high score
            'is_multipart': True
        }

    def _convert_singlepart_to_normalized_format(self, clip_data: Dict, segments: List[Dict]) -> Dict:
        """
        Convert single-part clip data to normalized format (backward compatibility)
        Treats it as a multi-part clip with 1 part
        """
        start = self._parse_timestamp(clip_data['start_time'])
        end = self._parse_timestamp(clip_data['end_time'])
        duration = end - start

        # Find matching segments
        clip_segments = [
            seg for seg in segments
            if not (seg['end'] < start or seg['start'] > end)
        ]

        # Collect words
        all_words = []
        for seg in clip_segments:
            all_words.extend(seg.get('words', []))

        clip_words = [
            w for w in all_words
            if w['start'] >= start and w['end'] <= end
        ]

        # Combine text
        clip_text = ' '.join([seg['text'] for seg in clip_segments])

        return {
            'title': clip_data.get('title', 'Interesting Clip'),
            'reason': clip_data.get('reason', ''),
            'keywords': clip_data.get('keywords', []),
            'parts': [{
                'start': start,
                'end': end,
                'text': clip_text,
                'words': clip_words,
                'duration': duration
            }],
            'score': 90,
            'is_multipart': False  # Mark as converted single-part
        }
