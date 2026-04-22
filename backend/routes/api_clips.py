import json
import re
from datetime import datetime
import subprocess
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from backend.core.constants import BASE_DIR
from backend.logger import app_logger

router = APIRouter()

@router.get("/api/clips")
async def get_all_clips():
    """Get all generated clips from ToUpload folder"""
    try:
        clips = []
        upload_dir = BASE_DIR / "ToUpload"

        if not upload_dir.exists():
            return {"success": True, "clips": [], "count": 0}

        # Scan all project folders
        for project_folder in upload_dir.iterdir():
            if not project_folder.is_dir():
                continue

            # Check both original and reels subfolders
            for format_type in ["original", "reels"]:
                format_folder = project_folder / format_type
                if not format_folder.exists():
                    continue

                # Find all video files
                for video_file in format_folder.glob("*.mp4"):
                    # Look for corresponding _info.json (new) or _info.txt (old)
                    info_json = video_file.parent / f"{video_file.stem}_info.json"
                    info_txt = video_file.parent / f"{video_file.stem}_info.txt"
                    info_file = info_json if info_json.exists() else info_txt if info_txt.exists() else None

                    clip_info = {
                        "filename": video_file.name,
                        "project": project_folder.name,
                        "format": format_type,
                        "path": str(video_file.relative_to(BASE_DIR)),
                        "size": video_file.stat().st_size,
                        "created": datetime.fromtimestamp(video_file.stat().st_mtime).isoformat(),
                        "has_info": info_file is not None and info_file.exists(),
                        "title": None,
                        "marker_color": None,
                    }

                    # Read info file if it exists
                    if info_file and info_file.exists():
                        if info_file.suffix == '.json':
                            with open(info_file, 'r', encoding='utf-8') as f:
                                info_data = json.load(f)
                                clip_info["info_data"] = info_data
                                clip_info["title"] = info_data.get("clip", {}).get("title")
                        else:
                            with open(info_file, 'r', encoding='utf-8') as f:
                                info_text = f.read()
                                clip_info["info_text"] = info_text
                                title_match = re.search(r'CLIP TITLE:\s*(.+?)(?:\n|$)', info_text)
                                if title_match:
                                    clip_info["title"] = title_match.group(1).strip()

                    # Read .marker sidecar (color tag)
                    marker_file = video_file.parent / f"{video_file.stem}.marker"
                    if marker_file.exists():
                        clip_info["marker_color"] = marker_file.read_text(encoding="utf-8").strip() or None

                    clips.append(clip_info)

        # Sort by creation date (newest first)
        clips.sort(key=lambda x: x["created"], reverse=True)

        return {"success": True, "clips": clips, "count": len(clips)}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching clips: {str(e)}")


@router.get("/api/clips/{project}/{format}/{filename}")
async def get_clip_details(project: str, format: str, filename: str):
    """Get details for a specific clip"""
    try:
        upload_dir = BASE_DIR / "ToUpload"
        video_path = upload_dir / project / format / filename

        if not video_path.exists():
            raise HTTPException(status_code=404, detail="Clip not found")

        # Check for JSON format first (new), then text format (old)
        info_json = video_path.parent / f"{video_path.stem}_info.json"
        info_txt = video_path.parent / f"{video_path.stem}_info.txt"
        info_path = info_json if info_json.exists() else info_txt if info_txt.exists() else None

        clip_details = {
            "filename": filename,
            "project": project,
            "format": format,
            "path": str(video_path.relative_to(BASE_DIR)),
            "size": video_path.stat().st_size,
            "created": datetime.fromtimestamp(video_path.stat().st_mtime).isoformat(),
            "has_info": info_path is not None and info_path.exists()
        }

        # Load info file data
        if info_path and info_path.exists():
            if info_path.suffix == '.json':
                with open(info_path, 'r', encoding='utf-8') as f:
                    clip_details["info_data"] = json.load(f)
            else:
                with open(info_path, 'r', encoding='utf-8') as f:
                    clip_details["info_text"] = f.read()

        return {"success": True, "clip": clip_details}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching clip details: {str(e)}")

@router.delete("/api/clips/{project}/{format}/{filename}")
async def delete_clip(project: str, format: str, filename: str):
    """Delete a specific clip and its metadata"""
    try:
        upload_dir = BASE_DIR / "ToUpload"
        video_path = upload_dir / project / format / filename

        if not video_path.exists():
            raise HTTPException(status_code=404, detail="Clip not found")

        # Identify metadata files
        info_json = video_path.parent / f"{video_path.stem}_info.json"
        info_txt = video_path.parent / f"{video_path.stem}_info.txt"

        # Delete files
        video_path.unlink()
        if info_json.exists():
            info_json.unlink()
        if info_txt.exists():
            info_txt.unlink()

        return {"success": True, "message": "Clip and metadata deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting clip: {str(e)}")


@router.post("/api/clips/{project}/{format}/{filename}/show-in-folder")
async def show_in_folder(project: str, format: str, filename: str):
    """Reveal the video clip in the native OS desktop file explorer (Finder/Explorer)"""
    try:
        import subprocess
        upload_dir = BASE_DIR / "ToUpload"
        video_path = upload_dir / project / format / filename

        if not video_path.exists():
            raise HTTPException(status_code=404, detail="Clip not found")

        # Open in Mac Finder revealing the file
        subprocess.run(["open", "-R", str(video_path)], check=True)
        return {"success": True}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Could not open folder: {str(e)}")


# ── Color marker ──────────────────────────────────────────────────────────────

@router.get("/api/clips/{project}/{format}/{filename}/marker")
async def get_marker(project: str, format: str, filename: str):
    """Return the color marker for a clip (or null if unset)."""
    try:
        upload_dir = BASE_DIR / "ToUpload"
        stem = filename.rsplit(".", 1)[0]
        marker_file = upload_dir / project / format / f"{stem}.marker"
        color = marker_file.read_text(encoding="utf-8").strip() if marker_file.exists() else None
        return {"success": True, "marker_color": color}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/api/clips/{project}/{format}/{filename}/marker")
async def set_marker(project: str, format: str, filename: str, body: dict):
    """Set or clear the color marker for a clip."""
    try:
        upload_dir = BASE_DIR / "ToUpload"
        stem = filename.rsplit(".", 1)[0]
        marker_file = upload_dir / project / format / f"{stem}.marker"
        color = (body.get("marker_color") or "").strip()
        if color:
            marker_file.write_text(color, encoding="utf-8")
        elif marker_file.exists():
            marker_file.unlink()
        return {"success": True, "marker_color": color or None}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/audio-preview")
async def get_audio_preview(
    videoId: str = Query(None),
    project: str = Query(None),
    start: float = Query(...),
    end: float = Query(...)
):
    """
    Stream a cropped MP3 segment of the original video.
    Priority: Downloads/{videoId}.mp4 > ToUpload/{project}/original/video.mp4
    """
    try:
        # Sanitize inputs
        if videoId: videoId = videoId.strip()
        if project: project = project.strip()
        
        app_logger.api(f"Audio Preview Request: videoId='{videoId}', project='{project}', start={start}, end={end}")
        
        source_path = None
        
        # 1. Primary: Search in Downloads directory using videoId
        if videoId:
            download_dir = BASE_DIR / "Downloads"
            # Try direct match for YouTube ID
            p1 = download_dir / f"{videoId}.mp4"
            if p1.exists():
                source_path = p1
                app_logger.success(f"Found source in Downloads: {source_path}")
            else:
                # Fuzzy search in Downloads if exact ID match fails
                for ext in [".mp4", ".m4a", ".wav", ".mp3", ".mkv", ".webm"]:
                    found = list(download_dir.glob(f"*{videoId}*{ext}"))
                    if found:
                        source_path = found[0]
                        app_logger.success(f"Found fuzzy source in Downloads: {source_path}")
                        break

        # 2. Secondary: Search in ToUpload project folder
        if not source_path and project:
            upload_dir = BASE_DIR / "ToUpload"
            project_dir = upload_dir / project
            if project_dir.exists():
                # Check original folder
                original_dir = project_dir / "original"
                if original_dir.exists():
                    found = list(original_dir.glob("*.mp4"))
                    if found:
                        source_path = found[0]
                        app_logger.success(f"Found source in project folder: {source_path}")

        # 3. Final fallback: Match project name in Downloads
        if not source_path and project:
             download_dir = BASE_DIR / "Downloads"
             # Match project name but avoid non-video files
             found = [f for f in download_dir.glob(f"*{project}*") if f.suffix.lower() in [".mp4", ".mkv", ".webm", ".mp3"]]
             if found: 
                 source_path = found[0]
                 app_logger.success(f"Found source in Downloads via project name: {source_path}")

        if not source_path or not source_path.exists():
            app_logger.logger.error(f"AUDIO SOURCE NOT FOUND: videoId='{videoId}', project='{project}'")
            raise HTTPException(status_code=404, detail=f"Source video not found. Tried videoId: {videoId} and project: {project}")

        # FFmpeg command to extract audio and stream as MP3
        # Fast seeking (-ss before -i)
        cmd = [
            "ffmpeg",
            "-ss", str(start),
            "-to", str(end),
            "-i", str(source_path.resolve()),
            "-f", "mp3",
            "-acodec", "libmp3lame",
            "-b:a", "128k",
            "-nostats",
            "-loglevel", "info",
            "-"
        ]

        def generate():
            # Use subprocess to stream output
            app_logger.api(f"Running FFmpeg: {' '.join(cmd)}")
            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            try:
                while True:
                    chunk = proc.stdout.read(8192)
                    if not chunk:
                        # Check for errors if no output produced
                        if proc.poll() is not None:
                            if proc.returncode != 0:
                                err = proc.stderr.read().decode()
                                app_logger.logger.error(f"FFmpeg error (code {proc.returncode}): {err}")
                            else:
                                app_logger.success("FFmpeg stream finished successfully")
                        break
                    yield chunk
            except Exception as e:
                app_logger.logger.error(f"Streaming error: {e}")
            finally:
                if proc.poll() is None:
                    proc.kill()
                if proc.stdout: proc.stdout.close()
                if proc.stderr: proc.stderr.close()
                proc.wait()

        return StreamingResponse(generate(), media_type="audio/mpeg")

    except Exception as e:
        app_logger.logger.error(f"Audio Preview Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
