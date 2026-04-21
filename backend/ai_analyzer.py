"""
AI-Based Clip Analyzer
Uses GPT to detect interesting sections from video transcripts
"""

import json
import re
import os
import uuid
import math
import traceback
from pathlib import Path
from typing import List, Dict, Optional
from openai import OpenAI
from backend.logger import app_logger


class AIAnalyzer:
    def __init__(
        self,
        api_key: str,
        model: str,
        temperature: float,
        min_clip_duration: int,
        max_clip_duration: int,
        provider_name: str = "OpenAI"
    ):
        """
        Initialize AI-based analyzer
        """
        self.client = OpenAI(api_key=api_key, timeout=60.0)
        self.model = model
        self.temperature = temperature
        self.min_clip_duration = min_clip_duration
        self.max_clip_duration = max_clip_duration
        self.provider_name = provider_name

    def get_system_prompt(self, num_clips: int, video_info: Dict = None, strategy: str = "viral-moments", extra_context: str = None) -> str:
        """
        Generate system prompt for GPT by reading from ai-prompt-strategy folder
        """
        project_root = Path(__file__).parent.parent
        strategy_folder = project_root / "ai-prompt-strategy"
        prompt_file = strategy_folder / f"{strategy}.txt"

        if not prompt_file.exists():
            old_prompt_file = project_root / "InterestFetchingPrompt.txt"
            if old_prompt_file.exists():
                prompt_file = old_prompt_file
                print(f"⚠️ Strategy '{strategy}' not found, using legacy InterestFetchingPrompt.txt")

        try:
            with open(prompt_file, 'r', encoding='utf-8') as f:
                prompt_template = f.read()
        except FileNotFoundError:
            print(f"Warning: {prompt_file} not found, using fallback prompt")
            prompt_template = """You are a viral content editor. Find the most interesting moments.
Return JSON array with start_time, end_time, title, reason, keywords."""

        video_context = ""
        if video_info:
            v_title = video_info.get('title', 'Unknown')
            v_desc = video_info.get('description', '')[:500]
            video_context = f"""VIDEO INFO:
- Title: {v_title}
- Description: {v_desc}

"""

        if extra_context and extra_context.strip():
            video_context += f"""⚠️ SPECIAL USER INSTRUCTIONS / CUSTOM STORY:
{extra_context.strip()}

"""

        target_duration = (self.min_clip_duration + self.max_clip_duration) // 2

        formatted_prompt = prompt_template.format(
            min_duration=self.min_clip_duration,
            max_duration=self.max_clip_duration,
            target_duration=target_duration
        )

        if video_context:
            # Inject context at the start
            formatted_prompt = video_context + "\n" + formatted_prompt

        return formatted_prompt

    def find_interesting_clips(
        self,
        segments: List[Dict],
        num_clips: int = 5,
        video_info: Dict = None,
        strategy: str = "viral-moments",
        extra_context: str = None
    ) -> List[Dict]:
        """
        Use AI to find interesting clips and generate multi-platform metadata
        """
        transcript = self._compress_transcript(segments)
        app_logger.analyze(f"📊 Transcript compressed: ~{len(transcript)} chars")

        request_clips = num_clips + 3
        system_prompt = self.get_system_prompt(request_clips, video_info, strategy, extra_context)
        full_prompt = f"{system_prompt}\n\nTranscript:\n{transcript}"

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": full_prompt}],
                temperature=self.temperature,
            )
            result = response.choices[0].message.content.strip()

            # Robust JSON extraction
            if result.startswith("```"):
                result = re.sub(r"```json?\n?", "", result)
                result = re.sub(r"```\n?", "", result)
            
            start_idx = result.find('[')
            if start_idx != -1:
                bracket_count = 0
                for i in range(start_idx, len(result)):
                    if result[i] == '[': bracket_count += 1
                    elif result[i] == ']':
                        bracket_count -= 1
                        if bracket_count == 0:
                            result = result[start_idx:i+1]
                            break

            highlights = json.loads(result, strict=False)
            if not isinstance(highlights, list): return []

            # Prepare source attribution
            channel = video_info.get('channel', 'Unknown Channel') if video_info else 'Unknown Channel'
            url = video_info.get('url', '') if video_info else ''
            source_attribution = f"\n\nSource of the Clip: {channel}\nLink: {url}"

            valid_clips = []
            for i, highlight in enumerate(highlights):
                if not isinstance(highlight, dict): continue

                is_multipart = 'parts' in highlight
                
                # Validation
                if is_multipart:
                    error = self._validate_multipart_clip(highlight, i+1)
                    if error:
                        app_logger.analyze(f"⚠️ Validation error for clip {i+1}: {error}")
                        continue
                    normalized = self._convert_multipart_to_normalized_format(highlight, segments)
                else:
                    if 'start_time' not in highlight or 'end_time' not in highlight: continue
                    normalized = self._convert_singlepart_to_normalized_format(highlight, segments)

                # Inject Platform Metadata
                # We overwrite the top-level keys if platform keys exist
                for platform in ["youtube", "instagram", "tiktok"]:
                    if platform in highlight:
                        package = highlight[platform]
                        # Append attribution if not already present
                        desc = str(package.get("description", ""))
                        if source_attribution not in desc:
                            package["description"] = desc + source_attribution
                        normalized[platform] = package

                normalized['id'] = str(uuid.uuid4())
                valid_clips.append(normalized)
                if len(valid_clips) >= num_clips: break

            valid_clips.sort(key=lambda x: x['parts'][0]['start'])
            for i, clip in enumerate(valid_clips): clip['clip_number'] = i + 1

            return self.validate_clips(valid_clips)

        except Exception as e:
            app_logger.analyze(f"❌ Error in find_interesting_clips: {e}")
            traceback.print_exc()
            return []

    def _compress_transcript(self, segments: List[Dict], max_chars: int = 40000) -> str:
        """Compress transcript to fit in context window"""
        lines = []
        for s in segments:
            ts = self._format_timestamp_short(s['start'])
            lines.append(f"[{ts}] {s['text'].strip()}")
        
        full = "\n".join(lines)
        if len(full) <= max_chars: return full
        
        # Aggressive compression if too long
        step = len(segments) // (max_chars // 100) or 1
        sampled = segments[::step]
        return "\n".join([f"[{self._format_timestamp_short(s['start'])}] {s['text'].strip()}" for s in sampled])

    def _format_timestamp_short(self, seconds: float) -> str:
        m, s = divmod(int(seconds), 60)
        h, m = divmod(m, 60)
        if h > 0: return f"{h:02d}:{m:02d}:{s:02d}"
        return f"{m:02d}:{s:02d}"

    def _parse_timestamp(self, ts: str) -> float:
        ts = ts.replace(',', '.')
        parts = ts.split(':')
        try:
            if len(parts) == 3:
                return int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])
            elif len(parts) == 2:
                return int(parts[0]) * 60 + float(parts[1])
            return float(ts)
        except: return 0.0

    def _format_timestamp(self, seconds: float) -> str:
        h, m = divmod(int(seconds), 3600)
        m, s = divmod(m, 60)
        ms = int((seconds % 1) * 1000)
        return f"{h:02d}:{m:02d}:{s:02d}.{ms:03d}"

    def _validate_multipart_clip(self, clip: Dict, index: int) -> Optional[str]:
        if 'parts' not in clip or not isinstance(clip['parts'], list): return "Missing parts list"
        if len(clip['parts']) < 1: return "Empty parts list"
        return None

    def _convert_multipart_to_normalized_format(self, clip: Dict, segments: List[Dict]) -> Dict:
        normalized_parts = []
        for p in clip['parts']:
            start = self._parse_timestamp(p['start_time'])
            end = self._parse_timestamp(p['end_time'])
            
            part_segments = [s for s in segments if not (s['end'] < start or s['start'] > end)]
            all_words = []
            for s in part_segments: all_words.extend(s.get('words', []))
            part_words = [w for w in all_words if not (w['end'] <= start or w['start'] >= end)]
            
            part_text = ' '.join([w.get('word', '').strip() for w in part_words]) if part_words else ' '.join([s['text'] for s in part_segments])
            
            normalized_parts.append({
                'start': start, 'end': end, 'text': part_text, 'words': part_words, 'duration': end - start
            })

        return {
            'title': clip.get('title', 'Multi-Part Reel'),
            'reason': clip.get('reason', ''),
            'keywords': clip.get('keywords', []),
            'parts': normalized_parts,
            'score': 90,
            'is_multipart': True
        }

    def _convert_singlepart_to_normalized_format(self, clip: Dict, segments: List[Dict]) -> Dict:
        start = self._parse_timestamp(clip['start_time'])
        end = self._parse_timestamp(clip['end_time'])
        
        clip_segments = [s for s in segments if not (s['end'] < start or s['start'] > end)]
        all_words = []
        for s in clip_segments: all_words.extend(s.get('words', []))
        clip_words = [w for w in all_words if not (w['end'] <= start or w['start'] >= end)]
        
        clip_text = ' '.join([w.get('word', '').strip() for w in clip_words]) if clip_words else ' '.join([s['text'] for s in clip_segments])

        return {
            'title': clip.get('title', 'Interesting Clip'),
            'reason': clip.get('reason', ''),
            'keywords': clip.get('keywords', []),
            'parts': [{
                'start': start, 'end': end, 'text': clip_text, 'words': clip_words, 'duration': end - start
            }],
            'score': 90,
            'is_multipart': False
        }

    def validate_clips(self, clips: List[Dict]) -> List[Dict]:
        # Minimal validation logic preserved
        for i, clip in enumerate(clips):
            clip['validation_status'] = 'valid'
            clip['validation_message'] = 'Clip looks good'
            clip['validation_warnings'] = []
            
            # Simple duration check
            total = sum(p['duration'] for p in clip['parts'])
            if total > self.max_clip_duration:
                clip['validation_status'] = 'error'
                clip['validation_message'] = f'Duration {total:.1f}s > {self.max_clip_duration}s'
            elif total < self.min_clip_duration:
                # Warning for short clips instead of error in this model
                clip['validation_status'] = 'warning'
                clip['validation_message'] = f'Duration {total:.1f}s < {self.min_clip_duration}s'
                
        return clips
