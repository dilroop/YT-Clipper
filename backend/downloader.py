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

        # Configure yt-dlp options with advanced bot detection bypass
        ydl_opts = {
            # Format selection with multiple fallbacks
            'format': (
                'bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/'
                'bestvideo[height<=1080]+bestaudio/'
                'best[height<=1080][ext=mp4]/'
                'best[height<=1080]/'
                'best'
            ),
            'outtmpl': str(self.download_dir / '%(id)s.%(ext)s'),
            'merge_output_format': 'mp4',
            'quiet': True,
            'no_warnings': True,
            'progress_hooks': [progress_hook] if progress_callback else [],

            # Network and retry settings
            'nocheckcertificate': True,
            'socket_timeout': 30,
            'retries': 10,
            'fragment_retries': 10,
            'file_access_retries': 3,
            'extractor_retries': 3,

            # Advanced bot detection bypass - workaround for YouTube player changes
            # See: https://github.com/yt-dlp/yt-dlp/issues/14680
            'extractor_args': {
                'youtube': {
                    'player_client': ['default', 'web_safari'],  # Use Safari client to bypass restrictions
                    'player_js_version': 'actual',  # Use actual player version
                }
            },

            # Comprehensive browser headers
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none',
                'Sec-Fetch-User': '?1',
                'Cache-Control': 'max-age=0',
            },
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
            error_msg = str(e)

            # Provide helpful error messages based on error type
            if '403' in error_msg or 'Forbidden' in error_msg:
                error_msg += '\n\n⚠️ YouTube is blocking the download. This can happen due to:\n'
                error_msg += '  • Rate limiting - Too many requests in a short time\n'
                error_msg += '  • Regional restrictions - Video not available in your region\n'
                error_msg += '  • Age restrictions - Video requires sign-in to view\n'
                error_msg += '  • Private/unlisted video - Requires authentication\n\n'
                error_msg += '💡 Solutions:\n'
                error_msg += '  • Wait 10-15 minutes before trying again\n'
                error_msg += '  • Try a different video to test if it\'s account-specific\n'
                error_msg += '  • Check if the video plays in your browser without sign-in\n'
                error_msg += '  • Update yt-dlp: pip install -U yt-dlp'

            elif 'timeout' in error_msg.lower():
                error_msg += '\n\n⚠️ Network timeout occurred.\n'
                error_msg += '💡 This is usually temporary - try again in a moment.'

            elif 'video unavailable' in error_msg.lower():
                error_msg += '\n\n⚠️ Video is unavailable or deleted.'

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
