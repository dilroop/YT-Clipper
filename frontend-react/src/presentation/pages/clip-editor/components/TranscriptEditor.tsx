import React, { useRef } from 'react';
import type { Clip } from '../../../../domain/types';
import type { TranscriptMapping } from '../../../../domain/transcriptUtils';
import { findWordIndexByCharPosition } from '../../../../domain/transcriptUtils';

interface Props {
  mapping: TranscriptMapping;
  activePart: Clip | null;
  isAddingPart: boolean;
  onAddPart: (startIdx: number, endIdx: number) => void;
  onUpdatePart: (startIdx: number, endIdx: number) => void;
}

export const TranscriptEditor: React.FC<Props> = ({ 
  mapping, 
  activePart, 
  isAddingPart, 
  onAddPart, 
  onUpdatePart 
}) => {
  const containerRef = useRef<HTMLDivElement>(null);

  // Helper to get absolute selection relative to the container
  const getAbsoluteSelectionOffset = () => {
    const selection = window.getSelection();
    if (!selection || selection.rangeCount === 0) return null;
    if (!containerRef.current) return null;

    const range = selection.getRangeAt(0);
    if (range.collapsed) return null;

    const preSelectionRange = range.cloneRange();
    preSelectionRange.selectNodeContents(containerRef.current);
    preSelectionRange.setEnd(range.startContainer, range.startOffset);

    const start = preSelectionRange.toString().length;
    return {
      start: start,
      end: start + range.toString().length
    };
  };

  const handleMouseUp = () => {
    const offsets = getAbsoluteSelectionOffset();
    if (!offsets) return;

    const startIdx = findWordIndexByCharPosition(mapping.words, offsets.start);
    const endIdx = findWordIndexByCharPosition(mapping.words, offsets.end - 1);

    if (startIdx !== -1 && endIdx !== -1) {
      if (isAddingPart) {
        onAddPart(startIdx, endIdx);
      } else if (activePart) {
        onUpdatePart(startIdx, endIdx);
      }
      window.getSelection()?.removeAllRanges();
    }
  };

  // Render logic for highlight
  const renderContent = () => {
    if (!activePart || isAddingPart) {
      return <>{mapping.fullText}</>;
    }

    // Find highlight bounds based on the active part's words
    const partWords = activePart.words;
    if (!partWords || partWords.length === 0) return <>{mapping.fullText}</>;

    const highlightStart = partWords[0].charStart ?? 0;
    const highlightEnd = partWords[partWords.length - 1].charEnd ?? 0;

    const preText = mapping.fullText.substring(0, highlightStart);
    const highlightText = mapping.fullText.substring(highlightStart, highlightEnd);
    const postText = mapping.fullText.substring(highlightEnd);

    return (
      <>
        {preText}
        <span className="transcript-highlight">
          {highlightText}
          {/* Handles can be inserted here as pseudo-elements or absolute generic spans */}
        </span>
        {postText}
      </>
    );
  };

  return (
    <div 
      className="transcript-content editor-transcript" 
      ref={containerRef}
      onMouseUp={handleMouseUp}
      style={{ whiteSpace: 'pre-wrap', cursor: isAddingPart ? 'text' : 'default' }}
    >
      {renderContent()}
    </div>
  );
};
