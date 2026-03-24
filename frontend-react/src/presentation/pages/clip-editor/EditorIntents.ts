import type { Clip } from '../../../domain/types';
import type { TranscriptMapping } from '../../../domain/transcriptUtils';

export interface EditorState {
  isOpen: false;
  editingClipIndex: number | null; // Which original Clip is being edited
  
  clips: Clip[];          // The "Parts" that make up the final Clip
  originalClips: Clip[];  // For cancellation rollback
  selectedPartIndex: number | null; // Which "Part" is currently selected in the UI
  
  transcriptMapping: TranscriptMapping | null;
  
  isAddingPart: boolean;
  
  // Potential UI states
  error: string | null;
}

export const initialEditorState: EditorState = {
  isOpen: false,
  editingClipIndex: null,
  clips: [],
  originalClips: [],
  selectedPartIndex: null,
  transcriptMapping: null,
  isAddingPart: false,
  error: null,
};

export type EditorIntent =
  | { type: 'OPEN_EDITOR'; payload: { editingClipIndex: number; parts: Clip[]; transcriptMapping: TranscriptMapping } }
  | { type: 'CLOSE_EDITOR' }
  | { type: 'SELECT_PART'; payload: number }
  | { type: 'TOGGLE_ADD_PART' }
  | { type: 'ADD_PART'; payload: { startIdx: number; endIdx: number } }
  | { type: 'UPDATE_SELECTED_PART'; payload: { startIdx: number; endIdx: number } }
  | { type: 'DELETE_PART'; payload: number }
  | { type: 'CANCEL_CHANGES' }
  | { type: 'SAVE_CHANGES' };

export const editorReducer = (state: EditorState, intent: EditorIntent): EditorState => {
  switch (intent.type) {
    case 'OPEN_EDITOR':
      return {
        ...state,
        isOpen: false, // Will be managed by parent route/modal state, but kept here for strictness
        editingClipIndex: intent.payload.editingClipIndex,
        clips: [...intent.payload.parts],
        originalClips: [...intent.payload.parts],
        selectedPartIndex: intent.payload.parts.length > 0 ? 0 : null,
        transcriptMapping: intent.payload.transcriptMapping,
        isAddingPart: false,
        error: null,
      };

    case 'CLOSE_EDITOR':
      return initialEditorState;

    case 'SELECT_PART':
      return {
        ...state,
        selectedPartIndex: intent.payload,
        isAddingPart: false, // Deselect add mode if selecting a card
      };

    case 'TOGGLE_ADD_PART':
      return {
        ...state,
        isAddingPart: !state.isAddingPart,
      };

    case 'ADD_PART': {
      if (!state.transcriptMapping) return state;
      const { startIdx, endIdx } = intent.payload;
      const words = state.transcriptMapping.words.slice(startIdx, endIdx + 1);
      
      const newPart: Clip = {
        id: `part-${Date.now()}`,
        title: 'New Part',
        explanation: 'Custom added part',
        start: words[0].start,
        end: words[words.length - 1].end,
        score: 100,
        duration: words[words.length - 1].end - words[0].start,
        words: words,
        isPart: true,
      };

      const newClips = [...state.clips, newPart];
      // Sort parts chronologically
      newClips.sort((a, b) => a.start - b.start);
      
      return {
        ...state,
        clips: newClips,
        isAddingPart: false,
        selectedPartIndex: newClips.findIndex(c => c.id === newPart.id),
      };
    }

    case 'UPDATE_SELECTED_PART': {
      if (state.selectedPartIndex === null || !state.transcriptMapping) return state;
      
      const { startIdx, endIdx } = intent.payload;
      const words = state.transcriptMapping.words.slice(startIdx, endIdx + 1);
      
      const updatedClips = [...state.clips];
      const target = updatedClips[state.selectedPartIndex];
      
      updatedClips[state.selectedPartIndex] = {
        ...target,
        start: words[0].start,
        end: words[words.length - 1].end,
        duration: words[words.length - 1].end - words[0].start,
        words: words,
      };

      // Sort parts chronologically after update
      updatedClips.sort((a, b) => a.start - b.start);

      return {
        ...state,
        clips: updatedClips,
        // Find new index of the updated part
        selectedPartIndex: updatedClips.findIndex(c => c.id === target.id),
      };
    }

    case 'DELETE_PART': {
      const updatedClips = state.clips.filter((_, idx) => idx !== intent.payload);
      return {
        ...state,
        clips: updatedClips,
        selectedPartIndex: updatedClips.length > 0 ? 0 : null,
      };
    }

    case 'CANCEL_CHANGES':
      return {
        ...state,
        clips: [...state.originalClips],
        selectedPartIndex: state.originalClips.length > 0 ? 0 : null,
        isAddingPart: false,
      };

    default:
      return state;
  }
};
