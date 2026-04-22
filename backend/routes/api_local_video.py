import os
import uuid
import shutil
import subprocess
import json
from fastapi import APIRouter, UploadFile, File, HTTPException
from backend.core.constants import DOWNLOAD_DIR, THUMBNAILS_DIR
from backend.database import save_to_history

router = APIRouter()

def get_video_metadata(filepath: str):
    """Get metadata using ffprobe"""
    cmd = [
        "ffprobe", 
        "-v", "quiet", 
        "-print_format", "json", 
        "-show_format", 
        "-show_streams", 
        filepath
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise Exception(f"ffprobe error: {result.stderr}")
    
    data = json.loads(result.stdout)
    format_data = data.get("format", {})
    
    duration = float(format_data.get("duration", 0))
    # Try to get title from tags, or use filename
    tags = format_data.get("tags", {})
    title = tags.get("title") or os.path.basename(filepath)
    
    return {
        "title": title,
        "duration": duration
    }

def generate_thumbnail(video_path: str, thumb_path: str):
    """Generate a thumbnail at the 1-second mark or start"""
    cmd = [
        "ffmpeg",
        "-y",
        "-ss", "00:00:01",
        "-i", video_path,
        "-vframes", "1",
        "-q:v", "2",
        thumb_path
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        # Fallback to start if 1s fails (e.g. very short video)
        cmd[3] = "00:00:00"
        subprocess.run(cmd, capture_output=True)

@router.post("/api/upload-video")
async def upload_local_video(file: UploadFile = File(...)):
    """
    Handle local video upload, extract metadata and generate thumbnail
    """
    if not file:
        raise HTTPException(status_code=400, detail="No file provided")

    file_id = f"local_{uuid.uuid4().hex[:12]}"
    ext = os.path.splitext(file.filename)[1] if file.filename else ".mp4"
    if not ext: ext = ".mp4"
    
    video_filename = f"{file_id}{ext}"
    video_path = DOWNLOAD_DIR / video_filename
    thumb_filename = f"{file_id}.jpg"
    thumb_path = THUMBNAILS_DIR / thumb_filename

    try:
        # 1. Save video
        with open(video_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # 2. Extract metadata
        meta = get_video_metadata(str(video_path))
        
        # 3. Generate thumbnail
        generate_thumbnail(str(video_path), str(thumb_path))
        
        # 4. Save to history
        save_to_history(
            url=f"local:{video_filename}",
            video_id=file_id,
            title=meta["title"],
            channel="Local File",
            duration=int(meta["duration"]),
            thumbnail=f"/thumbnails/{thumb_filename}",
            description=f"Uploaded local file: {file.filename}"
        )

        return {
            "success": True,
            "id": file_id,
            "video_id": file_id,
            "title": meta["title"],
            "channel": "Local File",
            "duration": int(meta["duration"]),
            "thumbnail": f"/thumbnails/{thumb_filename}",
            "url": f"local:{video_filename}"
        }

    except Exception as e:
        # Cleanup on failure
        if video_path.exists(): video_path.unlink()
        if thumb_path.exists(): thumb_path.unlink()
        raise HTTPException(status_code=500, detail=f"Failed to process local video: {str(e)}")
    finally:
        file.file.close()
