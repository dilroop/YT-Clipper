import json
import re
from datetime import datetime
from fastapi import APIRouter, HTTPException
from core.constants import BASE_DIR

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
                        "title": None
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
