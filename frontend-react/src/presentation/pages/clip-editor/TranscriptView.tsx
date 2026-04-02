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
  const highlightRef = useRef<HTMLElement | null>(null);

  // Auto-scroll to highlighted text when selection changes
  useEffect(() => {
    if (selectedPartIndex !== null && highlightRef.current) {
      highlightRef.current.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
  }, [selectedPartIndex]);

  // Build sentence-grouped segments with highlight and text effects.
  // Uses mappedWords for accurate character positions — no string scanning.
  const buildSegments = useCallback(() => {
    // Group words into sentence buckets (ending on . ? !)
    type Sentence = { words: MappedWord[]; isQuestion: boolean };
    const sentences: Sentence[] = [];
    let bucket: MappedWord[] = [];

    for (const w of mappedWords) {
      bucket.push(w);
      if (w.word.endsWith('?') || w.word.endsWith('.') || w.word.endsWith('!')) {
        sentences.push({ words: bucket, isQuestion: w.word.endsWith('?') });
        bucket = [];
      }
    }
    if (bucket.length > 0) sentences.push({ words: bucket, isQuestion: false });

    // Determine highlight bounds from selected part
    let hlStart = -1;
    let hlEnd = -1;
    if (selectedPartIndex !== null && parts[selectedPartIndex]) {
      const part = parts[selectedPartIndex];
      const sw = mappedWords[part.startWordIndex];
      const ew = mappedWords[part.endWordIndex];
      if (sw && ew) { hlStart = sw.charStart; hlEnd = ew.charEnd; }
    }

    // Build React nodes: one <span> per sentence, split into hl/non-hl parts
    return sentences.map((sent, si) => {
      const sentStart = sent.words[0].charStart;
      const nextSentStart = si < sentences.length - 1
        ? sentences[si + 1].words[0].charStart
        : fullText.length;
      const sentText = fullText.substring(sentStart, nextSentStart);

      // Split sentence text into highlighted / plain parts
      type Part = { text: string; hl: boolean };
      const parts_: Part[] = [];
      const noHighlight = hlStart < 0 || hlEnd <= sentStart || hlStart >= nextSentStart;

      if (noHighlight) {
        parts_.push({ text: sentText, hl: false });
      } else if (hlStart <= sentStart && hlEnd >= nextSentStart) {
        parts_.push({ text: sentText, hl: true });
      } else {
        const a = Math.max(sentStart, hlStart);
        const b = Math.min(nextSentStart, hlEnd);
        if (a > sentStart) parts_.push({ text: fullText.substring(sentStart, a), hl: false });
        if (b > a)         parts_.push({ text: fullText.substring(a, b),         hl: true  });
        if (b < nextSentStart) parts_.push({ text: fullText.substring(b, nextSentStart), hl: false });
      }

      const sentStyle: React.CSSProperties = sent.isQuestion ? {
        textDecoration: 'underline dashed',
        textDecorationColor: 'rgba(255, 200, 60, 0.85)',
        textUnderlineOffset: '4px',
      } : {};

      return (
        <span
          key={si}
          className={`transcript-sentence${sent.isQuestion ? ' question-sentence' : ''}`}
          style={sentStyle}
        >
          {parts_.map((p, j) =>
            p.hl ? (
              <mark key={j} ref={j === 0 ? highlightRef : undefined} className="transcript-highlight">
                {p.text}
              </mark>
            ) : (
              <React.Fragment key={j}>{p.text}</React.Fragment>
            )
          )}
        </span>
      );
    });
  }, [fullText, mappedWords, parts, selectedPartIndex]);

  const sentenceNodes = buildSegments();

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
      {sentenceNodes}
    </div>
  );
};
