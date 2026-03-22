"""
Watermark Processor Module
Adds text or image watermarks to videos
"""

import subprocess
import os
import tempfile
from pathlib import Path
from typing import Dict
from PIL import Image, ImageDraw, ImageFont


class WatermarkProcessor:
    def __init__(self, config: dict = None):
        """
        Initialize watermark processor

        Args:
            config: Watermark configuration (text, image, position)
        """
        self.config = config or {
            'enabled': False,
            'type': 'text',  # 'text' or 'image'
            'text': '',
            'image_path': '',
            'position': 'top_right',  # top_right, top_left, bottom_right, bottom_left
            'gap': 100  # pixels from edge
        }

    def add_watermark(
        self,
        video_path: str,
        output_path: str = None,
        watermark_config: dict = None
    ) -> Dict:
        """
        Add watermark to video

        Args:
            video_path: Path to input video
            output_path: Optional output path
            watermark_config: Optional watermark configuration

        Returns:
            dict with result
        """
        if watermark_config:
            config = watermark_config
        else:
            config = self.config

        # Skip if watermark disabled
        if not config.get('enabled', False):
            return {
                'success': True,
                'output_path': video_path,
                'watermark_added': False
            }

        video_path = Path(video_path)

        if output_path is None:
            output_path = video_path.parent / f"{video_path.stem}_watermarked.mp4"
        else:
            output_path = Path(output_path)

        watermark_type = config.get('type', 'text')

        if watermark_type == 'text':
            return self._add_text_watermark(str(video_path), str(output_path), config)
        else:
            return self._add_image_watermark(str(video_path), str(output_path), config)

    def _add_text_watermark(self, video_path: str, output_path: str, config: dict) -> Dict:
        """
        Add text watermark to video

        Args:
            video_path: Path to input video
            output_path: Output path
            config: Watermark configuration

        Returns:
            dict with result
        """
        text = config.get('text', '')
        position = config.get('position', 'top_right')
        gap = config.get('gap', 100)

        # Position coordinates for ffmpeg drawtext
        position_map = {
            'top_right': f"x=w-tw-{gap}:y={gap}",
            'top_left': f"x={gap}:y={gap}",
            'bottom_right': f"x=w-tw-{gap}:y=h-th-{gap}",
            'bottom_left': f"x={gap}:y=h-th-{gap}"
        }

        pos_string = position_map.get(position, position_map['top_right'])

        # Build drawtext filter
        drawtext_filter = (
            f"drawtext="
            f"text='{text}':"
            f"{pos_string}:"
            f"fontsize=32:"
            f"fontcolor=white@0.7:"
            f"shadowcolor=black@0.5:"
            f"shadowx=2:shadowy=2"
        )

        # Build ffmpeg command
        cmd = [
            'ffmpeg',
            '-i', video_path,
            '-vf', drawtext_filter,
            '-c:a', 'copy',  # Copy audio without re-encoding
            '-c:v', 'libx264',
            '-preset', 'medium',
            '-crf', '23',
            '-y',
            output_path
        ]

        try:
            print(f"[DEBUG] Adding text watermark with command: {' '.join(cmd)}")
            subprocess.run(cmd, check=True, capture_output=True)

            return {
                'success': True,
                'output_path': output_path,
                'watermark_added': True,
                'watermark_type': 'text'
            }

        except subprocess.CalledProcessError as e:
            stderr = e.stderr.decode()
            if "No such filter: 'drawtext'" in stderr:
                print("[DEBUG] FFmpeg 'drawtext' filter missing. Attempting PNG fallback...")
                return self._add_text_watermark_png_fallback(video_path, output_path, config)
            
            return {
                'success': False,
                'error': f"Error adding text watermark: {stderr}"
            }

    def _add_text_watermark_png_fallback(self, video_path: str, output_path: str, config: dict) -> Dict:
        """
        Fallback: Create a transparent PNG with text and overlay it.
        """
        import cv2
        text = config.get('text', 'YT-Clipper')
        position = config.get('position', 'top_right')
        gap = config.get('gap', 100)

        # 1. Get video dimensions
        cap = cv2.VideoCapture(video_path)
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        cap.release()

        # 2. Create transparent image
        img = Image.new('RGBA', (width, height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        # 3. Load font
        try:
            # Use a common system font
            font_path = "/System/Library/Fonts/Supplemental/Arial Bold.ttf" # Mac specific
            if not os.path.exists(font_path):
                font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" # Linux
            
            font = ImageFont.truetype(font_path, 32)
        except:
            font = ImageFont.load_default()

        # 4. Calculate position
        bbox = draw.textbbox((0, 0), text, font=font)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]

        if position == 'top_right':
            x, y = width - tw - gap, gap
        elif position == 'top_left':
            x, y = gap, gap
        elif position == 'bottom_right':
            x, y = width - tw - gap, height - th - gap
        elif position == 'bottom_left':
            x, y = gap, height - th - gap
        else:
            x, y = width - tw - gap, gap

        # 5. Draw text (white with 70% opacity, and shadow)
        # Shadow
        draw.text((x+2, y+2), text, font=font, fill=(0, 0, 0, 128))
        # Main text
        draw.text((x, y), text, font=font, fill=(255, 255, 255, 180))

        # 6. Save temp PNG
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
            tmp_png_path = tmp.name
            img.save(tmp_png_path)

        # 7. Overlay with FFmpeg
        overlay_cmd = [
            'ffmpeg',
            '-i', video_path,
            '-i', tmp_png_path,
            '-filter_complex', 'overlay=0:0',
            '-c:a', 'copy',
            '-c:v', 'libx264',
            '-preset', 'ultrafast',
            '-crf', '23',
            '-y',
            output_path
        ]

        try:
            subprocess.run(overlay_cmd, check=True, capture_output=True)
            if os.path.exists(tmp_png_path):
                os.remove(tmp_png_path)
            
            return {
                'success': True,
                'output_path': output_path,
                'watermark_added': True,
                'watermark_type': 'text_png_fallback'
            }
        except subprocess.CalledProcessError as e:
            if os.path.exists(tmp_png_path):
                os.remove(tmp_png_path)
            return {
                'success': False,
                'error': f"PNG Fallback watermark failed: {e.stderr.decode()}"
            }

    def _add_image_watermark(self, video_path: str, output_path: str, config: dict) -> Dict:
        """
        Add image watermark to video

        Args:
            video_path: Path to input video
            output_path: Output path
            config: Watermark configuration

        Returns:
            dict with result
        """
        image_path = config.get('image_path', '')

        if not image_path or not Path(image_path).exists():
            return {
                'success': False,
                'error': 'Watermark image not found'
            }

        position = config.get('position', 'top_right')
        gap = config.get('gap', 100)

        # Position coordinates for ffmpeg overlay
        position_map = {
            'top_right': f"W-w-{gap}:{gap}",
            'top_left': f"{gap}:{gap}",
            'bottom_right': f"W-w-{gap}:H-h-{gap}",
            'bottom_left': f"{gap}:H-h-{gap}"
        }

        pos_string = position_map.get(position, position_map['top_right'])

        # Build overlay filter
        overlay_filter = f"overlay={pos_string}"

        # Build ffmpeg command
        cmd = [
            'ffmpeg',
            '-i', video_path,
            '-i', image_path,
            '-filter_complex', overlay_filter,
            '-c:a', 'copy',  # Copy audio without re-encoding
            '-c:v', 'libx264',
            '-preset', 'medium',
            '-crf', '23',
            '-y',
            output_path
        ]

        try:
            subprocess.run(cmd, check=True, capture_output=True)

            return {
                'success': True,
                'output_path': output_path,
                'watermark_added': True,
                'watermark_type': 'image'
            }

        except subprocess.CalledProcessError as e:
            return {
                'success': False,
                'error': f"Error adding image watermark: {e.stderr.decode()}"
            }
