"""
Pytube Video Downloader Module
Alternative downloader using pytubefix library (maintained fork)
"""

from pytubefix import YouTube
from pathlib import Path
import os
import subprocess


class PytubeDownloader:
    def __init__(self, download_dir: str = "./downloads"):
        self.download_dir = Path(download_dir)
        self.download_dir.mkdir(exist_ok=True)

    def download_video(self, url: str, progress_callback=None) -> dict:
        """
        Download a YouTube video using pytube

        Args:
            url: YouTube video URL
            progress_callback: Optional callback function for progress updates

        Returns:
            dict with video info and file path
        """

        def on_progress(stream, chunk, bytes_remaining):
            """Progress callback for pytube"""
            if progress_callback:
                try:
                    total_size = stream.filesize
                    bytes_downloaded = total_size - bytes_remaining
                    percent = (bytes_downloaded / total_size) * 100

                    # Format file size
                    def format_bytes(bytes_val):
                        if bytes_val < 1024:
                            return f"{bytes_val}B"
                        elif bytes_val < 1024**2:
                            return f"{bytes_val/1024:.1f}KB"
                        elif bytes_val < 1024**3:
                            return f"{bytes_val/(1024**2):.1f}MB"
                        else:
                            return f"{bytes_val/(1024**3):.2f}GB"

                    downloaded_str = format_bytes(bytes_downloaded)
                    total_str = format_bytes(total_size)

                    message = f"Downloading {percent:.1f}% ({downloaded_str} of {total_str})"

                    progress_callback({
                        'stage': 'downloading',
                        'percent': min(percent, 100),
                        'message': message
                    })
                except Exception as e:
                    # Fallback to simple message if parsing fails
                    progress_callback({
                        'stage': 'downloading',
                        'percent': 0,
                        'message': 'Downloading video...'
                    })
                    print(f"Progress callback error: {e}")

        try:
            # Create YouTube object
            yt = YouTube(url, on_progress_callback=on_progress)

            # Get video info
            video_id = yt.video_id
            title = yt.title or 'Unknown'
            channel = yt.author or 'Unknown'
            duration = yt.length or 0
            description = yt.description or ''

            # Check if video already exists
            video_path = self.download_dir / f"{video_id}.mp4"

            if video_path.exists():
                print(f"✓ Video already exists: {video_path}")
                if progress_callback:
                    progress_callback({
                        'stage': 'downloading',
                        'percent': 100,
                        'message': 'Using existing video file...'
                    })
            else:
                # Download the video
                if progress_callback:
                    progress_callback({
                        'stage': 'downloading',
                        'percent': 0,
                        'message': 'Starting download...'
                    })

                # PRIORITY 1: Try to get 1080p adaptive streams (separate video+audio)
                # This gives us the best quality but requires ffmpeg merge
                video_stream = yt.streams.filter(
                    adaptive=True,
                    file_extension='mp4',
                    type='video',
                    resolution='1080p'
                ).first()

                audio_stream = yt.streams.filter(
                    adaptive=True,
                    type='audio'
                ).order_by('abr').desc().first()

                if video_stream and audio_stream:
                    # Download 1080p video and audio separately, then merge
                    print(f"Downloading 1080p adaptive streams (video + audio)")

                    # Download video
                    if progress_callback:
                        progress_callback({
                            'stage': 'downloading',
                            'percent': 10,
                            'message': 'Downloading 1080p video stream...'
                        })

                    video_temp_path = self.download_dir / f"{video_id}_video.mp4"
                    video_stream.download(
                        output_path=str(self.download_dir),
                        filename=f"{video_id}_video.mp4"
                    )

                    # Download audio
                    if progress_callback:
                        progress_callback({
                            'stage': 'downloading',
                            'percent': 50,
                            'message': 'Downloading audio stream...'
                        })

                    audio_temp_path = self.download_dir / f"{video_id}_audio.mp4"
                    audio_stream.download(
                        output_path=str(self.download_dir),
                        filename=f"{video_id}_audio.mp4"
                    )

                    # Merge video and audio with ffmpeg
                    if progress_callback:
                        progress_callback({
                            'stage': 'downloading',
                            'percent': 80,
                            'message': 'Merging video and audio...'
                        })

                    print(f"Merging streams with ffmpeg...")
                    ffmpeg_cmd = [
                        'ffmpeg',
                        '-i', str(video_temp_path),
                        '-i', str(audio_temp_path),
                        '-c:v', 'copy',
                        '-c:a', 'aac',
                        '-y',  # Overwrite output file if exists
                        str(video_path)
                    ]

                    result = subprocess.run(
                        ffmpeg_cmd,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True
                    )

                    if result.returncode != 0:
                        raise Exception(f"FFmpeg merge failed: {result.stderr}")

                    # Clean up temp files
                    video_temp_path.unlink(missing_ok=True)
                    audio_temp_path.unlink(missing_ok=True)

                    print(f"✓ Successfully merged 1080p video")

                else:
                    # FALLBACK: Use progressive stream (limited to 720p max)
                    print("1080p adaptive streams not available, falling back to progressive stream")

                    stream = yt.streams.filter(
                        progressive=True,
                        file_extension='mp4'
                    ).order_by('resolution').desc().first()

                    if not stream:
                        raise Exception("No suitable video stream found")

                    print(f"Downloading progressive stream: {stream.resolution}")
                    stream.download(
                        output_path=str(self.download_dir),
                        filename=f"{video_id}.mp4"
                    )

                if not video_path.exists():
                    raise FileNotFoundError(f"Downloaded video not found: {video_path}")

            return {
                'success': True,
                'video_path': str(video_path),
                'video_id': video_id,
                'title': title,
                'channel': channel,
                'duration': duration,
                'description': description,
            }

        except Exception as e:
            error_msg = str(e)

            # Provide helpful error messages
            if 'RegexMatchError' in error_msg or 'extract' in error_msg.lower():
                error_msg += '\n\n⚠️ Pytube failed to extract video data.\n'
                error_msg += '💡 This can happen when YouTube changes their player.\n'
                error_msg += 'Try switching to yt-dlp in settings.'

            elif 'unavailable' in error_msg.lower():
                error_msg += '\n\n⚠️ Video is unavailable or deleted.'

            elif 'private' in error_msg.lower():
                error_msg += '\n\n⚠️ Video is private or requires authentication.'

            return {
                'success': False,
                'error': error_msg
            }

    def cleanup_video(self, video_path: str):
        """Delete a downloaded video file"""
        try:
            path = Path(video_path)
            if path.exists():
                path.unlink()
                return True
        except Exception as e:
            print(f"Error cleaning up {video_path}: {e}")
        return False
