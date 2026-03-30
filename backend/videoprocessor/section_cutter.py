"""
Section Cutter Module
Cuts and joins multiple non-continuous sections of a video with smooth transitions.

Input: Source video path, list of parts (start/end times).
Output: Joined video clip.
"""

import subprocess
import time
import shutil
import tempfile
from pathlib import Path
from typing import List, Dict


class SectionCutter:
    def __init__(self, output_dir: str = "./temp"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True, parents=True)

    def create_multipart_clip(
        self,
        video_path: str,
        parts: List[Dict],
        output_path: str = None,
        transition_duration: float = 0.1
    ) -> dict:
        """
        Create a multi-part clip by stitching multiple segments with crossfade transitions

        Args:
            video_path: Path to source video
            parts: List of part metadata (start, end, duration)
            output_path: Optional output path
            transition_duration: Duration of crossfade transition (default: 0.1s)

        Returns:
            dict with clip info
        """
        video_path_obj = Path(video_path)
        if output_path is None:
            output_path = str(self.output_dir / f"multipart_clip_{video_path_obj.stem}_{int(time.time() * 1000)}.mp4")
        
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)

        if len(parts) < 1:
            return {'success': False, 'error': 'At least 1 part required'}

        if len(parts) == 1:
            # Simple extraction for single part
            part = parts[0]
            duration = part['end'] - part['start']
            cmd = [
                'ffmpeg', '-ss', str(part['start']), '-t', str(duration),
                '-i', str(video_path_obj),
                '-vf', 'scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2,setpts=PTS-STARTPTS',
                '-r', '30', '-c:v', 'libx264', '-c:a', 'aac', '-preset', 'medium', '-crf', '23', '-y', str(output_path)
            ]
            subprocess.run(cmd, check=True, capture_output=True)
            return {'success': True, 'clip_path': str(output_path), 'duration': duration}

        # Multi-part stitching
        try:
            temp_dir = Path(tempfile.mkdtemp())
            part_files = []

            for i, part in enumerate(parts):
                start, duration = part['start'], part['end'] - part['start']
                part_file = temp_dir / f"part_{i:03d}.mp4"
                cmd = [
                    'ffmpeg', '-ss', str(start), '-t', str(duration),
                    '-i', str(video_path_obj),
                    '-vf', 'scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2,setpts=PTS-STARTPTS',
                    '-r', '30', '-c:v', 'libx264', '-c:a', 'aac', '-preset', 'ultrafast', '-y', str(part_file)
                ]
                subprocess.run(cmd, check=True, capture_output=True)
                part_files.append(part_file)

            # Build xfade filter complex
            v_chain = "[0:v]"
            a_chain = "[0:a]"
            filter_parts = []
            cum_duration = parts[0]['end'] - parts[0]['start']

            for i in range(1, len(part_files)):
                p_dur = parts[i]['end'] - parts[i]['start']
                offset = cum_duration - transition_duration
                filter_parts.append(f"{v_chain}[{i}:v]xfade=transition=fade:duration={transition_duration}:offset={offset},setpts=PTS-STARTPTS[vt{i}]")
                filter_parts.append(f"{a_chain}[{i}:a]acrossfade=d={transition_duration}[at{i}]")
                v_chain, a_chain = f"[vt{i}]", f"[at{i}]"
                cum_duration += p_dur - transition_duration

            cmd = ['ffmpeg']
            for pf in part_files: cmd.extend(['-i', str(pf)])
            cmd.extend(['-filter_complex', ";".join(filter_parts), '-map', v_chain, '-map', a_chain, '-c:v', 'libx264', '-c:a', 'aac', '-preset', 'medium', '-crf', '23', '-y', str(output_path)])
            subprocess.run(cmd, check=True, capture_output=True)

            return {'success': True, 'clip_path': str(output_path), 'duration': cum_duration, 'parts': len(parts)}
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
