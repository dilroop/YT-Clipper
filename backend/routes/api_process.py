import os
import asyncio
import traceback
from fastapi import APIRouter, HTTPException
from backend.models.schemas import ProcessVideoRequest
from backend.utils.video_helpers import extract_video_id
from backend.core.config import load_config
from backend.core.executor import run_in_executor
from backend.core.connection_manager import manager
from backend.core.constants import TEMP_DIR

router = APIRouter()

@router.post("/api/process")
async def process_video(request: ProcessVideoRequest):
    """
    Process video: download, analyze, clip, caption, and organize
    """
    try:
        # Import processing modules
        from backend.downloader import VideoDownloader
        from backend.pytube_downloader import PytubeDownloader
        from backend.transcriber import AudioTranscriber
        from backend.analyzer import SectionAnalyzer
        from backend.ai_analyzer import AIAnalyzer
        from backend.clipper import VideoClipper
        from backend.caption_generator import CaptionGenerator
        from backend.reels_processor import ReelsProcessor
        from backend.watermark_processor import WatermarkProcessor
        from backend.file_manager import FileManager

        video_id = extract_video_id(request.url)

        # Load config
        config = load_config()
        caption_config = config.get('caption_settings', {})
        watermark_config = config.get('watermark_settings', {})
        downloader_backend = config.get('downloader_backend', 'yt-dlp')

        # Initialize downloader based on config
        if downloader_backend == 'pytube':
            downloader = PytubeDownloader()
        else:
            downloader = VideoDownloader()

        # Initialize modules
        transcriber = AudioTranscriber(model_name="base")
        ai_validation = config.get('ai_validation', {})
        min_duration = ai_validation.get('min_clip_duration', 15)
        max_duration = ai_validation.get('max_clip_duration', 60)

        # Use AI analyzer if API key is available, otherwise fall back to simple analyzer
        openai_api_key = os.getenv('OPENAI_API_KEY')
        if openai_api_key and openai_api_key.startswith('sk-'):
            analyzer = AIAnalyzer(
                api_key=openai_api_key,
                model=os.getenv('OPENAI_MODEL', 'gpt-4o-mini'),
                temperature=float(os.getenv('OPENAI_TEMPERATURE', '1.0')),
                min_clip_duration=min_duration,
                max_clip_duration=max_duration
            )
        else:
            analyzer = SectionAnalyzer()

        clipper = VideoClipper()
        caption_gen = CaptionGenerator(caption_config)
        reels_proc = ReelsProcessor()
        watermark_proc = WatermarkProcessor(watermark_config)
        file_mgr = FileManager()

        # Progress tracking with WebSocket broadcasting
        client_id = request.client_id
        loop = asyncio.get_running_loop()

        async def update_progress(data):
            await manager.broadcast({
                'type': 'progress',
                **data
            }, target_client_id=client_id)

        # Wrapper for sync callbacks
        def update_progress_sync(data):
            """Thread-safe progress callback for subprocess operations"""
            try:
                # Schedule coroutine on event loop from thread (thread-safe)
                asyncio.run_coroutine_threadsafe(update_progress(data), loop)
            except Exception as e:
                print(f"Progress update failed: {e}")

        # Step 1: Download video
        await update_progress({'stage': 'downloading', 'percent': 0, 'message': 'Downloading video...'})
        download_result = await run_in_executor(
            downloader.download_video,
            request.url,
            update_progress_sync
        )

        if not download_result['success']:
            raise Exception(download_result['error'])

        video_path = download_result['video_path']
        video_info = {
            'video_id': download_result['video_id'],
            'title': download_result['title'],
            'channel': download_result['channel'],
            'description': download_result['description'],
            'url': request.url
        }

        # Check if we have pre-analyzed clips (from manual workflow)
        if request.preanalyzed_clips:
            await update_progress({'stage': 'analyzing', 'percent': 60, 'message': 'Using pre-analyzed clips...'})
            interesting_clips = []
            for clip_data in request.preanalyzed_clips:
                if 'parts' in clip_data and len(clip_data['parts']) > 1:
                    interesting_clips.append({
                        'title': clip_data.get('title', 'Multi-Part Clip'),
                        'reason': clip_data.get('reason', ''),
                        'keywords': clip_data.get('keywords', []),
                        'parts': clip_data['parts']
                    })
                else:
                    interesting_clips.append({
                        'start': clip_data['start'],
                        'end': clip_data['end'],
                        'text': clip_data['text'],
                        'title': clip_data.get('title', 'Interesting Clip'),
                        'reason': clip_data.get('reason', ''),
                        'keywords': clip_data.get('keywords', []),
                        'words': clip_data.get('words', [])
                    })
            audio_path = None
        else:
            # Step 2: Transcribe audio
            await update_progress({'stage': 'transcribing', 'percent': 20, 'message': 'Transcribing audio...'})
            transcript_result = transcriber.transcribe(video_path, update_progress_sync)
            if not transcript_result['success']:
                raise Exception(transcript_result['error'])

            segments = transcript_result['segments']
            audio_path = transcript_result.get('audio_path')

            # Step 3: Find interesting clips
            await update_progress({'stage': 'analyzing', 'percent': 40, 'message': 'Finding interesting clips...'})
            if isinstance(analyzer, AIAnalyzer):
                interesting_clips = analyzer.find_interesting_clips(
                    segments,
                    num_clips=5,
                    video_info=video_info,
                    strategy=request.ai_strategy or "viral-moments"
                )
            else:
                interesting_clips = analyzer.find_interesting_clips(segments, num_clips=5)
                interesting_clips = [analyzer.adjust_clip_timing(clip) for clip in interesting_clips]

            if not request.preanalyzed_clips:
                if request.selected_clips is not None:
                    # Handle both integer indices and string IDs from frontend
                    selected_indices = {int(x) if isinstance(x, str) and x.isdigit() else x for x in request.selected_clips}
                    interesting_clips = [
                        clip for i, clip in enumerate(interesting_clips)
                        if i in selected_indices
                    ]
                else:
                    interesting_clips = [
                        clip for clip in interesting_clips
                        if clip.get('validation_level', 'valid') != 'error'
                    ]

        # Step 4: Create project folder
        project_folder = file_mgr.create_project_folder(video_info['title'])

        # Step 5: Process clips
        await update_progress({'stage': 'clipping', 'percent': 50, 'message': 'Creating clips...'})

        temp_files = []
        if audio_path:
            temp_files.append(audio_path)

        processed_clips = []

        for i, clip in enumerate(interesting_clips):
            clip_progress = 50 + (i / len(interesting_clips)) * 35
            await update_progress({
                'stage': 'clipping',
                'percent': clip_progress,
                'message': f'Processing clip {i+1}/{len(interesting_clips)}...'
            })

            # Handle multi-part vs single-part clip creation
            if 'parts' in clip and len(clip['parts']) > 1:
                clip_result = await run_in_executor(
                    clipper.create_multipart_clip,
                    video_path=str(video_path),
                    parts=clip['parts']
                )
            else:
                clip_result = await run_in_executor(
                    clipper.create_clip,
                    video_path=str(video_path),
                    start_time=clip['start'],
                    end_time=clip['end']
                )

            if not clip_result['success']:
                print(f"[REELS] Clipping failed for clip {i+1}: {clip_result.get('error', 'Unknown error')}")
                continue

            print(f"[REELS] Clip {i+1} extraction successful: {clip_result['clip_path']}")
            clip_path = clip_result['clip_path']
            temp_files.append(clip_path)

            # Get timing and words (Initial collection)
            if 'parts' in clip and len(clip['parts']) > 1:
                # MULTI-PART: Always re-map words to a synthetic contiguous timeline
                all_mapped_words = []
                current_output_time = 0
                transition_duration = 0.1 # Matches clipper.py
                
                # Determine source of words (full transcript is preferred for better coverage)
                word_source = request.full_transcript_words if request.full_transcript_words else None

                for pi, part in enumerate(clip['parts']):
                    p_start = part['start']
                    p_end = part['end']
                    p_duration = p_end - p_start
                    
                    # Find words for this part
                    if word_source:
                        part_words = [
                            w.copy() for w in word_source
                            if not (w['end'] <= p_start or w['start'] >= p_end)
                        ]
                    else:
                        # Fallback to existing words in part, but still copy and shift
                        part_words = [w.copy() for w in part.get('words', [])]
                    
                    print(f"[REELS] Part {pi+1}: Mapping {len(part_words)} words (Offset: {current_output_time:.2f}s)")
                    
                    # Shift word times to match the stitched output timeline
                    for w in part_words:
                        # Time relative to part start
                        rel_start = max(0, w['start'] - p_start)
                        rel_end = w['end'] - p_start
                        # New time in stitched video
                        w['start'] = current_output_time + rel_start
                        w['end'] = current_output_time + rel_end
                        
                    all_mapped_words.extend(part_words)
                    current_output_time += p_duration - transition_duration
                    
                clip_words = all_mapped_words
                clip_start = 0
                clip_end = current_output_time + transition_duration
                print(f"[REELS] Multi-part sync complete: {len(clip_words)} words, duration {clip_end:.1f}s")
            else:
                # SINGLE-PART: Normal timing and optional re-derivation
                clip_start = clip.get('start', 0)
                clip_end = clip.get('end', 0)
                clip_words = clip.get('words', [])
                
                if request.full_transcript_words:
                    derived_words = [
                        w for w in request.full_transcript_words
                        if not (w['end'] <= clip_start or w['start'] >= clip_end)
                    ]
                    if derived_words:
                        clip_words = derived_words

            # Reels conversion
            if request.format in ["reels", "vertical_9x16", "stacked_photo", "stacked_video"]:
                output_format_map = {
                    "reels": "vertical_9x16",
                    "vertical_9x16": "vertical_9x16",
                    "stacked_photo": "stacked_photo",
                    "stacked_video": "stacked_video"
                }
                reels_result = await run_in_executor(
                    reels_proc.convert_to_reels,
                    clip_path,
                    output_format=output_format_map.get(request.format, "vertical_9x16")
                )
                if reels_result['success']:
                    clip_path = reels_result['output_path']
                    temp_files.append(clip_path)

            # Captions
            caption_text = caption_gen.generate_clip_caption(clip_words, clip_start, clip_end)


            # Watermark
            watermark_result = await run_in_executor(
                watermark_proc.add_watermark,
                clip_path
            )
            if watermark_result['success'] and watermark_result.get('watermark_added'):
                clip_path = watermark_result['output_path']
                temp_files.append(clip_path)

            # Step 5: Final Call - Subtitle Burning (happens last to respect dimensions)
            if request.burn_captions:
                import cv2
                # Detect final video dimensions for correct caption positioning
                cap = cv2.VideoCapture(str(clip_path))
                v_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)) or 1920
                v_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)) or 1080
                cap.release()

                ass_path = TEMP_DIR / f"clip_{i+1}.ass"
                caption_gen.create_ass_subtitles(
                    words=clip_words,
                    output_path=str(ass_path),
                    clip_start_time=clip_start,
                    video_width=v_width,
                    video_height=v_height
                )
                temp_files.append(str(ass_path))

                captioned_path = TEMP_DIR / f"clip_{i+1}_captioned.mp4"
                burn_result = await run_in_executor(
                    caption_gen.burn_captions,
                    video_path=clip_path,
                    subtitle_path=str(ass_path),
                    output_path=str(captioned_path)
                )

                if burn_result['success']:
                    clip_path = burn_result['output_path']
                    temp_files.append(clip_path)
                else:
                    # Provide feedback on failure but continue with uncaptioned clip
                    error_msg = burn_result.get('error', 'Unknown error')
                    print(f"[WARNING] Subtitle burning failed: {error_msg}")
                    await update_progress({
                        'stage': 'clipping',
                        'percent': clip_progress,
                        'message': f"⚠️ Caption burning failed for clip {i+1}. Proceeding without captions."
                    })

            # Collect info for organization
            if 'parts' in clip and len(clip['parts']) > 1:
                clip_text = ' ... '.join([part.get('text', '') for part in clip['parts']])
            else:
                clip_text = clip.get('text', '')

            processed_clips.append({
                'clip_number': i + 1,
                'clip_path': clip_path,
                'start_time': clip_start,
                'end_time': clip_end,
                'duration': clip_end - clip_start,
                'text': clip_text,
                'caption_text': caption_text,
                'title': clip.get('title', 'Interesting Clip'),
                'reason': clip.get('reason', ''),
                'keywords': clip.get('keywords', [])
            })

        # Step 6: Organize
        await update_progress({'stage': 'organizing', 'percent': 90, 'message': 'Organizing files...'})
        org_format = "reels" if request.format in ["reels", "vertical_9x16", "stacked_photo", "stacked_video"] else request.format
        file_mgr.organize_clips(processed_clips, project_folder, video_info, org_format)

        # Cleanup
        await update_progress({'stage': 'cleanup', 'percent': 95, 'message': 'Cleaning up...'})
        file_mgr.cleanup_temp_files(temp_files)
        summary = file_mgr.get_project_summary(project_folder)

        await update_progress({'stage': 'complete', 'percent': 100, 'message': 'Processing complete!'})

        return {
            "success": True,
            "message": "Video processed successfully",
            "project_folder": str(project_folder),
            "clips_created": len(processed_clips),
            "summary": summary
        }

    except Exception as e:
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Error processing video: {str(e)}")
