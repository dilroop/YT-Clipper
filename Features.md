# YTClipper Frontend Features & Journeys

This document provides a comprehensive overview of the YTClipper frontend features, user interface components, and core logic workflows.

## 1. Home Page: Video Configuration

The home page is the entry point for all video processing workflows.

### Features
- **URL Input**: Paste any YouTube URL to instantly fetch video metadata (Title, Channel, Duration) and thumbnail via `/api/thumbnail`.
- **Reels Format Selection**:
    - **Vertical (9:16)**: Standard mobile-first vertical format.
    - **Photo**: Stacked layout with an AI-generated photo on top.
    - **Video**: Stacked layout with a relevant AI video segment on top.
    - **Original**: Keeps the source 16:9 or 4:3 aspect ratio.
- **Caption Controls**: Toggle "Burn into Video" to overlay high-quality captions (Impact font, yellow/white highlights).
- **AI Strategy & Advanced Instructions**:
    - Choose strategies like "Viral Moments" or "Multi Part Narrative".
    - **Advanced Instructions (New)**: Expandable textarea to provide the AI with a specific "story" or "theme" to focus on (e.g., "Extract only the discussion about Mars").

## 2. Workflows: Auto vs. Manual

### Auto Create (One-Click)
- **Input**: URL + Format + Strategy + Extra Context.
- **Process**: Hits `/api/process`. Backend downloads, transcribes, analyzes, clips, and renders automatically.
- **Output**: A grid of ready-to-download `.mp4` files.

### Manually Choose (Selection)
- **Input**: URL + Strategy + Extra Context.
- **Process**: Hits `/api/analyze`. Returns a list of "Suggested Clips" with titles and explanations.
- **UI**: Displayed as a list of selectable cards. User picks specific ones and clicks "Generate Selected Clips".

## 3. Clip Script Editor: Precision Editing

The Clip Editor allows for granular control over exactly what text/words make up a clip.

### Core Architecture
- **Single-Clip Focus**: The editor operates on one clip at a time to ensure data integrity.
- **Part-Based Grouping (Mutable)**: 
    - A single "Clip" can consist of multiple "Parts" (non-contiguous segments).
    - **Add (+) Feature**: Create a new part by clicking the `+` (add) button and selecting text directly in the transcript.
    - **Individually Editable**: Each part is displayed as a separate "card". You can re-select text for any existing part to update its specific timing.
    - **Deletable**: Quickly remove unwanted segments by clicking the "Delete" icon on any part card.
- **Word-Level Timing**: Uses character-level mapping to the transcript for precise selection.


### User Journey: Editing a Clip (Pseudocode)
```javascript
// 1. User selects "Edit" on a suggested clip card
onEditClick(clipId) {
    const clipIndex = analyzedClips.findIndex(c => c.id === clipId);
    openClipEditor(clipIndex);
}

// 2. Editor Initialization
openClipEditor(index) {
    // Clone specifically selected clip and its parts
    editorState.clips = splitMultiPartClips(analyzedClips, index);
    
    // Build clean transcript mapping (Sequential character offsets)
    const mapping = buildTranscriptWordMapping(fullTranscriptWords);
    renderTranscript(mapping.fullText);
}

// 3. User adds a new segment (+)
onAddPartClick() {
    clearTranscriptHighlight(); // Start clean
    editorState.isAddingClip = true;
}

// 4. User selects text in transcript
onMouseUp(event) {
    if (!editorState.isAddingClip) return;
    
    // Calculate ABSOLUTE character offset (fixes "jumping" bug)
    const offsets = getAbsoluteSelectionOffset(transcriptContainer);
    
    // Map offsets to word indices
    const startIdx = findWordIndex(offsets.start);
    const endIdx = findWordIndex(offsets.end - 1);
    
    // Create new part card in editor UI
    addPartToActiveGroup(startIdx, endIdx);
}

// 5. User saves changes
saveEditorChanges() {
    // Merge parts back into a single 'Clip' object
    const updatedClip = mergeParts(editorState.clips);
    
    // IN-PLACE update to prevent ID/Position shifting
    analyzedClips.splice(editingClipIndex, 1, updatedClip);
    
    refreshHomeUI();
    closeEditor();
}
```

## 4. Supporting Features

- **Gallery/Recent History**: Access `/api/history` to view previously processed videos and download generated clips.
- **Settings**:
    - **Captions**: Customize words per caption, font size, and vertical position.
    - **Analysis**: Set minimum and maximum duration limits for AI clip suggestions.
- **Live Logs**: Real-time server log streaming via WebSocket for debugging.

## 5. Selection Accuracy (Hardening)
- **Selection Handling**: Uses a robust `cloneRange()` and `toString().length` approach to calculate offsets relative to the entire transcript container, preventing "jumping" even when spans or highlights are present in the DOM.
- **Null Safety**: All global listeners in `script.js` are wrapped in existence checks, allowing the script to load safely on modular pages (Gallery/Settings/History).
