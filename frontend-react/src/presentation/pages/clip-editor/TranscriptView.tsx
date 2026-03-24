import React, { useRef, useCallback, useEffect } from 'react';
import type { MappedWord, EditorPart } from './useClipEditorMVI';
import { wordAtChar, getAbsoluteOffset } from './useClipEditorMVI';

interface Props {
  fullText: string;
  mappedWords: MappedWord[];
  parts: EditorPart[];
  selectedPartIndex: number | null;
  isAddingNewPart: boolean;
  onCommitSelection: (start: number, end: number, startWordIdx: number, endWordIdx: number) => void;
}

export const TranscriptView: React.FC<Props> = ({
  fullText,
  mappedWords,
  parts,
  selectedPartIndex,
  isAddingNewPart,
  onCommitSelection,
}) => {
  const containerRef = useRef<HTMLDivElement>(null);

  // Build highlighted HTML from current selected part
  const buildHighlightedHtml = useCallback(() => {
    if (selectedPartIndex === null || !parts[selectedPartIndex]) {
      return [{ text: fullText, highlighted: false }];
    }

    const part = parts[selectedPartIndex];
    const startWord = mappedWords[part.startWordIndex];
    const endWord = mappedWords[part.endWordIndex];

    if (!startWord || !endWord) return [{ text: fullText, highlighted: false }];

    const before = fullText.slice(0, startWord.charStart);
    const highlighted = fullText.slice(startWord.charStart, endWord.charEnd);
    const after = fullText.slice(endWord.charEnd);

    return [
      { text: before, highlighted: false },
      { text: highlighted, highlighted: true },
      { text: after, highlighted: false },
    ];
  }, [fullText, mappedWords, parts, selectedPartIndex]);

  const segments = buildHighlightedHtml();

  // Handle text selection (mouseup)
  const handleMouseUp = useCallback(() => {
    if (!containerRef.current) return;
    const selection = window.getSelection();
    if (!selection || selection.isCollapsed) return;

    const range = selection.getRangeAt(0);

    // Only act if selection is within our container
    if (!containerRef.current.contains(range.commonAncestorContainer)) return;

    try {
      const charStart = getAbsoluteOffset(containerRef.current, range.startContainer, range.startOffset);
      const charEnd = getAbsoluteOffset(containerRef.current, range.endContainer, range.endOffset);

      if (charEnd <= charStart) return;

      const startWord = wordAtChar(charStart, mappedWords);
      const endWord = wordAtChar(charEnd - 1, mappedWords);

      const startWordIdx = mappedWords.indexOf(startWord);
      const endWordIdx = mappedWords.indexOf(endWord);

      onCommitSelection(startWord.start, endWord.end, startWordIdx, endWordIdx);
    } catch (e) {
      console.error('Selection error', e);
    } finally {
      selection.removeAllRanges();
    }
  }, [mappedWords, onCommitSelection]);

  useEffect(() => {
    document.addEventListener('mouseup', handleMouseUp);
    return () => document.removeEventListener('mouseup', handleMouseUp);
  }, [handleMouseUp]);

  return (
    <div
      ref={containerRef}
      className={`editor-transcript-content ${isAddingNewPart ? 'editor-transcript--selecting' : ''}`}
      style={{ userSelect: 'text', cursor: isAddingNewPart ? 'text' : 'default' }}
    >
      {segments.map((seg, i) =>
        seg.highlighted ? (
          <mark key={i} className="transcript-highlight">{seg.text}</mark>
        ) : (
          <span key={i}>{seg.text}</span>
        )
      )}
    </div>
  );
};
