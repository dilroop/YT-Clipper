import os
import asyncio
import time
import uuid
import subprocess
from pathlib import Path
from fastapi import APIRouter, HTTPException, Form
from backend.core.constants import BASE_DIR, TEMP_DIR, THUMBNAILS_DIR
from backend.videoprocessor.subtitle_burner import SubtitleBurner

router = APIRouter()

@router.post("/api/workflow/transcriber/preview/{project}/{format}/{filename}")
async def get_transcriber_preview(
    project: str,
    format: str,
    filename: str,
    font_family: str = Form("Arial"),
    font_size: int = Form(80),
    vertical_position: int = Form(80),
    words_per_caption: int = Form(5),
    spoken_word_color: str = Form("#FFFF00"),
    other_words_color: str = Form("#FFFFFF"),
    bg_color: str = Form("#000000"),
    use_background_box: bool = Form(False),
    outline_color: str = Form("#000000"),
    outline_width: float = Form(3.0)
):
    try:
        TEMP_DIR.mkdir(parents=True, exist_ok=True)
        THUMBNAILS_DIR.mkdir(parents=True, exist_ok=True)
        from backend.core.constants import FONTS_DIR

        upload_dir = BASE_DIR / "ToUpload"
        video_dir = upload_dir / project / format
        main_video_path = video_dir / filename

        if not main_video_path.exists():
            # Fallback to local workspace clips if not in ToUpload
            WORKSPACE_DIR = os.environ.get("WORKSPACE_DIR", ".")
            main_video_path = Path(WORKSPACE_DIR) / "clips" / project / format / filename
            if not main_video_path.exists():
                raise HTTPException(status_code=404, detail=f"Source video not found: {filename}")

        # Extract native dimensions via ffmpeg
        import cv2
        cap = cv2.VideoCapture(str(main_video_path))
        if cap.isOpened():
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            cap.release()
        else:
            width, height = 1920, 1080

        # Create dummy words that simulate TikTok-style highlighting:
        # We will make 'EXAMPLE' the actively spoken word at time 0.25s
        dummy_words = [
            {'word': 'THIS', 'start': 0.0, 'end': 0.1},
            {'word': 'IS', 'start': 0.1, 'end': 0.2},
            {'word': 'EXAMPLE', 'start': 0.2, 'end': 0.3},
            {'word': 'TEXT', 'start': 0.3, 'end': 0.4}
        ]

        config = {
            'font_family': font_family,
            'font_size': font_size,
            'vertical_position': vertical_position,
            'words_per_caption': words_per_caption,
            'spoken_word_color': spoken_word_color,
            'other_words_color': other_words_color,
            'bg_color': bg_color,
            'use_background_box': use_background_box,
            'outline_color': outline_color,
            'outline_width': outline_width
        }

        burner = SubtitleBurner(config=config)
        session_id = uuid.uuid4().hex[:8]
        temp_ass_path = TEMP_DIR / f"preview_ass_{session_id}.ass"
        
        # Build the wrapper
        burner.create_ass_subtitles(
            words=dummy_words,
            output_path=str(temp_ass_path),
            clip_start_time=0,
            video_width=width,
            video_height=height
        )

        preview_filename = "workflowTranscriberPreview.png"
        preview_path = THUMBNAILS_DIR / preview_filename

        if preview_path.exists():
            try:
                os.remove(preview_path)
            except:
                pass

        # Extract single frame at 0.25 (where EXAMPLE is active) & burn subtitle!
        # Switch to PIL-based rendering for 100% font reliability in previews
        temp_frame_path = TEMP_DIR / f"raw_frame_{session_id}.png"
        
        extract_cmd = [
            "ffmpeg", "-y", "-i", str(main_video_path),
            "-ss", "00:00:00.250", "-vframes", "1", str(temp_frame_path)
        ]
        subprocess.run(extract_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        if not temp_frame_path.exists():
             # Fallback if 0.25 is too far
             extract_cmd = [
                "ffmpeg", "-y", "-i", str(main_video_path),
                "-vframes", "1", str(temp_frame_path)
            ]
             subprocess.run(extract_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        if temp_frame_path.exists():
            burner.burn_preview_to_image(
                image_path=temp_frame_path,
                output_path=preview_path,
                words=dummy_words,
                current_time=0.25
            )
            try: os.remove(temp_frame_path)
            except: pass
        else:
            # Absolute fallback: just a blank image or error
            raise Exception("Failed to extract preview frame")

        try:
            if temp_ass_path.exists():
                os.remove(temp_ass_path)
        except OSError:
            pass

        return {
            "success": True,
            "preview_url": f"/thumbnails/{preview_filename}",
            "timestamp": time.time()
        }

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
