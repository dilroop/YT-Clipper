from fastapi import APIRouter, HTTPException
from backend.models.schemas import VideoURLRequest
from backend.utils.video_helpers import extract_video_id, get_thumbnail_url, check_url_exists
# Note: database is expected to be in the parent directory context or installed
from backend.database import save_to_history
import yt_dlp

router = APIRouter()

@router.post("/api/thumbnail")
async def get_thumbnail(request: VideoURLRequest):
    """
    Get video thumbnail and metadata without downloading
    """
    try:
        video_id = extract_video_id(request.url)
        thumbnail_urls = get_thumbnail_url(video_id)

        # Use yt-dlp to get metadata (fast, no download)
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'skip_download': True,
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(request.url, download=False, process=False)

            title = info.get('title', 'Unknown')
            channel = info.get('uploader', 'Unknown')
            duration = info.get('duration', 0)
            description = info.get('description', '')

            # Check if maxres exists to avoid browser console 404 errors
            thumbnail = thumbnail_urls['maxres']
            if not check_url_exists(thumbnail):
                thumbnail = thumbnail_urls['hq']

            # Save to history
            save_to_history(
                url=request.url,
                video_id=video_id,
                title=title,
                channel=channel,
                duration=duration,
                thumbnail=thumbnail,
                description=description
            )

            return {
                "success": True,
                "video_id": video_id,
                "title": title,
                "channel": channel,
                "duration": duration,
                "description": description,
                "thumbnail": thumbnail,
                "thumbnail_fallback": thumbnail_urls['hq'],
            }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching thumbnail: {str(e)}")
