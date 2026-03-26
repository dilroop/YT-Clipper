import type { Clip, ClipPart, TranscriptWord } from '../../../domain/types';

// ─── Types ────────────────────────────────────────────────────────────────────

export interface MappedWord extends TranscriptWord {
  charStart: number;
  charEnd: number;
}

export interface EditorPart {
  id: string;
  start: number;
  end: number;
  startWordIndex: number;
  endWordIndex: number;
  hasPendingChange: boolean; // shows ✓ button
}

export interface EditorState {
  clip: Clip;
  parts: EditorPart[];
  mappedWords: MappedWord[];
  fullText: string;

  selectedPartIndex: number | null;
  isAddingNewPart: boolean;   // + button was clicked, next selection = new part
  isDirty: boolean;
}

export type EditorIntent =
  | { type: 'SELECT_PART'; payload: number }
  | { type: 'START_NEW_PART' }
  | { type: 'COMMIT_SELECTION'; payload: { start: number; end: number; startWordIdx: number; endWordIdx: number } }
  | { type: 'CONFIRM_PART_CHANGE'; payload: number }
  | { type: 'DELETE_PART'; payload: number }
  | { type: 'CANCEL_ADD' };

// ─── Word Mapping ─────────────────────────────────────────────────────────────

export function buildWordMapping(words: TranscriptWord[]): { fullText: string; mappedWords: MappedWord[] } {
  let pos = 0;
  const mappedWords: MappedWord[] = words.map(w => {
    const charStart = pos;
    const charEnd = charStart + w.word.length;
    pos = charEnd + 1; // space between words
    return { ...w, charStart, charEnd };
  });
  const fullText = mappedWords.map(w => w.word).join(' ');
  return { fullText, mappedWords };
}

export function wordAtChar(charPos: number, words: MappedWord[]): MappedWord {
  return words.find(w => w.charEnd >= charPos) ?? words[words.length - 1];
}

export function findWordIndexByTime(time: number, words: MappedWord[]): number {
  const idx = words.findIndex(w => w.end >= time);
  return idx >= 0 ? idx : words.length - 1;
}

/** Get absolute character offset from container element start */
export function getAbsoluteOffset(container: Node, targetNode: Node, nodeOffset: number): number {
  const range = document.createRange();
  range.setStart(container, 0);
  range.setEnd(targetNode, nodeOffset);
  return range.toString().length;
}

// ─── Reducer ─────────────────────────────────────────────────────────────────

let nextPartId = 1;

export function editorReducer(state: EditorState, intent: EditorIntent): EditorState {
  switch (intent.type) {
    case 'SELECT_PART':
      return { ...state, selectedPartIndex: intent.payload, isAddingNewPart: false };

    case 'START_NEW_PART':
      return { ...state, isAddingNewPart: true, selectedPartIndex: null };

    case 'CANCEL_ADD':
      return { ...state, isAddingNewPart: false };

    case 'COMMIT_SELECTION': {
      const { start, end, startWordIdx, endWordIdx } = intent.payload;

      if (state.isAddingNewPart) {
        // Create a brand new part
        const newPart: EditorPart = {
          id: `part-${nextPartId++}`,
          start, end,
          startWordIndex: startWordIdx,
          endWordIndex: endWordIdx,
          hasPendingChange: false,
        };
        const parts = [...state.parts, newPart];
        return {
          ...state,
          parts,
          isAddingNewPart: false,
          selectedPartIndex: parts.length - 1,
          isDirty: true,
        };
      } else if (state.selectedPartIndex !== null) {
        // Update existing selected part — mark as pending change (needs ✓)
        const parts = state.parts.map((p, i) =>
          i === state.selectedPartIndex
            ? { ...p, start, end, startWordIndex: startWordIdx, endWordIndex: endWordIdx, hasPendingChange: true }
            : p
        );
        return { ...state, parts, isDirty: true };
      }
      return state;
    }

    case 'CONFIRM_PART_CHANGE': {
      const parts = state.parts.map((p, i) =>
        i === intent.payload ? { ...p, hasPendingChange: false } : p
      );
      return { ...state, parts };
    }

    case 'DELETE_PART': {
      const parts = state.parts.filter((_, i) => i !== intent.payload);
      const selectedPartIndex =
        state.selectedPartIndex === intent.payload ? null
        : state.selectedPartIndex !== null && state.selectedPartIndex > intent.payload
          ? state.selectedPartIndex - 1
          : state.selectedPartIndex;
      return { ...state, parts, selectedPartIndex, isDirty: true };
    }

    default:
      return state;
  }
}

// ─── Initialiser ─────────────────────────────────────────────────────────────

export function buildInitialEditorState(clip: Clip, fullTranscript: TranscriptWord[]): EditorState {
  const { fullText, mappedWords } = buildWordMapping(fullTranscript);

  let parts: EditorPart[];
  if (clip.parts && clip.parts.length > 0) {
    parts = clip.parts.map((p: ClipPart): EditorPart => {
      const startWordIdx = findWordIndexByTime(p.start, mappedWords);
      const endWordIdx = findWordIndexByTime(p.end, mappedWords);
      return {
        id: `part-${nextPartId++}`,
        start: p.start,
        end: p.end,
        startWordIndex: startWordIdx,
        endWordIndex: endWordIdx,
        hasPendingChange: false,
      };
    });
  } else {
    // Treat the whole clip as one part
    const startWordIdx = findWordIndexByTime(clip.start, mappedWords);
    const endWordIdx = findWordIndexByTime(clip.end, mappedWords);
    parts = [{
      id: `part-${nextPartId++}`,
      start: clip.start,
      end: clip.end,
      startWordIndex: startWordIdx,
      endWordIndex: endWordIdx,
      hasPendingChange: false,
    }];
  }

  return {
    clip,
    parts,
    mappedWords,
    fullText,
    selectedPartIndex: 0,
    isAddingNewPart: false,
    isDirty: false,
  };
}

// ─── Serialise back to Clip ───────────────────────────────────────────────────

export function serialiseEditorState(editorState: EditorState): Clip {
  const { clip, parts, mappedWords } = editorState;

  const serialisedParts: ClipPart[] = parts.map(p => {
    const startWord = mappedWords[p.startWordIndex];
    const endWord = mappedWords[p.endWordIndex];
    const partWords = mappedWords.slice(p.startWordIndex, p.endWordIndex + 1);
    return {
      start: startWord?.start ?? p.start,
      end: endWord?.end ?? p.end,
      duration: (endWord?.end ?? p.end) - (startWord?.start ?? p.start),
      text: partWords.map(w => w.word).join(' '),
    };
  });

  // Outer clip timing = min start to max end of all parts
  const start = Math.min(...serialisedParts.map(p => p.start));
  const end = Math.max(...serialisedParts.map(p => p.end));

  return {
    ...clip,
    start,
    end,
    duration: end - start,
    parts: serialisedParts,
  };
}
