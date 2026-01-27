# YTClipper Project Context

Mobile-first web application for clipping YouTube videos with AI-powered analysis, auto-captioning, and reels conversion.

---

## API Endpoints

### Core Processing
- `POST /api/thumbnail` - Get video thumbnail and metadata without downloading
- `POST /api/analyze` - Analyze video and return AI-suggested clips WITHOUT creating them (for manual clip selection)
- `POST /api/process` - Full pipeline: download, analyze, clip, caption, and organize video clips

### Configuration
- `GET /api/config` - Get current configuration (caption/watermark settings)
- `POST /api/config` - Update configuration settings

### Clips Management
- `GET /api/clips` - Get all generated clips from ToUpload folder with metadata
- `GET /api/clips/{project}/{format}/{filename}` - Get details for a specific clip including info file

### History
- `GET /api/history` - Get video processing history from SQLite database
- `DELETE /api/history` - Clear all history

### Logs
- `GET /api/logs` - Get the last N lines from log file (default 500)
- `WebSocket /ws/logs` - Live streaming logs with auto-updates

### System
- `GET /api/health` - Health check endpoint for dependencies (ffmpeg, yt-dlp)
- `WebSocket /ws` - WebSocket for real-time progress updates during processing

### Static Pages
- `GET /` - Main index page (video input and processing)
- `GET /gallery.html` - Gallery of all generated clips
- `GET /clip-detail.html` - Detailed clip view with video player and copyable metadata
- `GET /logs.html` - Live log viewer

---

## Frontend Pages & Features

### 1. Index Page (`index.html`)
**Purpose:** Main video processing interface

**Features:**
- URL input with validation
- Thumbnail preview with metadata (title, channel, duration)
- Processing mode selection (Auto vs Manual)
- Format selection (Original 16:9 vs Reels 9:16)
- Caption toggle (burn captions on/off)
- Real-time progress updates via WebSocket
- Video history sidebar with recent videos
- Manual clip selection interface with preview
- Copy YouTube timestamp links for each clip
- Navigation to gallery and logs

**Key JavaScript:** Inline in HTML file

### 2. Gallery Page (`gallery.html`)
**Purpose:** Browse all generated clips

**Features:**
- Grid view of all clips with video thumbnails
- Filter by format (All, Original, Reels)
- Display clip title, filename, size, and creation date
- Total clips count and total size statistics
- Click to view clip details
- Refresh button to reload clips
- Home navigation

**JavaScript:** `gallery.js`

### 3. Clip Detail Page (`clip-detail.html`)
**Purpose:** View and download individual clips

**Features:**
- Full-screen video player with controls
- Copyable content sections:
  - Clip Title (from AI analysis)
  - Clip Description (AI-generated reason)
  - Tags/Keywords (extracted from AI analysis)
- Clip metadata (filename, project, format, size, created date)
- Download button
- View full info file metadata
- Copy-to-clipboard functionality with toast notifications
- Back to gallery and home navigation

**JavaScript:** `clip-detail.js`

### 4. Logs Page (`logs.html`)
**Purpose:** Live log streaming viewer

**Features:**
- Live WebSocket connection for real-time logs
- Auto-scroll functionality (toggleable)
- Line count display
- Color-coded log levels (error, warning, info, success, debug)
- Clear display button
- Connection status indicator
- Auto-reconnect on disconnect
- GitHub-style log viewer interface

**JavaScript:** `logs.js`

---

## Folder Structure

```
YTClipper/
├── .claude/                    # Claude Code configuration
│   ├── settings.local.json     # Local Claude settings
│   └── project-context.md      # This file - project reference
│
├── backend/                    # Python backend modules
│   ├── server.py               # FastAPI server (main entry point)
│   ├── downloader.py           # YouTube video downloader (yt-dlp)
│   ├── transcriber.py          # Audio transcription (Whisper)
│   ├── analyzer.py             # Simple keyword-based clip analyzer
│   ├── ai_analyzer.py          # AI-powered clip analyzer (OpenAI GPT)
│   ├── clipper.py              # Video clipping (ffmpeg)
│   ├── caption_generator.py    # Caption generation and burning (ASS format)
│   ├── reels_processor.py      # Reels conversion with face detection
│   ├── watermark_processor.py  # Watermark overlay
│   └── file_manager.py         # File organization and cleanup
│
├── frontend/                   # HTML/CSS/JS frontend
│   ├── index.html              # Main page
│   ├── gallery.html            # Clips gallery
│   ├── clip-detail.html        # Clip detail view
│   ├── logs.html               # Log viewer
│   ├── gallery.js              # Gallery page logic
│   ├── clip-detail.js          # Clip detail page logic
│   └── logs.js                 # Log viewer logic
│
├── temp/                       # Temporary files (auto-cleanup)
│   ├── *_audio.wav             # Extracted audio files
│   ├── clip_*.ass              # ASS subtitle files
│   ├── clip_*_captioned.mp4    # Captioned clips (intermediate)
│   └── clip_*_reels.mp4        # Reels clips (intermediate)
│
├── downloads/                  # Downloaded videos (kept for reference)
│   └── {video_id}.mp4          # Original downloaded videos
│
├── ToUpload/                   # Final organized output
│   └── {Project_Name}_{Date}/  # Project folders
│       ├── original/           # Original format clips (16:9)
│       │   ├── clip_001.mp4
│       │   ├── clip_001_info.txt
│       │   └── ...
│       └── reels/              # Reels format clips (9:16)
│           ├── clip_001.mp4
│           ├── clip_001_info.txt
│           └── ...
│
├── tests/                      # Test scripts and utilities
│   ├── test_dual_face.py       # Test dual-face detection
│   └── visualize_face_detection.py  # Visualize face detection boundaries
│
├── logs/                       # Application logs
│   └── ytclipper.log           # Main log file (timestamped)
│
├── history.db                  # SQLite database for video history
├── config.json                 # User configuration (captions, watermark)
├── .env                        # Environment variables (API keys)
└── requirements.txt            # Python dependencies

```

---

## Key Processing Pipeline

1. **Download** (`downloader.py`) - yt-dlp downloads video to `downloads/`
2. **Transcribe** (`transcriber.py`) - Extracts audio to `temp/`, Whisper transcribes with word timestamps
3. **Analyze** (`ai_analyzer.py` or `analyzer.py`) - AI or keyword-based clip selection with title/description/keywords
4. **Clip** (`clipper.py`) - Extract clips to `temp/`
5. **Reels** (`reels_processor.py`) - Convert to 9:16 with face detection (optional, dual-face split-screen support)
6. **Caption** (`caption_generator.py`) - Generate ASS subtitles in `temp/`, burn onto video
7. **Watermark** (`watermark_processor.py`) - Add watermark if enabled (optional)
8. **Organize** (`file_manager.py`) - Copy to `ToUpload/` with info files containing AI metadata
9. **Cleanup** - Delete temp files on success, keep downloaded video

---

## Important Implementation Details

### Dual-Face Detection Algorithm
**Location:** `backend/reels_processor.py`

Uses OpenCV Haar Cascade face detection to detect speakers and create intelligent crops for reels format:

**Single-face mode:** Centers crop on detected face or uses default position
**Dual-face mode:** Creates split-screen with two 9:8 boxes stacked vertically to make 9:16

**Algorithm (corner-based):**
```
Given face with corners: topLeft (LT) and rightBottom (RB)
Box.LT-x = Face.LT-x - face.width
Box.LT-y = Face.LT-y - (face.height / 2)
Box.RB-x = Face.RB-x + face.width
Box.RB-y = Face.RB-y + (face.height * 0.75)

Then conform to 9:8 ratio, scale to 1080px width
```

**Dynamic mode:** Checks faces every 8 frames and switches between dual/single mode as needed

### AI Metadata Utilization
**Location:** `backend/server.py` (lines 673-685), `backend/file_manager.py` (lines 104-129)

OpenAI GPT-4 generates for each clip:
- **Title:** Short descriptive title
- **Reason:** Why this clip is interesting
- **Keywords:** Relevant tags/topics

These are saved to `_info.txt` files in the output folder and displayed in the clip detail page.

### Temp File Management
**Location:** All modules use `./temp` folder

All intermediate files (audio, clips, subtitles) are created in the centralized `temp/` folder and cleaned up only after successful completion. This eliminates redundant operations like re-extracting audio.

### Logging System
**Location:** `backend/server.py` (lines 59-85)

Custom `TeeOutput` class writes to both console and log file with timestamps. Logs are served via REST API and WebSocket for live viewing.

---

## Configuration Files

### `.env` - Environment Variables
```
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini
OPENAI_TEMPERATURE=1.0
```

### `config.json` - User Settings
```json
{
  "caption_settings": {
    "font_name": "Arial",
    "font_size": 24,
    "bold": true,
    "primary_color": "&H00FFFFFF",
    "outline_color": "&H00000000"
  },
  "watermark_settings": {
    "enabled": true,
    "text": "@YourHandle",
    "position": "bottom_right"
  }
}
```

---

## Database Schema

### `history` Table (SQLite)
```sql
CREATE TABLE history (
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
```

---

## Dependencies

**Python:**
- FastAPI - Web framework
- yt-dlp - YouTube downloader
- openai-whisper - Speech-to-text
- opencv-python - Face detection
- openai - GPT-4 API
- ffmpeg-python - Video processing wrapper

**System:**
- ffmpeg - Video/audio processing
- Python 3.8+

---

## Server Info

**Host:** 0.0.0.0:5000 (accessible on local network)
**Protocol:** HTTP with WebSocket support
**CORS:** Enabled for all origins
