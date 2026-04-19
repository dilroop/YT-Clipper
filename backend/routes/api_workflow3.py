import os
import sys
import shutil
import asyncio
import time
from pathlib import Path
from fastapi import APIRouter, HTTPException, BackgroundTasks, Form
from backend.core.constants import BASE_DIR, TEMP_DIR
from backend.core.connection_manager import manager

router = APIRouter()

async def execute_workflow3(
    project: str,
    format: str,
    filename: str,
    client_id: str,
    min_silence_len: int,
    keep_silence_len: int,
):
    async def broadcast_log(line: str):
        print(f"[WORKFLOW3] {line}")
        await manager.broadcast({'type': 'log', 'line': line}, target_client_id=client_id)

    try:
        upload_dir = BASE_DIR / "ToUpload"
        video_dir = upload_dir / project / format
        main_video_path = video_dir / filename

        if not main_video_path.exists():
            raise Exception(f"Main video not found: {main_video_path}")

        workflow_script = BASE_DIR / "backend" / "videoprocessor" / "workflow3.py"

        # Build unique timestamped output filename
        timestamp = int(time.time())
        stem = main_video_path.stem
        final_filename = f"{stem}_no_silence_{timestamp}.mp4"
        final_output_path = video_dir / final_filename
        temp_output_path = TEMP_DIR / final_filename

        cmd = [
            sys.executable, str(workflow_script),
            "--input", str(main_video_path),
            "--output", str(temp_output_path),
            "--threshold", str(min_silence_len),
            "--keep", str(keep_silence_len),
        ]

        await broadcast_log(f"> Starting Silence Removal for {filename}...")
        await broadcast_log(f"> Threshold: {min_silence_len}ms, Keep: {keep_silence_len}ms")

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
            raise Exception(f"Workflow 3 script failed with return code {returncode}")

        if not temp_output_path.exists():
            raise Exception(f"Expected output file not found: {temp_output_path}")

        shutil.move(str(temp_output_path), str(final_output_path))

        # Copy metadata from source clip if exists
        info_json = video_dir / f"{stem}_info.json"
        info_txt = video_dir / f"{stem}_info.txt"
        new_stem = final_filename.replace('.mp4', '')
        if info_json.exists():
            shutil.copy2(str(info_json), str(video_dir / f"{new_stem}_info.json"))
        elif info_txt.exists():
            shutil.copy2(str(info_txt), str(video_dir / f"{new_stem}_info.txt"))

        await manager.broadcast(
            {'type': 'progress', 'stage': 'complete', 'message': 'Silence removal complete!'},
            target_client_id=client_id
        )

    except Exception as e:
        import traceback
        traceback.print_exc()
        await broadcast_log(f"[ERROR] {str(e)}")
        await manager.broadcast(
            {'type': 'progress', 'stage': 'error', 'message': f"Silence removal failed: {str(e)}"},
            target_client_id=client_id
        )

@router.post("/api/workflow3/run/{project}/{format}/{filename}")
async def run_workflow3(
    project: str,
    format: str,
    filename: str,
    background_tasks: BackgroundTasks,
    client_id: str = Form(...),
    min_silence_len: int = Form(500),
    keep_silence_len: int = Form(100),
):
    try:
        TEMP_DIR.mkdir(parents=True, exist_ok=True)
        background_tasks.add_task(
            execute_workflow3,
            project, format, filename, client_id,
            min_silence_len, keep_silence_len
        )
        return {"success": True, "message": "Workflow 3 started"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
