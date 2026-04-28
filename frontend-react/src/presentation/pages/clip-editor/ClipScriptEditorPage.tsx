import React, { useReducer, useCallback, useRef, useState } from 'react';
import type { Clip, TranscriptWord } from '../../../domain/types';
import {
  editorReducer,
  buildInitialEditorState,
  serialiseEditorState,
} from './useClipEditorMVI';
import { TranscriptView } from './TranscriptView';

interface Props {
  clip: Clip;
  fullTranscript: TranscriptWord[];
  videoId?: string;
  project?: string;
  onSave: (updatedClip: Clip) => void;
  onClose: () => void;
  showBurnCaptionsToggle?: boolean;
  initialBurnCaptions?: boolean;
}

export const ClipScriptEditorPage: React.FC<Props> = ({ clip, fullTranscript, videoId, project, onSave, onClose, showBurnCaptionsToggle, initialBurnCaptions }) => {
  const [editorState, dispatch] = useReducer(editorReducer, clip, (c) => buildInitialEditorState(c, fullTranscript, videoId, project));
  const audioRef = useRef<HTMLAudioElement>(null);
  const [isPlayingIdx, setIsPlayingIdx] = useState<number | null>(null);
  const currentPlayingRef = useRef<{ start: number; end: number } | null>(null);
  const [burnCaptions, setBurnCaptions] = useState(initialBurnCaptions ?? false);

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
    if (showBurnCaptionsToggle) {
      const anyClip = updatedClip as any;
      if (!anyClip.info_data) anyClip.info_data = {};
      if (!anyClip.info_data.clip) anyClip.info_data.clip = {};
      anyClip.info_data.clip.burn_captions = burnCaptions;
    }
    onSave(updatedClip);
  };

  const handlePlayPart = (idx: number) => {
    const part = editorState.parts[idx];
    if (!audioRef.current) return;

    // Use videoId or project as reference
    const vid = videoId || editorState.videoId || '';
    const prj = project || editorState.project || '';
    
    const params = new URLSearchParams({
      start: part.start.toString(),
      end: part.end.toString()
    });
    if (vid) params.append('videoId', vid);
    if (prj) params.append('project', prj);

    const apiUrl = `/api/audio-preview?${params.toString()}`;
    
    // If already playing this part, stop it
    if (isPlayingIdx === idx) {
      audioRef.current.pause();
      setIsPlayingIdx(null);
      return;
    }

    audioRef.current.src = apiUrl;
    currentPlayingRef.current = { start: part.start, end: part.end };
    setIsPlayingIdx(idx);
    audioRef.current.play().catch(err => {
      console.error("Playback failed:", err);
      alert("Playback failed: " + err.message);
      setIsPlayingIdx(null);
    });
  };

  const handleTimeUpdate = () => {
    // Optional: could use this to stop playback exactly at 'end' if FFmpeg wasn't precise enough
    // But since FFmpeg crops it, we'll let it play to the end of the stream.
  };

  const handleAudioError = (e: any) => {
    console.error("Audio error:", e);
    setIsPlayingIdx(null);
    alert("Audio playback failed. Please check if the source video exists in Downloads.");
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
                  draggable
                  onDragStart={e => {
                    e.dataTransfer.setData('text/plain', idx.toString());
                    e.currentTarget.classList.add('cse-part-card--dragging');
                  }}
                  onDragEnd={e => {
                    e.currentTarget.classList.remove('cse-part-card--dragging');
                  }}
                  onDragOver={e => {
                    e.preventDefault();
                    e.currentTarget.classList.add('cse-part-card--drag-over');
                  }}
                  onDragLeave={e => {
                    e.currentTarget.classList.remove('cse-part-card--drag-over');
                  }}
                  onDrop={e => {
                    e.preventDefault();
                    e.currentTarget.classList.remove('cse-part-card--drag-over');
                    const fromIdx = parseInt(e.dataTransfer.getData('text/plain'), 10);
                    dispatch({ type: 'REORDER_PARTS', payload: { fromIndex: fromIdx, toIndex: idx } });
                  }}
                  onClick={() => dispatch({ type: 'SELECT_PART', payload: idx })}
                >
                  <div className="cse-part-card-header">
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      {/* Drag handle */}
                      <span className="cse-part-drag" style={{ cursor: 'grab' }}>≡</span>
                      
                      {/* Play button */}
                      <button 
                        className={`cse-part-play ${isPlayingIdx === idx ? 'cse-part-play--active' : ''}`}
                        title={isPlayingIdx === idx ? "Stop" : "Play audio"}
                        onClick={(e) => { e.stopPropagation(); handlePlayPart(idx); }}
                      >
                        {isPlayingIdx === idx ? (
                          <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor">
                            <rect x="6" y="6" width="12" height="12" />
                          </svg>
                        ) : (
                          <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor">
                            <path d="M8 5v14l11-7z" />
                          </svg>
                        )}
                      </button>
                    </div>

                    {/* Delete (✕) */}
                    <button
                      className="cse-part-delete"
                      title="Delete part"
                      onClick={e => { e.stopPropagation(); dispatch({ type: 'DELETE_PART', payload: idx }); }}
                    >✕</button>
                  </div>

                  <div className="cse-part-time">
                    {formatTime(part.start)} — {formatTime(part.end)} 
                    <span style={{ marginLeft: '6px', opacity: 0.6, fontSize: '0.9em', fontWeight: 500 }}>
                      ({(part.end - part.start).toFixed(1)}s)
                    </span>
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
        {isPlayingIdx !== null && (
          <div className="cse-playing-status">
            <span className="cse-play-dot"></span>
            Playing audio...
          </div>
        )}
        <div style={{ flex: 1 }} />
        {showBurnCaptionsToggle && (
          <label style={{ display: 'flex', alignItems: 'center', gap: '8px', color: '#fff', fontSize: '0.9rem', cursor: 'pointer', marginRight: '16px' }}>
            <input 
              type="checkbox" 
              checked={burnCaptions} 
              onChange={e => setBurnCaptions(e.target.checked)} 
              style={{ width: '16px', height: '16px', accentColor: '#3b82f6' }}
            />
            🔥 Burn Captions
          </label>
        )}
        <button className="cse-cancel-btn" onClick={onClose}>Cancel</button>
        <button className="cse-save-btn" onClick={handleSave}>Save Changes</button>
      </div>

      {/* Hidden audio element */}
      <audio 
        ref={audioRef} 
        style={{ display: 'none' }} 
        onTimeUpdate={handleTimeUpdate}
        onEnded={() => setIsPlayingIdx(null)}
        onError={handleAudioError}
      />
    </div>
  );
};
