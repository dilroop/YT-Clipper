import { useReducer, useCallback } from 'react';
import { editorReducer, initialEditorState } from './EditorIntents';
import type { Clip } from '../../../domain/types';
import type { TranscriptMapping } from '../../../domain/transcriptUtils';

export function useEditorMVI() {
  const [state, dispatch] = useReducer(editorReducer, initialEditorState);

  const openEditor = useCallback((editingClipIndex: number, parts: Clip[], transcriptMapping: TranscriptMapping) => {
    dispatch({ type: 'OPEN_EDITOR', payload: { editingClipIndex, parts, transcriptMapping } });
  }, []);

  const closeEditor = useCallback(() => {
    dispatch({ type: 'CLOSE_EDITOR' });
  }, []);

  const selectPart = useCallback((index: number) => {
    dispatch({ type: 'SELECT_PART', payload: index });
  }, []);

  const toggleAddPart = useCallback(() => {
    dispatch({ type: 'TOGGLE_ADD_PART' });
  }, []);

  const addPart = useCallback((startIdx: number, endIdx: number) => {
    dispatch({ type: 'ADD_PART', payload: { startIdx, endIdx } });
  }, []);

  const updateSelectedPart = useCallback((startIdx: number, endIdx: number) => {
    dispatch({ type: 'UPDATE_SELECTED_PART', payload: { startIdx, endIdx } });
  }, []);

  const deletePart = useCallback((index: number) => {
    dispatch({ type: 'DELETE_PART', payload: index });
  }, []);

  const cancelChanges = useCallback(() => {
    dispatch({ type: 'CANCEL_CHANGES' });
  }, []);

  return {
    state,
    intents: {
      openEditor,
      closeEditor,
      selectPart,
      toggleAddPart,
      addPart,
      updateSelectedPart,
      deletePart,
      cancelChanges,
    }
  };
}
