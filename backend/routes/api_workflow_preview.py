import os
import sys
import shutil
import asyncio
import time
import uuid
from pathlib import Path
from fastapi import APIRouter, HTTPException, Form, UploadFile, File
from backend.core.constants import BASE_DIR, TEMP_DIR, THUMBNAILS_DIR

router = APIRouter()


@router.post("/api/workflow/preview/{project}/{format}/{filename}")
async def get_workflow_preview(
    project: str,
    format: str,
    filename: str,
    second_media: UploadFile = File(...),
    main_position: str      = Form("top"),
    text: str               = Form(""),
    font_family: str        = Form("Arial"),
    text_color: str         = Form("#FFFFFF"),
    text_bg_color: str      = Form("#000000"),
    highlight_color: str    = Form("#FFFF00"),
    text_size: int          = Form(70),
    text_pos_x: float       = Form(50.0),
    text_pos_y: float       = Form(50.0),
    outline_width: int      = Form(6),
    watermark_text: str     = Form(""),
    watermark_size: int     = Form(45),
    watermark_alpha: float  = Form(0.6),
    watermark_top: int      = Form(100),
    watermark_right: int    = Form(40),
    detection_mode: str     = Form("face"),
):
    try:
        TEMP_DIR.mkdir(parents=True, exist_ok=True)
        THUMBNAILS_DIR.mkdir(parents=True, exist_ok=True)

        # 1. Locate main video
        upload_dir = BASE_DIR / "ToUpload"
        video_dir = upload_dir / project / format
        main_video_path = video_dir / filename

        if not main_video_path.exists():
            raise HTTPException(status_code=404, detail=f"Main video not found: {main_video_path}")

        # 2. Save uploaded secondary media to temp
        _, ext = os.path.splitext(second_media.filename or "second.mp4")
        second_temp_path = TEMP_DIR / f"wf1_preview_second_{uuid.uuid4().hex}{ext}"
        with open(second_temp_path, "wb") as buf:
            shutil.copyfileobj(second_media.file, buf)

        # 3. Preview output PNG path
        preview_filename = "workflow1preview.png"
        preview_output_path = THUMBNAILS_DIR / preview_filename

        # 4. Build CLI command
        workflow_script = BASE_DIR / "backend" / "videoprocessor" / "workflow.py"

        cmd = [
            sys.executable, str(workflow_script),
            "--main",            str(main_video_path),
            "--second",          str(second_temp_path),
            "--main-position",   main_position,
            "--text",            text,
            "--font",            font_family,
            "--font-color",      text_color,
            "--bg-color",        text_bg_color,
            "--highlight-color", highlight_color,
            "--font-size",       str(text_size),
            "--text-x",          str(text_pos_x),
            "--text-y",          str(text_pos_y),
            "--outline-width",   str(outline_width),
            "--watermark-text",  watermark_text,
            "--watermark-size",  str(watermark_size),
            "--watermark-alpha", str(watermark_alpha),
            "--watermark-top",   str(watermark_top),
            "--watermark-right", str(watermark_right),
            "--detection-mode",  detection_mode,
            "--preview",
            "--output",          str(preview_output_path),
        ]

        # Set up environment to include project root in PYTHONPATH
        env = os.environ.copy()
        env["PYTHONPATH"] = str(BASE_DIR) + os.pathsep + env.get("PYTHONPATH", "")

        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(BASE_DIR),
            env=env,
        )
        stdout, stderr = await process.communicate()

        # Clean up temp secondary file
        if second_temp_path.exists():
            os.remove(second_temp_path)

        if process.returncode != 0:
            err = stderr.decode().strip() or stdout.decode().strip()
            raise Exception(f"Preview generation failed: {err}")

        return {
            "success": True,
            "previewUrl": f"/thumbnails/{preview_filename}",
            "timestamp": time.time(),
        }

    except Exception as e:
        print(f"[WF1 PREVIEW ERROR] {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
