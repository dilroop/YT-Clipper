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

    // Build a list of all highlighted ranges: { start, end, type: 'selected' | 'other' }
    type HlRange = { start: number; end: number; type: 'selected' | 'other' };
    const hlRanges: HlRange[] = parts
      .map((part, idx) => {
        const sw = mappedWords[part.startWordIndex];
        const ew = mappedWords[part.endWordIndex];
        if (!sw || !ew) return null;
        return {
          start: sw.charStart,
          end: ew.charEnd,
          type: idx === selectedPartIndex ? 'selected' : 'other',
        } as HlRange;
      })
      .filter(Boolean) as HlRange[];

    // For a given character position, find if it falls within any range
    const getRangeAt = (pos: number): HlRange | null => {
      // Prefer 'selected' over 'other' if overlapping
      return (
        hlRanges.find(r => r.type === 'selected' && pos >= r.start && pos < r.end) ||
        hlRanges.find(r => r.type === 'other'    && pos >= r.start && pos < r.end) ||
        null
      );
    };

    // Build React nodes: one <span> per sentence, split by highlight boundaries
    let firstSelectedFound = false;

    return sentences.map((sent, si) => {
      const sentStart = sent.words[0].charStart;
      const nextSentStart = si < sentences.length - 1
        ? sentences[si + 1].words[0].charStart
        : fullText.length;

      // Walk through every character in the sentence and group consecutive same-type spans
      type SpanChunk = { text: string; type: 'selected' | 'other' | 'plain' };
      const chunks: SpanChunk[] = [];
      let i = sentStart;
      while (i < nextSentStart) {
        const range = getRangeAt(i);
        const chunkType = range ? range.type : 'plain';
        // Advance to the next boundary
        let j = i + 1;
        while (j < nextSentStart) {
          const nextRange = getRangeAt(j);
          const nextType = nextRange ? nextRange.type : 'plain';
          if (nextType !== chunkType) break;
          j++;
        }
        chunks.push({ text: fullText.substring(i, j), type: chunkType });
        i = j;
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
          {chunks.map((chunk, j) => {
            if (chunk.type === 'selected') {
              const shouldAssignRef = !firstSelectedFound;
              if (shouldAssignRef) firstSelectedFound = true;
              return (
                <mark
                  key={j}
                  ref={shouldAssignRef ? (el) => { highlightRef.current = el; } : undefined}
                  className="transcript-highlight"
                >
                  {chunk.text}
                </mark>
              );
            }
            if (chunk.type === 'other') {
              return (
                <mark key={j} className="transcript-highlight-other">
                  {chunk.text}
                </mark>
              );
            }
            return <React.Fragment key={j}>{chunk.text}</React.Fragment>;
          })}
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
