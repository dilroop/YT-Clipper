"""
Video Downloader Module
Downloads YouTube videos using yt-dlp
"""

import yt_dlp
from pathlib import Path
import os


class VideoDownloader:
    def __init__(self, download_dir: str = "./Downloads"):
        self.download_dir = Path(download_dir)
        self.download_dir.mkdir(exist_ok=True)

    def download_video(self, url: str, progress_callback=None) -> dict:
        """
        Download a YouTube video in 1080p max quality (to keep file sizes reasonable)

        Args:
            url: YouTube video URL
            progress_callback: Optional callback function for progress updates

        Returns:
            dict with video info and file path
        """

        # Progress hook for yt-dlp
        def progress_hook(d):
            if progress_callback and d['status'] == 'downloading':
                try:
                    # Calculate percentage
                    downloaded = d.get('downloaded_bytes', 0)
                    total = d.get('total_bytes') or d.get('total_bytes_estimate', 0)

                    if total > 0:
                        percent = (downloaded / total) * 100
                    else:
                        percent = 0

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

                    # Format speed
                    speed = d.get('speed')
                    speed_str = f" at {format_bytes(speed)}/s" if speed else ""

                    # Format ETA
                    eta = d.get('eta')
                    if eta:
                        eta_mins = eta // 60
                        eta_secs = eta % 60
                        eta_str = f" ETA {eta_mins}m {eta_secs}s"
                    else:
                        eta_str = ""

                    # Build detailed message
                    downloaded_str = format_bytes(downloaded)
                    total_str = format_bytes(total) if total > 0 else "Unknown"

                    message = f"Downloading {percent:.1f}% ({downloaded_str} of {total_str}){speed_str}{eta_str}"

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
                    print(f"Progress hook error: {e}")

        # Configure yt-dlp options - limit to 1080p max to keep file sizes reasonable
        ydl_opts = {
            'format': 'bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[height<=1080][ext=mp4]/best[height<=1080]',
            'outtmpl': str(self.download_dir / '%(id)s.%(ext)s'),
            'merge_output_format': 'mp4',
            'quiet': True,
            'no_warnings': True,
            'progress_hooks': [progress_hook] if progress_callback else [],
            'nocheckcertificate': True,  # Skip SSL certificate verification
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # Get video info first
                info = ydl.extract_info(url, download=False)

                video_id = info['id']
                title = info.get('title', 'Unknown')
                channel = info.get('uploader', 'Unknown')
                duration = info.get('duration', 0)
                description = info.get('description', '')

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

                    ydl.download([url])

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
            return {
                'success': False,
                'error': str(e)
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
