import os
import sys
import shutil
import asyncio
import time
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, HTTPException, BackgroundTasks, Form, UploadFile, File
from backend.core.constants import BASE_DIR, TEMP_DIR
from backend.core.connection_manager import manager

router = APIRouter()


async def execute_workflow2(
    project: str,
    format: str,
    filename: str,
    client_id: str,
    header_image_path: str,
    story_text: str,
    suffix_text1: str,
    suffix_text2: str,
    top_margin: int,
    padding: int,
    header_height: int,
    bg_color: str,
    font_name: str,
    story_size: int,
    story_color: str,
    highlight_color: str,
    suffix1_size: int,
    suffix1_color: str,
    suffix2_size: int,
    suffix2_color: str,
    fps: int,
    detection_mode: str,
    crop_mode: str,
    auto_scale: bool,
):
    async def broadcast_log(line: str):
        print(f"[WORKFLOW2] {line}")
        await manager.broadcast({'type': 'log', 'line': line}, target_client_id=client_id)

    try:
        upload_dir = BASE_DIR / "ToUpload"
        video_dir = upload_dir / project / format
        main_video_path = video_dir / filename

        if not main_video_path.exists():
            raise Exception(f"Main video not found: {main_video_path}")

        workflow_script = BASE_DIR / "backend" / "videoprocessor" / "workflow2.py"

        # Build unique timestamped output filename
        timestamp = int(time.time())
        stem = main_video_path.stem
        final_filename = f"{stem}_story_{timestamp}.mp4"
        final_output_path = video_dir / final_filename
        temp_output_path = TEMP_DIR / final_filename

        # ── Setup primary input ──────────────────────────────────────────────
        video_for_workflow = str(main_video_path)

        cmd = [
            sys.executable, str(workflow_script),
            "--video",          video_for_workflow,
            "--header-image",   header_image_path,
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
            "--fps",            str(fps),
            "--output",         str(temp_output_path),
            "--detection-mode", detection_mode,
            "--crop-mode",      crop_mode,
        ]

        if auto_scale:
            cmd += ["--auto-scale"]

        # Only pass --font if it's not the default Arial fallback
        if font_name and font_name.lower() not in ("arial", ""):
            cmd += ["--font", font_name]

        await broadcast_log(f"> Starting Workflow 2 for {filename}...")

        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        async def stream_output(stream):
            buffer = ""
            while True:
                chunk = await stream.read(1024)
                if not chunk:
                    break
                buffer += chunk.decode('utf-8', errors='replace')
                while '\r' in buffer or '\n' in buffer:
                    r_idx = buffer.find('\r')
                    n_idx = buffer.find('\n')
                    sep_idx = min(r_idx, n_idx) if r_idx != -1 and n_idx != -1 else (r_idx if r_idx != -1 else n_idx)
                    line = buffer[:sep_idx].strip()
                    buffer = buffer[sep_idx + 1:]
                    if line:
                        await broadcast_log(line)
            if buffer.strip():
                await broadcast_log(buffer.strip())

        await asyncio.gather(stream_output(process.stdout), stream_output(process.stderr))
        returncode = await process.wait()

        if returncode != 0:
            raise Exception(f"Workflow 2 script failed with return code {returncode}")

        if not temp_output_path.exists():
            raise Exception(f"Expected output file not found: {temp_output_path}")

        shutil.move(str(temp_output_path), str(final_output_path))

        # Copy metadata from source clip
        info_json = video_dir / f"{stem}_info.json"
        info_txt = video_dir / f"{stem}_info.txt"
        new_stem = final_filename.replace('.mp4', '')
        if info_json.exists():
            shutil.copy2(str(info_json), str(video_dir / f"{new_stem}_info.json"))
        elif info_txt.exists():
            shutil.copy2(str(info_txt), str(video_dir / f"{new_stem}_info.txt"))

        await manager.broadcast(
            {'type': 'progress', 'stage': 'complete', 'message': 'Workflow 2 complete!'},
            target_client_id=client_id
        )

    except Exception as e:
        import traceback
        traceback.print_exc()
        await broadcast_log(f"[ERROR] {str(e)}")
        await manager.broadcast(
            {'type': 'progress', 'stage': 'error', 'message': f"Workflow 2 failed: {str(e)}"},
            target_client_id=client_id
        )

    finally:
        # Clean up the saved header image temp file
        try:
            if os.path.exists(header_image_path):
                os.remove(header_image_path)
        except OSError:
            pass
        # Clean up the saved header image temp file
        try:
            if os.path.exists(header_image_path):
                os.remove(header_image_path)
        except OSError:
            pass


@router.post("/api/workflow2/run/{project}/{format}/{filename}")
async def run_workflow2(
    project: str,
    format: str,
    filename: str,
    background_tasks: BackgroundTasks,
    client_id: str         = Form(...),
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

        # Save the uploaded header image to a temp path
        _, ext = os.path.splitext(header_image.filename or "header.png")
        header_temp_path = TEMP_DIR / f"header_{client_id}{ext}"
        with open(header_temp_path, "wb") as buf:
            shutil.copyfileobj(header_image.file, buf)

        background_tasks.add_task(
            execute_workflow2,
            project, format, filename, client_id,
            str(header_temp_path),
            story_text, suffix_text1, suffix_text2,
            top_margin, padding, header_height,
            bg_color, font_name,
            story_size, story_color, highlight_color,
            suffix1_size, suffix1_color,
            suffix2_size, suffix2_color,
            fps,
            detection_mode,
            crop_mode,
            auto_scale,
        )

        return {"success": True, "message": "Workflow 2 started"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
