import os
import sys
import shutil
import asyncio
from fastapi import APIRouter, HTTPException, BackgroundTasks, Form, UploadFile, File
from backend.core.constants import BASE_DIR, TEMP_DIR
from backend.core.connection_manager import manager

router = APIRouter()

async def execute_workflow(
    project: str,
    format: str,
    filename: str,
    client_id: str,
    second_media_path: str,
    main_position: str,
    text: str,
    watermark_text: str,
    watermark_size: int,
    watermark_alpha: float,
    watermark_top: int,
    watermark_right: int,
):
    try:
        upload_dir = BASE_DIR / "ToUpload"
        video_dir = upload_dir / project / format
        main_video_path = video_dir / filename

        if not main_video_path.exists():
            raise Exception(f"Main video not found: {main_video_path}")

        workflow_script = BASE_DIR / "backend" / "videoprocessor" / "workflow.py"
        
        # Build a unique output filename based on stem + timestamp
        import time
        timestamp = int(time.time())
        stem = main_video_path.stem
        final_filename = f"{stem}_workflow_{timestamp}.mp4"
        final_output_path = video_dir / final_filename
        
        # Temp output for the script
        temp_output_path = TEMP_DIR / final_filename
        
        cmd = [
            sys.executable, str(workflow_script),
            "--main", str(main_video_path),
            "--second", str(second_media_path),
            "--main-position", main_position,
            "--text", text,
            "--watermark-text", watermark_text,
            "--watermark-size", str(watermark_size),
            "--watermark-alpha", str(watermark_alpha),
            "--watermark-top", str(watermark_top),
            "--watermark-right", str(watermark_right),
            "--output", str(temp_output_path)
        ]

        await manager.broadcast({
            'type': 'log',
            'line': f"> Starting workflow for {filename}...\n"
        }, target_client_id=client_id)

        # Run subprocess
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
                    
                    if r_idx != -1 and n_idx != -1:
                        sep_idx = min(r_idx, n_idx)
                    else:
                        sep_idx = r_idx if r_idx != -1 else n_idx
                        
                    line = buffer[:sep_idx].strip()
                    buffer = buffer[sep_idx+1:]
                    
                    if line:
                        print(f"[WORKFLOW] {line}")
                        await manager.broadcast({
                            'type': 'log',
                            'line': line
                        }, target_client_id=client_id)
            
            # Drain any remaining buffer
            if buffer.strip():
                print(f"[WORKFLOW] {buffer.strip()}")
                await manager.broadcast({
                    'type': 'log',
                    'line': buffer.strip()
                }, target_client_id=client_id)

        await asyncio.gather(
            stream_output(process.stdout),
            stream_output(process.stderr)
        )

        returncode = await process.wait()

        if returncode != 0:
            raise Exception(f"Workflow script failed with return code {returncode}")

        # Move to original directory
        if not temp_output_path.exists():
            raise Exception(f"Expected output file not found: {temp_output_path}")

        shutil.move(str(temp_output_path), str(final_output_path))

        # Copy metadata — name matches the timestamped video
        info_json = video_dir / f"{stem}_info.json"
        info_txt = video_dir / f"{stem}_info.txt"
        new_stem = final_filename.replace('.mp4', '')
        
        if info_json.exists():
            new_info = video_dir / f"{new_stem}_info.json"
            shutil.copy2(str(info_json), str(new_info))
        elif info_txt.exists():
            new_info = video_dir / f"{new_stem}_info.txt"
            shutil.copy2(str(info_txt), str(new_info))

        # Cleanup second media
        try:
            os.remove(second_media_path)
        except OSError:
            pass

        await manager.broadcast({
            'type': 'progress',
            'stage': 'complete',
            'message': 'Workflow complete!'
        }, target_client_id=client_id)

    except Exception as e:
        import traceback
        traceback.print_exc()
        await manager.broadcast({
            'type': 'log',
            'line': f"[ERROR] {str(e)}"
        }, target_client_id=client_id)
        
        await manager.broadcast({
            'type': 'progress',
            'stage': 'error',
            'message': f"Workflow failed: {str(e)}"
        }, target_client_id=client_id)

@router.post("/api/workflow/run/{project}/{format}/{filename}")
async def run_workflow(
    project: str,
    format: str,
    filename: str,
    background_tasks: BackgroundTasks,
    client_id: str = Form(...),
    second_media: UploadFile = File(...),
    main_position: str = Form(...),
    text: str = Form(""),
    watermark_text: str = Form("@MrSinghExperience"),
    watermark_size: int = Form(45),
    watermark_alpha: float = Form(0.6),
    watermark_top: int = Form(100),
    watermark_right: int = Form(40),
):
    try:
        TEMP_DIR.mkdir(parents=True, exist_ok=True)
        _, ext = os.path.splitext(second_media.filename or "file.tmp")
        temp_second = TEMP_DIR / f"second_media_{client_id}{ext}"
        
        with open(temp_second, "wb") as buffer:
            shutil.copyfileobj(second_media.file, buffer)

        background_tasks.add_task(
            execute_workflow,
            project,
            format,
            filename,
            client_id,
            str(temp_second),
            main_position,
            text,
            watermark_text,
            watermark_size,
            watermark_alpha,
            watermark_top,
            watermark_right
        )

        return {"success": True, "message": "Workflow started in background"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
