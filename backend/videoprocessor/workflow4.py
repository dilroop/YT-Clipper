import os
import asyncio
import datetime
import json
import uuid
from pathlib import Path
from backend.core.constants import BASE_DIR, TEMP_DIR, CLIPS_DIR, UPLOAD_DIR
from backend.routes.websocket import manager

async def execute_workflow4(
    project: str, format: str, filename: str, client_id: str,
    text_input: str, audio_file_path: str, use_tts: bool, tts_voice: str, tts_speed: float,
    bg_frame_percent: float, bg_blur: float,
    media_list: list, fill_screen: bool, global_scale: float,
    sticker_path: str, sticker_x: int, sticker_y: int, sticker_scale: float,
    burn_captions: bool,
    caption_config: dict,
    generate_separately: bool
):
    source_path = UPLOAD_DIR / project / format / filename

    if not source_path.exists():
        source_path = CLIPS_DIR / project / format / filename

    if not source_path.exists():
        await manager.broadcast({'type': 'progress', 'stage': 'error', 'message': f"Source not found: {source_path}"}, target_client_id=client_id)
        return

    async def broadcast_log(msg: str):
        await manager.broadcast({'type': 'log', 'workflow': 'w4', 'message': msg}, target_client_id=client_id)

    try:
        await broadcast_log(f"\n[{datetime.datetime.now().strftime('%H:%M:%S')}] Started W4 TTS Hook for {filename}")
        
        # 1. Resolve Audio Content
        import soundfile as sf
        hook_audio_path = audio_file_path
        if use_tts and text_input.strip():
            await broadcast_log(f"> Generating TTS using Kokoro ({tts_voice})")
            from backend.videoprocessor.tts import generate_tts_file
            hook_audio_path = str(TEMP_DIR / f"w4_tts_{uuid.uuid4().hex[:8]}.wav")
            generate_tts_file(text_input, hook_audio_path, speaker=tts_voice, speed=tts_speed)
        
        if not hook_audio_path or not os.path.exists(hook_audio_path):
            raise Exception("No valid audio source found for TTS Hook.")
            
        with sf.SoundFile(hook_audio_path) as f:
            audio_duration = f.frames / f.samplerate
        await broadcast_log(f"> Hook audio duration: {audio_duration:.2f} seconds")

        # 2. Extract Metadata via ffprobe
        probe_cmd = [
            "ffprobe", "-v", "error", "-show_entries", 
            "stream=codec_type,width,height,r_frame_rate,pix_fmt,sample_rate,channels",
            "-of", "json", str(source_path)
        ]
        import subprocess
        probe_output = subprocess.check_output(probe_cmd).decode('utf-8')
        probe_data = json.loads(probe_output)
        
        v_stream = next(s for s in probe_data['streams'] if s['codec_type'] == 'video')
        a_stream = next((s for s in probe_data['streams'] if s['codec_type'] == 'audio'), None)
        
        vid_width = v_stream['width']
        vid_height = v_stream['height']
        fps = v_stream['r_frame_rate']
        pix_fmt = v_stream.get('pix_fmt', 'yuv420p')
        
        # Audio matching
        sample_rate = a_stream['sample_rate'] if a_stream else "44100"
        channels = a_stream['channels'] if a_stream else "2"

        # Extract Background Frame
        import cv2
        cap = cv2.VideoCapture(str(source_path))
        if not cap.isOpened():
            raise Exception("Failed to open source video for frame extraction.")
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        target_frame = int((bg_frame_percent / 100.0) * total_frames)
        cap.set(cv2.CAP_PROP_POS_FRAMES, target_frame)
        ret, frame = cap.read()
        cap.release()
        if not ret:
            raise Exception(f"Failed to read frame {target_frame}")
        bg_frame_path = str(TEMP_DIR / f"w4_bg_{uuid.uuid4().hex[:8]}.png")
        cv2.imwrite(bg_frame_path, frame)

        # 3. Create Slide Show Config
        import subprocess
        
        # Build complex FFMPEG filter
        inputs = []
        filter_complex = []
        
        # Input 0: Background
        inputs.extend(["-loop", "1", "-t", str(audio_duration), "-i", bg_frame_path])
        bg_filter = f"[0:v]scale={vid_width}:{vid_height}"
        if bg_blur > 0:
            bg_filter += f",gblur=sigma={bg_blur}"
        filter_complex.append(f"{bg_filter}[bg];")
        
        # Input 1: Audio
        inputs.extend(["-i", hook_audio_path])
        
        current_input_idx = 2
        last_overlay_label = "[bg]"
        
        # Handle Slideshow Overlays
        # For simplicity, if multiple media files, we generate sequential overlays
        if media_list:
            total_media_time = sum([m.get('duration', 3.0) for m in media_list])
            # Loop media if it's less than audio duration
            repeats = int(audio_duration / total_media_time) + 1 if total_media_time > 0 else 1
            
            for rep in range(repeats):
                t_offset = rep * total_media_time
                for m in media_list:
                    if t_offset > audio_duration: break
                    dur = m.get('duration', 3.0)
                    t_end = min(t_offset + dur, audio_duration)
                    
                    m_path = m['path']
                    with open("/tmp/w4_debug.log", "a") as debug_log:
                        debug_log.write(f"  Loop Item: path={m_path} dur={dur} t={t_offset}-{t_end}\n")
                    
                    if m_path.startswith('blob:'):
                        with open("/tmp/w4_debug.log", "a") as debug_log: debug_log.write("    SKIPPED: is blob\n")
                        continue
                    # Use absolute paths if relative
                    if not m_path.startswith('/'): m_path = str(BASE_DIR / m_path.lstrip('/'))
                    
                    if not os.path.exists(m_path):
                        with open("/tmp/w4_debug.log", "a") as debug_log: debug_log.write(f"    SKIPPED: file not found at {m_path}\n")
                        continue
                    
                    with open("/tmp/w4_debug.log", "a") as debug_log: debug_log.write("    FOUND: adding to inputs\n")
                    
                    is_vid = m.get('isVideo', False)
                    if is_vid:
                        inputs.extend(["-t", str(dur), "-i", m_path])
                    else:
                        inputs.extend(["-loop", "1", "-t", str(dur), "-i", m_path])
                    
                    scale_val = global_scale * m.get('scale', 1.0)
                    if fill_screen:
                        v_filter = f"[{current_input_idx}:v]scale={vid_width}:{vid_height}:force_original_aspect_ratio=increase,crop={vid_width}:{vid_height}[med{current_input_idx}];"
                    else:
                        v_filter = f"[{current_input_idx}:v]scale=iw*{scale_val}:ih*{scale_val}[med{current_input_idx}];"
                    
                    filter_complex.append(v_filter)
                    
                    # Overlay it
                    new_label = f"[ov{current_input_idx}]"
                    overlay_cmd = f"{last_overlay_label}[med{current_input_idx}]overlay=(W-w)/2:(H-h)/2:enable='between(t,{t_offset},{t_end})'{new_label};"
                    filter_complex.append(overlay_cmd)
                    
                    last_overlay_label = new_label
                    current_input_idx += 1
                    t_offset = t_end

        # Handle Sticker Overlay
        if sticker_path and os.path.exists(sticker_path):
            inputs.extend(["-loop", "1", "-t", str(audio_duration), "-i", sticker_path])
            s_scaled = f"[s_scaled{current_input_idx}]"
            filter_complex.append(f"[{current_input_idx}:v]scale=iw*{sticker_scale}:ih*{sticker_scale}{s_scaled};")
            s_label = f"[sticker_out]"
            # Center anchor math: (W * pos/100) - (w/2)
            filter_complex.append(f"{last_overlay_label}{s_scaled}overlay=(W*{sticker_x}/100)-(w/2):(H*{sticker_y}/100)-(h/2){s_label};")
            last_overlay_label = s_label
            current_input_idx += 1

        base_vid_path = str(TEMP_DIR / f"w4_base_{uuid.uuid4().hex[:8]}.mp4")
        
        ffmpeg_cmd = [
            "ffmpeg", "-y", "-r", str(fps)
        ] + inputs + [
            "-filter_complex", "".join(filter_complex).rstrip(";"),
            "-map", f"{last_overlay_label}",
            "-map", "1:a",
            "-c:v", "libx264", "-c:a", "aac",
            "-ac", str(channels), "-ar", str(sample_rate),
            "-pix_fmt", pix_fmt,
            "-r", str(fps),
            "-t", str(audio_duration),
            base_vid_path
        ]
        
        with open("/tmp/w4_debug.log", "a") as debug_log:
            debug_log.write(f"FFMPEG COMMAND: {' '.join(ffmpeg_cmd)}\n")

        await broadcast_log("Rendering base Hook Sequence via FFMPEG...")
        process = await asyncio.create_subprocess_exec(
            *ffmpeg_cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        out, err = await process.communicate()
        if process.returncode != 0:
            raise Exception(f"FFMPEG hook generation failed: {err.decode('utf-8')}")

        hook_seq_path = base_vid_path

        # 4. Transcribe and Burn Subtitles
        if burn_captions:
            await broadcast_log("> Transcribing hook audio for subtitles...")
            from backend.videoprocessor.transcriber import AudioTranscriber
            from backend.videoprocessor.subtitle_burner import SubtitleBurner
            
            transcriber = AudioTranscriber()
            t_res = transcriber.transcribe(hook_audio_path)
            words = []
            for seg in t_res.get('segments', []):
                for w in seg.get('words', []): words.append(w)
                
            if words:
                await broadcast_log(f"> Detected {len(words)} words in hook.")
                sub_burner = SubtitleBurner(config=caption_config)
                ass_path = str(TEMP_DIR / f"w4_ass_{uuid.uuid4().hex[:8]}.ass")
                sub_burner.create_ass_subtitles(words, ass_path, 0, vid_width, vid_height)
                
                hook_sub_path = str(TEMP_DIR / f"w4_sub_{uuid.uuid4().hex[:8]}.mp4")
                burn_res = sub_burner.burn_captions(base_vid_path, ass_path, hook_sub_path)
                if burn_res.get('success'):
                    hook_seq_path = hook_sub_path
                try:
                    os.remove(ass_path)
                except:
                    pass

        timestamp_suffix = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        
        if generate_separately:
            await broadcast_log("Running in 'Generate Separately' mode.")
            output_name = f"{source_path.stem}_hook_{timestamp_suffix}.mp4"
            final_output_path = source_path.parent / output_name
            import shutil
            shutil.copy2(hook_seq_path, str(final_output_path))
        else:
            await broadcast_log("Merging sequence via Concat...")
            concat_txt = TEMP_DIR / f"concat_{uuid.uuid4().hex[:8]}.txt"
            with open(concat_txt, "w") as f:
                f.write(f"file '{hook_seq_path}'\n")
                f.write(f"file '{str(source_path)}'\n")
                
            output_name = f"{source_path.stem}_w4_{timestamp_suffix}.mp4"
            final_output_path = source_path.parent / output_name
            
            concat_cmd = [
                "ffmpeg", "-y", "-f", "concat", "-safe", "0",
                "-i", str(concat_txt),
                "-c", "copy",
                str(final_output_path)
            ]
            concat_proc = await asyncio.create_subprocess_exec(
                *concat_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            c_out, c_err = await concat_proc.communicate()
            if concat_proc.returncode != 0:
                # If copy fails due to mismatched streams, fallback to re-encode
                await broadcast_log("Stream mismatch detected, falling back to soft re-encode...")
                concat_cmd = [
                    "ffmpeg", "-y", "-f", "concat", "-safe", "0",
                    "-i", str(concat_txt),
                    "-c:v", "libx264", "-c:a", "aac",
                    str(final_output_path)
                ]
                concat_proc2 = await asyncio.create_subprocess_exec(*concat_cmd)
                await concat_proc2.communicate()
            try:
                os.remove(concat_txt)
            except:
                pass
                
        # Copy original metadata
        import shutil
        stem = source_path.stem
        info_json = source_path.parent / f"{stem}_info.json"
        info_txt = source_path.parent / f"{stem}_info.txt"
        new_stem = final_output_path.stem
        
        if info_json.exists(): shutil.copy2(str(info_json), str(source_path.parent / f"{new_stem}_info.json"))
        elif info_txt.exists(): shutil.copy2(str(info_txt), str(source_path.parent / f"{new_stem}_info.txt"))
            
        await broadcast_log("Workflow 4 complete!")
        await manager.broadcast(
            {'type': 'progress', 'stage': 'complete', 'message': "Workflow 4 finished", 'output_file': output_name},
            target_client_id=client_id
        )

    except Exception as e:
        import traceback
        traceback.print_exc()
        await broadcast_log(f"[ERROR] {str(e)}")
        await manager.broadcast(
            {'type': 'progress', 'stage': 'error', 'message': f"Workflow 4 failed: {str(e)}"},
            target_client_id=client_id
        )
