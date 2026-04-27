import os
import asyncio
import datetime
from pathlib import Path
from fastapi import APIRouter, BackgroundTasks, Form, HTTPException
from backend.videoprocessor.transcriber import AudioTranscriber
from backend.videoprocessor.subtitle_burner import SubtitleBurner
from backend.routes.websocket import manager

router = APIRouter()

from backend.core.constants import BASE_DIR, TEMP_DIR, CLIPS_DIR

# Keep WORKSPACE_DIR for env compat if needed by other logic, but use shared CLIPS_DIR
WORKSPACE_DIR = os.environ.get("WORKSPACE_DIR", str(BASE_DIR))

async def execute_transcriber_workflow(
    project: str,
    format: str,
    filename: str,
    client_id: str,
    font_family: str,
    font_size: int,
    vertical_position: int,
    words_per_caption: int,
    spoken_word_color: str,
    other_words_color: str,
    bg_color: str,
    use_background_box: bool,
    outline_color: str,
    outline_width: float
):
    from backend.core.constants import BASE_DIR
    upload_dir = BASE_DIR / "ToUpload"
    source_path = upload_dir / project / format / filename

    if not source_path.exists():
        # Fallback to local workspace clips if not in ToUpload
        source_path = CLIPS_DIR / project / format / filename

    if not source_path.exists():
        await manager.broadcast(
            {'type': 'progress', 'stage': 'error', 'message': f"Source not found: {source_path}"},
            target_client_id=client_id
        )
        return

    async def broadcast_log(msg: str):
        await manager.broadcast(
            {'type': 'log', 'workflow': 'transcriber', 'message': msg},
            target_client_id=client_id
        )

    try:
        await broadcast_log(f"\n[{datetime.datetime.now().strftime('%H:%M:%S')}] Started Transcriber workflow for {filename}")
        
        # 1. Transcribe the Video
        transcriber = AudioTranscriber()
        def transcribe_progress(data):
            # We can broadcast transcribe progress if needed
            asyncio.run_coroutine_threadsafe(
                broadcast_log(f"[Whisper] {data.get('message')} ({data.get('percent')}%)"),
                asyncio.get_event_loop()
            )

        transcript_result = transcriber.transcribe(str(source_path), progress_callback=transcribe_progress)
        
        if not transcript_result.get('success', False):
            raise Exception(f"Transcription failed: {transcript_result.get('error')}")

        words = []
        for segment in transcript_result.get('segments', []):
            for word in segment.get('words', []):
                words.append(word)

        if not words:
            await broadcast_log("[WARNING] No speech detected in the audio track.")
            timestamp_suffix = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            output_name = f"{source_path.stem}_transcribed_{timestamp_suffix}.mp4"
            output_path = source_path.parent / output_name
            import shutil
            shutil.copy2(source_path, output_path)
            
            # Copy metadata from source clip
            stem = source_path.stem
            info_json = source_path.parent / f"{stem}_info.json"
            info_txt = source_path.parent / f"{stem}_info.txt"
            new_stem = output_path.stem
            
            if info_json.exists():
                shutil.copy2(str(info_json), str(source_path.parent / f"{new_stem}_info.json"))
            elif info_txt.exists():
                shutil.copy2(str(info_txt), str(source_path.parent / f"{new_stem}_info.txt"))
            
            await manager.broadcast(
                {'type': 'progress', 'stage': 'complete', 'message': "Processed (No Speech Detected)", 'output_file': output_name},
                target_client_id=client_id
            )
            return

        await broadcast_log(f"Detected {len(words)} words. Initializing subtitle burner...")

        # 2. Burn Subtitles
        import cv2
        cap = cv2.VideoCapture(str(source_path))
        if cap.isOpened():
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            cap.release()
        else:
            width, height = 1920, 1080

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
        TEMP_DIR.mkdir(parents=True, exist_ok=True)
        timestamp_suffix = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        temp_ass_path = TEMP_DIR / f"temp_ass_{timestamp_suffix}.ass"
        
        output_name = f"{source_path.stem}_transcribed_{timestamp_suffix}.mp4"
        output_path = source_path.parent / output_name

        await broadcast_log("Generating ASS Subtitles...")
        burner.create_ass_subtitles(
            words=words,
            output_path=str(temp_ass_path),
            clip_start_time=0,
            video_width=width,
            video_height=height
        )

        await broadcast_log("Rendering video with FFMPEG. This may take a while...")
        
        result = burner.burn_captions(
            video_path=str(source_path),
            subtitle_path=str(temp_ass_path),
            output_path=str(output_path)
        )

        if result.get('success'):
            await broadcast_log("Successfully burned subtitles!")
            
            # Copy metadata from source clip
            import shutil
            stem = source_path.stem
            info_json = source_path.parent / f"{stem}_info.json"
            info_txt = source_path.parent / f"{stem}_info.txt"
            new_stem = output_path.stem
            
            if info_json.exists():
                shutil.copy2(str(info_json), str(source_path.parent / f"{new_stem}_info.json"))
            elif info_txt.exists():
                shutil.copy2(str(info_txt), str(source_path.parent / f"{new_stem}_info.txt"))
            
            await manager.broadcast(
                {'type': 'progress', 'stage': 'complete', 'message': "Workflow finished", 'output_file': output_name},
                target_client_id=client_id
            )
        else:
            raise Exception(f"Subtitle rendering failed: {result.get('error')}")

        try:
            if temp_ass_path.exists():
                os.remove(temp_ass_path)
        except OSError:
            pass

    except Exception as e:
        import traceback
        traceback.print_exc()
        await broadcast_log(f"[ERROR] {str(e)}")
        await manager.broadcast(
            {'type': 'progress', 'stage': 'error', 'message': f"Workflow failed: {str(e)}"},
            target_client_id=client_id
        )

@router.post("/api/workflow/transcriber/run/{project}/{format}/{filename}")
async def run_workflow_transcriber(
    project: str,
    format: str,
    filename: str,
    background_tasks: BackgroundTasks,
    client_id: str = Form(...),
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
        background_tasks.add_task(
            execute_transcriber_workflow,
            project, format, filename, client_id,
            font_family, font_size, vertical_position, words_per_caption,
            spoken_word_color, other_words_color, bg_color, use_background_box,
            outline_color, outline_width
        )
        return {"success": True, "message": "Transcriber workflow started"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
