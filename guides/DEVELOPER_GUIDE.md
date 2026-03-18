# Developer Guide - Transcript UI Redesign

## Quick Start

### Understanding the Data Flow

```
CLIPS (with words)
    ↓
buildTranscriptWordMapping()
    ↓
{transcriptWords: [...], transcriptFullText: "..."}
    ↓
renderEditorTranscript()
    ↓
<div class="transcript-paragraph">Full text here</div>
    ↓
selectClip(index)
    ↓
highlightTranscriptRange(startTime, endTime)
    ↓
<span class="transcript-highlight">Selected text</span>
+ Selection Handles (Start & End)
```

## Core Data Structures

### transcriptWords Array
```javascript
[
  {
    word: "Welcome",
    start: 15.2,
    end: 15.8,
    charStart: 0,
    charEnd: 7
  },
  {
    word: "to",
    start: 15.8,
    end: 16.0,
    charStart: 8,
    charEnd: 10
  },
  // ... more words
]
```

### clipModifications Object
```javascript
{
  0: { start: 15.5, end: 18.2 },  // Clip 0 modified
  2: { start: 25.0, end: 30.5 }   // Clip 2 modified
  // Only stores modified clips
}
```

## Key Functions Reference

### 1. buildTranscriptWordMapping(clips)
**Purpose**: Build character-level word mapping from clips

**Input**: Array of clip objects with words
```javascript
clips = [
  {
    words: [
      {word: "Hello", start: 1.0, end: 1.5},
      // ...
    ]
  }
]
```

**Output**: Object with word mapping
```javascript
{
  words: [
    {word: "Hello", start: 1.0, end: 1.5, charStart: 0, charEnd: 5},
    // ...
  ],
  fullText: "Hello world this is a test"
}
```

**Algorithm**:
1. Collect all words from all clips
2. Remove duplicates by start time
3. Sort by start time
4. Build continuous text string
5. Assign character positions

### 2. findWordIndexByCharPosition(charPos)
**Purpose**: Map character position → word index

**Input**: Character position in full text (number)

**Output**: Word index (number) or -1 if not found

**Use Case**: When user selects text, find corresponding words

### 3. findWordIndexByTime(time)
**Purpose**: Map timestamp → word index

**Input**: Time in seconds (number)

**Output**: Word index (number)

**Use Case**: When selecting clip by time, find corresponding text

### 4. highlightTranscriptRange(startTime, endTime)
**Purpose**: Highlight text range and create drag handles

**Process**:
1. Clear existing highlights/handles
2. Find word indices for start/end times
3. Create Range object
4. Wrap text in highlight span
5. Create and position handles
6. Scroll into view

**DOM Structure Created**:
```html
<div class="transcript-paragraph">
  Normal text
  <span class="transcript-highlight" id="transcriptHighlight">
    Highlighted text
  </span>
  Normal text
</div>
<div class="selection-handle selection-handle-start" id="selectionHandleStart">
  <div class="selection-handle-knob"></div>
  <div class="selection-handle-bar"></div>
</div>
<div class="selection-handle selection-handle-end" id="selectionHandleEnd">
  <div class="selection-handle-knob"></div>
  <div class="selection-handle-bar"></div>
</div>
```

### 5. attachHandleDragListeners(handle, type, startIndex, endIndex)
**Purpose**: Enable handle dragging with mouse/touch

**Parameters**:
- `handle`: DOM element
- `type`: 'start' or 'end'
- `startIndex`: Initial start word index
- `endIndex`: Initial end word index

**Event Flow**:
```
mousedown/touchstart
    ↓
isDragging = true
    ↓
mousemove/touchmove → handleDragMove()
    ↓
Find character position at cursor
    ↓
Find word index
    ↓
Update highlight range (real-time)
    ↓
mouseup/touchend
    ↓
isDragging = false
    ↓
updateClipModification() → Cache changes
```

## Modifying the Implementation

### Adding a New Feature: Show Time During Drag

**Step 1**: Add tooltip element to handle
```javascript
// In createSelectionHandles()
startHandle.innerHTML = `
  <div class="selection-handle-knob"></div>
  <div class="selection-handle-bar"></div>
  <div class="handle-tooltip"></div>  // ADD THIS
`;
```

**Step 2**: Update CSS
```css
.handle-tooltip {
  position: absolute;
  top: -30px;
  left: 50%;
  transform: translateX(-50%);
  background: rgba(0, 0, 0, 0.9);
  color: white;
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 12px;
  white-space: nowrap;
  opacity: 0;
  pointer-events: none;
  transition: opacity 0.2s;
}

.selection-handle:active .handle-tooltip {
  opacity: 1;
}
```

**Step 3**: Update tooltip during drag
```javascript
// In handleDragMove() function
const tooltip = handle.querySelector('.handle-tooltip');
const time = handleType === 'start' ? newStartWord.start : newEndWord.end;
tooltip.textContent = formatTime(time);
```

### Debugging Tips

**1. Check Word Mapping**
```javascript
console.log('Total words:', editorState.transcriptWords.length);
console.log('Full text length:', editorState.transcriptFullText.length);
console.log('First word:', editorState.transcriptWords[0]);
console.log('Last word:', editorState.transcriptWords[editorState.transcriptWords.length - 1]);
```

**2. Monitor Selection**
```javascript
// In selectClip()
console.log('Selected clip:', index);
console.log('Start time:', startTime, 'End time:', endTime);
console.log('Start word index:', startWordIndex, 'End word index:', endWordIndex);
```

**3. Track Drag Events**
```javascript
// In handleDragMove()
console.log('Dragging:', handleType);
console.log('Cursor position:', clientX, clientY);
console.log('Character position:', charPos);
console.log('Word index:', wordIndex);
```

**4. Inspect Modifications**
```javascript
console.log('Clip modifications:', editorState.clipModifications);
```

## Common Issues and Solutions

### Issue 1: Handles Not Appearing
**Cause**: Highlight span not created or wrong positioning

**Debug**:
```javascript
const highlight = document.getElementById('transcriptHighlight');
console.log('Highlight exists:', !!highlight);
if (highlight) {
  console.log('Highlight rect:', highlight.getBoundingClientRect());
}
```

**Solution**: Check that `transcriptWords` array is populated and word indices are valid

### Issue 2: Drag Not Working
**Cause**: Event listeners not attached or wrong element

**Debug**:
```javascript
const startHandle = document.getElementById('selectionHandleStart');
console.log('Start handle exists:', !!startHandle);
console.log('isDragging:', isDragging);
```

**Solution**: Ensure handles are created after highlight and event listeners are properly attached

### Issue 3: Wrong Text Selected
**Cause**: Character position mapping incorrect

**Debug**:
```javascript
const charPos = 100; // example
const wordIndex = findWordIndexByCharPosition(charPos);
const word = editorState.transcriptWords[wordIndex];
console.log('Char position:', charPos);
console.log('Word index:', wordIndex);
console.log('Word:', word);
console.log('Word char range:', word.charStart, '-', word.charEnd);
```

**Solution**: Verify `buildTranscriptWordMapping()` correctly assigns character positions

### Issue 4: Confirm Button Not Showing
**Cause**: Modification not cached or render not called

**Debug**:
```javascript
console.log('Modifications:', editorState.clipModifications);
console.log('Selected clip index:', editorState.selectedClipIndex);
```

**Solution**: Ensure `updateClipModification()` is called after drag ends and `renderEditorClips()` is called

## Performance Optimization

### Current Performance
- **Word mapping**: O(n) where n = total words
- **Find word by char**: O(n) linear search
- **Find word by time**: O(n) linear search
- **Create highlight**: O(1)
- **Drag update**: O(n) due to word lookup

### Optimization Opportunities

**1. Binary Search for Word Lookup**
```javascript
function findWordIndexByCharPosition(charPos) {
  let left = 0;
  let right = editorState.transcriptWords.length - 1;

  while (left <= right) {
    const mid = Math.floor((left + right) / 2);
    const word = editorState.transcriptWords[mid];

    if (charPos >= word.charStart && charPos <= word.charEnd) {
      return mid;
    } else if (charPos < word.charStart) {
      right = mid - 1;
    } else {
      left = mid + 1;
    }
  }
  return -1;
}
```
**Improvement**: O(n) → O(log n)

**2. Throttle Drag Updates**
```javascript
let dragThrottleTimer = null;

function handleDragMove(clientX, clientY, handleType, startIdx, endIdx) {
  if (dragThrottleTimer) return;

  dragThrottleTimer = setTimeout(() => {
    // ... existing logic
    dragThrottleTimer = null;
  }, 16); // ~60fps
}
```
**Improvement**: Reduces DOM updates during fast dragging

**3. Cache Range Calculations**
```javascript
const rangeCache = new Map();

function getWordRange(startIndex, endIndex) {
  const key = `${startIndex}-${endIndex}`;
  if (rangeCache.has(key)) {
    return rangeCache.get(key);
  }

  const range = calculateRange(startIndex, endIndex);
  rangeCache.set(key, range);
  return range;
}
```
**Improvement**: Avoids recalculating same ranges

## Testing Guide

### Unit Tests (Conceptual - adapt to your test framework)

```javascript
describe('buildTranscriptWordMapping', () => {
  it('should create word mapping from clips', () => {
    const clips = [
      {
        words: [
          {word: "Hello", start: 1.0, end: 1.5},
          {word: "world", start: 1.5, end: 2.0}
        ]
      }
    ];

    const result = buildTranscriptWordMapping(clips);

    expect(result.words).toHaveLength(2);
    expect(result.fullText).toBe("Hello world");
    expect(result.words[0].charStart).toBe(0);
    expect(result.words[0].charEnd).toBe(5);
    expect(result.words[1].charStart).toBe(6);
    expect(result.words[1].charEnd).toBe(11);
  });
});

describe('findWordIndexByCharPosition', () => {
  beforeEach(() => {
    editorState.transcriptWords = [
      {word: "Hello", charStart: 0, charEnd: 5},
      {word: "world", charStart: 6, charEnd: 11}
    ];
  });

  it('should find word at start', () => {
    expect(findWordIndexByCharPosition(0)).toBe(0);
  });

  it('should find word at end', () => {
    expect(findWordIndexByCharPosition(11)).toBe(1);
  });

  it('should return -1 for invalid position', () => {
    expect(findWordIndexByCharPosition(100)).toBe(-1);
  });
});
```

### Integration Tests

```javascript
describe('Clip Selection Flow', () => {
  it('should highlight text when clip is selected', () => {
    openClipEditor(0);
    selectClip(0);

    const highlight = document.getElementById('transcriptHighlight');
    expect(highlight).toBeTruthy();

    const startHandle = document.getElementById('selectionHandleStart');
    const endHandle = document.getElementById('selectionHandleEnd');
    expect(startHandle).toBeTruthy();
    expect(endHandle).toBeTruthy();
  });

  it('should cache modifications after drag', () => {
    openClipEditor(0);
    selectClip(0);

    // Simulate drag
    const handle = document.getElementById('selectionHandleStart');
    handle.dispatchEvent(new MouseEvent('mousedown'));
    document.dispatchEvent(new MouseEvent('mousemove', {clientX: 100, clientY: 100}));
    document.dispatchEvent(new MouseEvent('mouseup'));

    expect(editorState.clipModifications[0]).toBeTruthy();
  });
});
```

## Code Style Guidelines

### Naming Conventions
- **Functions**: camelCase (e.g., `buildTranscriptWordMapping`)
- **Variables**: camelCase (e.g., `transcriptWords`)
- **Constants**: UPPER_SNAKE_CASE (e.g., `SEGMENT_DURATION`)
- **DOM IDs**: camelCase (e.g., `transcriptHighlight`)
- **CSS Classes**: kebab-case (e.g., `selection-handle-start`)

### Comments
- **Function headers**: Describe purpose, inputs, outputs
- **Complex logic**: Explain why, not what
- **TODOs**: Include context and priority

### Error Handling
- **Validate inputs**: Check for null/undefined
- **Graceful degradation**: Don't crash on missing data
- **Console errors**: Use `console.error()` for debugging

## Extension Points

### 1. Custom Handle Styles
Modify CSS in `/Users/dilroop.singh/YTClipper/frontend/style.css`:
```css
.selection-handle-knob {
  /* Change size, color, border */
}
```

### 2. Different Highlight Colors
```css
.transcript-highlight {
  background: your-color;
}
```

### 3. Alternative Drag Behavior
Modify `handleDragMove()` function in `attachHandleDragListeners()`

### 4. Keyboard Shortcuts
Add event listeners in `openClipEditor()`:
```javascript
document.addEventListener('keydown', (e) => {
  if (e.key === 'ArrowLeft') {
    // Move start handle left
  }
});
```

## Resources

### Files to Reference
1. `/Users/dilroop.singh/YTClipper/frontend/script.js` - All JavaScript logic
2. `/Users/dilroop.singh/YTClipper/frontend/style.css` - All CSS styles
3. `/Users/dilroop.singh/YTClipper/TRANSCRIPT_UI_REDESIGN.md` - Implementation details
4. `/Users/dilroop.singh/YTClipper/VISUAL_REFERENCE.md` - Visual examples

### Browser APIs Used
- [Range API](https://developer.mozilla.org/en-US/docs/Web/API/Range)
- [Selection API](https://developer.mozilla.org/en-US/docs/Web/API/Selection)
- [Touch Events](https://developer.mozilla.org/en-US/docs/Web/API/Touch_events)
- [Mouse Events](https://developer.mozilla.org/en-US/docs/Web/API/MouseEvent)

### Related Patterns
- iOS Text Selection (inspiration)
- Android Text Selection (inspiration)
- Medium.com text highlighting (similar concept)
- Google Docs comment highlighting (similar concept)

## Summary

This guide provides developers with:
- Understanding of data flow and structures
- Reference for all key functions
- Debugging tips and common issues
- Performance optimization opportunities
- Testing strategies
- Extension points for customization

For implementation details, see `TRANSCRIPT_UI_REDESIGN.md`.
For visual examples, see `VISUAL_REFERENCE.md`.
