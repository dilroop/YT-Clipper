import type { TranscriptWord, Clip } from './types';

export interface TranscriptMapping {
  words: TranscriptWord[];
  fullText: string;
}

/**
 * Builds a continuous character-level mapping from the transcript words.
 * Ported from vanilla JS script.js -> domain logic
 */
export function buildTranscriptWordMapping(
  fullWords: TranscriptWord[] | undefined,
  clips: Clip[]
): TranscriptMapping {
  let sourceWords: TranscriptWord[];

  if (fullWords && fullWords.length > 0) {
    sourceWords = fullWords;
  } else {
    // Fallback: collect unique words from AI-suggested clips
    const wordMap = new Map<number, TranscriptWord>();
    clips.forEach((clip) => {
      (clip.words || []).forEach((w) => {
        const wordText = (w.word || w.text || '').trim();
        if (wordText && !wordMap.has(w.start)) {
          wordMap.set(w.start, { ...w, word: wordText });
        }
      });
    });
    sourceWords = Array.from(wordMap.values()).sort((a, b) => a.start - b.start);
  }

  let charPosition = 0;
  let fullText = '';
  const words: TranscriptWord[] = [];

  sourceWords.forEach((word, index) => {
    const wordText = (word.word || word.text || '').trim();
    if (!wordText) return;

    const charStart = charPosition;
    const charEnd = charPosition + wordText.length;

    words.push({
      ...word,
      word: wordText,
      charStart,
      charEnd,
    });

    fullText += wordText;
    charPosition = charEnd;

    // Add space after each word except the last
    if (index < sourceWords.length - 1) {
      fullText += ' ';
      charPosition += 1;
    }
  });

  return { words, fullText };
}

/**
 * Finds the index of a word given an absolute character position.
 */
export function findWordIndexByCharPosition(words: TranscriptWord[], charPos: number): number {
  for (let i = 0; i < words.length; i++) {
    const word = words[i];
    if (word.charStart !== undefined && word.charEnd !== undefined) {
      if (charPos >= word.charStart && charPos <= word.charEnd) {
        return i;
      }
    }
  }
  return -1;
}

/**
 * Finds the index of a word given a time in seconds.
 */
export function findWordIndexByTime(words: TranscriptWord[], time: number): number {
    for (let i = 0; i < words.length; i++) {
        const word = words[i];
        if (time >= word.start && time <= word.end) {
            return i;
        }
        if (time < word.start) {
            return Math.max(0, i - 1);
        }
    }
    return Math.max(0, words.length - 1);
}
