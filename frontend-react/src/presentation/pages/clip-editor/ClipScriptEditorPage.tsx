import React, { useReducer, useCallback } from 'react';
import type { Clip } from '../../../domain/types';
import {
  editorReducer,
  buildInitialEditorState,
  serialiseEditorState,
} from './useClipEditorMVI';
import { TranscriptView } from './TranscriptView';

interface Props {
  clip: Clip;
  onSave: (updatedClip: Clip) => void;
  onClose: () => void;
}

export const ClipScriptEditorPage: React.FC<Props> = ({ clip, onSave, onClose }) => {
  const [editorState, dispatch] = useReducer(editorReducer, clip, buildInitialEditorState);

  const formatTime = (secs: number) => {
    const h = Math.floor(secs / 3600);
    const m = Math.floor((secs % 3600) / 60);
    const s = Math.floor(secs % 60);
    if (h > 0) return `${String(h).padStart(2,'0')}:${String(m).padStart(2,'0')}:${String(s).padStart(2,'0')}`;
    return `${String(m).padStart(2,'0')}:${String(s).padStart(2,'0')}`;
  };

  const handleCommitSelection = useCallback((start: number, end: number, startWordIdx: number, endWordIdx: number) => {
    dispatch({ type: 'COMMIT_SELECTION', payload: { start, end, startWordIdx, endWordIdx } });
  }, []);

  const handleSave = () => {
    const updatedClip = serialiseEditorState(editorState);
    onSave(updatedClip);
  };

  return (
    <div className="cse-container">
      {/* ── Header ── */}
      <div className="cse-header">
        <h2 className="cse-title">Clip Script Editor</h2>
        <button className="cse-close-btn" onClick={onClose} aria-label="Close">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
          </svg>
        </button>
      </div>

      {/* ── Body ── */}
      <div className="cse-body">
        {/* Left — Parts panel */}
        <div className="cse-parts-panel">
          <div className="cse-panel-header">
            <span className="cse-panel-label">CLIPS</span>
            <span className="cse-clip-count">{editorState.parts.length} {editorState.parts.length === 1 ? 'clip' : 'clips'}</span>
          </div>

          <div className="cse-parts-list">
            {editorState.parts.map((part, idx) => {
              const isSelected = editorState.selectedPartIndex === idx;
              const words = editorState.mappedWords.slice(part.startWordIndex, part.endWordIndex + 1);
              const previewText = words.slice(0, 12).map(w => w.word).join(' ') + (words.length > 12 ? '…' : '');

              return (
                <div
                  key={part.id}
                  className={`cse-part-card ${isSelected ? 'cse-part-card--selected' : ''}`}
                  onClick={() => dispatch({ type: 'SELECT_PART', payload: idx })}
                >
                  <div className="cse-part-card-header">
                    {/* Drag handle */}
                    <span className="cse-part-drag">≡</span>
                    {/* Delete (✗) */}
                    <button
                      className="cse-part-delete"
                      title="Delete part"
                      onClick={e => { e.stopPropagation(); dispatch({ type: 'DELETE_PART', payload: idx }); }}
                    >✕</button>
                  </div>

                  <div className="cse-part-time">
                    {formatTime(part.start)} — {formatTime(part.end)}
                  </div>
                  <div className="cse-part-preview">{previewText}</div>

                  {/* ✓ Confirm button — appears only when boundary has pending change */}
                  {part.hasPendingChange && (
                    <button
                      className="cse-part-confirm"
                      title="Confirm new boundary"
                      onClick={e => { e.stopPropagation(); dispatch({ type: 'CONFIRM_PART_CHANGE', payload: idx }); }}
                    >✓ Confirm</button>
                  )}
                </div>
              );
            })}
          </div>
        </div>

        {/* Divider */}
        <div className="cse-divider" />

        {/* Right — Transcript panel */}
        <div className="cse-transcript-panel">
          <div className="cse-panel-header">
            <span className="cse-panel-label">TRANSCRIPT</span>
            {/* + button: enters "add new part" mode */}
            <button
              className={`cse-add-part-btn ${editorState.isAddingNewPart ? 'cse-add-part-btn--active' : ''}`}
              title={editorState.isAddingNewPart ? 'Click Cancel to stop adding' : 'Add new part — then select text'}
              onClick={() => {
                if (editorState.isAddingNewPart) dispatch({ type: 'CANCEL_ADD' });
                else dispatch({ type: 'START_NEW_PART' });
              }}
            >
              {editorState.isAddingNewPart ? (
                <span>✕ Cancel</span>
              ) : (
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                  <line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/>
                </svg>
              )}
            </button>
          </div>

          {editorState.isAddingNewPart && (
            <div className="cse-selection-hint">
              🔵 Select text below to create a new part
            </div>
          )}

          <TranscriptView
            fullText={editorState.fullText}
            mappedWords={editorState.mappedWords}
            parts={editorState.parts}
            selectedPartIndex={editorState.selectedPartIndex}
            isAddingNewPart={editorState.isAddingNewPart}
            onCommitSelection={handleCommitSelection}
          />
        </div>
      </div>

      {/* ── Footer ── */}
      <div className="cse-footer">
        <button className="cse-cancel-btn" onClick={onClose}>Cancel</button>
        <button className="cse-save-btn" onClick={handleSave}>Save Changes</button>
      </div>
    </div>
  );
};
