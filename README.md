# 🎬 YTClipper - YouTube Video Clipper

A mobile-first web application for automatically clipping interesting moments from YouTube videos, optimized for creating Reels and social media content.

## PreRequests
- Install ffmpeg from Homebrew

## ✅ What's Been Built (Phase 1 Complete!)

### Backend
- ✅ FastAPI server with network access (accessible from phone)
- ✅ YouTube thumbnail & metadata preview API
- ✅ Configuration management system
- ✅ WebSocket support for real-time updates
- ✅ Health check endpoint

### Frontend
- ✅ Mobile-first responsive UI (optimized for Chrome on phone)
- ✅ YouTube URL input with clear button
- ✅ Thumbnail preview with video metadata
- ✅ Format selection (Original 16:9 / Reels 9:16)
- ✅ "Burn Captions into Video" toggle
- ✅ Settings modal for caption styling
- ✅ Touch-friendly buttons and controls

### Dependencies Installed
- ✅ yt-dlp (YouTube downloading)
- ✅ ffmpeg (video processing)
- ✅ OpenAI Whisper (transcription)
- ✅ OpenCV (face detection for reels)
- ✅ FastAPI + Uvicorn (web server)
- ✅ All Python dependencies

## 🚀 How to Start the Server

### Quick Start:
```bash
cd /Users/dilroop.singh/YTClipper
python3 backend/server.py
```

The server will automatically:
- Start on port 5000
- Listen on all network interfaces (0.0.0.0)
- Display your local IP address for phone access

### You'll see output like:
```
============================================================
🎬 YTClipper Server Starting...
============================================================

📱 Access from your phone (Chrome):
   http://192.168.1.X:5000

💻 Access from this computer:
   http://localhost:5000

⚙️  Server running on all network interfaces (0.0.0.0:5000)

📖 Make sure your phone and computer are on the same WiFi!
============================================================
```

## 📱 How to Use from Your Phone

### One-Time Setup:
1. Make sure your phone and Mac are on the **same WiFi network**
2. Start the server (see command above)
3. On your phone, open Chrome
4. Go to: `http://[YOUR_LOCAL_IP]:5000` (shown when server starts)
5. Bookmark the page for easy access

### Daily Use:
1. Find a YouTube video you want to clip
2. Copy the video URL (Share → Copy Link)
3. Open Chrome → Open YTClipper bookmark
4. Paste URL in the input field
5. See the thumbnail preview instantly!
6. Select format: Original (16:9) or Reels (9:16)
7. Toggle "Burn Captions into Video" (ON by default)
8. Tap "Process Video"

## 🎯 Features Currently Working

### ✅ Fully Functional:
- URL input with auto-clear button
- YouTube video thumbnail preview
- Video metadata display (title, channel, duration)
- Format selection (Original/Reels)
- Burn captions toggle
- Settings modal with caption styling options
- Mobile-optimized touch interface
- Network access from phone

### 🚧 Coming in Phase 2:
- Video downloading
- Whisper transcription
- Interesting section detection
- Actual video clipping
- Caption burning into video
- Reels format with auto-focus
- Results with download/share buttons

## 📂 Project Structure

```
/YTClipper
  /backend
    - server.py              ← FastAPI server (READY)
  /frontend
    - index.html            ← Mobile UI (READY)
    - style.css             ← Mobile-first styles (READY)
    - script.js             ← Frontend logic (READY)
  /Downloads                ← Original video downloads
  /ToUpload                 ← Final clips will go here
  /temp                     ← Temporary processing files
  /watermarks               ← User uploaded watermarks
  - config.json             ← Settings storage (READY)
  - README.md               ← This file
  - plan.txt                ← Full project plan
  - project.txt             ← Project description
```

## 🧪 Testing

The system has been tested with:
- Test video: https://www.youtube.com/watch?v=GRqPnRcfMIY
- Successfully fetches metadata and thumbnail
- All UI elements are touch-friendly and mobile-optimized

### Test the API:
```bash
# Health check
curl http://localhost:5000/api/health

# Thumbnail preview
curl -X POST http://localhost:5000/api/thumbnail \
  -H "Content-Type: application/json" \
  -d '{"url":"https://www.youtube.com/watch?v=GRqPnRcfMIY"}'
```

## ⚙️ Configuration

Settings are stored in `config.json` and can be modified via the Settings modal in the UI.

Current settings:
- Caption words per line: 2
- Font: Impact
- Font size: 48px
- Vertical position: 80% (lower third)
- Burn captions: Enabled by default

## 🔄 Next Steps (Phase 2)

1. Implement video downloading with yt-dlp
2. Add Whisper transcription with word-level timestamps
3. Build interesting section detection algorithm
4. Implement video clipping with ffmpeg
5. Add caption generation and burning
6. Create file organization system (_info.txt files)
7. Test end-to-end workflow

## 📝 Notes

- **Server must be running** for the app to work
- **Same WiFi required** for phone access
- Bookmarking the page in Chrome makes access instant
- Server can be stopped with Ctrl+C
- All processing happens on your Mac (fast, doesn't drain phone battery)

## 🎉 What You Have Now

A fully functional mobile-first web interface that:
- Accepts YouTube URLs from your phone
- Shows thumbnail previews instantly
- Lets you configure output format and caption settings
- Has a beautiful, touch-friendly UI
- Is ready for Phase 2 implementation (actual video processing)

---

**Built with:** Python, FastAPI, yt-dlp, ffmpeg, OpenAI Whisper, OpenCV

**Status:** Phase 1 Complete ✅ | Phase 2 Coming Next 🚀
