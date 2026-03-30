"""
Watermarker Module
Adds text or image watermarks to videos.

Input: Video path, watermark config (text/image, position, opacity).
Output: Watermarked video.
"""

import subprocess
import os
import tempfile
from pathlib import Path
from typing import Dict
from PIL import Image, ImageDraw, ImageFont


class Watermarker:
    def __init__(self, config: dict = None):
        """Initialize watermarker with configuration"""
        self.config = config or {
            'enabled': False,
            'type': 'text',
            'text': '',
            'image_path': '',
            'position': 'top_right',
            'gap': 100
        }

    def add_watermark(self, video_path: str, output_path: str = None, watermark_config: dict = None) -> Dict:
        """Add watermark to video"""
        config = watermark_config or self.config
        if not config.get('enabled', False):
            return {'success': True, 'output_path': video_path, 'watermark_added': False}

        v_path = Path(video_path)
        out_path = Path(output_path) if output_path else v_path.parent / f"{v_path.stem}_watermarked.mp4"

        if config.get('type', 'text') == 'text':
            return self._add_text_watermark(str(v_path), str(out_path), config)
        return self._add_image_watermark(str(v_path), str(out_path), config)

    def _add_text_watermark(self, video_path: str, output_path: str, config: dict) -> Dict:
        text, pos, gap = config.get('text', ''), config.get('position', 'top_right'), config.get('gap', 100)
        p_map = {'top_right': f"x=w-tw-{gap}:y={gap}", 'top_left': f"x={gap}:y={gap}", 'bottom_right': f"x=w-tw-{gap}:y=h-th-{gap}", 'bottom_left': f"x={gap}:y=h-th-{gap}"}
        
        cmd = ['ffmpeg', '-i', video_path, '-vf', f"drawtext=text='{text}':{p_map.get(pos, p_map['top_right'])}:fontsize=32:fontcolor=white@0.7:shadowcolor=black@0.5:shadowx=2:shadowy=2", '-c:a', 'copy', '-c:v', 'libx264', '-preset', 'medium', '-crf', '23', '-y', output_path]
        try:
            subprocess.run(cmd, check=True, capture_output=True)
            return {'success': True, 'output_path': output_path, 'watermark_added': True}
        except subprocess.CalledProcessError:
            return self._text_png_fallback(video_path, output_path, config)

    def _text_png_fallback(self, v_path, out_path, config):
        import cv2
        text, pos, gap = config.get('text', 'YT-Clipper'), config.get('position', 'top_right'), config.get('gap', 100)
        cap = cv2.VideoCapture(v_path)
        w, h = int(cap.get(3)), int(cap.get(4))
        cap.release()
        img = Image.new('RGBA', (w, h), (0,0,0,0))
        draw = ImageDraw.Draw(img)
        try: font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Bold.ttf", 32)
        except: font = ImageFont.load_default()
        bbox = draw.textbbox((0,0), text, font=font)
        tw, th = bbox[2]-bbox[0], bbox[3]-bbox[1]
        x, y = (w-tw-gap, gap) if pos == 'top_right' else (gap, gap) if pos == 'top_left' else (w-tw-gap, h-th-gap) if pos == 'bottom_right' else (gap, h-th-gap)
        draw.text((x+2, y+2), text, font=font, fill=(0,0,0,128))
        draw.text((x,y), text, font=font, fill=(255,255,255,180))
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
            img.save(tmp.name)
            cmd = ['ffmpeg', '-i', v_path, '-i', tmp.name, '-filter_complex', 'overlay=0:0', '-c:a', 'copy', '-c:v', 'libx264', '-preset', 'ultrafast', '-crf', '23', '-y', out_path]
            subprocess.run(cmd, check=True, capture_output=True)
            os.remove(tmp.name)
        return {'success': True, 'output_path': out_path, 'watermark_added': True}

    def _add_image_watermark(self, v_path, out_path, config):
        img_p, pos, gap = config.get('image_path', ''), config.get('position', 'top_right'), config.get('gap', 100)
        if not img_p or not Path(img_p).exists(): return {'success': False, 'error': 'Image not found'}
        p_map = {'top_right': f"W-w-{gap}:{gap}", 'top_left': f"{gap}:{gap}", 'bottom_right': f"W-w-{gap}:H-h-{gap}", 'bottom_left': f"{gap}:H-h-{gap}"}
        cmd = ['ffmpeg', '-i', v_path, '-i', img_p, '-filter_complex', f"overlay={p_map.get(pos, p_map['top_right'])}", '-c:a', 'copy', '-c:v', 'libx264', '-preset', 'medium', '-crf', '23', '-y', out_path]
        subprocess.run(cmd, check=True, capture_output=True)
        return {'success': True, 'output_path': out_path, 'watermark_added': True}
