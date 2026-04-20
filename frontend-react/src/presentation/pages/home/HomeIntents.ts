import type { VideoData, Clip } from '../../../domain/types';

// ─── Screen State Machine ────────────────────────────────────────────────────
// URL input + header are ALWAYS visible — these screens govern the panel below.
export type HomeScreen =
  | 'videoInfo'      // Thumbnail + config grid + workflow buttons
  | 'generating'     // Progress bar (analysis OR processing)
  | 'aiSuggestions'  // Suggested clip grid (after manual analysis)
  | 'clipsReady';    // Final clips ready

export type GenerationMode = 'auto' | 'manual' | null;

// ─── Progress ────────────────────────────────────────────────────────────────
export interface ProgressState {
  percent: number;
  message: string;
  stage: string | null;
}

// ─── Home State ──────────────────────────────────────────────────────────────
export interface HomeState {
  url: string;

  // Video metadata (fetched after URL paste)
  infoStatus: 'idle' | 'loading' | 'success' | 'error';
  videoInfo: VideoData | null;

  // Config (shown in videoInfo screen)
  selectedFormat: string;
  burnCaptions: boolean;
  aiStrategy: string;
  extraContext: string;
  aiContentPosition: 'top' | 'bottom';
  aiContentFile: File | null;

  // State machine
  screen: HomeScreen | null;
  generationMode: GenerationMode;

  // Progress (shown in generating screen)
  progress: ProgressState | null;

  // Clips (shown in aiSuggestions or clipsReady)
  clips: Clip[] | null;
  fullTranscriptWords: any[] | null;

  // AI provider selection
  availableStrategies: string[];
  aiProvider: 'openai' | 'deepseek';

  error: string | null;
  clientId: string | null;
}

export const initialHomeState: HomeState = {
  url: '',
  infoStatus: 'idle',
  videoInfo: null,
  selectedFormat: localStorage.getItem('ytc_selected_format') || 'vertical_9x16',
  burnCaptions: localStorage.getItem('ytc_burn_captions') !== 'false',
  aiStrategy: localStorage.getItem('ytc_ai_strategy') || 'viral-moments',
  extraContext: '',
  aiContentPosition: (localStorage.getItem('ytc_ai_content_position') as 'top' | 'bottom') || 'top',
  aiContentFile: null,
  screen: null,
  generationMode: null,
  progress: null,
  clips: null,
  fullTranscriptWords: null,
  availableStrategies: ['viral-moments', 'multi-part-narrative', 'educational-insights'],
  aiProvider: (localStorage.getItem('ytc_ai_provider') as 'openai' | 'deepseek') || 'openai',
  error: null,
  clientId: null,
};

// ─── Intents ─────────────────────────────────────────────────────────────────
export type HomeIntent =
  // URL / Config
  | { type: 'UPDATE_URL'; payload: string }
  | { type: 'CLEAR_INPUT' }
  | { type: 'UPDATE_FORMAT'; payload: string }
  | { type: 'TOGGLE_CAPTIONS'; payload: boolean }
  | { type: 'UPDATE_STRATEGY'; payload: string }
  | { type: 'UPDATE_EXTRA_CONTEXT'; payload: string }
  | { type: 'UPDATE_AI_PROVIDER'; payload: 'openai' | 'deepseek' }
  | { type: 'UPDATE_POSITION'; payload: 'top' | 'bottom' }
  | { type: 'UPDATE_AI_CONTENT_FILE'; payload: File | null }
  | { type: 'SET_AVAILABLE_STRATEGIES'; payload: string[] }
  // WebSocket
  | { type: 'WS_CONNECTED'; payload: string }
  | { type: 'WS_PROGRESS'; payload: ProgressState }
  // Video Info
  | { type: 'START_INFO_FETCH' }
  | { type: 'INFO_FETCH_SUCCESS'; payload: VideoData }
  | { type: 'INFO_FETCH_ERROR'; payload: string }
  // Analysis (manual flow)
  | { type: 'START_ANALYSIS' }
  | { type: 'ANALYSIS_SUCCESS'; payload: { clips: Clip[]; fullTranscriptWords?: any[] } }
  | { type: 'ANALYSIS_ERROR'; payload: string }
  // Process (auto or generate-selected flow)
  | { type: 'START_PROCESS'; payload: GenerationMode }
  | { type: 'PROCESS_SUCCESS' }
  | { type: 'PROCESS_ERROR'; payload: string }
  // Clips
  | { type: 'UPDATE_CLIP'; payload: { index: number; clip: Clip } }
  | { type: 'ADD_CUSTOM_CLIP'; payload: Clip }
  // Upload Local
  | { type: 'START_UPLOAD' }
  | { type: 'UPLOAD_SUCCESS'; payload: VideoData }
  | { type: 'UPLOAD_ERROR'; payload: string }
  // Reset
  | { type: 'RESET_TO_VIDEO_INFO' };

// ─── Reducer ─────────────────────────────────────────────────────────────────
export function homeReducer(state: HomeState, intent: HomeIntent): HomeState {
  switch (intent.type) {
    // URL
    case 'UPDATE_URL':
      if (!intent.payload) {
        // Clearing URL resets everything
        return { ...initialHomeState, clientId: state.clientId };
      }
      // If URL changes while info was fetched for a different URL, reset info
      return {
        ...state,
        url: intent.payload,
        // Reset info/screen if URL changed and we already had data
        infoStatus: state.url !== intent.payload ? 'idle' : state.infoStatus,
        videoInfo: state.url !== intent.payload && state.infoStatus === 'success' ? null : state.videoInfo,
        screen: state.url !== intent.payload && state.infoStatus === 'success' ? null : state.screen,
        error: null,
      };
    case 'CLEAR_INPUT':
      return { ...initialHomeState, clientId: state.clientId };

    // Config
    case 'UPDATE_FORMAT':        return { ...state, selectedFormat: intent.payload };
    case 'TOGGLE_CAPTIONS':      return { ...state, burnCaptions: intent.payload };
    case 'UPDATE_STRATEGY':      return { ...state, aiStrategy: intent.payload };
    case 'UPDATE_EXTRA_CONTEXT': return { ...state, extraContext: intent.payload };
    case 'UPDATE_AI_PROVIDER':   return { ...state, aiProvider: intent.payload };
    case 'UPDATE_POSITION':      return { ...state, aiContentPosition: intent.payload };
    case 'UPDATE_AI_CONTENT_FILE':return { ...state, aiContentFile: intent.payload };
    case 'SET_AVAILABLE_STRATEGIES': return { ...state, availableStrategies: intent.payload };

    // WebSocket
    case 'WS_CONNECTED': return { ...state, clientId: intent.payload };
    case 'WS_PROGRESS':  return { ...state, progress: intent.payload };

    // Video Info
    case 'START_INFO_FETCH':
      return { ...state, infoStatus: 'loading', videoInfo: null, screen: null, error: null };
    case 'INFO_FETCH_SUCCESS':
      return { ...state, infoStatus: 'success', videoInfo: intent.payload, screen: 'videoInfo', error: null };
    case 'INFO_FETCH_ERROR':
      return { ...state, infoStatus: 'error', error: intent.payload };

    // Analysis
    case 'START_ANALYSIS':
      return { ...state, screen: 'generating', generationMode: 'manual', progress: null, clips: null, error: null };
    case 'ANALYSIS_SUCCESS':
      return { 
        ...state, 
        screen: 'aiSuggestions', 
        clips: intent.payload.clips, 
        fullTranscriptWords: intent.payload.fullTranscriptWords || null,
        progress: null 
      };
    case 'ANALYSIS_ERROR':
      return { ...state, screen: 'videoInfo', error: intent.payload };

    // Process
    case 'START_PROCESS':
      return { ...state, screen: 'generating', generationMode: intent.payload, progress: null, error: null };
    case 'PROCESS_SUCCESS':
      return { ...state, screen: 'clipsReady', progress: null };
    case 'PROCESS_ERROR':
      return { ...state, screen: state.clips ? 'aiSuggestions' : 'videoInfo', error: intent.payload };

    // Clip editing
    case 'UPDATE_CLIP': {
      if (!state.clips) return state;
      const clips = [...state.clips];
      clips[intent.payload.index] = intent.payload.clip;
      return { ...state, clips };
    }
    case 'ADD_CUSTOM_CLIP': {
      const clips = state.clips ? [...state.clips] : [];
      clips.unshift(intent.payload);
      return { ...state, clips };
    }

    // Reset back to config screen
    case 'RESET_TO_VIDEO_INFO':
      return { ...state, screen: 'videoInfo', progress: null, clips: null, error: null, generationMode: null };

    // Upload
    case 'START_UPLOAD':
      return { ...state, infoStatus: 'loading', error: null, screen: null, videoInfo: null };
    case 'UPLOAD_SUCCESS':
      return { ...state, infoStatus: 'success', videoInfo: intent.payload, screen: 'videoInfo', url: intent.payload.url || '' };
    case 'UPLOAD_ERROR':
      return { ...state, infoStatus: 'error', error: intent.payload };

    default:
      return state;
  }
}
