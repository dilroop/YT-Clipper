"""
Subtitle Burner Module
Burns subtitles into video based on height and word count settings.

Input: Video path, subtitle data (words/timestamps), and styling config.
Output: Video with burned subtitles.
"""

from pathlib import Path
import subprocess
import shutil
import os
import tempfile
from typing import List, Dict, Optional
from PIL import Image, ImageDraw, ImageFont


class SubtitleBurner:
    def __init__(self, config: dict = None):
        """
        Initialize subtitle burner with styling configuration

        Args:
            config: Caption styling configuration (words_per_caption, font_family, font_size, vertical_position)
        """
        self.config = config or {
            'words_per_caption': 2,
            'font_family': 'Impact',
            'font_size': 48,
            'vertical_position': 80  # Percentage from top
        }
        print(f"[DEBUG] SubtitleBurner Initialized (Version 2.1 - PNG Fallback Enabled)")

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

        # ASS file header — must include ScriptType, WrapStyle, ScaledBorderAndShadow for ffmpeg subtitles filter
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
        words_per_caption = int(self.config.get('words_per_caption', 2))
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
        """Format time for ASS subtitle format (H:MM:SS.CS)"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        centiseconds = int((seconds % 1) * 100)

        return f"{hours}:{minutes:02d}:{secs:02d}.{centiseconds:02d}"

    def burn_captions(
        self,
        video_path: str,
        subtitle_path: str,
        output_path: Optional[str] = None
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
        v_path = Path(video_path)
        sub_path = Path(subtitle_path)

        if output_path is None:
            out_path = v_path.parent / f"{v_path.stem}_captioned.mp4"
        else:
            out_path = Path(output_path)

        # Escape subtitle path for ffmpeg filter
        # Need to escape special characters for ffmpeg filter syntax
        escaped_subtitle_path = str(sub_path.absolute()).replace('\\', '\\\\').replace(':', '\\:')

        # Build ffmpeg command to burn subtitles using subtitles filter with filename parameter
        cmd = [
            'ffmpeg',
            '-i', str(v_path),
            '-vf', f"subtitles=filename='{escaped_subtitle_path}'",
            '-c:v', 'libx264',
            '-c:a', 'copy',  # Copy audio without re-encoding
            '-preset', 'medium',
            '-crf', '23',
            '-y',
            str(out_path)
        ]

        print(f"[DEBUG] [V2.1] Burning captions with command: {' '.join(cmd)}")

        try:
            result = subprocess.run(cmd, check=True, capture_output=True, text=True)
            print(f"[DEBUG] Captions burned successfully to: {out_path}")

            return {
                'success': True,
                'output_path': str(out_path)
            }

        except subprocess.CalledProcessError as e:
            error_msg = e.stderr or e.stdout or "Unknown ffmpeg error"
            print(f"[ERROR] FFmpeg caption burning (subtitles filter) failed: {error_msg}")

            # FALLBACK: Try burning with PNG overlays if subtitles filter fails
            print(f"[DEBUG] Attempting PNG-based rendering fallback...")
            return self.burn_captions_with_pngs(video_path, subtitle_path, output_path)

    def burn_captions_with_pngs(
        self,
        video_path: str,
        subtitle_path: str,
        output_path: Optional[str] = None
    ) -> dict:
        """
        Fallback method: Burn captions using transparent PNG overlays via FFmpeg's overlay filter.
        Used when 'subtitles' filter is missing in FFmpeg.
        """
        v_path = Path(video_path)
        if output_path is None:
            out_path = v_path.parent / f"{v_path.stem}_captioned_png.mp4"
        else:
            out_path = Path(output_path)

        # 1. Parse ASS file to get caption timings and text
        captions = self._parse_ass_file(Path(subtitle_path))
        if not captions:
            print("[WARNING] No captions found in ASS file for PNG rendering.")
            return {'success': False, 'error': "No captions found in ASS file"}

        # 2. Get video dimensions
        import cv2
        cap = cv2.VideoCapture(str(video_path))
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        cap.release()

        # 3. Create temporary directory for PNGs
        temp_png_dir = Path(tempfile.gettempdir()) / f"captions_{os.getpid()}"
        temp_png_dir.mkdir(parents=True, exist_ok=True)

        try:
            # 4. Generate PNGs
            png_overlays = []
            for i, caption in enumerate(captions):
                png_path = temp_png_dir / f"cap_{i}.png"
                self._render_single_caption_png(
                    text=caption['text'],
                    width=width,
                    height=height,
                    output_path=png_path
                )
                png_overlays.append({
                    'path': png_path,
                    'start': caption['start'],
                    'end': caption['end']
                })

            # 5. Build FFmpeg command with complex filter
            inputs = ['-i', str(video_path)]
            for overlay in png_overlays:
                inputs.extend(['-i', str(overlay['path'])])

            filter_chains = []
            last_v = "[0]"
            for i, overlay in enumerate(png_overlays):
                next_v = f"[v{i+1}]"
                filter_chains.append(f"{last_v}[{i+1}]overlay=enable='between(t,{overlay['start']},{overlay['end']})'{next_v}")
                last_v = next_v

            cmd = [
                'ffmpeg',
                *inputs,
                '-filter_complex', ';'.join(filter_chains),
                '-map', last_v if filter_chains else '0:v',
                '-map', '0:a?',
                '-c:v', 'libx264',
                '-preset', 'ultrafast',
                '-crf', '23',
                '-y',
                str(out_path)
            ]

            print(f"[DEBUG] Running PNG overlay FFmpeg command...")
            subprocess.run(cmd, check=True, capture_output=True)

            return {
                'success': True,
                'output_path': str(output_path)
            }

        except Exception as e:
            print(f"[ERROR] PNG-based captioning failed: {str(e)}")
            return {'success': False, 'error': str(e)}
        finally:
            # Cleanup PNGs
            shutil.rmtree(temp_png_dir, ignore_errors=True)

    def _render_single_caption_png(self, text: str, width: int, height: int, output_path: Path):
        """Render a single caption segment to a transparent PNG."""
        img = Image.new('RGBA', (width, height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        # Load style from config
        font_name = self.config.get('font_family', 'Impact')
        font_size = int(self.config.get('font_size', 48))
        v_pos_percent = int(self.config.get('vertical_position', 80))

        # Attempt to load font
        try:
            font_paths = [
                f"/System/Library/Fonts/Supplemental/{font_name}.ttf",
                f"/System/Library/Fonts/{font_name}.ttf",
                "/System/Library/Fonts/Supplemental/Arial.ttf"  # Fallback
            ]
            font = None
            for fp in font_paths:
                if Path(fp).exists():
                    font = ImageFont.truetype(fp, font_size)
                    break
            if not font:
                font = ImageFont.load_default()
        except:
            font = ImageFont.load_default()

        # Calculate bounding box for background
        bbox = draw.textbbox((0, 0), text, font=font)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]

        # Calculate position (centered horizontally, configured vertically)
        x = (width - text_w) // 2
        y = int(v_pos_percent * height / 100) - text_h

        # Draw background box
        padding = 15
        draw.rectangle(
            [x - padding, y - padding, x + text_w + padding, y + text_h + padding],
            fill=(0, 0, 0, 160)  # Semi-transparent black
        )

        # Draw text
        draw.text((x, y), text, fill=(255, 255, 255, 255), font=font)

        img.save(output_path)

    def _parse_ass_file(self, ass_path: Path) -> List[Dict]:
        """Simple parser to extract timings and text from ASS file."""
        import re
        captions = []
        try:
            with open(ass_path, 'r', encoding='utf-8') as f:
                content = f.read()

            pattern = r"Dialogue: \d+,(\d+:\d+:\d+\.\d+),(\d+:\d+:\d+\.\d+),.*,,(.*)"
            matches = re.finditer(pattern, content)

            for m in matches:
                start_str, end_str, text = m.groups()
                captions.append({
                    'start': self._ass_time_to_seconds(start_str),
                    'end': self._ass_time_to_seconds(end_str),
                    'text': text.strip()
                })
        except Exception as e:
            print(f"[ERROR] Parsing ASS for fallback failed: {e}")
        return captions

    def _ass_time_to_seconds(self, time_str: str) -> float:
        """Convert H:MM:SS.CS to seconds."""
        h, m, s = time_str.split(':')
        return int(h) * 3600 + int(m) * 60 + float(s)

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
            Caption text as continuous text
        """
        clip_words = [
            w['word'].strip()
            for w in words
            if not (w['end'] <= clip_start_time or w['start'] >= clip_end_time)
        ]
        return ' '.join(clip_words)
