"""
Caption Generator Module
Creates ASS subtitle files with dynamic word-by-word captions
"""

from pathlib import Path
import subprocess
from typing import List, Dict


class CaptionGenerator:
    def __init__(self, config: dict = None):
        """
        Initialize caption generator

        Args:
            config: Caption styling configuration
        """
        self.config = config or {
            'words_per_caption': 2,
            'font_family': 'Impact',
            'font_size': 48,
            'vertical_position': 80  # Percentage from top
        }

    def create_ass_subtitles(
        self,
        words: List[Dict],
        output_path: str,
        clip_start_time: float = 0,
        video_width: int = 1920,
        video_height: int = 1080
    ) -> str:
        """
        Create ASS subtitle file with word-by-word captions

        Args:
            words: List of word dictionaries with 'word', 'start', 'end' keys
            output_path: Path to save ASS file
            clip_start_time: Offset for clip timing
            video_width: Video width in pixels
            video_height: Video height in pixels

        Returns:
            Path to created ASS file
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Calculate vertical position
        margin_v = int((100 - self.config.get('vertical_position', 80)) * video_height / 100)

        # ASS file header
        ass_content = f"""[Script Info]
Title: YTClipper Captions
ScriptType: v4.00+
WrapStyle: 0
PlayResX: {video_width}
PlayResY: {video_height}
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{self.config.get('font_family', 'Impact')},{self.config.get('font_size', 48)},&H00FFFFFF,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,3,2,2,10,10,{margin_v},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

        # Group words according to words_per_caption
        words_per_caption = self.config.get('words_per_caption', 2)
        captions = []

        for i in range(0, len(words), words_per_caption):
            word_group = words[i:i + words_per_caption]

            # Get timing from first and last word in group
            start_time = word_group[0]['start'] - clip_start_time
            end_time = word_group[-1]['end'] - clip_start_time

            # Combine words into caption text
            text = ' '.join([w['word'].strip() for w in word_group])

            # Format timing for ASS
            start_str = self._format_ass_time(max(0, start_time))
            end_str = self._format_ass_time(end_time)

            # Make text uppercase and bold for emphasis
            text = text.upper()

            captions.append(f"Dialogue: 0,{start_str},{end_str},Default,,0,0,0,,{text}")

        # Combine all captions
        ass_content += '\n'.join(captions)

        # Write to file
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(ass_content)

        return str(output_path)

    def _format_ass_time(self, seconds: float) -> str:
        """
        Format time for ASS subtitle format (H:MM:SS.CS)

        Args:
            seconds: Time in seconds

        Returns:
            Formatted time string
        """
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        centiseconds = int((seconds % 1) * 100)

        return f"{hours}:{minutes:02d}:{secs:02d}.{centiseconds:02d}"

    def burn_captions(
        self,
        video_path: str,
        subtitle_path: str,
        output_path: str = None
    ) -> dict:
        """
        Burn subtitles into video using ffmpeg

        Args:
            video_path: Path to video
            subtitle_path: Path to ASS subtitle file
            output_path: Optional output path

        Returns:
            dict with result
        """
        video_path = Path(video_path)
        subtitle_path = Path(subtitle_path)

        if output_path is None:
            output_path = video_path.parent / f"{video_path.stem}_captioned.mp4"
        else:
            output_path = Path(output_path)

        # Escape subtitle path for ffmpeg filter
        # Need to escape special characters for ffmpeg filter syntax
        escaped_subtitle_path = str(subtitle_path.absolute()).replace('\\', '\\\\').replace(':', '\\:')

        # Build ffmpeg command to burn subtitles using subtitles filter with filename parameter
        cmd = [
            'ffmpeg',
            '-i', str(video_path),
            '-vf', f"subtitles=filename='{escaped_subtitle_path}'",
            '-c:v', 'libx264',
            '-c:a', 'copy',  # Copy audio without re-encoding
            '-preset', 'medium',
            '-crf', '23',
            '-y',
            str(output_path)
        ]

        try:
            subprocess.run(cmd, check=True, capture_output=True)

            return {
                'success': True,
                'output_path': str(output_path)
            }

        except subprocess.CalledProcessError as e:
            return {
                'success': False,
                'error': f"Error burning captions: {e.stderr.decode()}"
            }

    def generate_clip_caption(
        self,
        words: List[Dict],
        clip_start_time: float,
        clip_end_time: float
    ) -> str:
        """
        Generate full caption text for a clip (for _info.txt file)

        Args:
            words: List of word dictionaries
            clip_start_time: Clip start time
            clip_end_time: Clip end time

        Returns:
            Caption text formatted as complete sentences
        """
        # Filter words that overlap with clip timeframe
        # Include words if they overlap with the clip (not strictly contained)
        clip_words = [
            w['word'].strip()
            for w in words
            if not (w['end'] <= clip_start_time or w['start'] >= clip_end_time)
        ]

        # Return all words as continuous text (full sentences)
        # This preserves the natural sentence structure from transcription
        return ' '.join(clip_words)
