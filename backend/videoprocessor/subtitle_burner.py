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
from backend.core.constants import FONTS_DIR
from backend.videoprocessor.font_utils import get_font


class SubtitleBurner:
    def __init__(self, config: dict = None):
        """
        Initialize subtitle burner with styling configuration

        Args:
            config: Caption styling configuration (words_per_caption, font_family, font_size, vertical_position)
        """
        self.config = config or {
            'words_per_caption': 2,
            'font_family': 'Arial',
            'font_size': 80,
            'vertical_position': 80,  # Percentage from top
            'text_color': '#FFFFFF',
            'outline_color': '#000000',
            'outline_width': 3,
            'outline_opacity': 100
        }
        print(f"[DEBUG] SubtitleBurner Initialized (Version 2.1 - PNG Fallback Enabled)")

    def _hex_to_ass_color(self, hex_color: str, alpha="00") -> str:
        """Convert #RRGGBB to ASS &HAABBGGRR"""
        hex_color = hex_color.lstrip('#')
        if len(hex_color) == 6:
            r, g, b = hex_color[0:2], hex_color[2:4], hex_color[4:6]
            return f"&H{alpha}{b}{g}{r}"
        return "&H00FFFFFF"

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

        # Setup dynamic colors for TikTok style captions
        # If spoken_word_color is provided, it means we do dynamic word-by-word highlights.
        is_dynamic = 'spoken_word_color' in self.config
        text_color = self.config.get('text_color', '#FFFFFF')
        
        # When dynamic, text_color is used as the fallback if other_words_color isn't specified
        other_color = self.config.get('other_words_color', text_color)
        spoken_color = self.config.get('spoken_word_color', '#FFFF00')
        
        outline_color = self.config.get('outline_color', '#000000')
        outline_opacity = self.config.get('outline_opacity', 100)
        outline_width = float(self.config.get('outline_width', 3))

        # Background box settings
        use_bg_box = self.config.get('use_background_box', False)
        border_style = 3 if use_bg_box else 1
        
        # In ASS, 00=opaque, FF=transparent
        alpha_val = int(255 * (100 - outline_opacity) / 100)
        outline_alpha_hex = f"{alpha_val:02X}"
        
        bg_color = self.config.get('bg_color', '#000000')
        # If using a background box, usually we want some transparency (like 50% = 127 = 7F)
        # We can map standard alpha logic here. Hardcoded to somewhat transparent box or solid if stroke.
        bg_alpha_hex = outline_alpha_hex if not use_bg_box else "40" # Slight transparency for box
        
        # Base primary color (used when not dynamically overriding)
        primary_color_ass = self._hex_to_ass_color(other_color if is_dynamic else text_color, "00")
        outline_color_ass = self._hex_to_ass_color(outline_color, outline_alpha_hex)
        back_color_ass = self._hex_to_ass_color(bg_color, bg_alpha_hex)
        
        # For ASS overrides within the text
        other_ass_override = self._hex_to_ass_color(other_color, "00").replace('&H00', '&H') # {\c&HBBGGRR&}
        spoken_ass_override = self._hex_to_ass_color(spoken_color, "00").replace('&H00', '&H')

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
Style: Default,{self.config.get('font_family', 'Arial')},{self.config.get('font_size', 80)},{primary_color_ass},&H000000FF,{outline_color_ass},{back_color_ass},-1,0,0,0,100,100,0,0,{border_style},{outline_width},0,2,10,10,{margin_v},1

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

            # Dynamically format text block if dynamic styling is enabled
            if is_dynamic:
                # We emit one ASS Dialog event per word, changing the highlighted word.
                for j, target_word_obj in enumerate(word_group):
                    # Timing for this specific word to be highlighted
                    target_start = target_word_obj['start'] - clip_start_time
                    target_end = target_word_obj['end'] - clip_start_time
                    
                    # If the word time is somehow completely outside, skip its highlight
                    if target_start < 0: target_start = 0
                    
                    word_start_str = self._format_ass_time(target_start)
                    word_end_str = self._format_ass_time(target_end)
                    
                    # Build the text string with inline ASS color overrides
                    line_parts = []
                    for k, w_obj in enumerate(word_group):
                        raw_w = w_obj['word'].strip().upper()
                        if k == j:
                            # Highlighted word
                            line_parts.append(f"{{\\c{spoken_ass_override}}}{raw_w}{{\\c{other_ass_override}}}")
                        else:
                            # Normal word
                            line_parts.append(raw_w)
                            
                    full_text = ' '.join(line_parts)
                    captions.append(f"Dialogue: 0,{word_start_str},{word_end_str},Default,,0,0,0,,{full_text}")
            else:
                # Static format: display the entire block for the whole duration
                text = ' '.join([w['word'].strip() for w in word_group])
                start_str = self._format_ass_time(max(0, start_time))
                end_str = self._format_ass_time(end_time)
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
        def escape_ffmpeg_filter_path(p):
            return str(p).replace('\\', '/').replace(':', '\\:').replace("'", "'\\\\\\''")
            
        escaped_subtitle_path = escape_ffmpeg_filter_path(sub_path.absolute())
        escaped_fonts_dir = escape_ffmpeg_filter_path(FONTS_DIR)

        cmd = [
            'ffmpeg',
            '-i', str(v_path),
            '-vf', f"subtitles=filename='{escaped_subtitle_path}':fontsdir='{escaped_fonts_dir}'",
            '-c:v', 'libx264',
            '-c:a', 'copy',  # Copy audio without re-encoding
            '-preset', 'medium',
            '-crf', '23',
            '-y',
            str(out_path)
        ]

        print(f"[DEBUG] [V2.1] Burning captions with command: {' '.join(cmd)}")

        try:
            # Use Popen so we can stream ffmpeg output line-by-line.
            # Passing sys.stdout/stderr directly fails inside FastAPI because
            # TeeOutput (the server logger wrapper) has no fileno() method.
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,  # merge stderr into stdout
                text=True,
                bufsize=1
            )
            output_lines = []
            for line in process.stdout:
                line = line.rstrip()
                if line:
                    print(line)  # visible in CLI mode
                    output_lines.append(line)
            process.wait()

            if process.returncode != 0:
                raise subprocess.CalledProcessError(process.returncode, cmd, '\n'.join(output_lines))

            print(f"[DEBUG] Captions burned successfully to: {out_path}")
            return {
                'success': True,
                'output_path': str(out_path)
            }

        except subprocess.CalledProcessError as e:
            error_msg = str(e.output) if e.output else "Unknown ffmpeg error"
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
            last_v = "[0:v]"
            for i, overlay in enumerate(png_overlays):
                next_v = f"[v{i+1}]"
                in_png = f"[{i+1}:v]"
                filter_chains.append(f"{last_v}{in_png}overlay=enable='between(t,{overlay['start']},{overlay['end']})'{next_v}")
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
            subprocess.run(cmd, check=True, capture_output=True, text=True)

            return {
                'success': True,
                'output_path': str(out_path)
            }

        except subprocess.CalledProcessError as e:
            error_msg = e.stderr or e.stdout or str(e)
            print(f"[ERROR] PNG-based captioning failed (FFmpeg): {error_msg}")
            return {'success': False, 'error': error_msg}
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

        # Parse text color
        text_color_hex = self.config.get('text_color', '#FFFFFF').lstrip('#')
        if len(text_color_hex) == 6:
            text_rgba = (int(text_color_hex[:2], 16), int(text_color_hex[2:4], 16), int(text_color_hex[4:], 16), 255)
        else:
            text_rgba = (255, 255, 255, 255)

        # Parse outline color
        out_col_hex = self.config.get('outline_color', '#000000').lstrip('#')
        out_opac = self.config.get('outline_opacity', 100)
        out_width = float(self.config.get('outline_width', 3))
        alpha = int(255 * (out_opac / 100))
        if len(out_col_hex) == 6:
            out_rgba = (int(out_col_hex[:2], 16), int(out_col_hex[2:4], 16), int(out_col_hex[4:], 16), alpha)
        else:
            out_rgba = (0, 0, 0, alpha)

        # Attempt to load font
        font = get_font(font_name, font_size)

        # Calculate bounding box for text
        bbox = draw.textbbox((0, 0), text, font=font, stroke_width=int(out_width))
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]

        # Calculate position (centered horizontally, configured vertically)
        x = (width - text_w) // 2
        y = int(v_pos_percent * height / 100) - text_h

        # Draw text with stroke
        draw.text((x, y), text, fill=text_rgba, font=font, stroke_width=int(out_width), stroke_fill=out_rgba)

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
    def burn_preview_to_image(self, image_path: Path, output_path: Path, words: List[Dict], current_time: float):
        """Render captions onto an image using Pillow (reliable for previews)."""
        from PIL import Image, ImageDraw
        from backend.videoprocessor.font_utils import get_font, measure_text_with_fallback, draw_text_with_fallback, get_emoji_font
        
        # 1. Load image
        img = Image.open(image_path).convert("RGBA")
        width, height = img.size
        draw = ImageDraw.Draw(img)
        
        # 2. Styling from config
        f_name = self.config.get('font_family', 'Arial')
        f_size = self.config.get('font_size', 80)
        v_pos_percent = self.config.get('vertical_position', 80)
        use_bg_box = self.config.get('use_background_box', False)
        bg_color = self.config.get('bg_color', '#000000')
        text_color = self.config.get('other_words_color', '#FFFFFF')
        spoken_color = self.config.get('spoken_word_color', '#FFFF00')
        outline_color = self.config.get('outline_color', '#000000')
        outline_width = self.config.get('outline_width', 3)

        def hex_to_rgba(h, alpha=255):
            h = h.lstrip('#')
            if len(h) == 6:
                return tuple(int(h[i:i+2], 16) for i in (0, 2, 4)) + (alpha,)
            return (255, 255, 255, alpha)

        bg_rgba = hex_to_rgba(bg_color, alpha=160)
        text_rgba = hex_to_rgba(text_color)
        spoken_rgba = hex_to_rgba(spoken_color)
        out_rgba = hex_to_rgba(outline_color)
        
        # 3. Load Font
        font = get_font(f_name, f_size)
        emoji_font = get_emoji_font(f_size)
        
        # 4. Find active caption block
        # Group words into blocks based on words_per_caption logic (simplified)
        wpc = self.config.get('words_per_caption', 5)
        blocks = []
        for i in range(0, len(words), wpc):
            blocks.append(words[i:i + wpc])
            
        active_block = []
        for block in blocks:
            if not block: continue
            if block[0]['start'] <= current_time <= block[-1]['end']:
                active_block = block
                break
        
        if not active_block:
            # Fallback: find the closest upcoming block or just the first one
            active_block = blocks[0] if blocks else []

        if not active_block:
            img.save(output_path)
            return

        # 5. Measure and Draw
        # We'll draw them on one line for simplicity in preview
        line_text = " ".join([w['word'] for w in active_block])
        tw, th = measure_text_with_fallback(line_text, font, emoji_font=emoji_font, stroke_width=outline_width)
        
        x = (width - tw) // 2
        y = int(v_pos_percent * height / 100) - (th // 2)
        
        # Background box
        if use_bg_box:
            pad = 20
            draw.rectangle([x - pad, y - pad, x + tw + pad, y + th + pad], fill=bg_rgba)
        
        # Line drawing logic with highlighting
        curr_x = x
        for i, w in enumerate(active_block):
            is_active = w['start'] <= current_time <= w['end']
            fill = spoken_rgba if is_active else text_rgba
            
            # Add space if not first word
            txt = w['word']
            if i > 0:
                txt = " " + txt
                
            curr_x = draw_text_with_fallback(
                draw, (curr_x, y), txt, font, fill,
                emoji_font=emoji_font, stroke_width=int(outline_width), stroke_fill=out_rgba
            )

        img.save(output_path)
