# Test Scripts

This folder contains testing and development scripts for the YTClipper AI analyzer.

## Quick Start

### Fast Testing Workflow (Recommended)

```bash
# 1. Transcribe a video once (from project root)
python3 test/transcribe_local_video.py downloads/your-video.mp4

# 2. Test AI prompts instantly (no re-downloading!)
python3 test/test_ai_prompt.py

# 3. Edit backend/ai_analyzer.py to modify prompts

# 4. Test again immediately
python3 test/test_ai_prompt.py
```

## Scripts

### 📝 `transcribe_local_video.py`
Transcribe a local video file and save to `transcript.json` for fast testing.

**Usage:**
```bash
python3 test/transcribe_local_video.py <video_file> [output.json]
```

**Example:**
```bash
python3 test/transcribe_local_video.py downloads/-jDfA8BeOgw.mp4
```

**Output:** Creates `transcript.json` in project root

---

### 🤖 `test_ai_prompt.py` (Main Testing Tool)
Test AI analyzer with cached transcript - **FASTEST way to iterate on prompts!**

**Usage:**
```bash
python3 test/test_ai_prompt.py [--transcript file.json] [--clips N]
```

**Examples:**
```bash
# Use default transcript.json, find 5 clips
python3 test/test_ai_prompt.py

# Use custom transcript, find 10 clips
python3 test/test_ai_prompt.py --transcript my_video.json --clips 10
```

**Why use this:** Test different prompts in seconds without re-downloading/transcribing videos!

---

### 🎬 `analyze_video.py`
Full pipeline: download, transcribe, and analyze YouTube video (slower).

**Usage:**
```bash
python3 test/analyze_video.py <youtube_url>
```

**Example:**
```bash
python3 test/analyze_video.py https://www.youtube.com/watch?v=GRqPnRcfMIY
```

**When to use:** First-time analysis of a new YouTube video

---

### 💾 `save_transcript.py`
Download YouTube video, transcribe, and save transcript for testing.

**Usage:**
```bash
python3 test/save_transcript.py <youtube_url> [output.json]
```

**Example:**
```bash
python3 test/save_transcript.py https://www.youtube.com/watch?v=VIDEO_ID
```

---

### 📊 `test_ai_analyzer_request.py`
Show example OpenAI API request format and prompt structure.

**Usage:**
```bash
python3 test/test_ai_analyzer_request.py
```

**Output:** Displays full prompt, request structure, and makes live API call

---

## Workflow for Prompt Development

### Initial Setup
```bash
# 1. Transcribe a test video (one time)
python3 test/transcribe_local_video.py downloads/test-video.mp4
```

### Iteration Loop
```bash
# 2. Test current prompt
python3 test/test_ai_prompt.py

# 3. Edit backend/ai_analyzer.py (modify the prompt)
nano backend/ai_analyzer.py  # or use your editor

# 4. Test again (takes ~3 seconds vs 5+ minutes!)
python3 test/test_ai_prompt.py

# 5. Repeat steps 3-4 until satisfied
```

### Current Prompt Focus

The AI analyzer now prioritizes:
- 🚨 **CONTROVERSIAL** statements or shocking claims
- 💥 **EXTRAORDINARY** stories or impossible-seeming events
- 🤯 **MINDBLOWING** revelations that make people say "WHAT?!"
- 🎯 **HARD TRUTH BOMBS** that most people won't admit
- 🔥 **Provocative** or polarizing opinions that spark debate

## Environment Variables

Set in `.env` file:
```env
OPENAI_API_KEY=sk-your-key-here
OPENAI_MODEL=gpt-4o-mini
OPENAI_TEMPERATURE=1.0
```

## Output Format

All scripts show:
- ⏱️ **Time:** Start → End (Duration)
- 🔥 **Reason:** Why this clip is extraordinary/controversial/mindblowing
- 🏷️ **Keywords:** Related tags
- 📝 **Text:** Preview of the clip content

## Tips

- Use `test_ai_prompt.py` for rapid iteration
- Adjust `OPENAI_TEMPERATURE` in `.env` (0.0-2.0) for more/less creative responses
- Keep transcripts in project root for easy access
- Test with multiple videos to ensure prompt works across different content types
