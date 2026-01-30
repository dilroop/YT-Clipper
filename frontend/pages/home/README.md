# Home Page - Main Processing UI

This is the main landing page of YTClipper with the full video processing workflow.

## Components on This Page

### 1. Video Input Section
- YouTube URL input
- Thumbnail preview
- Format selector (Shorts/Long-form)
- Auto Create button (original workflow)
- Manual Choose button (clip selection workflow)

### 2. Progress Tracker
- WebSocket-based live progress updates
- 5 stages: Starting, Downloading, Transcribing, Analyzing, Processing
- Progress bar with percentage
- Cancel button
- Error handling with retry

### 3. Clip Selector (Manual Workflow)
- AI-analyzed clip suggestions
- Clip preview cards with:
  - Thumbnail
  - Title and reason
  - Time range and duration
  - Validation status
  - Checkbox for selection
- Edit clip button (opens clip editor modal)
- Generate Selected Clips button

### 4. Clip Editor Modal
- Full-screen modal with 2-column layout:
  - Left: List of clips (drag to reorder)
  - Right: Full transcript with text selection
- iOS/Android-style drag handles for clip boundary adjustment
- Add new clips from transcript text selection
- Word-boundary snapping
- Cached changes with ✓ confirm button
- Save/Cancel with change detection

### 5. Settings Modal
- Caption settings:
  - Enable/disable captions
  - Font size slider
  - Position slider
- AI validation settings:
  - Enable/disable validation
  - Minimum duration
  - Maximum duration
- Strategy selector
- Save to server

### 6. History Modal
- List of recently processed videos
- Thumbnail preview
- Title and view count
- Time ago
- Click to reload
- Clear history button

### 7. Results Section
- Download button for combined video
- Individual clip cards
- Gallery button

## File Organization

```
pages/home/
├── index.html      # Main HTML structure
├── home.css        # Home page specific styles (stub)
└── home.js         # Home page specific logic (stub)
```

## Current Status

- ✅ HTML moved to `pages/home/index.html`
- ✅ References `shared/common.css` for common styles
- ⏳ Still using monolithic `script.js` (to be extracted)
- ⏳ Still using monolithic `style.css` (to be extracted)
- ✅ `home.css` created (stub, ready for extraction)
- ✅ `home.js` created (stub, ready for extraction)

## Code to Extract

### From `script.js` (lines to extract):
- **Video Input Component** (~70-280)
- **Progress Tracker Component** (~281-600)
- **Clip Selector Component** (~845-1040)
- **Settings Panel Component** (~654-680)
- **History Panel Component** (~718-843)
- **Strategies Panel Component** (~1112-1152)
- **Clip Editor Component** (~1185-2247)

### From `style.css` (lines to extract):
- **Input section styles** (~200-400)
- **Progress section styles** (~700-1100)
- **Clip selector styles** (~1100-1500)
- **Clip editor styles** (~1503-2200)
- **Modal styles** (Already in `shared/common.css`)

## Future Improvements

1. Extract each component into `components/` directory
2. Convert to ES6 modules with proper imports/exports
3. Create unit tests for each component
4. Add component-specific error boundaries
5. Implement lazy loading for heavy components
6. Add loading skeletons for better UX

## Dependencies

- `shared/utils.js` - Utility functions (formatTime, showToast, etc.)
- `shared/api.js` - API calls (processVideo, analyzeVideo, etc.)
- `shared/websocket.js` - WebSocket connection manager
- `shared/common.css` - Common styles (variables, buttons, modals)

## Usage

The home page is served at the root URL `/` by the backend server:

```python
@app.get("/")
async def root():
    return FileResponse(str(BASE_DIR / "frontend" / "pages" / "home" / "index.html"))
```

All static assets are served from `/static/` mount point.
