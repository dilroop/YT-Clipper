import re
import requests

def extract_video_id(url: str) -> str:
    """Extract YouTube video ID from URL"""
    patterns = [
        r'(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/)([a-zA-Z0-9_-]{11})',
        r'youtube\.com/watch\?.*v=([a-zA-Z0-9_-]{11})',
    ]

    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)

    raise ValueError("Invalid YouTube URL")

def get_thumbnail_url(video_id: str) -> dict:
    """Get YouTube thumbnail URLs"""
    return {
        "maxres": f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg",
        "hq": f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg",
        "mq": f"https://img.youtube.com/vi/{video_id}/mqdefault.jpg",
        "default": f"https://img.youtube.com/vi/{video_id}/default.jpg"
    }

def check_url_exists(url: str) -> bool:
    """Check if a URL exists using a HEAD request"""
    try:
        response = requests.head(url, timeout=1.5)
        return response.status_code == 200
    except:
        return False
