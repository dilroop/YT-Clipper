import React from 'react';
import { useEditorMVI } from './useEditorMVI';
import { PartList } from './components/PartList';
import { TranscriptEditor } from './components/TranscriptEditor';

// In a real app, this would be passed in or fetched via a global context/store
// For this migration blueprint, we assume it's provided by the parent via a ref or prop
interface Props {
  onSave: (updatedParts: any[]) => void;
  onCancel: () => void;
}

export const ClipEditorView: React.FC<Props> = ({ onSave, onCancel }) => {
  const { state, intents } = useEditorMVI();

  // In a real integration, the parent component would trigger intents.openEditor(...)

  if (!state.isOpen) return null;

  return (
    <div className="editor-modal">
      <div className="editor-modal-content">
        <header className="editor-modal-header">
          <h2>Clip Editor</h2>
          <div className="editor-modal-actions">
            <button className="btn secondary" onClick={() => {
              intents.cancelChanges();
              onCancel();
            }}>Cancel</button>
            <button className="btn primary" onClick={() => {
              // The parent handles the actual merge logic via onSave
              onSave(state.clips); 
              intents.closeEditor();
            }}>Save Changes</button>
          </div>
        </header>

        <div className="editor-modal-body">
          <PartList 
            clips={state.clips}
            selectedPartIndex={state.selectedPartIndex}
            onSelectPart={intents.selectPart}
            onDeletePart={intents.deletePart}
            isAddingPart={state.isAddingPart}
            onToggleAdd={intents.toggleAddPart}
          />
          
          <div className="editor-right-panel">
            <div className="editor-panel-header">
              <h3>Script Transcript</h3>
              {state.isAddingPart && (
                <div className="toast info">
                  <div className="toast-icon">ℹ️</div>
                  <div className="toast-content">
                    <h4>Add Mode</h4>
                    <p>Select text in the transcript below to create a new part.</p>
                  </div>
                </div>
              )}
            </div>
            
            <div className="transcript-container">
              {state.transcriptMapping ? (
                <TranscriptEditor 
                  mapping={state.transcriptMapping}
                  activePart={state.selectedPartIndex !== null ? state.clips[state.selectedPartIndex] : null}
                  isAddingPart={state.isAddingPart}
                  onAddPart={intents.addPart}
                  onUpdatePart={intents.updateSelectedPart}
                />
              ) : (
                <div className="editor-empty-state">Loading transcript...</div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
