import os
import asyncio
import traceback
from fastapi import APIRouter, HTTPException, BackgroundTasks
from backend.models.schemas import ProcessVideoRequest
from backend.utils.video_helpers import extract_video_id
from backend.core.config import get_config_with_defaults
from backend.core.executor import run_in_executor
from backend.core.connection_manager import manager
from backend.core.constants import TEMP_DIR

router = APIRouter()

async def _perform_video_processing(request: ProcessVideoRequest):
    """
    Background task to process video: download, analyze, clip, caption, and organize
    """
    # Import processing modules inside task to avoid circular imports
    from backend.downloader import VideoDownloader
    from backend.pytube_downloader import PytubeDownloader
    from backend.videoprocessor.transcriber import AudioTranscriber
    from backend.analyzer import SectionAnalyzer
    from backend.ai_analyzer import AIAnalyzer
    from backend.logger import app_logger
    from backend.videoprocessor.section_cutter import SectionCutter
    from backend.videoprocessor.subtitle_burner import SubtitleBurner
    from backend.videoprocessor.video_cropper import VideoCropper
    from backend.videoprocessor.watermarker import Watermarker
    from backend.file_manager import FileManager

    client_id = request.client_id
    loop = asyncio.get_running_loop()

    async def update_progress(data):
        await manager.broadcast({
            'type': 'progress',
            **data
        }, target_client_id=client_id)

    def update_progress_sync(data):
        """Thread-safe progress callback for subprocess operations"""
        try:
            asyncio.run_coroutine_threadsafe(update_progress(data), loop)
        except Exception as e:
            print(f"Progress update failed: {e}")

    try:
        video_id = extract_video_id(request.url)
        config = get_config_with_defaults()
        caption_config = config.get('caption_settings', {})
        watermark_config = config.get('watermark_settings', {})
        downloader_backend = config.get('downloader_backend', 'yt-dlp')

        if downloader_backend == 'pytube':
            downloader = PytubeDownloader()
        else:
            downloader = VideoDownloader()

        transcriber = AudioTranscriber(model_name="base")
        ai_validation = config.get('ai_validation', {})
        min_duration = ai_validation.get('min_clip_duration', 15)
        max_duration = ai_validation.get('max_clip_duration', 60)

        openai_api_key = os.getenv('OPENAI_API_KEY')

        # ── Determine which analyzer to use ──────────────────────────────────
        ai_settings = config.get('ai_settings', {})
        provider = (request.ai_provider or 'openai').lower()

        if provider == 'deepseek':
            ds_cfg = ai_settings.get('deepseek', {})
            ds_key = ds_cfg.get('api_key', '')
            if ds_key:
                from backend.deepseek_analyzer import DeepSeekAnalyzer
                analyzer = DeepSeekAnalyzer(
                    api_key=ds_key,
                    model=ds_cfg.get('model'),
                    temperature=float(ds_cfg.get('temperature')),
                    min_clip_duration=min_duration,
                    max_clip_duration=max_duration,
                )
            else:
                app_logger.analyze("⚠️ DeepSeek selected but no API key found — falling back to SectionAnalyzer")
                analyzer = SectionAnalyzer(min_clip_duration=min_duration, max_clip_duration=max_duration)
        else:
            oa_cfg = ai_settings.get('openai', {})
            oa_key = oa_cfg.get('api_key', '')
            if oa_key and oa_key.startswith('sk-'):
                analyzer = AIAnalyzer(
                    api_key=oa_key,
                    model=oa_cfg.get('model'),
                    temperature=float(oa_cfg.get('temperature')),
                    min_clip_duration=min_duration,
                    max_clip_duration=max_duration,
                )
            else:
                analyzer = SectionAnalyzer(min_clip_duration=min_duration, max_clip_duration=max_duration)

        cutter = SectionCutter()
        subtitle_burner = SubtitleBurner(caption_config)
        cropper = VideoCropper()
        watermarker = Watermarker(watermark_config)
        file_mgr = FileManager()

        # Step 1: Download
        await update_progress({'stage': 'downloading', 'percent': 5, 'message': 'Downloading video...'})
        download_result = await run_in_executor(downloader.download_video, request.url, update_progress_sync)
        if not download_result['success']:
            raise Exception(f"Download failed: {download_result.get('error')}")

        video_path = download_result['video_path']
        video_info = {
            'video_id': download_result['video_id'],
            'title': download_result['title'],
            'channel': download_result['channel'],
            'description': download_result['description'],
            'url': request.url
        }

        # Step 2 & 3: Clips
        interesting_clips = []
        if request.preanalyzed_clips:
            await update_progress({'stage': 'clipping', 'percent': 15, 'message': 'Preparing selected clips...'})
            for clip_data in request.preanalyzed_clips:
                if 'parts' in clip_data and len(clip_data['parts']) > 1:
                    interesting_clips.append({
                        'title': clip_data.get('title', 'Multi-Part Clip'),
                        'reason': clip_data.get('reason', clip_data.get('explanation', '')),
                        'keywords': clip_data.get('keywords', []),
                        'parts': clip_data['parts']
                    })
                else:
                    interesting_clips.append({
                        'start': clip_data['start'],
                        'end': clip_data['end'],
                        'text': clip_data.get('text', clip_data.get('explanation', '')),
                        'title': clip_data.get('title', 'Interesting Clip'),
                        'reason': clip_data.get('reason', clip_data.get('explanation', '')),
                        'keywords': clip_data.get('keywords', []),
                        'words': clip_data.get('words', [])
                    })
            audio_path = None
        else:
            await update_progress({'stage': 'transcribing', 'percent': 15, 'message': 'Transcribing audio...'})
            transcript_result = transcriber.transcribe(video_path, update_progress_sync)
            if not transcript_result['success']: raise Exception(transcript_result['error'])
            segments = transcript_result['segments']
            audio_path = transcript_result.get('audio_path')
            provider_name = getattr(analyzer, 'provider_name', 'Basic AI')
            await update_progress({'stage': 'analyzing', 'percent': 35, 'message': f'Finding clips with {provider_name}...'})
            if isinstance(analyzer, AIAnalyzer):
                interesting_clips = analyzer.find_interesting_clips(segments, num_clips=5, video_info=video_info, strategy=request.ai_strategy or "viral-moments")
            else:
                interesting_clips = analyzer.find_interesting_clips(segments, num_clips=5)
                interesting_clips = [analyzer.adjust_clip_timing(clip) for clip in interesting_clips]

            if request.selected_clips is not None:
                selected_indices = {int(x) if isinstance(x, str) and x.isdigit() else x for x in request.selected_clips}
                interesting_clips = [clip for i, clip in enumerate(interesting_clips) if i in selected_indices]
            else:
                interesting_clips = [clip for clip in interesting_clips if clip.get('validation_level', 'valid') != 'error']
        
        print(f"[DEBUG] Found {len(interesting_clips)} interesting clips to process")
        if not interesting_clips:
            raise Exception("No interesting clips found or selected for processing.")

        # Step 4: Folder
        project_folder = file_mgr.create_project_folder(video_info['title'])

        # Step 5: Process
        await update_progress({'stage': 'clipping', 'percent': 45, 'message': 'Creating clips...'})
        temp_files = []
        if audio_path: temp_files.append(audio_path)
        processed_clips = []

        for i, clip in enumerate(interesting_clips):
            clip_progress = 45 + (i / len(interesting_clips)) * 45
            await update_progress({'stage': 'clipping', 'percent': clip_progress, 'message': f'Processing clip {i+1}/{len(interesting_clips)}...'})

            # Create a unique temporary path for this clip to avoid collisions
            # Using mills to be extremely safe against overwriting
            ts_ms = int(asyncio.get_event_loop().time() * 1000)
            temp_out = TEMP_DIR / f"processed_clip_{i+1}_{ts_ms}.mp4"

            if 'parts' in clip and len(clip['parts']) > 1:
                clip_result = await run_in_executor(cutter.create_multipart_clip, video_path=str(video_path), parts=clip['parts'], output_path=str(temp_out))
            else:
                # Use cutter.create_multipart_clip even for single parts as it handles them correctly
                clip_result = await run_in_executor(cutter.create_multipart_clip, video_path=str(video_path), parts=[clip], output_path=str(temp_out))

            if not clip_result['success']: continue
            clip_path = str(clip_result['clip_path'])
            temp_files.append(clip_path)

            # Get timing and words
            if 'parts' in clip and len(clip['parts']) > 1:
                # MULTI-PART: Always re-map words to a synthetic contiguous timeline
                all_mapped_words = []
                current_output_time = 0
                transition_duration = 0.1 # Matches clipper.py
                
                # Use full transcript if available for better mapping
                word_source = request.full_transcript_words if request.full_transcript_words is not None else []

                for pi, part in enumerate(clip['parts']):
                    p_start = part['start']
                    p_end = part['end']
                    p_duration = p_end - p_start
                    
                    # Ensure word_source is iterable
                    part_words = []
                    if word_source:
                        part_words = [w.copy() for w in word_source if not (w.get('end', 0) <= p_start or w.get('start', 0) >= p_end)]
                    else:
                        part_words = [w.copy() for w in part.get('words', [])]
                    
                    for w in part_words:
                        # Use .get() or cast to dict to satisfy linter
                        w_start = w.get('start', 0)
                        w_end = w.get('end', 0)
                        rel_start = max(0, w_start - p_start)
                        rel_end = w_end - p_start
                        w['start'] = current_output_time + rel_start
                        w['end'] = current_output_time + rel_end
                        
                    all_mapped_words.extend(part_words)
                    current_output_time += p_duration - transition_duration
                    
                clip_words = all_mapped_words
                clip_start = 0
                clip_end = current_output_time + transition_duration
            else:
                # SINGLE-PART
                clip_start = clip.get('start', 0)
                clip_end = clip.get('end', 0)
                clip_words = clip.get('words', [])
                
                if request.full_transcript_words:
                    derived_words = [w for w in request.full_transcript_words if not (w.get('end', 0) <= clip_start or w.get('start', 0) >= clip_end)]
                    if derived_words: clip_words = derived_words

            if request.format in ["reels", "vertical_9x16", "stacked_photo", "stacked_video"]:
                print(f"[DEBUG] Converting clip {i+1} to reels format: {request.format}")
                reels_out = TEMP_DIR / f"clip_{i+1}_reels.mp4"
                
                if request.format in ["stacked_photo", "stacked_video"]:
                    from backend.videoprocessor.media_stacker import MediaStacker
                    stacker = MediaStacker()
                    ai_content_type = "photo" if request.format == "stacked_photo" else "video"
                    ai_content_path = getattr(request, 'ai_content_path', None)
                    reels_result = await run_in_executor(
                        stacker.convert_stacked_format,
                        str(clip_path),
                        str(reels_out),
                        ai_content_type,
                        ai_content_path,
                        caption_text if 'caption_text' in dir() else None,
                        request.ai_content_position
                    )
                else:
                    reels_result = await run_in_executor(cropper.convert_to_reels, str(clip_path), output_path=str(reels_out), output_format=request.format)
                
                if reels_result['success']:
                    clip_path = str(reels_result['output_path'])
                    temp_files.append(clip_path)
                    print(f"[DEBUG]   Reels conversion success: {clip_path}")

            print(f"[DEBUG] Adding watermark to clip {i+1}")
            watermark_result = await run_in_executor(watermarker.add_watermark, str(clip_path))
            if watermark_result['success'] and watermark_result.get('watermark_added'):
                clip_path = str(watermark_result['output_path'])
                temp_files.append(clip_path)
                print(f"[DEBUG]   Watermark success: {clip_path}")

            # Captions
            caption_text = subtitle_burner.generate_clip_caption(clip_words, clip_start, clip_end)
            print(f"[DEBUG] Generated caption for clip {i+1}: {caption_text[:50]}...")

            if request.burn_captions:
                import cv2
                cap = cv2.VideoCapture(str(clip_path))
                c_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                c_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                cap.release()
                
                ass_path = TEMP_DIR / f"clip_{i+1}.ass"
                subtitle_burner.create_ass_subtitles(clip_words, str(ass_path), clip_start_time=clip_start, video_width=c_width, video_height=c_height)
                temp_files.append(str(ass_path))
                
                captioned_path = TEMP_DIR / f"clip_{i+1}_captioned.mp4"
                burn_result = await run_in_executor(subtitle_burner.burn_captions, video_path=clip_path, subtitle_path=str(ass_path), output_path=str(captioned_path))
                if burn_result['success']:
                    clip_path = str(burn_result['output_path'])
                    temp_files.append(clip_path)

            # Handle multi-part text joining
            if 'parts' in clip and len(clip['parts']) > 1:
                clip_text = ' ... '.join([part.get('text', '') for part in clip['parts']])
            else:
                clip_text = clip.get('text', clip.get('explanation', ''))

            processed_clips.append({
                'clip_number': i + 1,
                'clip_path': clip_path,
                'start_time': clip_start,
                'end_time': clip_end,
                'duration': clip_end - clip_start,
                'text': clip_text if 'clip_text' in locals() else "", # Fallback
                'caption_text': caption_text,
                'title': clip.get('title', 'Interesting Clip'),
                'reason': clip.get('reason', ''),
                'keywords': clip.get('keywords', [])
            })

        if not processed_clips: raise Exception("All clipping operations failed.")

        await update_progress({'stage': 'organizing', 'percent': 90, 'message': 'Organizing files...'})
        org_format = "reels" if request.format in ["reels", "vertical_9x16", "stacked_photo", "stacked_video"] else request.format
        file_mgr.organize_clips(processed_clips, project_folder, video_info, org_format)
        file_mgr.cleanup_temp_files(temp_files)
        # Final success broadcast
        await update_progress({'stage': 'complete', 'percent': 100, 'message': 'Processing complete!'})

    except Exception as e:
        print(traceback.format_exc())
        await update_progress({'stage': 'error', 'percent': 0, 'message': f"Error: {str(e)}"})


@router.post("/api/process")
async def process_video(request: ProcessVideoRequest, background_tasks: BackgroundTasks):
    """
    Start video processing in background to avoid HTTP timeouts
    """
    background_tasks.add_task(_perform_video_processing, request)
    return {"success": True, "message": "Processing started in background"}

