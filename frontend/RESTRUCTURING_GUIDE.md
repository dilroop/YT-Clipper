# Frontend Restructuring Guide

## Current Structure

The frontend has been reorganized into a modular structure:

```
frontend/
├── index.html                    # Main entry point
├── script.js                     # Original monolithic JS (to be deprecated)
├── style.css                     # Original monolithic CSS (to be deprecated)
│
├── pages/                        # Individual pages
│   ├── clip-detail/
│   │   ├── index.html
│   │   ├── clip-detail.js
│   │   └── clip-detail.css
│   ├── gallery/
│   │   ├── index.html
│   │   ├── gallery.js
│   │   └── gallery.css
│   └── logs/
│       ├── index.html
│       ├── logs.js
│       └── logs.css
│
├── components/                   # Reusable UI components
│   ├── video-input/
│   │   ├── video-input.js
│   │   └── video-input.css
│   ├── progress-tracker/
│   │   ├── progress-tracker.js
│   │   └── progress-tracker.css
│   ├── clip-editor/
│   │   ├── clip-editor.js       # ✅ Created (stub)
│   │   └── clip-editor.css      # To be extracted
│   ├── clip-selector/
│   │   ├── clip-selector.js
│   │   └── clip-selector.css
│   ├── settings-panel/
│   │   ├── settings-panel.js
│   │   └── settings-panel.css
│   ├── history-panel/
│   │   ├── history-panel.js
│   │   └── history-panel.css
│   └── strategies-panel/
│       ├── strategies-panel.js
│       └── strategies-panel.css
│
└── shared/                       # Shared utilities and styles
    ├── utils.js                  # ✅ Created
    ├── api.js                    # ✅ Created
    ├── websocket.js              # ✅ Created
    └── common.css                # ✅ Created
```

## Completed Steps

1. ✅ Created folder structure
2. ✅ Moved page files (clip-detail, gallery, logs) to `pages/` folder
3. ✅ Created shared modules:
   - `shared/utils.js` - Common utility functions
   - `shared/api.js` - API communication functions
   - `shared/websocket.js` - WebSocket manager
   - `shared/common.css` - Shared styles (reset, variables, buttons, modals)
4. ✅ Created clip-editor component stub

## Code Mapping Guide

### From script.js → Component Files

#### Clip Editor Component (`components/clip-editor/`)
**Lines: ~1185-2247 in script.js**

- State: `editorState` object
- Functions to extract:
  - `splitMultiPartClips()`
  - `openClipEditor()`
  - `closeClipEditor()`
  - `extractTranscriptSegments()`
  - `buildTranscriptWordMapping()`
  - `getAbsoluteCharPosition()`
  - `findWordIndexByCharPosition()`
  - `findWordIndexByTime()`
  - `renderEditorClips()`
  - `createEditorClipCard()`
  - `renderEditorTranscript()`
  - `enableTranscriptSelection()`
  - `showSelectionPreview()`
  - `createNewClipFromSelection()`
  - `deleteClip()`
  - `reorderClip()`
  - `selectClip()`
  - `highlightTranscriptRange()`
  - `clearTranscriptHighlight()`
  - `createSelectionHandles()`
  - `attachHandleDragListeners()`
  - `saveEditorChanges()`
  - `cancelEditorChanges()`
- Event listeners (lines 2183-2247)

#### Video Input Component (`components/video-input/`)
**Lines: ~70-280 in script.js**

- DOM elements: `videoInput`, `thumbnailPreview`, `autoCreateBtn`, etc.
- Functions to extract:
  - `fetchThumbnail()`
  - Video input event listeners
  - Format selection logic

#### Progress Tracker Component (`components/progress-tracker/`)
**Lines: ~281-600 in script.js**

- Functions to extract:
  - `processVideo()`
  - `connectWebSocketAndWait()`
  - `cancelProcessing()`
  - `updateProgress()`
  - `updateStageStatus()`
  - `resetProgressStages()`
  - `showProcessingError()`
  - `showResults()`

#### Clip Selector Component (`components/clip-selector/`)
**Lines: ~845-1040 in script.js**

- Functions to extract:
  - `analyzeAndShowClips()`
  - `displayClipSelection()`
  - `generateSelectedClips()`

#### Settings Panel Component (`components/settings-panel/`)
**Lines: ~654-680 in script.js**

- Functions to extract:
  - `loadSettings()`
  - `saveSettingsToServer()`
- Event listeners for settings sliders

#### History Panel Component (`components/history-panel/`)
**Lines: ~718-843 in script.js**

- Functions to extract:
  - `loadHistory()`
  - `clearHistoryFromServer()`

#### Strategies Panel Component (`components/strategies-panel/`)
**Lines: ~1112-1152 in script.js**

- Functions to extract:
  - `loadStrategies()`

### From style.css → Component CSS Files

#### clip-editor.css
**Lines: 1503-2200+ in style.css**

Classes to extract:
- `.clip-editor-content`
- `.clip-editor-body`
- `.editor-clips-section`
- `.editor-transcript-section`
- `.editor-separator`
- `.editor-section-header`
- `.editor-clips-list`
- `.editor-clip-card`
- `.editor-clip-header`
- `.editor-clip-time`
- `.editor-clip-text`
- `.editor-transcript-content`
- `.transcript-paragraph`
- `.transcript-highlight`
- `.selection-handle*`
- `.add-clip-btn`
- `.clip-confirm-btn`
- `.clip-delete-btn`
- `.clip-drag-handle`
- `.editor-footer`
- `.editor-cancel-btn`
- `.editor-save-btn`
- `.editor-empty-state`

#### video-input.css
**Lines: ~200-400 in style.css**

Classes to extract:
- `.input-section`
- `.input-group`
- `.thumbnail-preview`
- `.format-selector`

#### progress-tracker.css
**Lines: ~700-1100 in style.css**

Classes to extract:
- `.progress-section`
- `.progress-stages`
- `.stage-item`
- `.progress-bar`
- `.spinner`

#### clip-selector.css
**Lines: ~1100-1500 in style.css**

Classes to extract:
- `.preview-section`
- `.clips-grid`
- `.clip-card`
- `.clip-checkbox`
- `.clip-header`
- `.validation-indicator`

## Migration Strategy

### Phase 1: Shared Modules (✅ DONE)
- Created `shared/utils.js`
- Created `shared/api.js`
- Created `shared/websocket.js`
- Created `shared/common.css`

### Phase 2: Extract One Component at a Time
For each component (recommended order):

1. **Clip Editor** (largest, most complex)
   - Copy relevant functions from `script.js` (lines 1185-2247)
   - Export functions as ES6 modules
   - Copy relevant CSS from `style.css` (lines 1503-2200+)
   - Test thoroughly

2. **Progress Tracker**
   - Extract WebSocket handling
   - Extract progress update functions
   - Extract progress UI styles

3. **Clip Selector**
   - Extract clip selection UI
   - Extract validation logic

4. **Video Input**
   - Extract input handling
   - Extract thumbnail preview

5. **Settings Panel**
   - Extract settings management
   - Extract modal logic

6. **History Panel**
   - Extract history display
   - Extract clear history

7. **Strategies Panel**
   - Extract strategy loading
   - Extract strategy display

### Phase 3: Update index.html
Replace single script/style tags with modular imports:

```html
<!-- Shared styles -->
<link rel="stylesheet" href="shared/common.css">

<!-- Component styles -->
<link rel="stylesheet" href="components/video-input/video-input.css">
<link rel="stylesheet" href="components/progress-tracker/progress-tracker.css">
<link rel="stylesheet" href="components/clip-editor/clip-editor.css">
<!-- ... other components -->

<!-- Shared modules -->
<script type="module" src="shared/utils.js"></script>
<script type="module" src="shared/api.js"></script>
<script type="module" src="shared/websocket.js"></script>

<!-- Component modules -->
<script type="module" src="components/video-input/video-input.js"></script>
<script type="module" src="components/progress-tracker/progress-tracker.js"></script>
<script type="module" src="components/clip-editor/clip-editor.js"></script>
<!-- ... other components -->

<!-- Main app initialization -->
<script type="module" src="main.js"></script>
```

### Phase 4: Create main.js
Orchestrate component initialization:

```javascript
import { initVideoInput } from './components/video-input/video-input.js';
import { initProgressTracker } from './components/progress-tracker/progress-tracker.js';
import { initClipEditor } from './components/clip-editor/clip-editor.js';
// ... other imports

// Initialize all components
initVideoInput();
initProgressTracker();
initClipEditor();
// ... other initializations
```

## Testing Strategy

After each component extraction:

1. Test the specific component functionality
2. Test integration with other components
3. Test on desktop and mobile
4. Check browser console for errors
5. Verify WebSocket connections
6. Test file processing end-to-end

## Benefits of This Structure

1. **Maintainability**: Each component is in its own file
2. **Reusability**: Components can be reused across pages
3. **Testability**: Easier to unit test individual components
4. **Collaboration**: Multiple developers can work on different components
5. **Performance**: Can lazy-load components as needed
6. **Debugging**: Easier to locate and fix bugs

## Notes

- Keep `script.js` and `style.css` as backup during migration
- Use ES6 modules (`import`/`export`)
- Maintain backward compatibility during transition
- Document any breaking changes
- Update component APIs as needed
