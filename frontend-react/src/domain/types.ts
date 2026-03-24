// Core Domain Types for YTClipper

export interface TranscriptWord {
  word: string;
  start: number;
  end: number;
  text?: string;       // Fallback for some backend response formats
  charStart?: number;  // Computed via text mapping
  charEnd?: number;    // Computed via text mapping
}

export interface ClipPart {
  start: number;
  end: number;
  duration: number;
  text: string;
}

export interface Clip {
  id: string;
  title: string;
  explanation: string;
  start: number;
  end: number;
  score: number;
  duration: number;
  words: TranscriptWord[];
  
  // Multi-part support
  parts?: ClipPart[];
  
  // Validation
  validation_status?: 'valid' | 'overlap' | 'error';
  validation_message?: string;
  
  // Extension properties for the Clip Editor features (grouping/parts)
  groupId?: string;
  isPart?: boolean;
}

export interface VideoData {
  id: string;
  title: string;
  duration: number;
  thumbnail: string;
  channel: string;
  original_duration?: number;
}
