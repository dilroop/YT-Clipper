"""
Interesting Section Analyzer
Detects engaging clips from transcribed video
"""

import re
from typing import List, Dict


class SectionAnalyzer:
    def __init__(self, min_clip_duration: int = 15, max_clip_duration: int = 60):
        """
        Initialize analyzer

        Args:
            min_clip_duration: Minimum clip length in seconds
            max_clip_duration: Maximum clip length in seconds
        """
        self.min_clip_duration = min_clip_duration
        self.max_clip_duration = max_clip_duration

        # Keywords that indicate interesting content
        self.excitement_words = {
            'amazing', 'incredible', 'unbelievable', 'wow', 'holy', 'insane',
            'crazy', 'mind-blowing', 'spectacular', 'extraordinary', 'fantastic',
            'awesome', 'phenomenal', 'remarkable', 'stunning', 'shocking',
            'hilarious', 'epic', 'legendary', 'perfect', 'genius'
        }

        self.question_words = {
            'what', 'why', 'how', 'when', 'where', 'who', 'which',
            'really', 'seriously', 'actually'
        }

        self.emphasis_words = {
            'never', 'always', 'definitely', 'absolutely', 'literally',
            'totally', 'completely', 'exactly', 'obviously', 'clearly'
        }

    def score_segment(self, segment: Dict) -> float:
        """
        Score a transcript segment for interestingness

        Args:
            segment: Transcript segment with text and timestamps

        Returns:
            Score from 0-100
        """
        text = segment['text'].lower()
        words = re.findall(r'\b\w+\b', text)

        score = 0.0

        # 1. Excitement keywords (0-30 points)
        excitement_count = sum(1 for word in words if word in self.excitement_words)
        score += min(excitement_count * 10, 30)

        # 2. Questions (0-20 points)
        question_count = sum(1 for word in words if word in self.question_words)
        if '?' in text:
            question_count += 2
        score += min(question_count * 5, 20)

        # 3. Emphasis words (0-15 points)
        emphasis_count = sum(1 for word in words if word in self.emphasis_words)
        score += min(emphasis_count * 3, 15)

        # 4. Exclamation marks (0-10 points)
        exclamation_count = text.count('!')
        score += min(exclamation_count * 5, 10)

        # 5. Capital letters (indicates emphasis) (0-10 points)
        caps_ratio = sum(1 for c in segment['text'] if c.isupper()) / max(len(segment['text']), 1)
        if caps_ratio > 0.3:  # More than 30% caps
            score += 10

        # 6. Length penalty (prefer medium-length segments)
        duration = segment['end'] - segment['start']
        if duration < 5:  # Too short
            score *= 0.5
        elif duration > 120:  # Too long
            score *= 0.3

        # 7. Word count (conversational segments score higher)
        if len(words) > 10 and len(words) < 50:
            score += 5

        return min(score, 100)

    def find_interesting_clips(self, segments: List[Dict], num_clips: int = 5) -> List[Dict]:
        """
        Find the most interesting clips from transcript

        Args:
            segments: List of transcript segments
            num_clips: Number of clips to extract

        Returns:
            List of clip metadata (start, end, text, score)
        """
        # Score all segments
        scored_segments = []
        for segment in segments:
            score = self.score_segment(segment)
            scored_segments.append({
                'start': segment['start'],
                'end': segment['end'],
                'text': segment['text'],
                'words': segment.get('words', []),
                'score': score
            })

        # Sort by score
        scored_segments.sort(key=lambda x: x['score'], reverse=True)

        # Select top clips, ensuring no overlap
        selected_clips = []
        for segment in scored_segments:
            # Skip if score is too low
            if segment['score'] < 20:
                continue

            # Check for overlap with already selected clips
            overlaps = False
            for selected in selected_clips:
                if not (segment['end'] < selected['start'] or segment['start'] > selected['end']):
                    overlaps = True
                    break

            if not overlaps:
                # Expand clip to meet minimum duration
                duration = segment['end'] - segment['start']
                if duration < self.min_clip_duration:
                    # Try to expand by including adjacent segments
                    expanded = self._expand_clip(segment, segments)
                    selected_clips.append(expanded)
                else:
                    selected_clips.append(segment)

                if len(selected_clips) >= num_clips:
                    break

        # Sort by timestamp
        selected_clips.sort(key=lambda x: x['start'])

        # Assign clip numbers
        for i, clip in enumerate(selected_clips):
            clip['clip_number'] = i + 1

        return selected_clips

    def _expand_clip(self, segment: Dict, all_segments: List[Dict]) -> Dict:
        """
        Expand a clip to meet minimum duration by including adjacent segments

        Args:
            segment: The segment to expand
            all_segments: All available segments

        Returns:
            Expanded segment
        """
        start_time = segment['start']
        end_time = segment['end']
        text_parts = [segment['text']]
        all_words = segment.get('words', []).copy()

        # Find segments immediately before and after
        for seg in all_segments:
            # Segment right before
            if abs(seg['end'] - start_time) < 1.0:
                start_time = seg['start']
                text_parts.insert(0, seg['text'])
                all_words = seg.get('words', []) + all_words

            # Segment right after
            if abs(seg['start'] - end_time) < 1.0:
                end_time = seg['end']
                text_parts.append(seg['text'])
                all_words = all_words + seg.get('words', [])

            # Check if we've reached minimum duration
            if end_time - start_time >= self.min_clip_duration:
                break

        return {
            'start': start_time,
            'end': end_time,
            'text': ' '.join(text_parts),
            'words': all_words,
            'score': segment['score']
        }

    def adjust_clip_timing(self, clip: Dict, padding: float = 0.5) -> Dict:
        """
        Adjust clip timing to include padding and align with natural breaks

        Args:
            clip: Clip metadata
            padding: Seconds to add before/after

        Returns:
            Adjusted clip
        """
        clip = clip.copy()
        clip['start'] = max(0, clip['start'] - padding)
        clip['end'] = clip['end'] + padding

        # Ensure we don't exceed max duration
        if clip['end'] - clip['start'] > self.max_clip_duration:
            clip['end'] = clip['start'] + self.max_clip_duration

        return clip
