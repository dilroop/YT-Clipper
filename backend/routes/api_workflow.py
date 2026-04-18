import os
import sys
import shutil
import asyncio
import time
from pathlib import Path
from typing import List
from fastapi import APIRouter, HTTPException, BackgroundTasks, Form, UploadFile, File
from backend.core.constants import BASE_DIR, TEMP_DIR
from backend.core.connection_manager import manager

router = APIRouter()

# File type classification
VIDEO_EXTS = {'.mp4', '.mov', '.avi', '.mkv', '.webm', '.m4v'}
IMAGE_EXTS = {'.jpg', '.jpeg', '.png', '.bmp', '.webp', '.gif', '.tiff'}


async def _run_ffmpeg(*args, check=True):
    """Run an ffmpeg command as async subprocess, return (returncode, stderr)."""
    proc = await asyncio.create_subprocess_exec(
        'ffmpeg', *args,
        stdout=asyncio.subprocess.DEVNULL,
        stderr=asyncio.subprocess.PIPE
    )
    _, stderr = await proc.communicate()
    if check and proc.returncode != 0:
        raise Exception(f"ffmpeg failed: {stderr.decode(errors='replace')[-500:]}")
    return proc.returncode, stderr.decode(errors='replace')


async def assemble_secondary_media(
    file_paths: list[str],
    durations: list[int],
    client_id: str,
    tmp_dir: Path,
    broadcast_fn
) -> str:
    """
    Convert multiple image/video files into a single assembled secondary video.

    Rules:
    - Images  → 2-second clip each
    - Videos  → full duration
    - Mixed   → images 2s + videos at their native length
    - Result is concatenated; workflow.py will loop it to match main duration.
    """
    if not file_paths:
        raise Exception("No secondary media files provided")

    if len(file_paths) == 1:
        # Single file — no assembly needed
        return file_paths[0]

    await broadcast_fn(f"[ASSEMBLY] Assembling {len(file_paths)} secondary media files...")

    segment_paths = []
    base_filter = (
        "scale=1080:960:force_original_aspect_ratio=increase,"
        "crop=1080:960"
    )

    for i, fpath in enumerate(file_paths):
        ext = Path(fpath).suffix.lower()
        seg_path = tmp_dir / f"secondary_seg_{i}_{client_id}.mp4"
        duration = durations[i] if i < len(durations) else 2

        if ext in IMAGE_EXTS:
            await broadcast_fn(f"[ASSEMBLY]  [{i+1}/{len(file_paths)}] Image → {duration}s clip")
            await _run_ffmpeg(
                '-y',
                '-loop', '1', '-t', str(duration),
                '-i', fpath,
                '-vf', base_filter,
                '-r', '30', '-c:v', 'libx264', '-pix_fmt', 'yuv420p',
                '-an',
                str(seg_path)
            )
            segment_paths.append(str(seg_path))

        elif ext in VIDEO_EXTS:
            await broadcast_fn(f"[ASSEMBLY]  [{i+1}/{len(file_paths)}] Video → native length")
            await _run_ffmpeg(
                '-y',
                '-i', fpath,
                '-vf', base_filter,
                '-r', '30', '-c:v', 'libx264', '-pix_fmt', 'yuv420p',
                '-c:a', 'aac',
                str(seg_path)
            )
            segment_paths.append(str(seg_path))

        else:
            await broadcast_fn(f"[ASSEMBLY]  [{i+1}/{len(file_paths)}] Skipping unsupported: {Path(fpath).name}")

    if not segment_paths:
        raise Exception("No valid secondary media files could be processed")

    if len(segment_paths) == 1:
        return segment_paths[0]

    # Write concat list
    concat_list = tmp_dir / f"concat_{client_id}.txt"
    with open(concat_list, 'w') as f:
        for seg in segment_paths:
            f.write(f"file '{seg}'\n")

    assembled_path = tmp_dir / f"secondary_assembled_{client_id}.mp4"
    await broadcast_fn(f"[ASSEMBLY] Concatenating {len(segment_paths)} segments...")
    await _run_ffmpeg(
        '-y',
        '-f', 'concat', '-safe', '0',
        '-i', str(concat_list),
        '-c', 'copy',
        str(assembled_path)
    )

    await broadcast_fn("[ASSEMBLY] Secondary media assembled ✓")
    return str(assembled_path)


async def execute_workflow(
    project: str,
    format: str,
    filename: str,
    client_id: str,
    second_media_paths: list[str],   # now a list
    second_media_durations: list[int], # corresponds to paths
    main_position: str,
    text: str,
    watermark_text: str,
    watermark_size: int,
    watermark_alpha: float,
    watermark_top: int,
    watermark_right: int,
    font_family: str,
    text_color: str,
    text_bg_color: str,
    text_size: int,
    text_pos_x: float,
    text_pos_y: float,
    detection_mode: str = "face",
):
    tmp_files_to_clean = list(second_media_paths)

    async def broadcast_log(line: str):
        print(f"[WORKFLOW] {line}")
        await manager.broadcast({'type': 'log', 'line': line}, target_client_id=client_id)

    try:
        upload_dir = BASE_DIR / "ToUpload"
        video_dir = upload_dir / project / format
        main_video_path = video_dir / filename

        if not main_video_path.exists():
            raise Exception(f"Main video not found: {main_video_path}")

        workflow_script = BASE_DIR / "backend" / "videoprocessor" / "workflow.py"

        # Build unique timestamped output filename
        timestamp = int(time.time())
        stem = main_video_path.stem
        final_filename = f"{stem}_workflow_{timestamp}.mp4"
        final_output_path = video_dir / final_filename
        temp_output_path = TEMP_DIR / final_filename

        # ── Pre-process main video to 9:8 with face tracking ────────────────
        from backend.videoprocessor.video_cropper import VideoCropper
        cropper = VideoCropper()
        await broadcast_log("> Cropping main video to 9:8 with face tracking...")
        cropped_main_path = TEMP_DIR / f"{stem}_9x8_{timestamp}.mp4"
        loop = asyncio.get_event_loop()
        crop_result = await loop.run_in_executor(None, lambda: cropper.crop_to_9x8(str(main_video_path), str(cropped_main_path), mode=detection_mode))
        if crop_result.get('success'):
            main_for_workflow = str(cropped_main_path)
            tmp_files_to_clean.append(main_for_workflow)
            await broadcast_log("> 9:8 crop complete.")
        else:
            await broadcast_log(f"[WARN] Crop failed ({crop_result.get('error')}), using original video.")
            main_for_workflow = str(main_video_path)

        # ── Assemble secondary media if multiple files ───────────────────────
        assembled_second = await assemble_secondary_media(
            second_media_paths, second_media_durations, client_id, TEMP_DIR, broadcast_log
        )
        if assembled_second not in tmp_files_to_clean:
            tmp_files_to_clean.append(assembled_second)

        cmd = [
            sys.executable, str(workflow_script),
            "--main", main_for_workflow,
            "--second", assembled_second,
            "--main-position", main_position,
            "--text", text,
            "--watermark-text", watermark_text,
            "--watermark-size", str(watermark_size),
            "--watermark-alpha", str(watermark_alpha),
            "--watermark-top", str(watermark_top),
            "--watermark-right", str(watermark_right),
            "--font", font_family,
            "--font-color", text_color,
            "--bg-color", text_bg_color,
            "--font-size", str(text_size),
            "--text-x", str(text_pos_x),
            "--text-y", str(text_pos_y),
            "--output", str(temp_output_path)
        ]

        await broadcast_log(f"> Starting workflow for {filename}...")

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
            raise Exception(f"Workflow script failed with return code {returncode}")

        if not temp_output_path.exists():
            raise Exception(f"Expected output file not found: {temp_output_path}")

        shutil.move(str(temp_output_path), str(final_output_path))

        # Copy metadata
        info_json = video_dir / f"{stem}_info.json"
        info_txt = video_dir / f"{stem}_info.txt"
        new_stem = final_filename.replace('.mp4', '')
        if info_json.exists():
            shutil.copy2(str(info_json), str(video_dir / f"{new_stem}_info.json"))
        elif info_txt.exists():
            shutil.copy2(str(info_txt), str(video_dir / f"{new_stem}_info.txt"))

        await manager.broadcast({
            'type': 'progress', 'stage': 'complete', 'message': 'Workflow complete!'
        }, target_client_id=client_id)

    except Exception as e:
        import traceback
        traceback.print_exc()
        await broadcast_log(f"[ERROR] {str(e)}")
        await manager.broadcast({
            'type': 'progress', 'stage': 'error', 'message': f"Workflow failed: {str(e)}"
        }, target_client_id=client_id)

    finally:
        # Clean up all temp files
        for path in tmp_files_to_clean:
            try:
                os.remove(path)
            except OSError:
                pass
        # Clean up segment files
        for f in TEMP_DIR.glob(f"secondary_seg_*_{client_id}.mp4"):
            try:
                f.unlink()
            except OSError:
                pass
        concat_list = TEMP_DIR / f"concat_{client_id}.txt"
        if concat_list.exists():
            concat_list.unlink()


@router.post("/api/workflow/run/{project}/{format}/{filename}")
async def run_workflow(
    project: str,
    format: str,
    filename: str,
    background_tasks: BackgroundTasks,
    client_id: str = Form(...),
    second_media_files: List[UploadFile] = File(...),
    second_media_durations: str = Form("[]"),
    main_position: str = Form(...),
    text: str = Form(""),
    watermark_text: str = Form("@MrSinghExperience"),
    watermark_size: int = Form(45),
    watermark_alpha: float = Form(0.6),
    watermark_top: int = Form(100),
    watermark_right: int = Form(40),
    font_family: str = Form("Arial"),
    text_color: str = Form("#ffffff"),
    text_bg_color: str = Form("#000000"),
    text_size: int = Form(70),
    text_pos_x: float = Form(50.0),
    text_pos_y: float = Form(50.0),
    detection_mode: str = Form("face"),
):
    try:
        TEMP_DIR.mkdir(parents=True, exist_ok=True)

        saved_paths = []
        for i, upload in enumerate(second_media_files):
            _, ext = os.path.splitext(upload.filename or f"file_{i}.tmp")
            temp_path = TEMP_DIR / f"second_media_{client_id}_{i}{ext}"
            with open(temp_path, "wb") as buf:
                shutil.copyfileobj(upload.file, buf)
            saved_paths.append(str(temp_path))

        import json
        durations_list = []
        try:
            durations_list = json.loads(second_media_durations)
        except json.JSONDecodeError:
            pass

        background_tasks.add_task(
            execute_workflow,
            project, format, filename, client_id,
            saved_paths, durations_list,
            main_position, text,
            watermark_text, watermark_size, watermark_alpha,
            watermark_top, watermark_right,
            font_family, text_color, text_bg_color, text_size, text_pos_x, text_pos_y,
            detection_mode
        )

        return {"success": True, "message": f"Workflow started with {len(saved_paths)} secondary file(s)"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
