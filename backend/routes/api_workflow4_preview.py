import os
import asyncio
import datetime
import json
import uuid
from typing import Optional
from pathlib import Path
from fastapi import APIRouter, Form, UploadFile, File, BackgroundTasks, Request
from fastapi.responses import FileResponse
from backend.core.constants import BASE_DIR, TEMP_DIR, CLIPS_DIR, UPLOAD_DIR
from backend.videoprocessor.subtitle_burner import SubtitleBurner

router = APIRouter()

@router.post("/api/workflow4/preview/{project}/{format}/{filename}")
async def generate_workflow4_preview(
    request: Request,
    project: str,
    format: str,
    filename: str,
    background_tasks: BackgroundTasks,
    text_input: str = Form(""),
    use_tts: bool = Form(True),
    bg_frame_percent: float = Form(0.0),
    bg_blur: float = Form(0.0),
    media_list: str = Form("[]"),
    fill_screen: bool = Form(True),
    global_scale: float = Form(1.0),
    sticker: UploadFile = File(None),
    sticker_x: int = Form(50),
    sticker_y: int = Form(50),
    sticker_scale: float = Form(1.0),
    burn_captions: bool = Form(True),
    
    # Caption styling 
    font_family: str = Form("Arial"),
    font_size: int = Form(80),
    vertical_position: int = Form(80),
    words_per_caption: int = Form(5),
    spoken_word_color: str = Form("#FFFF00"),
    other_words_color: str = Form("#FFFFFF"),
    bg_color: str = Form("#000000"),
    use_background_box: bool = Form(False),
    outline_color: str = Form("#000000"),
    outline_width: float = Form(3.0),
    media_file: Optional[UploadFile] = File(None)
):
    try:
        TEMP_DIR.mkdir(parents=True, exist_ok=True)

        video_dir = UPLOAD_DIR / project / format
        main_video_path = video_dir / filename

        if not main_video_path.exists():
            main_video_path = CLIPS_DIR / project / format / filename
            if not main_video_path.exists():
                raise Exception("Missing preview source video")

        # 1. Grab Frame using FFmpeg for reliable seeking
        # Get duration first
        import subprocess
        probe_cmd = [
            "ffprobe", "-v", "error", "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1", str(main_video_path)
        ]
        duration = float(subprocess.check_output(probe_cmd).decode().strip())
        seek_time = (bg_frame_percent / 100.0) * duration
        
        bg_frame_path = str(TEMP_DIR / f"w4_prev_bg_{uuid.uuid4().hex[:8]}.png")
        extract_cmd = [
            "ffmpeg", "-y", "-ss", str(seek_time), "-i", str(main_video_path),
            "-frames:v", "1", "-update", "1", bg_frame_path
        ]
        subprocess.run(extract_cmd, check=True, capture_output=True)
        
        # Determine dimensions from extracted frame
        import cv2
        frame = cv2.imread(bg_frame_path)
        if frame is None:
            raise Exception("Failed to read extracted preview frame")
        vid_height, vid_width = frame.shape[:2]

        inputs = ["-i", bg_frame_path]
        bg_filter = f"[0:v]scale={vid_width}:{vid_height}"
        if bg_blur > 0:
            bg_filter += f",gblur=sigma={bg_blur}"
        filter_complex = [f"{bg_filter}[bg];"]
        
        current_input_idx = 1
        last_overlay_label = "[bg]"

        # Try to find media_0 for the preview
        form_data = await request.form()
        media_list_parsed = json.loads(media_list)
        preview_media_path = None
        
        with open("/tmp/w4_debug_preview.log", "w") as debug_log:
            debug_log.write(f"W4 PREVIEW: Form keys: {list(form_data.keys())}\n")
            media_0 = form_data.get("media_0")

        if media_0 is not None and hasattr(media_0, 'filename') and media_0.filename:
            _, ext = os.path.splitext(media_0.filename)
            preview_media_path = str(TEMP_DIR / f"w4_prev_med_{uuid.uuid4().hex[:8]}{ext}")
            with open(preview_media_path, "wb") as f:
                f.write(await media_0.read())
        else:
            # Fallback to checking media_list for local files
            media_list_parsed = json.loads(media_list)
            if media_list_parsed:
                m = media_list_parsed[0]
                m_path = m['path']
                if os.path.exists(m_path):
                     preview_media_path = m_path
                elif not m_path.startswith('blob:') and not m_path.startswith('/'):
                     possible_path = str(BASE_DIR / m_path.lstrip('/'))
                     if os.path.exists(possible_path):
                         preview_media_path = possible_path

        if preview_media_path:
            inputs.extend(["-i", preview_media_path])
            media_list_parsed = json.loads(media_list)
            m = media_list_parsed[0] if media_list_parsed else {}
            scale_val = global_scale * m.get('scale', 1.0)
            
            if fill_screen:
                v_filter = f"[{current_input_idx}:v]scale={vid_width}:{vid_height}:force_original_aspect_ratio=increase,crop={vid_width}:{vid_height}[med];"
            else:
                v_filter = f"[{current_input_idx}:v]scale=iw*{scale_val}:ih*{scale_val}[med];"
                
            filter_complex.append(v_filter)
            filter_complex.append(f"{last_overlay_label}[med]overlay=(W-w)/2:(H-h)/2[ov];")
            last_overlay_label = "[ov]"
            current_input_idx += 1
            
        sticker_path = None
        if sticker and sticker.filename:
            _, ext = os.path.splitext(sticker.filename)
            sticker_path = str(TEMP_DIR / f"w4_prev_st_{uuid.uuid4().hex[:8]}{ext}")
            with open(sticker_path, "wb") as f:
                f.write(await sticker.read())
            
            inputs.extend(["-i", sticker_path])
            s_scaled = f"[s_scaled{current_input_idx}]"
            filter_complex.append(f"[{current_input_idx}:v]scale=iw*{sticker_scale}:ih*{sticker_scale}{s_scaled};")
            filter_complex.append(f"{last_overlay_label}{s_scaled}overlay=(W*{sticker_x}/100)-(w/2):(H*{sticker_y}/100)-(h/2)[st];")
            last_overlay_label = "[st]"

        # Create base image preview
        base_prev_path = str(TEMP_DIR / f"w4_prev_base_{uuid.uuid4().hex[:8]}.png")
        ffmpeg_cmd = [
            "ffmpeg", "-y", "-v", "error"
        ] + inputs + [
            "-filter_complex", "".join(filter_complex).rstrip(";"),
            "-map", last_overlay_label,
            "-update", "1", "-frames:v", "1",
            base_prev_path
        ]
        
        proc = await asyncio.create_subprocess_exec(*ffmpeg_cmd, stderr=asyncio.subprocess.PIPE)
        stdout, stderr = await proc.communicate()
        if proc.returncode != 0:
             print(f"FFMPEG PREVIEW FAIL: {stderr.decode()}")
             raise Exception(f"FFMPEG Fail: {stderr.decode()}")
        
        if sticker_path:
            try: os.remove(sticker_path)
            except: pass

        if not burn_captions:
            return FileResponse(base_prev_path, media_type="image/png")

        # 3. Burn dummy captions onto the base image
        config = {
            'font_family': font_family, 'font_size': font_size,
            'vertical_position': vertical_position, 'words_per_caption': words_per_caption,
            'spoken_word_color': spoken_word_color, 'other_words_color': other_words_color,
            'bg_color': bg_color, 'use_background_box': use_background_box,
            'outline_color': outline_color, 'outline_width': outline_width
        }

        dummy_words = [
            {"word": "Let's", "start": 0.0, "end": 0.5},
            {"word": "generate", "start": 0.5, "end": 1.0},
            {"word": "an", "start": 1.0, "end": 1.5},
            {"word": "EXAMPLE", "start": 1.5, "end": 2.0},
            {"word": "hook!", "start": 2.0, "end": 2.5}
        ]

        sub_burner = SubtitleBurner(config=config)
        final_prev_path = str(TEMP_DIR / f"w4_prev_final_{uuid.uuid4().hex[:8]}.png")
        
        # Switch to PIL-based rendering for 100% font reliability in previews
        sub_burner.burn_preview_to_image(
            image_path=Path(base_prev_path),
            output_path=Path(final_prev_path),
            words=dummy_words,
            current_time=1.7
        )

        background_tasks.add_task(os.remove, base_prev_path)
        background_tasks.add_task(os.remove, bg_frame_path)
        if preview_media_path and "w4_prev_med_" in preview_media_path:
             background_tasks.add_task(os.remove, preview_media_path)

        if os.path.exists(final_prev_path):
            background_tasks.add_task(os.remove, final_prev_path)
            return FileResponse(final_prev_path, media_type="image/png")
        return FileResponse(base_prev_path, media_type="image/png")

    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"[PREVIEW ERROR] Workflow 4 failed: {str(e)}")
        raise Exception(f"W4 Preview Gen Failed: {str(e)}")
