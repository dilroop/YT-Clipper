# YTClipper Data Flow Documentation

## 📊 Complete Data Flow and Properties Tracking

This document describes all data properties tracked throughout the YTClipper application lifecycle.

---

## 1. URL Input Stage

**Endpoint:** `POST /api/thumbnail`

**Trigger:** User pastes YouTube URL into input field

**Properties Fetched:**
```json
{
    "url": "https://youtube.com/watch?v=...",
    "video_id": "extracted_video_id",
    "title": "Video Title",
    "channel": "Channel Name",
    "duration": 1234,
    "thumbnail": "https://i.ytimg.com/...",
    "thumbnail_fallback": "https://img.youtube.com/...",
    "description": "Video description text"
}
```

**Saved To:**
- **SQLite Database** (`ytclipper.db` → `history` table)
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

**History Uniqueness:**
- Only unique videos (by `video_id`) are stored in history
- If the same video is accessed again, the existing entry is updated with a new timestamp
- This ensures the history shows only unique links, with the most recent access time

---

## 2. Analysis Phase

**Endpoint:** `POST /api/analyze`

**Trigger:** User clicks "Auto Create" or "Manually Choose"

### 2A. Transcription Data

**Source:** Whisper AI model

**Properties:**
```json
{
    "segments": [
        {
            "id": 0,
            "seek": 0,
            "start": 0.0,
            "end": 5.2,
            "text": " transcribed text",
            "tokens": [50364, 2425, ...],
            "temperature": 0.0,
            "avg_logprob": -0.5,
            "compression_ratio": 1.5,
            "no_speech_prob": 0.01,
            "words": [
                {
                    "start": 0.0,
                    "end": 0.5,
                    "word": "Hello",
                    "probability": 0.95
                }
            ]
        }
    ]
}
```

### 2B. AI Analysis Data

**Source:** OpenAI GPT-4 (or fallback analyzer)

**Clip Suggestions:**
```json
{
    "clips": [
        {
            "start": 10.5,
            "end": 25.3,
            "title": "Interesting Moment Title",
            "reason": "Why this clip is interesting",
            "text": "Full transcript of this section",
            "keywords": ["keyword1", "keyword2", "keyword3"],
            "youtube_link": "https://youtube.com/watch?v=...&t=10",
            "words": [
                {
                    "start": 10.5,
                    "end": 10.8,
                    "word": "And",
                    "probability": 0.99
                }
            ]
        }
    ]
}
```

**Response to Frontend:**
```json
{
    "success": true,
    "clips": [...],
    "video_info": {
        "title": "...",
        "channel": "...",
        "duration": 1234,
        "url": "..."
    }
}
```

---

## 3. Processing Phase

**Endpoint:** `POST /api/process`

**Trigger:** User confirms clip selection and clicks "Generate"

### 3A. Request Data

```json
{
    "url": "https://youtube.com/watch?v=...",
    "format": "reels" | "original",
    "burn_captions": true | false,
    "selected_clips": [0, 2, 4],
    "preanalyzed_clips": [
        {
            "start": 10.5,
            "end": 25.3,
            "title": "...",
            "reason": "...",
            "text": "...",
            "keywords": [...],
            "words": [...]
        }
    ]
}
```

### 3B. Video Processing

**Steps:**
1. **Download video** (yt-dlp or pytube)
2. **Extract audio** (if not using preanalyzed)
3. **Transcribe** (Whisper - if not using preanalyzed)
4. **Analyze clips** (AI - if not using preanalyzed)
5. **Create clips** (FFmpeg)
6. **Burn captions** (FFmpeg + drawtext filter - optional)
7. **Organize files** (move to project folder)

### 3C. Progress Updates

**Via WebSocket:** `ws://localhost:5000/ws`

```json
{
    "stage": "downloading" | "transcribing" | "analyzing" | "clipping" | "organizing",
    "percent": 0-100,
    "message": "Status message",
    "details": "Detailed progress info"
}
```

---

## 4. File Storage Structure

### 4A. Project Folder

```
ToUpload/
└── Video_Title_YYYY-MM-DD_N/
    ├── original/
    │   ├── clip_001.mp4
    │   ├── clip_001_info.json  ✅ NEW JSON FORMAT
    │   ├── clip_002.mp4
    │   └── clip_002_info.json
    └── reels/
        ├── clip_001.mp4
        ├── clip_001_info.json
        ├── clip_002.mp4
        └── clip_002_info.json
```

### 4B. Info File Format

**New JSON Format** (`_info.json`):
```json
{
  "clip": {
    "title": "Interesting Clip Title",
    "description": "AI-generated reason why this clip is interesting",
    "keywords": ["tag1", "tag2", "tag3"],
    "start_time": "00:00:10",
    "end_time": "00:00:25",
    "duration_seconds": 15.0,
    "format": "reels"
  },
  "video": {
    "title": "Original YouTube Video Title",
    "channel": "Channel Name",
    "description": "Video description (first 500 chars)...",
    "url": "https://youtube.com/watch?v=..."
  },
  "transcript": "Full transcript text for this clip segment with word-level timing preserved"
}
```

**Legacy Text Format** (`_info.txt` - backward compatible):
```
================================
CLIP TITLE: Interesting Clip Title

CLIP DESCRIPTION:
AI-generated reason why this clip is interesting

KEYWORDS: tag1, tag2, tag3

================================
VIDEO TITLE: Original YouTube Video Title
CHANNEL: Channel Name
DESCRIPTION: Video description...
URL: https://youtube.com/watch?v=...
TIMESTAMP: 00:00:10 - 00:00:25 (15 seconds)
FORMAT: reels

TRANSCRIPT:
Full transcript text for this clip segment

================================
```

---

## 5. Gallery & Clips API

**Endpoint:** `GET /api/clips`

**Response:**
```json
{
    "success": true,
    "clips": [
        {
            "filename": "clip_001.mp4",
            "project": "Video_Title_YYYY-MM-DD_1",
            "format": "reels",
            "path": "ToUpload/Project/format/clip_001.mp4",
            "size": 1234567,
            "created": "2026-01-28T12:34:56",
            "has_info": true,
            "title": "Interesting Clip Title",

            // NEW: JSON format data
            "info_data": {
                "clip": {...},
                "video": {...},
                "transcript": "..."
            },

            // OLD: Text format (backward compatibility)
            "info_text": "raw text content..."
        }
    ]
}
```

**Endpoint:** `GET /api/clips/{project}/{format}/{filename}`

**Response:**
```json
{
    "success": true,
    "clip": {
        "filename": "clip_001.mp4",
        "project": "Video_Title_YYYY-MM-DD_1",
        "format": "reels",
        "path": "ToUpload/.../clip_001.mp4",
        "size": 1234567,
        "created": "2026-01-28T12:34:56",
        "has_info": true,
        "info_data": {...}  // or "info_text" for old format
    }
}
```

---

## 6. History API

**Endpoint:** `GET /api/history?limit=50`

**Response:**
```json
{
    "success": true,
    "count": 10,
    "history": [
        {
            "id": 1,
            "url": "https://youtube.com/watch?v=...",
            "video_id": "dQw4w9WgXcQ",
            "title": "Video Title",
            "channel": "Channel Name",
            "duration": 1234,
            "description": "Video description",
            "thumbnail": "https://...",
            "timestamp": "2026-01-28T12:34:56"
        }
    ]
}
```

**Endpoint:** `DELETE /api/history`

Clears all history from database.

---

## Summary of All Tracked Properties

### Database (History)
- `id` - Auto-incrementing primary key
- `url` - Full YouTube URL
- `video_id` - YouTube video ID
- `title` - Video title
- `channel` - Channel name
- `duration` - Duration in seconds
- `description` - Video description
- `thumbnail` - Thumbnail URL
- `timestamp` - When added to history

### Transcription
- `segments` - Array of transcript segments
- `start`, `end` - Timestamps in seconds
- `text` - Transcribed text
- `words` - Word-level timing data
- `confidence` - Transcription confidence scores

### Clips (JSON Info)
- **Clip metadata:**
  - `title` - AI-generated title
  - `description` - Why clip is interesting
  - `keywords` - Extracted tags
  - `start_time`, `end_time` - Formatted timestamps
  - `duration_seconds` - Clip length
  - `format` - "original" or "reels"

- **Video metadata:**
  - `title`, `channel`, `description`, `url`

- **Content:**
  - `transcript` - Full caption text

### File Metadata
- `filename` - Clip filename
- `project` - Project folder name
- `format` - Video format (original/reels)
- `path` - Relative file path
- `size` - File size in bytes
- `created` - Creation timestamp

---

## Configuration

**Config file:** `config.json`

```json
{
    "downloader_backend": "yt-dlp" | "pytube",
    "caption_settings": {
        "words_per_caption": 2,
        "font_family": "Impact",
        "font_size": 48,
        "vertical_position": 80
    },
    "watermark_settings": {
        // Future implementation
    }
}
```

---

## Implementation Status

✅ **Implemented:**
- SQLite history tracking
- JSON info file format
- Backward compatibility with TXT format
- Word-level timing preservation
- Complete metadata tracking
- Gallery/detail page JSON parsing

🔄 **In Progress:**
- Watermark settings

---

**Last Updated:** January 28, 2026
