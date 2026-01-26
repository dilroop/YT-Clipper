"""
Video Clipper Module
Cuts video clips using ffmpeg
"""

import subprocess
from pathlib import Path
from typing import List, Dict


class VideoClipper:
    def __init__(self, output_dir: str = "./temp"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)

    def create_clip(
        self,
        video_path: str,
        start_time: float,
        end_time: float,
        output_path: str = None,
        format_type: str = "original"
    ) -> dict:
        """
        Create a clip from video

        Args:
            video_path: Path to source video
            start_time: Start time in seconds
            end_time: End time in seconds
            output_path: Optional output path
            format_type: "original" or "reels"

        Returns:
            dict with clip info
        """
        video_path = Path(video_path)

        if output_path is None:
            output_path = self.output_dir / f"clip_{start_time}_{end_time}.mp4"
        else:
            output_path = Path(output_path)

        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Calculate duration
        duration = end_time - start_time

        # Build ffmpeg command
        cmd = [
            'ffmpeg',
            '-ss', str(start_time),  # Start time
            '-i', str(video_path),  # Input file
            '-t', str(duration),  # Duration
            '-c:v', 'libx264',  # Video codec
            '-c:a', 'aac',  # Audio codec
            '-preset', 'medium',  # Encoding speed/quality
            '-crf', '23',  # Quality (lower = better, 23 is default)
            '-y',  # Overwrite output
            str(output_path)
        ]

        try:
            subprocess.run(
                cmd,
                check=True,
                capture_output=True
            )

            return {
                'success': True,
                'clip_path': str(output_path),
                'start_time': start_time,
                'end_time': end_time,
                'duration': duration
            }

        except subprocess.CalledProcessError as e:
            return {
                'success': False,
                'error': f"ffmpeg error: {e.stderr.decode()}"
            }

    def create_clips_batch(
        self,
        video_path: str,
        clips: List[Dict],
        output_dir: str = None
    ) -> List[Dict]:
        """
        Create multiple clips from video

        Args:
            video_path: Path to source video
            clips: List of clip metadata (start, end, clip_number)
            output_dir: Optional output directory

        Returns:
            List of created clips with paths
        """
        if output_dir:
            self.output_dir = Path(output_dir)
            self.output_dir.mkdir(parents=True, exist_ok=True)

        results = []

        for clip in clips:
            clip_num = clip.get('clip_number', 0)
            output_path = self.output_dir / f"clip_{clip_num:03d}.mp4"

            result = self.create_clip(
                video_path=video_path,
                start_time=clip['start'],
                end_time=clip['end'],
                output_path=str(output_path),
                format_type=clip.get('format_type', 'original')
            )

            if result['success']:
                result['clip_number'] = clip_num
                result['text'] = clip.get('text', '')
                result['words'] = clip.get('words', [])
                results.append(result)

        return results

    def get_video_dimensions(self, video_path: str) -> tuple:
        """
        Get video dimensions using ffprobe

        Args:
            video_path: Path to video

        Returns:
            (width, height) tuple
        """
        cmd = [
            'ffprobe',
            '-v', 'error',
            '-select_streams', 'v:0',
            '-show_entries', 'stream=width,height',
            '-of', 'csv=s=x:p=0',
            str(video_path)
        ]

        try:
            result = subprocess.run(
                cmd,
                check=True,
                capture_output=True,
                text=True
            )
            width, height = map(int, result.stdout.strip().split('x'))
            return (width, height)
        except Exception as e:
            print(f"Error getting dimensions: {e}")
            return (1920, 1080)  # Default

    def convert_to_reels(
        self,
        clip_path: str,
        output_path: str = None,
        crop_params: Dict = None
    ) -> dict:
        """
        Convert clip to reels format (9:16)

        Args:
            clip_path: Path to clip
            output_path: Optional output path
            crop_params: Optional crop parameters (x, y, width, height)

        Returns:
            dict with result
        """
        clip_path = Path(clip_path)

        if output_path is None:
            output_path = clip_path.parent / f"{clip_path.stem}_reels.mp4"
        else:
            output_path = Path(output_path)

        # Get original dimensions
        orig_width, orig_height = self.get_video_dimensions(str(clip_path))

        # Calculate reels dimensions (9:16 aspect ratio)
        target_width = 1080
        target_height = 1920

        if crop_params:
            # Use provided crop parameters
            crop_filter = f"crop={crop_params['width']}:{crop_params['height']}:{crop_params['x']}:{crop_params['y']}"
        else:
            # Default: center crop to 9:16
            # Calculate what width would give us 9:16 from current height
            crop_width = int(orig_height * 9 / 16)
            crop_x = (orig_width - crop_width) // 2

            crop_filter = f"crop={crop_width}:{orig_height}:{crop_x}:0"

        # Build ffmpeg command
        cmd = [
            'ffmpeg',
            '-i', str(clip_path),
            '-vf', f"{crop_filter},scale={target_width}:{target_height}",
            '-c:v', 'libx264',
            '-c:a', 'aac',
            '-preset', 'medium',
            '-crf', '23',
            '-y',
            str(output_path)
        ]

        try:
            subprocess.run(cmd, check=True, capture_output=True)

            return {
                'success': True,
                'reels_path': str(output_path)
            }

        except subprocess.CalledProcessError as e:
            return {
                'success': False,
                'error': f"Error converting to reels: {e.stderr.decode()}"
            }
