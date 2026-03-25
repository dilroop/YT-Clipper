import React, { useState } from 'react';
import { ClipScriptEditorPage } from '../../clip-editor/ClipScriptEditorPage';
import type { HomeState } from '../HomeIntents';
import type { Clip, ClipPart, TranscriptWord } from '../../../../domain/types';

interface Props {
  state: HomeState;
  intents: Record<string, any>;
}

export const ClipSelectionSection: React.FC<Props> = ({ state, intents }) => {
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [editorClip, setEditorClip] = useState<{ clip: Clip; index: number } | null>(null);

  if (!state.clips) return null;

  const toggleSelect = (id: string) => {
    setSelectedIds(prev => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id); else next.add(id);
      return next;
    });
  };

  const allSelected = state.clips.length > 0 && selectedIds.size === state.clips.length;

  const toggleAll = () => {
    if (allSelected) setSelectedIds(new Set());
    else setSelectedIds(new Set(state.clips!.map((c: Clip, i: number) => c.id || `clip-${i}`)));
  };

  const formatTime = (secs: number) => {
    const h = Math.floor(secs / 3600);
    const m = Math.floor((secs % 3600) / 60);
    const s = Math.floor(secs % 60);
    if (h > 0) return `${String(h).padStart(2,'0')}:${String(m).padStart(2,'0')}:${String(s).padStart(2,'0')}`;
    return `${String(m).padStart(2,'0')}:${String(s).padStart(2,'0')}`;
  };

  return (
    <>
    <div className="clip-selection-section">
      <div className="clip-selection-header">
        <h3>Select Clips to Generate</h3>
        <button className="select-all-btn" onClick={toggleAll}>{allSelected ? 'Deselect All' : 'Select All'}</button>
      </div>
      <div className="clips-grid">
        {state.clips.map((clip: Clip, idx: number) => {
          const clipId = clip.id || `clip-${idx}`;
          const isSelected = selectedIds.has(clipId);
          const validStatus = clip.validation_status || 'valid';

          return (
            <div
              key={clipId}
              className={`clip-item ${isSelected ? 'selected' : ''} status-${validStatus}`}
              onClick={() => toggleSelect(clipId)}
            >
              <div className="clip-header-new">
                <div className="clip-header-left">
                  <div className={`custom-checkbox ${isSelected ? 'checked' : ''}`}>
                    {isSelected && <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="4"><polyline points="20 6 9 17 4 12"/></svg>}
                  </div>
                  <div className={`status-icon-circle ${validStatus}`}>
                    {validStatus === 'valid' ? (
                      <svg viewBox="0 0 24 24" fill="currentColor"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"/></svg>
                    ) : (
                      <svg viewBox="0 0 24 24" fill="currentColor"><path d="M12 2C6.47 2 2 6.47 2 12s4.47 10 10 10 10-4.47 10-10S17.53 2 12 2zm5 13.59L15.59 17 12 13.41 8.41 17 7 15.59 10.59 12 7 8.41 8.41 7 12 10.59 15.59 7 17 8.41 13.41 12 17 15.59z"/></svg>
                    )}
                  </div>
                  <span className="clip-title-new">{clip.title}</span>
                </div>
                <div className="clip-header-right">
                  <span className="clip-duration-new">{(clip.duration || 0).toFixed(1)}s</span>
                  <button className="clip-edit-btn-new" title="Edit Clip"
                    onClick={e => { e.stopPropagation(); setEditorClip({ clip, index: idx }); }}>
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/>
                    </svg>
                  </button>
                </div>
              </div>

              <div className={`clip-status-bar ${validStatus}`}>
                {validStatus === 'valid' ? 'No validation errors - clip is good to use' : clip.validation_message || 'Overlap detected - this clip overlaps with another clip and may have quality issues.'}
              </div>

              <p className="clip-explanation-new">{clip.explanation}</p>

              <div className="clip-parts-new">
                {(clip.parts || []).map((part: ClipPart, pi: number) => (
                  <div key={pi} className="clip-part-new">
                    <span className="clip-part-time-new">
                      [{formatTime(part.start)} — {formatTime(part.end)}] Part {pi + 1} ({part.duration.toFixed(1)}s)
                    </span>
                    <p className="clip-part-text-new">{part.text}</p>
                  </div>
                ))}
                {!clip.parts && clip.words && (
                  <div className="clip-part-new">
                    <span className="clip-part-time-new">
                      [{formatTime(clip.start)} — {formatTime(clip.end)}] {(clip.duration || 0).toFixed(1)}s
                    </span>
                    <p className="clip-part-text-new">{clip.words.slice(0, 30).map((w: TranscriptWord) => w.word).join(' ')}...</p>
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>

    {/* Sticky generate bar */}
    <div className="clip-generate-bar">
      <span className="clip-generate-count">{selectedIds.size} of {state.clips.length} selected</span>
      <button className="generate-btn" disabled={selectedIds.size === 0}
        onClick={() => intents.processVideoSelection(Array.from(selectedIds))}>
        Generate Selected Clips
      </button>
    </div>

    {/* Clip Script Editor — full-screen overlay */}
    {editorClip && (
      <div className="clip-editor-fullscreen">
        <ClipScriptEditorPage 
          clip={editorClip.clip} 
          onSave={(updatedClip: Clip) => {
            intents.updateClip(editorClip.index, updatedClip);
            setEditorClip(null);
          }} 
          onClose={() => setEditorClip(null)} 
        />
      </div>
    )}
    </>
  );
};
