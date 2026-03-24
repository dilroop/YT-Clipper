import React from 'react';
import type { Clip } from '../../../../domain/types';

interface Props {
  clips: Clip[];
  selectedPartIndex: number | null;
  onSelectPart: (index: number) => void;
  onDeletePart: (index: number) => void;
  isAddingPart: boolean;
  onToggleAdd: () => void;
}

export const PartList: React.FC<Props> = ({ 
  clips, 
  selectedPartIndex, 
  onSelectPart, 
  onDeletePart,
  isAddingPart,
  onToggleAdd
}) => {
  return (
    <div className="editor-left-panel">
      <div className="editor-panel-header">
        <h3>Clip Parts <span>({clips.length})</span></h3>
        <button 
          className={`add-clip-btn ${isAddingPart ? 'active' : ''}`} 
          onClick={onToggleAdd}
          title="Add new part"
        >
          {isAddingPart ? 'Cancel Add' : '+ Add'}
        </button>
      </div>
      
      <div className="editor-clips-list">
        {clips.map((clip, index) => (
          <div 
            key={clip.id} 
            className={`editor-clip-card ${selectedPartIndex === index ? 'selected' : ''}`}
            onClick={() => onSelectPart(index)}
          >
            <div className="editor-clip-card-header">
              <span className="part-number">Part {index + 1}</span>
              <span className="duration">{(clip.duration).toFixed(1)}s</span>
            </div>
            <div className="editor-clip-card-body">
              <p className="clip-text">
                {clip.words && clip.words.length > 0 
                  ? clip.words.map(w => w.word).join(' ') 
                  : 'Empty part'}
              </p>
            </div>
            <button 
              className="delete-clip-btn" 
              onClick={(e) => { e.stopPropagation(); onDeletePart(index); }}
              title="Delete Part"
            >
              🗑️
            </button>
          </div>
        ))}
        {clips.length === 0 && (
          <div style={{ padding: '20px', textAlign: 'center', color: '#666' }}>
            No parts yet. Click + Add to start.
          </div>
        )}
      </div>
    </div>
  );
};
