import os
import uuid
import json
import asyncio
from typing import Optional
from fastapi import APIRouter, BackgroundTasks, Form, UploadFile, File, HTTPException, Request
from fastapi.responses import FileResponse
from backend.core.constants import TEMP_DIR
from backend.videoprocessor.workflow4 import execute_workflow4

router = APIRouter()

@router.post("/api/workflow4/tts-sample")
async def generate_tts_sample(
    text: str = Form("This is example voice"),
    voice: str = Form("am_echo"),
    speed: float = Form(1.0)
):
    try:
        from backend.videoprocessor.tts import generate_tts_file
        TEMP_DIR.mkdir(parents=True, exist_ok=True)
        # Use single temp file or uuid so it doesn't leak massively
        out_path = str(TEMP_DIR / f"tts_sample_{uuid.uuid4().hex[:8]}.wav")
        generate_tts_file(text, out_path, speaker=voice, speed=speed)
        return FileResponse(out_path, media_type="audio/wav")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/api/workflow4/run/{project}/{format}/{filename}")
async def run_workflow4(
    project: str,
    format: str,
    filename: str,
    background_tasks: BackgroundTasks,
    request: Request,
    client_id: str = Form(...),
    text_input: str = Form(""),
    audio_file: Optional[UploadFile] = File(None),
    use_tts: bool = Form(True),
    tts_voice: str = Form("am_echo"),
    tts_speed: float = Form(1.0),
    bg_frame_percent: float = Form(0.0),
    bg_blur: float = Form(0.0),
    media_list: str = Form("[]"),
    fill_screen: bool = Form(True),
    global_scale: float = Form(1.0),
    sticker: Optional[UploadFile] = File(None),
    sticker_x: int = Form(50),
    sticker_y: int = Form(50),
    sticker_scale: float = Form(1.0),
    burn_captions: bool = Form(True),
    generate_separately: bool = Form(False),
    
    # Caption styling (like w3)
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

        # Handle dynamic media files from multi-part form
        form_data = await request.form()
        media_list_parsed = json.loads(media_list)
        
        with open("/tmp/w4_debug.log", "w") as debug_log:
            debug_log.write(f"W4 RUN: media_list_parsed count={len(media_list_parsed)}\n")
            debug_log.write(f"Form keys: {list(form_data.keys())}\n")

            # Save uploaded media files and update paths in media_list_parsed
            for idx in range(len(media_list_parsed)):
                field_name = f"media_{idx}"
                up_file = form_data.get(field_name)
                debug_log.write(f"Checking {field_name}: {'found' if up_file else 'NOT FOUND'}\n")
                
                if up_file is not None and hasattr(up_file, 'filename') and up_file.filename:
                    _, ext = os.path.splitext(up_file.filename)
                    save_path = str(TEMP_DIR / f"w4_media_{idx}_{uuid.uuid4().hex[:8]}{ext}")
                    try:
                        content = await up_file.read()
                        with open(save_path, "wb") as f:
                            f.write(content)
                        media_list_parsed[idx]['path'] = save_path
                        debug_log.write(f"REPLACED {field_name} path with {save_path}\n")
                    except Exception as e:
                        debug_log.write(f"Error saving {field_name}: {str(e)}\n")
                else:
                    debug_log.write(f"Ignoring {field_name} - not an UploadFile or empty filename\n")
            
            debug_log.write(f"FINAL media_list for execute: {media_list_parsed}\n")

        audio_path = None
        if audio_file and audio_file.filename:
            _, ext = os.path.splitext(audio_file.filename)
            audio_path = str(TEMP_DIR / f"w4_audio_{uuid.uuid4().hex[:8]}{ext}")
            with open(audio_path, "wb") as f:
                f.write(await audio_file.read())
        
        sticker_path = None
        if sticker and sticker.filename:
            _, ext = os.path.splitext(sticker.filename)
            sticker_path = str(TEMP_DIR / f"w4_sticker_{uuid.uuid4().hex[:8]}{ext}")
            with open(sticker_path, "wb") as f:
                f.write(await sticker.read())
                
        caption_config = {
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

        background_tasks.add_task(
            execute_workflow4,
            project, format, filename, client_id,
            text_input, audio_path, use_tts, tts_voice, tts_speed,
            bg_frame_percent, bg_blur,
            media_list_parsed, fill_screen, global_scale,
            sticker_path, sticker_x, sticker_y, sticker_scale,
            burn_captions, caption_config,
            generate_separately
        )

        return {"success": True, "message": "Workflow 4 started"}
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
