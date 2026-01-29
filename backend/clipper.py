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

    def create_multipart_clip(
        self,
        video_path: str,
        parts: List[Dict],
        output_path: str = None,
        transition_duration: float = 0.1,
        format_type: str = "original"
    ) -> dict:
        """
        Create a multi-part clip by stitching multiple segments with crossfade transitions

        Args:
            video_path: Path to source video
            parts: List of part metadata (start, end, text, words, duration)
            output_path: Optional output path
            transition_duration: Duration of crossfade transition in seconds (default: 0.1s)
            format_type: "original" or "reels"

        Returns:
            dict with clip info
        """
        video_path = Path(video_path)

        if output_path is None:
            output_path = self.output_dir / f"multipart_clip_{parts[0]['start']}.mp4"
        else:
            output_path = Path(output_path)

        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Validate parts
        if len(parts) < 1:
            return {
                'success': False,
                'error': 'At least 1 part required for multi-part clip'
            }

        # Single part - use regular clip creation
        if len(parts) == 1:
            return self.create_clip(
                video_path=str(video_path),
                start_time=parts[0]['start'],
                end_time=parts[0]['end'],
                output_path=str(output_path),
                format_type=format_type
            )

        # Multi-part - build complex ffmpeg filter
        try:
            # Build filter_complex for stitching with crossfades
            filter_parts = []
            audio_parts = []

            # Extract each part
            for i, part in enumerate(parts):
                start = part['start']
                end = part['end']
                duration = end - start

                # Trim video and audio for this part
                filter_parts.append(
                    f"[0:v]trim=start={start}:end={end},setpts=PTS-STARTPTS[v{i}]"
                )
                audio_parts.append(
                    f"[0:a]atrim=start={start}:end={end},asetpts=PTS-STARTPTS[a{i}]"
                )

            # Build crossfade chain for video
            video_chain = "[v0]"
            for i in range(1, len(parts)):
                prev_duration = parts[i-1]['end'] - parts[i-1]['start']
                offset = prev_duration - transition_duration

                if i == 1:
                    # First crossfade
                    filter_parts.append(
                        f"{video_chain}[v{i}]xfade=transition=fade:duration={transition_duration}:offset={offset}[vt{i}]"
                    )
                    video_chain = f"[vt{i}]"
                else:
                    # Subsequent crossfades
                    filter_parts.append(
                        f"{video_chain}[v{i}]xfade=transition=fade:duration={transition_duration}:offset={offset}[vt{i}]"
                    )
                    video_chain = f"[vt{i}]"

            # Build acrossfade chain for audio
            audio_chain = "[a0]"
            for i in range(1, len(parts)):
                if i == 1:
                    # First crossfade
                    filter_parts.append(
                        f"{audio_chain}[a{i}]acrossfade=d={transition_duration}[at{i}]"
                    )
                    audio_chain = f"[at{i}]"
                else:
                    # Subsequent crossfades
                    filter_parts.append(
                        f"{audio_chain}[a{i}]acrossfade=d={transition_duration}[at{i}]"
                    )
                    audio_chain = f"[at{i}]"

            # Final output tags
            filter_complex = ";".join(filter_parts)

            # Build ffmpeg command
            cmd = [
                'ffmpeg',
                '-i', str(video_path),
                '-filter_complex', filter_complex,
                '-map', video_chain.strip('[]'),  # Map final video chain
                '-map', audio_chain.strip('[]'),  # Map final audio chain
                '-c:v', 'libx264',
                '-c:a', 'aac',
                '-preset', 'medium',
                '-crf', '23',
                '-y',
                str(output_path)
            ]

            print(f"\n🎬 Stitching {len(parts)} parts with {transition_duration}s crossfade...")
            print(f"   Filter complex: {filter_complex[:200]}..." if len(filter_complex) > 200 else f"   Filter complex: {filter_complex}")

            subprocess.run(
                cmd,
                check=True,
                capture_output=True
            )

            # Calculate total duration
            total_duration = sum(part['duration'] for part in parts)
            # Subtract overlaps from transitions
            total_duration -= transition_duration * (len(parts) - 1)

            return {
                'success': True,
                'clip_path': str(output_path),
                'parts': parts,
                'part_count': len(parts),
                'duration': total_duration,
                'is_multipart': True
            }

        except subprocess.CalledProcessError as e:
            error_msg = e.stderr.decode() if e.stderr else str(e)
            return {
                'success': False,
                'error': f"ffmpeg error during multi-part stitching: {error_msg}"
            }
        except Exception as e:
            return {
                'success': False,
                'error': f"Error creating multi-part clip: {str(e)}"
            }

    def create_clips_batch(
        self,
        video_path: str,
        clips: List[Dict],
        output_dir: str = None
    ) -> List[Dict]:
        """
        Create multiple clips from video (handles both single-part and multi-part)

        Args:
            video_path: Path to source video
            clips: List of clip metadata with 'parts' array
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

            # All clips now have 'parts' array (normalized format from Phase 1)
            if 'parts' in clip and isinstance(clip['parts'], list):
                # Use multipart clip method (handles both 1-part and N-part)
                result = self.create_multipart_clip(
                    video_path=video_path,
                    parts=clip['parts'],
                    output_path=str(output_path),
                    transition_duration=0.1,  # 100ms as specified
                    format_type=clip.get('format_type', 'original')
                )

                if result['success']:
                    result['clip_number'] = clip_num
                    result['title'] = clip.get('title', 'Clip')
                    result['reason'] = clip.get('reason', '')
                    result['keywords'] = clip.get('keywords', [])
                    # Merge all text from parts
                    result['text'] = ' '.join([part.get('text', '') for part in clip['parts']])
                    # Merge all words from parts
                    result['words'] = []
                    for part in clip['parts']:
                        result['words'].extend(part.get('words', []))
                    results.append(result)
            else:
                # Legacy format fallback (for old code that doesn't use normalized format)
                # This shouldn't happen if using Phase 1 AI analyzer
                print(f"⚠️  Warning: Clip {clip_num} using legacy format (no 'parts' array)")
                result = self.create_clip(
                    video_path=video_path,
                    start_time=clip.get('start', 0),
                    end_time=clip.get('end', 0),
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
