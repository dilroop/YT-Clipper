"""
YTClipper - FastAPI Server
Mobile-first web app for clipping YouTube videos
"""

import ssl
import certifi

# Disable SSL certificate verification globally (for corporate networks/proxies)
ssl._create_default_https_context = ssl._create_unverified_context

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import json
import os
from pathlib import Path
import re
from typing import Optional
import sqlite3
from datetime import datetime
import asyncio
import sys

# Initialize FastAPI app
app = FastAPI(title="YTClipper", version="1.0.0")

# Add CORS middleware for cross-origin requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Base directory
BASE_DIR = Path(__file__).parent.parent

# Database path
DB_PATH = BASE_DIR / "history.db"

# Log file path
LOG_FILE = BASE_DIR / "logs" / "ytclipper.log"

# Ensure logs directory exists
LOG_FILE.parent.mkdir(exist_ok=True)

# Tee class to write to both file and console
class TeeOutput:
    """Write to both console and log file"""
    def __init__(self, file_path, original_stream):
        self.file = open(file_path, 'a', encoding='utf-8')
        self.original_stream = original_stream

    def write(self, message):
        # Write to console
        self.original_stream.write(message)
        self.original_stream.flush()
        # Write to file with timestamp
        if message.strip():  # Only log non-empty messages
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            self.file.write(f"[{timestamp}] {message}")
            self.file.flush()

    def flush(self):
        self.original_stream.flush()
        self.file.flush()

    def isatty(self):
        return self.original_stream.isatty()

# Redirect stdout and stderr to also write to log file
sys.stdout = TeeOutput(LOG_FILE, sys.stdout)
sys.stderr = TeeOutput(LOG_FILE, sys.stderr)

# Mount static files (frontend)
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "frontend")), name="static")

# Mount ToUpload folder for serving generated clips
app.mount("/clips", StaticFiles(directory=str(BASE_DIR / "ToUpload")), name="clips")

# WebSocket connections for real-time progress updates
active_connections: list[WebSocket] = []


# Pydantic models
class VideoURLRequest(BaseModel):
    url: str


class ProcessVideoRequest(BaseModel):
    url: str
    format: str  # "original" or "reels"
    burn_captions: bool = True
    selected_clips: Optional[list] = None  # List of clip indices to process (for manual mode)


class ConfigUpdate(BaseModel):
    caption_settings: Optional[dict] = None
    watermark_settings: Optional[dict] = None


# Helper functions
def extract_video_id(url: str) -> str:
    """Extract YouTube video ID from URL"""
    patterns = [
        r'(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/)([a-zA-Z0-9_-]{11})',
        r'youtube\.com/watch\?.*v=([a-zA-Z0-9_-]{11})',
    ]

    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)

    raise ValueError("Invalid YouTube URL")


def get_thumbnail_url(video_id: str) -> dict:
    """Get YouTube thumbnail URLs"""
    return {
        "maxres": f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg",
        "hq": f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg",
        "default": f"https://img.youtube.com/vi/{video_id}/default.jpg"
    }


def load_config() -> dict:
    """Load configuration from config.json"""
    config_path = BASE_DIR / "config.json"
    if config_path.exists():
        with open(config_path, 'r') as f:
            return json.load(f)
    return {}


def save_config(config: dict):
    """Save configuration to config.json"""
    config_path = BASE_DIR / "config.json"
    with open(config_path, 'w') as f:
        json.dump(config, f, indent=2)


# Database functions
def init_database():
    """Initialize SQLite database for history tracking"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            url TEXT NOT NULL,
            video_id TEXT NOT NULL,
            title TEXT,
            channel TEXT,
            duration INTEGER,
            description TEXT,
            thumbnail TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    conn.close()


def save_to_history(url: str, video_id: str, title: str, channel: str, duration: int, thumbnail: str, description: str = ''):
    """Save a video to history"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO history (url, video_id, title, channel, duration, description, thumbnail, timestamp)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (url, video_id, title, channel, duration, description, thumbnail, datetime.now().isoformat()))

    conn.commit()
    conn.close()


def get_history(limit: int = 50):
    """Get history from database"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, url, video_id, title, channel, duration, description, thumbnail, timestamp
        FROM history
        ORDER BY timestamp DESC
        LIMIT ?
    """, (limit,))

    rows = cursor.fetchall()
    conn.close()

    return [dict(row) for row in rows]


def clear_history():
    """Clear all history"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM history")
    conn.commit()
    conn.close()


# Initialize database on startup
init_database()


# WebSocket manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except:
                pass


manager = ConnectionManager()


# Routes
@app.get("/")
async def root():
    """Serve the main HTML page"""
    return FileResponse(str(BASE_DIR / "frontend" / "index.html"))


@app.get("/gallery.html")
async def gallery():
    """Serve the gallery HTML page"""
    return FileResponse(str(BASE_DIR / "frontend" / "gallery.html"))


@app.get("/clip-detail.html")
async def clip_detail():
    """Serve the clip detail HTML page"""
    return FileResponse(str(BASE_DIR / "frontend" / "clip-detail.html"))


@app.get("/logs.html")
async def logs():
    """Serve the logs HTML page"""
    return FileResponse(str(BASE_DIR / "frontend" / "logs.html"))


@app.post("/api/thumbnail")
async def get_thumbnail(request: VideoURLRequest):
    """
    Get video thumbnail and metadata without downloading
    """
    try:
        video_id = extract_video_id(request.url)
        thumbnail_urls = get_thumbnail_url(video_id)

        # Use yt-dlp to get metadata (fast, no download)
        import yt_dlp

        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'skip_download': True,
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(request.url, download=False)

            title = info.get('title', 'Unknown')
            channel = info.get('uploader', 'Unknown')
            duration = info.get('duration', 0)
            description = info.get('description', '')
            thumbnail = thumbnail_urls['maxres']

            # Save to history
            save_to_history(
                url=request.url,
                video_id=video_id,
                title=title,
                channel=channel,
                duration=duration,
                thumbnail=thumbnail,
                description=description
            )

            return {
                "success": True,
                "video_id": video_id,
                "title": title,
                "channel": channel,
                "duration": duration,
                "description": description,
                "thumbnail": thumbnail,
                "thumbnail_fallback": thumbnail_urls['hq'],
            }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching thumbnail: {str(e)}")


@app.post("/api/analyze")
async def analyze_video(request: VideoURLRequest):
    """
    Analyze video and return AI-suggested clips WITHOUT creating them
    Used for manual clip selection workflow
    """
    import asyncio

    try:
        # Import processing modules
        from downloader import VideoDownloader
        from transcriber import AudioTranscriber
        from ai_analyzer import AIAnalyzer
        from analyzer import SectionAnalyzer

        video_id = extract_video_id(request.url)

        # Initialize modules
        downloader = VideoDownloader()
        transcriber = AudioTranscriber(model_name="base")

        # Use AI analyzer if API key is available
        openai_api_key = os.getenv('OPENAI_API_KEY')
        if openai_api_key and openai_api_key.startswith('sk-'):
            analyzer = AIAnalyzer(
                api_key=openai_api_key,
                model=os.getenv('OPENAI_MODEL', 'gpt-4o-mini'),
                temperature=float(os.getenv('OPENAI_TEMPERATURE', '1.0'))
            )
        else:
            analyzer = SectionAnalyzer()

        # Progress tracking with WebSocket broadcasting
        async def update_progress(data):
            print(f"Progress: {data}")
            await manager.broadcast({
                'type': 'progress',
                **data
            })

        # Wrapper for sync callbacks
        def update_progress_sync(data):
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    asyncio.create_task(update_progress(data))
                else:
                    loop.run_until_complete(update_progress(data))
            except:
                print(f"Progress: {data}")

        # Step 1: Download video
        await update_progress({'stage': 'downloading', 'percent': 0, 'message': 'Downloading video...'})
        download_result = downloader.download_video(request.url, update_progress_sync)

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
        transcript_result = transcriber.transcribe(video_path, update_progress_sync)

        if not transcript_result['success']:
            raise Exception(transcript_result['error'])

        segments = transcript_result['segments']

        # Step 3: Find interesting clips using AI
        await update_progress({'stage': 'analyzing', 'percent': 60, 'message': 'Finding interesting clips...'})
        if isinstance(analyzer, AIAnalyzer):
            interesting_clips = analyzer.find_interesting_clips(
                segments,
                num_clips=5,
                video_info=video_info
            )
        else:
            interesting_clips = analyzer.find_interesting_clips(segments, num_clips=5)
            interesting_clips = [analyzer.adjust_clip_timing(clip) for clip in interesting_clips]

        # Check if we found any clips
        if not interesting_clips or len(interesting_clips) == 0:
            raise Exception("Could not find any interesting clips in this video. The AI may have had trouble analyzing the content. Try again or use a different video.")

        # Format clips for frontend
        formatted_clips = []
        for i, clip in enumerate(interesting_clips):
            # Calculate timestamp in seconds for YouTube link
            start_seconds = int(clip['start'])

            formatted_clips.append({
                'index': i,
                'start': clip['start'],
                'end': clip['end'],
                'duration': clip['end'] - clip['start'],
                'title': clip.get('title', f'Clip {i+1}'),
                'reason': clip.get('reason', ''),
                'text': clip['text'],
                'youtube_link': f"{request.url}&t={start_seconds}",
                'keywords': clip.get('keywords', [])
            })

        await update_progress({'stage': 'complete', 'percent': 100, 'message': 'Analysis complete!'})

        return {
            "success": True,
            "video_id": video_id,
            "video_info": video_info,
            "clips": formatted_clips,
            "total_clips": len(formatted_clips)
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        import traceback
        print("="*60)
        print("Exception in /api/analyze:")
        print(traceback.format_exc())
        print("="*60)
        raise HTTPException(status_code=500, detail=f"Error analyzing video: {str(e)}")


@app.post("/api/process")
async def process_video(request: ProcessVideoRequest):
    """
    Process video: download, analyze, clip, caption, and organize
    """
    import asyncio

    try:
        # Import processing modules
        from downloader import VideoDownloader
        from transcriber import AudioTranscriber
        from analyzer import SectionAnalyzer
        from ai_analyzer import AIAnalyzer
        from clipper import VideoClipper
        from caption_generator import CaptionGenerator
        from reels_processor import ReelsProcessor
        from watermark_processor import WatermarkProcessor
        from file_manager import FileManager

        video_id = extract_video_id(request.url)

        # Load config
        config = load_config()
        caption_config = config.get('caption_settings', {})
        watermark_config = config.get('watermark_settings', {})

        # Initialize modules
        downloader = VideoDownloader()
        transcriber = AudioTranscriber(model_name="base")

        # Use AI analyzer if API key is available, otherwise fall back to simple analyzer
        openai_api_key = os.getenv('OPENAI_API_KEY')
        if openai_api_key and openai_api_key.startswith('sk-'):
            print("Using AI-based clip analyzer (GPT)")
            analyzer = AIAnalyzer(
                api_key=openai_api_key,
                model=os.getenv('OPENAI_MODEL', 'gpt-4o-mini'),
                temperature=float(os.getenv('OPENAI_TEMPERATURE', '1.0'))
            )
        else:
            print("Using simple keyword-based analyzer (no API key found)")
            analyzer = SectionAnalyzer()

        clipper = VideoClipper()
        caption_gen = CaptionGenerator(caption_config)
        reels_proc = ReelsProcessor()
        watermark_proc = WatermarkProcessor(watermark_config)
        file_mgr = FileManager()

        # Progress tracking with WebSocket broadcasting
        async def update_progress(data):
            print(f"Progress: {data}")
            await manager.broadcast({
                'type': 'progress',
                **data
            })

        # Wrapper for sync callbacks
        def update_progress_sync(data):
            # Create event loop if needed and broadcast
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    asyncio.create_task(update_progress(data))
                else:
                    loop.run_until_complete(update_progress(data))
            except:
                print(f"Progress: {data}")

        # Step 1: Download video
        await update_progress({'stage': 'downloading', 'percent': 0, 'message': 'Downloading video...'})
        download_result = downloader.download_video(request.url, update_progress_sync)

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
        await update_progress({'stage': 'transcribing', 'percent': 20, 'message': 'Transcribing audio...'})
        transcript_result = transcriber.transcribe(video_path, update_progress_sync)

        if not transcript_result['success']:
            raise Exception(transcript_result['error'])

        segments = transcript_result['segments']

        # Step 3: Find interesting clips
        await update_progress({'stage': 'analyzing', 'percent': 40, 'message': 'Finding interesting clips...'})

        try:
            # AI analyzer can use video info for better context
            if isinstance(analyzer, AIAnalyzer):
                interesting_clips = analyzer.find_interesting_clips(
                    segments,
                    num_clips=5,
                    video_info=video_info
                )
            else:
                interesting_clips = analyzer.find_interesting_clips(segments, num_clips=5)
                # Adjust timing with padding (only for simple analyzer)
                interesting_clips = [analyzer.adjust_clip_timing(clip) for clip in interesting_clips]
        except Exception as e:
            error_msg = str(e)
            # Check for OpenAI quota error
            if "OPENAI_QUOTA_ERROR" in error_msg:
                raise Exception("OPENAI_QUOTA_ERROR: " + error_msg.split("OPENAI_QUOTA_ERROR: ", 1)[1])
            raise

        # Filter clips if selected_clips is provided (manual mode)
        if request.selected_clips is not None:
            interesting_clips = [
                clip for i, clip in enumerate(interesting_clips)
                if i in request.selected_clips
            ]

        # Step 4: Create project folder
        project_folder = file_mgr.create_project_folder(video_info['title'])

        # Step 5: Process clips
        await update_progress({'stage': 'clipping', 'percent': 50, 'message': 'Creating clips...'})

        temp_files = []
        processed_clips = []

        for i, clip in enumerate(interesting_clips):
            clip_progress = 50 + (i / len(interesting_clips)) * 35
            await update_progress({
                'stage': 'clipping',
                'percent': clip_progress,
                'message': f'Processing clip {i+1}/{len(interesting_clips)}...'
            })

            # Create base clip from original video
            clip_result = clipper.create_clip(
                video_path=video_path,
                start_time=clip['start'],
                end_time=clip['end']
            )

            if not clip_result['success']:
                continue

            clip_path = clip_result['clip_path']
            temp_files.append(clip_path)

            # Convert to reels format FIRST if requested (before captions)
            # This ensures captions are centered on the reels crop
            if request.format == "reels":
                reels_result = reels_proc.convert_to_reels(clip_path)
                if reels_result['success']:
                    clip_path = reels_result['output_path']
                    temp_files.append(clip_path)

            # Generate caption text
            caption_text = caption_gen.generate_clip_caption(
                clip['words'],
                clip['start'],
                clip['end']
            )

            # NOW burn captions onto the clip (after reels conversion if applicable)
            if request.burn_captions:
                # Create ASS subtitles
                ass_path = Path(clip_path).parent / f"clip_{i+1}.ass"
                caption_gen.create_ass_subtitles(
                    words=clip['words'],
                    output_path=str(ass_path),
                    clip_start_time=clip['start']
                )
                temp_files.append(str(ass_path))

                # Burn captions
                captioned_path = Path(clip_path).parent / f"clip_{i+1}_captioned.mp4"
                burn_result = caption_gen.burn_captions(
                    video_path=clip_path,
                    subtitle_path=str(ass_path),
                    output_path=str(captioned_path)
                )

                if burn_result['success']:
                    clip_path = burn_result['output_path']
                    temp_files.append(clip_path)

            # Add watermark if enabled
            watermark_result = watermark_proc.add_watermark(clip_path)
            if watermark_result['success'] and watermark_result.get('watermark_added'):
                clip_path = watermark_result['output_path']
                temp_files.append(clip_path)

            # Store processed clip info
            processed_clips.append({
                'clip_number': i + 1,
                'clip_path': clip_path,
                'start_time': clip['start'],
                'end_time': clip['end'],
                'duration': clip['end'] - clip['start'],
                'text': clip['text'],
                'caption_text': caption_text
            })

        # Step 6: Organize clips based on selected format
        await update_progress({'stage': 'organizing', 'percent': 90, 'message': 'Organizing files...'})
        file_mgr.organize_clips(processed_clips, project_folder, video_info, request.format)

        # Step 8: Cleanup
        await update_progress({'stage': 'cleanup', 'percent': 95, 'message': 'Cleaning up...'})
        file_mgr.cleanup_temp_files(temp_files)
        # Keep downloaded video instead of auto-deleting (user preference)
        # downloader.cleanup_video(video_path)

        # Step 9: Get summary
        summary = file_mgr.get_project_summary(project_folder)

        await update_progress({'stage': 'complete', 'percent': 100, 'message': 'Processing complete!'})

        return {
            "success": True,
            "message": "Video processed successfully",
            "project_folder": str(project_folder),
            "clips_created": len(processed_clips),
            "summary": summary
        }

    except ValueError as e:
        import traceback
        print("="*60)
        print("ValueError caught:")
        print(traceback.format_exc())
        print("="*60)
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        import traceback
        print("="*60)
        print("Exception caught:")
        print(traceback.format_exc())
        print("="*60)
        raise HTTPException(status_code=500, detail=f"Error processing video: {str(e)}")


@app.get("/api/config")
async def get_config():
    """Get current configuration"""
    config = load_config()
    return config


@app.post("/api/config")
async def update_config(config_update: ConfigUpdate):
    """Update configuration"""
    try:
        config = load_config()

        if config_update.caption_settings:
            config['caption_settings'] = {**config.get('caption_settings', {}), **config_update.caption_settings}

        if config_update.watermark_settings:
            config['watermark_settings'] = {**config.get('watermark_settings', {}), **config_update.watermark_settings}

        save_config(config)

        return {"success": True, "config": config}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating config: {str(e)}")


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket for real-time progress updates"""
    await manager.connect(websocket)
    try:
        while True:
            # Keep connection alive
            data = await websocket.receive_text()
            # Echo back (for testing)
            await websocket.send_json({"type": "echo", "message": data})
    except WebSocketDisconnect:
        manager.disconnect(websocket)


@app.get("/api/history")
async def get_history_endpoint(limit: int = 50):
    """Get video history"""
    try:
        history = get_history(limit)
        return {"success": True, "history": history, "count": len(history)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching history: {str(e)}")


@app.get("/api/logs")
async def get_logs(lines: int = 500):
    """Get the last N lines from the log file"""
    try:
        # Ensure logs directory exists
        LOG_FILE.parent.mkdir(exist_ok=True)

        if not LOG_FILE.exists():
            return {"success": True, "logs": [], "count": 0}

        # Read the last N lines efficiently
        with open(LOG_FILE, 'r', encoding='utf-8') as f:
            # Read all lines
            all_lines = f.readlines()
            # Get last N lines
            last_lines = all_lines[-lines:] if len(all_lines) > lines else all_lines

        return {
            "success": True,
            "logs": last_lines,
            "count": len(last_lines),
            "total_lines": len(all_lines)
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading logs: {str(e)}")


@app.websocket("/ws/logs")
async def websocket_logs(websocket: WebSocket):
    """WebSocket for live log streaming"""
    await websocket.accept()
    print(f"🔌 WebSocket connected from logs panel")

    try:
        # Send initial log content (last 500 lines)
        if LOG_FILE.exists():
            print(f"📂 Log file exists, reading last 500 lines...")
            with open(LOG_FILE, 'r', encoding='utf-8') as f:
                all_lines = f.readlines()
                last_lines = all_lines[-500:] if len(all_lines) > 500 else all_lines
                print(f"📤 Sending {len(last_lines)} initial log lines...")
                for line in last_lines:
                    await websocket.send_json({"type": "history", "line": line.rstrip()})
                print(f"✅ Sent all initial log lines")
        else:
            print(f"⚠️ Log file does not exist yet")

        # Track the last position in the file
        last_position = LOG_FILE.stat().st_size if LOG_FILE.exists() else 0

        # Stream new log lines as they appear
        while True:
            await asyncio.sleep(0.5)  # Check every 500ms

            if not LOG_FILE.exists():
                continue

            current_size = LOG_FILE.stat().st_size

            if current_size > last_position:
                # File has grown, read new content
                with open(LOG_FILE, 'r', encoding='utf-8') as f:
                    f.seek(last_position)
                    new_lines = f.readlines()

                    for line in new_lines:
                        await websocket.send_json({"type": "new", "line": line.rstrip()})

                last_position = current_size

    except WebSocketDisconnect:
        print("Log viewer disconnected")
    except Exception as e:
        print(f"Error in log stream: {e}")


@app.delete("/api/history")
async def clear_history_endpoint():
    """Clear all history"""
    try:
        clear_history()
        return {"success": True, "message": "History cleared"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error clearing history: {str(e)}")


@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "version": "1.0.0",
        "dependencies": {
            "ffmpeg": os.system("which ffmpeg") == 0,
            "yt-dlp": True,  # Already checked in import
        }
    }


@app.get("/api/clips")
async def get_all_clips():
    """Get all generated clips from ToUpload folder"""
    try:
        clips = []
        upload_dir = BASE_DIR / "ToUpload"

        if not upload_dir.exists():
            return {"success": True, "clips": [], "count": 0}

        # Scan all project folders
        for project_folder in upload_dir.iterdir():
            if not project_folder.is_dir():
                continue

            # Check both original and reels subfolders
            for format_type in ["original", "reels"]:
                format_folder = project_folder / format_type
                if not format_folder.exists():
                    continue

                # Find all video files
                for video_file in format_folder.glob("*.mp4"):
                    # Look for corresponding _info.txt file
                    info_file = video_file.parent / f"{video_file.stem}_info.txt"

                    clip_info = {
                        "filename": video_file.name,
                        "project": project_folder.name,
                        "format": format_type,
                        "path": str(video_file.relative_to(BASE_DIR)),
                        "size": video_file.stat().st_size,
                        "created": datetime.fromtimestamp(video_file.stat().st_mtime).isoformat(),
                        "has_info": info_file.exists(),
                        "title": None
                    }

                    # Read info file if it exists and extract title
                    if info_file.exists():
                        with open(info_file, 'r', encoding='utf-8') as f:
                            info_text = f.read()
                            clip_info["info_text"] = info_text

                            # Extract title from info file
                            import re
                            title_match = re.search(r'Title:\s*(.+?)(?:\n|$)', info_text)
                            if title_match:
                                clip_info["title"] = title_match.group(1).strip()

                    clips.append(clip_info)

        # Sort by creation date (newest first)
        clips.sort(key=lambda x: x["created"], reverse=True)

        return {"success": True, "clips": clips, "count": len(clips)}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching clips: {str(e)}")


@app.get("/api/clips/{project}/{format}/{filename}")
async def get_clip_details(project: str, format: str, filename: str):
    """Get details for a specific clip"""
    try:
        upload_dir = BASE_DIR / "ToUpload"
        video_path = upload_dir / project / format / filename
        info_path = video_path.parent / f"{video_path.stem}_info.txt"

        if not video_path.exists():
            raise HTTPException(status_code=404, detail="Clip not found")

        clip_details = {
            "filename": filename,
            "project": project,
            "format": format,
            "path": str(video_path.relative_to(BASE_DIR)),
            "size": video_path.stat().st_size,
            "created": datetime.fromtimestamp(video_path.stat().st_mtime).isoformat(),
            "has_info": info_path.exists(),
            "info_text": ""
        }

        if info_path.exists():
            with open(info_path, 'r', encoding='utf-8') as f:
                clip_details["info_text"] = f.read()

        return {"success": True, "clip": clip_details}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching clip details: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    import socket

    # Get local IP for display
    try:
        # Create a socket to get the local IP
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
    except:
        local_ip = "YOUR_LOCAL_IP"

    print("\n" + "="*60)
    print("🎬 YTClipper Server Starting...")
    print("="*60)
    print(f"\n📱 Access from your phone (Chrome):")
    print(f"   http://{local_ip}:5000")
    print(f"\n💻 Access from this computer:")
    print(f"   http://localhost:5000")
    print(f"\n⚙️  Server running on all network interfaces (0.0.0.0:5000)")
    print(f"\n📖 Make sure your phone and computer are on the same WiFi!")
    print("="*60 + "\n")

    # Run server on all network interfaces
    uvicorn.run(
        app,
        host="0.0.0.0",  # Listen on all network interfaces
        port=5000,
        log_level="info"
    )
