# Multi-Format Reels System

## Overview

The YTClipper now supports three different output formats for reels conversion, allowing flexible content creation with different layouts and AI content integration.

## Output Formats

### Format 1: Vertical 9:16 (Standard)
- **Constant**: `FORMAT_VERTICAL_9_16`
- **Output**: 1080x1920 (standard vertical reels)
- **Features**:
  - Full 9:16 aspect ratio
  - Dual-face split-screen mode (two 9:8 boxes stacked)
  - Single-face tracking with Bezier interpolation
  - Zero-face smooth panning
  - Automatic mode switching based on face detection

### Format 2: Stacked 9:8 (AI Photo)
- **Constant**: `FORMAT_STACKED_PHOTO`
- **Output**: 1080x1920 (two 1080x960 boxes stacked)
- **Features**:
  - **TOP box**: AI-generated animated photo (placeholder or custom)
  - **BOTTOM box**: Tracked podcast highlight with face following
  - Audio from bottom box (podcast audio)
  - Optional caption overlay
  - Smooth face tracking in bottom box

### Format 3: Stacked 9:8 (AI Video)
- **Constant**: `FORMAT_STACKED_VIDEO`
- **Output**: 1080x1920 (two 1080x960 boxes stacked)
- **Features**:
  - **TOP box**: AI-generated video (animated placeholder or custom)
  - **BOTTOM box**: Tracked podcast highlight with face following
  - Audio from bottom box (podcast audio)
  - Optional caption overlay
  - Animated content in top box

## Usage

### Python API

```python
from backend.reels_processor import ReelsProcessor, FORMAT_VERTICAL_9_16, FORMAT_STACKED_PHOTO, FORMAT_STACKED_VIDEO

processor = ReelsProcessor()

# Format 1: Standard 9:16
result = processor.convert_to_reels(
    video_path="input.mp4",
    output_path="output_9x16.mp4",
    output_format=FORMAT_VERTICAL_9_16,
    auto_detect=True,
    dynamic_mode=True
)

# Format 2: Stacked with AI Photo
result = processor.convert_to_reels(
    video_path="input.mp4",
    output_path="output_photo.mp4",
    output_format=FORMAT_STACKED_PHOTO,
    ai_content_path="ai_photo.jpg",  # Optional, uses placeholder if None
    caption_text="Your caption here"  # Optional
)

# Format 3: Stacked with AI Video
result = processor.convert_to_reels(
    video_path="input.mp4",
    output_path="output_video.mp4",
    output_format=FORMAT_STACKED_VIDEO,
    ai_content_path="ai_video.mp4",  # Optional, uses placeholder if None
    caption_text="Your caption here"  # Optional
)
```

### Parameters

- `video_path` (str): Path to input video
- `output_path` (str, optional): Path for output video
- `auto_detect` (bool, default=True): Use face detection for cropping
- `dynamic_mode` (bool, default=True): Enable dynamic mode switching
- `output_format` (str, optional): Format type (defaults to FORMAT_VERTICAL_9_16)
  - `FORMAT_VERTICAL_9_16`: Standard vertical reels
  - `FORMAT_STACKED_PHOTO`: Stacked with AI photo on top
  - `FORMAT_STACKED_VIDEO`: Stacked with AI video on top
- `ai_content_path` (str, optional): Path to AI-generated content
  - For stacked formats only
  - If None, uses generated placeholder
- `caption_text` (str, optional): Caption text to overlay at bottom

### Return Value

```python
{
    'success': True/False,
    'output_path': '/path/to/output.mp4',
    'mode': 'vertical_9x16' | 'stacked_photo' | 'stacked_video',
    'format': '1080x1920 (description)',  # For stacked formats
    'error': 'Error message'  # If success=False
}
```

## Testing

### Run Test Suite

```bash
# Test all three formats
python3 tests/test_formats.py

# Results will be in tests/results/test-formats-{timestamp}/
```

### Test Output

The test script will:
1. Extract first 30 seconds of test_clip.mp4
2. Convert to all three formats
3. Generate VERIFY.txt with manual check instructions
4. Display success/failure for each format

### Verification Checklist

**Format 1 (Vertical 9:16):**
- ✓ Full 9:16 aspect ratio (1080x1920)
- ✓ Face tracking with Bezier interpolation
- ✓ Dual-face split-screen if 2 faces detected
- ✓ Zero-face panning if no faces detected

**Format 2 (Stacked Photo):**
- ✓ Two 9:8 boxes (1080x960 each) stacked vertically
- ✓ Top box shows static placeholder or AI photo
- ✓ Bottom box tracks face smoothly
- ✓ Audio from bottom box (podcast)
- ✓ Captions at bottom if provided

**Format 3 (Stacked Video):**
- ✓ Two 9:8 boxes (1080x960 each) stacked vertically
- ✓ Top box shows animated placeholder or AI video
- ✓ Bottom box tracks face smoothly
- ✓ Audio from bottom box (podcast)
- ✓ Captions at bottom if provided

## AI Content Integration

### Placeholders

When `ai_content_path` is None or file doesn't exist:

- **Photo placeholder**: Solid color (dark gray) with "AI Photo Placeholder" text
- **Video placeholder**: Animated test pattern with "AI Video Placeholder" text

### Custom AI Content

To use custom AI-generated content:

1. Generate AI content (photo or video) using your AI service
2. Save to file (e.g., `ai_photo.jpg` or `ai_video.mp4`)
3. Pass path via `ai_content_path` parameter
4. Content will be automatically resized to 1080x960 (9:8)
5. Duration will match input video

**Supported formats:**
- **Photo**: JPG, PNG, etc. (will be converted to video)
- **Video**: MP4, MOV, etc. (will be trimmed/looped to match duration)

## UI Icons (Recommended Design)

### Icon 1: Vertical 9:16
```
┌─────┐
│     │
│ 9:16│
│     │
└─────┘
```
Simple rectangle with "9:16" text

### Icon 2: Stacked Photo
```
┌─────┐
│🏔️ ✨│ ← Photo icon + AI star
├─────┤
│ 9:8 │ ← Text "9:8"
└─────┘
```
Stacked rectangle with mountain/photo icon + AI star (top), "9:8" text (bottom)

### Icon 3: Stacked Video
```
┌─────┐
│🎬 ✨│ ← Video icon + AI star
├─────┤
│ 9:8 │ ← Text "9:8"
└─────┘
```
Stacked rectangle with video icon + AI star (top), "9:8" text (bottom)

## Technical Details

### Face Tracking Settings

Configured in `backend/reels_processor.py`:

```python
FACE_CHECK_INTERVAL_FRAMES = 4  # Check faces every 4 frames
USE_SMOOTH_INTERPOLATION = True  # Bezier curve interpolation
SMOOTHING_STRENGTH = 0.5  # 0.0-1.0 smoothness
ENABLE_ZERO_FACE_PANNING = True  # Pan when no faces
PAN_LEFT_BOUNDARY = 0.15  # Pan from 15% width
PAN_RIGHT_BOUNDARY = 0.85  # Pan to 85% width
PAN_CYCLE_DURATION = 8.0  # 8 seconds per pan cycle
```

### Processing Pipeline

**Format 1 (Vertical 9:16):**
1. Detect face segments (0/1/2 faces)
2. Apply appropriate mode (panning/tracking/split-screen)
3. Generate smooth crop expressions
4. Convert to 1080x1920

**Format 2 & 3 (Stacked):**
1. Detect face positions in input video
2. Generate smooth tracking for 9:8 crop
3. Create bottom box (1080x960) with tracking
4. Generate or load top box (1080x960) with AI content
5. Stack boxes vertically (1080x1920)
6. Add captions if provided
7. Merge audio from bottom box

### Performance

- Face detection: ~0.13s per check (@30fps, every 4 frames)
- Bezier interpolation: <1s preprocessing
- FFmpeg encoding: Depends on video length and preset
- Total time: ~1-3x video duration (depending on format)

## Architecture

### New Methods

**`backend/reels_processor.py`:**

- `convert_to_reels()` - Updated with format selection
- `_convert_to_stacked_format()` - Main stacked format processor
- `_generate_ai_photo_placeholder()` - Creates photo placeholder
- `_generate_ai_video_placeholder()` - Creates video placeholder
- `_add_captions_overlay()` - Adds caption text overlay

### New Constants

```python
FORMAT_VERTICAL_9_16 = "vertical_9x16"
FORMAT_STACKED_PHOTO = "stacked_photo"
FORMAT_STACKED_VIDEO = "stacked_video"
```

## Future Enhancements

1. **Real AI Integration**:
   - Connect to AI image generation (DALL-E, Midjourney, Stable Diffusion)
   - Connect to AI video generation (Runway, Pika, etc.)
   - Auto-generate content based on podcast transcript

2. **Caption Generation**:
   - Auto-transcribe podcast using Whisper
   - Generate captions automatically
   - Support multiple caption styles

3. **UI Improvements**:
   - Visual format selector with icons
   - Real-time preview
   - Drag-and-drop AI content upload
   - Caption editor

4. **Additional Formats**:
   - 1:1 square for Instagram
   - 4:5 portrait for Instagram feed
   - Custom aspect ratios

## Troubleshooting

### Issue: "Cannot open video"
- **Cause**: Invalid video path or corrupted file
- **Fix**: Check file exists and is readable

### Issue: "Error in stacked conversion"
- **Cause**: FFmpeg error or missing dependencies
- **Fix**: Check FFmpeg is installed and up to date

### Issue: Captions not visible
- **Cause**: Caption text empty or drawtext filter error
- **Fix**: Verify caption_text is non-empty string

### Issue: Top box placeholder looks wrong
- **Cause**: FFmpeg lavfi issues
- **Fix**: Update FFmpeg to latest version

## Support

For issues or questions:
1. Check VERIFY.txt in test results folder
2. Review FFmpeg error messages
3. Test with smaller video clips first
4. Ensure all dependencies are installed

## License

Same as YTClipper project license.
