"""
Watermark Processor Module
Adds text or image watermarks to videos
"""

import subprocess
from pathlib import Path
from typing import Dict


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
            subprocess.run(cmd, check=True, capture_output=True)

            return {
                'success': True,
                'output_path': output_path,
                'watermark_added': True,
                'watermark_type': 'text'
            }

        except subprocess.CalledProcessError as e:
            return {
                'success': False,
                'error': f"Error adding text watermark: {e.stderr.decode()}"
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
