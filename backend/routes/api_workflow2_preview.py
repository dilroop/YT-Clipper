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

@router.post("/api/workflow2/preview/{project}/{format}/{filename}")
async def get_workflow2_preview(
    project: str,
    format: str,
    filename: str,
    header_image: UploadFile = File(...),
    story_text: str        = Form(...),
    suffix_text1: str      = Form(""),
    suffix_text2: str      = Form(""),
    top_margin: int        = Form(60),
    padding: int           = Form(40),
    header_height: int     = Form(160),
    bg_color: str          = Form("#000000"),
    font_name: str         = Form("Arial"),
    story_size: int        = Form(52),
    story_color: str       = Form("#FFFFFF"),
    highlight_color: str   = Form("#22DD66"),
    suffix1_size: int      = Form(38),
    suffix1_color: str     = Form("#AAAAAA"),
    suffix2_size: int      = Form(44),
    suffix2_color: str     = Form("#22DD66"),
    fps: int               = Form(30),
    detection_mode: str    = Form("face"),
    crop_mode: str         = Form("9:8"),
    auto_scale: bool       = Form(False),
):
    try:
        TEMP_DIR.mkdir(parents=True, exist_ok=True)
        THUMBNAILS_DIR.mkdir(parents=True, exist_ok=True)

        # 1. Setup Input Video path
        upload_dir = BASE_DIR / "ToUpload"
        video_dir = upload_dir / project / format
        main_video_path = video_dir / filename

        if not main_video_path.exists():
            raise HTTPException(status_code=404, detail=f"Main video not found: {main_video_path}")

        # 2. Save the uploaded header image to a temp path
        _, ext = os.path.splitext(header_image.filename or "header.png")
        header_temp_path = TEMP_DIR / f"preview_header_{uuid.uuid4().hex}{ext}"
        with open(header_temp_path, "wb") as buf:
            shutil.copyfileobj(header_image.file, buf)

        # 3. Prepare Preview Output path (in thumbnails dir for easy serving)
        preview_filename = "workflow2preview.png"
        preview_output_path = THUMBNAILS_DIR / preview_filename

        # 4. Run workflow2.py in PREVIEW mode
        workflow_script = BASE_DIR / "backend" / "videoprocessor" / "workflow2.py"
        
        cmd = [
            sys.executable, str(workflow_script),
            "--video",          str(main_video_path),
            "--header-image",   str(header_temp_path),
            "--story-text",     story_text,
            "--suffix-text1",   suffix_text1,
            "--suffix-text2",   suffix_text2,
            "--top-margin",     str(top_margin),
            "--padding",        str(padding),
            "--header-height",  str(header_height),
            "--bg-color",       bg_color,
            "--story-size",     str(story_size),
            "--story-color",    story_color,
            "--highlight-color", highlight_color,
            "--suffix1-size",   str(suffix1_size),
            "--suffix1-color",  suffix1_color,
            "--suffix2-size",   str(suffix2_size),
            "--suffix2-color",  suffix2_color,
            "--crop-mode",      crop_mode,
            # Feature flags
            "--preview",
            "--output",         str(preview_output_path),
        ]

        if auto_scale:
            cmd += ["--auto-scale"]

        if font_name and font_name.lower() not in ("arial", ""):
            cmd += ["--font", font_name]

        # Set up environment to include project root in PYTHONPATH
        env = os.environ.copy()
        env["PYTHONPATH"] = str(BASE_DIR) + os.pathsep + env.get("PYTHONPATH", "")

        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(BASE_DIR),
            env=env
        )
        stdout, stderr = await process.communicate()

        # Clean up the header temp file
        if header_temp_path.exists():
            os.remove(header_temp_path)

        if process.returncode != 0:
            err = stderr.decode().strip() or stdout.decode().strip()
            raise Exception(f"Preview generation failed: {err}")

        # 5. Return the URL
        return {
            "success": True,
            "previewUrl": f"/thumbnails/{preview_filename}",
            "timestamp": time.time()
        }

    except Exception as e:
        print(f"[PREVIEW ERROR] {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
