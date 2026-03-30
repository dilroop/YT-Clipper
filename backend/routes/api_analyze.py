import os
import asyncio
import traceback
from fastapi import APIRouter, HTTPException
from backend.models.schemas import AnalyzeVideoRequest
from backend.utils.video_helpers import extract_video_id
from backend.core.config import get_config_with_defaults
from backend.core.executor import run_in_executor
from backend.core.connection_manager import manager

router = APIRouter()

@router.post("/api/analyze")
async def analyze_video(request: AnalyzeVideoRequest):
    """
    Analyze video and return AI-suggested clips WITHOUT creating them
    Used for manual clip selection workflow
    """
    try:
        # Import processing modules
        from backend.downloader import VideoDownloader
        from backend.pytube_downloader import PytubeDownloader
        from backend.videoprocessor.transcriber import AudioTranscriber
        from backend.ai_analyzer import AIAnalyzer
        from backend.analyzer import SectionAnalyzer
        from backend.logger import app_logger

        video_id = extract_video_id(request.url)

        # Load config with defaults
        config = get_config_with_defaults()
        downloader_backend = config.get('downloader_backend', 'yt-dlp')

        # Initialize downloader based on config
        if downloader_backend == 'pytube':
            downloader = PytubeDownloader()
        else:
            downloader = VideoDownloader()

        # Initialize modules
        transcriber = AudioTranscriber(model_name="base")

        # Use AI analyzer if API key is available
        openai_api_key = os.getenv('OPENAI_API_KEY')

        # Load validation settings from config
        ai_validation = config.get('ai_validation', {})
        min_duration = ai_validation.get('min_clip_duration', 15)
        max_duration = ai_validation.get('max_clip_duration', 60)

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
            # OpenAI (default)
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

        # Step 2: Transcribe audio
        await update_progress({'stage': 'transcribing', 'percent': 30, 'message': 'Transcribing audio...'})
        transcript_result = await run_in_executor(
            transcriber.transcribe,
            video_path,
            update_progress_sync
        )

        if not transcript_result['success']:
            raise Exception(transcript_result['error'])

        segments = transcript_result['segments']

        # Step 3: Find interesting clips using AI
        provider_name = getattr(analyzer, 'provider_name', 'Basic AI')
        await update_progress({'stage': 'analyzing', 'percent': 60, 'message': f'Finding clips with {provider_name}...'})
        if isinstance(analyzer, AIAnalyzer):
            interesting_clips = analyzer.find_interesting_clips(
                segments,
                num_clips=5,
                video_info=video_info,
                strategy=request.ai_strategy or "viral-moments",
                extra_context=request.extra_context
            )
        else:
            interesting_clips = analyzer.find_interesting_clips(segments, num_clips=5)
            interesting_clips = [analyzer.adjust_clip_timing(clip) for clip in interesting_clips]

        # Format clips for frontend
        formatted_clips = []
        for i, clip in enumerate(interesting_clips):
            if 'parts' in clip and len(clip['parts']) > 0:
                first_part = clip['parts'][0]
                last_part = clip['parts'][-1]
                start = first_part['start']
                end = last_part['end']
                total_duration = sum(part['end'] - part['start'] for part in clip['parts'])
                text = ' ... '.join([part.get('text', '') for part in clip['parts']])
                words = []
                for part in clip['parts']:
                    words.extend(part.get('words', []))
            else:
                start = clip['start']
                end = clip['end']
                total_duration = end - start
                text = clip.get('text', '')
                words = clip.get('words', [])

            formatted_clips.append({
                'id': str(i),
                'index': i,
                'start': start,
                'end': end,
                'duration': total_duration,
                'title': clip.get('title', f'Clip {i+1}'),
                'reason': clip.get('reason', ''),
                'text': text,
                'youtube_link': f"{request.url}&t={int(start)}",
                'keywords': clip.get('keywords', []),
                'words': words,
                'parts': clip.get('parts', []),
                'is_valid': clip.get('is_valid', True),
                'validation_warnings': clip.get('validation_warnings', []),
                'validation_level': clip.get('validation_level', 'valid')
            })

        await update_progress({'stage': 'complete', 'percent': 100, 'message': 'Analysis complete!'})

        # Build full transcript word list from all Whisper segments (for clip editor)
        full_transcript_words = []
        for seg in segments:
            for w in seg.get('words', []):
                word_text = (w.get('word') or w.get('text') or '').strip()
                if word_text:
                    full_transcript_words.append({
                        'word': word_text,
                        'start': w['start'],
                        'end': w['end']
                    })

        return {
            "success": True,
            "video_id": video_id,
            "video_info": video_info,
            "clips": formatted_clips,
            "total_clips": len(formatted_clips),
            "full_transcript_words": full_transcript_words
        }

    except Exception as e:
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Error analyzing video: {str(e)}")
