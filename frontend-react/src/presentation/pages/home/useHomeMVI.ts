import { useReducer, useCallback, useEffect, useRef } from 'react';
import { homeReducer, initialHomeState } from './HomeIntents';
import type { Clip } from '../../../domain/types';
import { VideoRepository } from '../../../data/VideoRepository';

export function useHomeMVI() {
  const [state, dispatch] = useReducer(homeReducer, initialHomeState);
  const wsRef = useRef<WebSocket | null>(null);

  // ─── WebSocket Connection ──────────────────────────────────────────────────
  useEffect(() => {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws`;
    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === 'connection') {
          dispatch({ type: 'WS_CONNECTED', payload: data.client_id });
        } else if (data.type === 'progress') {
          dispatch({
            type: 'WS_PROGRESS',
            payload: { percent: data.percent || 0, message: data.message || 'Processing...', stage: data.stage || null }
          });
          
          if (data.stage === 'complete') {
            dispatch({ type: 'PROCESS_SUCCESS' });
          } else if (data.stage === 'error') {
            dispatch({ type: 'PROCESS_ERROR', payload: data.message || 'Unknown processing error' });
          }
        }
      } catch (e) {
        console.error('WS parse error', e);
      }
    };

    return () => { ws.close(); wsRef.current = null; };
  }, []);

  // ─── Persistence ───────────────────────────────────────────────────────────
  useEffect(() => {
    localStorage.setItem('ytc_selected_format', state.selectedFormat);
    localStorage.setItem('ytc_burn_captions', state.burnCaptions.toString());
    localStorage.setItem('ytc_ai_strategy', state.aiStrategy);
    localStorage.setItem('ytc_ai_provider', state.aiProvider);
    localStorage.setItem('ytc_ai_content_position', state.aiContentPosition);
  }, [state.selectedFormat, state.burnCaptions, state.aiStrategy, state.aiProvider, state.aiContentPosition]);

  // URL Auto-Fetch removed - now handled manually by VideoInput via intents.fetchVideoInfo

  // ─── Intent Dispatchers ────────────────────────────────────────────────────
  const updateUrl = useCallback((url: string) => dispatch({ type: 'UPDATE_URL', payload: url }), []);
  const clearInput = useCallback(() => dispatch({ type: 'CLEAR_INPUT' }), []);
  const updateFormat = useCallback((f: string) => dispatch({ type: 'UPDATE_FORMAT', payload: f }), []);
  const toggleCaptions = useCallback((v: boolean) => dispatch({ type: 'TOGGLE_CAPTIONS', payload: v }), []);
  const updateStrategy = useCallback((s: string) => dispatch({ type: 'UPDATE_STRATEGY', payload: s }), []);
  const updateExtraContext = useCallback((s: string) => dispatch({ type: 'UPDATE_EXTRA_CONTEXT', payload: s }), []);
  const updateAiProvider = useCallback((p: 'openai' | 'deepseek') => dispatch({ type: 'UPDATE_AI_PROVIDER', payload: p }), []);

  const resetToVideoInfo = useCallback(() => dispatch({ type: 'RESET_TO_VIDEO_INFO' }), []);

  // ─── Async Workflows ───────────────────────────────────────────────────────
  const fetchVideoInfo = useCallback(async (urlToFetch: string) => {
    if (!urlToFetch) return;
    dispatch({ type: 'START_INFO_FETCH' });
    try {
      const videoData = await VideoRepository.fetchThumbnail(urlToFetch);
      dispatch({ type: 'INFO_FETCH_SUCCESS', payload: videoData });
    } catch (err: any) {
      dispatch({ type: 'INFO_FETCH_ERROR', payload: err.message });
    }
  }, []);

  const analyzeVideo = useCallback(async (skipAi: boolean = false) => {
    if (!state.url || !state.clientId) return;
    dispatch({ type: 'START_ANALYSIS' });
    try {
      const result = await VideoRepository.analyzeVideo(state.url, state.aiStrategy, state.extraContext || null, state.clientId, state.aiProvider, skipAi);
      dispatch({ 
        type: 'ANALYSIS_SUCCESS', 
        payload: { 
          clips: result.clips, 
          fullTranscriptWords: result.full_transcript_words 
        } 
      });
    } catch (err: any) {
      dispatch({ type: 'ANALYSIS_ERROR', payload: err.message });
    }
  }, [state.url, state.aiStrategy, state.extraContext, state.clientId, state.aiProvider]);

  const processVideo = useCallback(async () => {
    if (!state.url || !state.clientId) return;
    dispatch({ type: 'START_PROCESS', payload: 'auto' });
    try {
      await VideoRepository.processVideo(
        state.url, 
        state.selectedFormat, 
        state.burnCaptions, 
        state.aiStrategy, 
        state.extraContext || null, 
        state.clientId, 
        undefined, 
        undefined, 
        undefined, 
        state.aiProvider,
        state.aiContentPosition,
        state.aiContentFile
      );
      // No dispatch here - wait for WS 'complete' stage
    } catch (err: any) {
      dispatch({ type: 'PROCESS_ERROR', payload: err.message });
    }
  }, [state.url, state.selectedFormat, state.burnCaptions, state.aiStrategy, state.extraContext, state.clientId, state.aiProvider, state.aiContentPosition, state.aiContentFile]);

  const processVideoSelection = useCallback(async (clipIds: string[]) => {
    if (!state.url || !state.clientId || !state.clips) return;
    dispatch({ type: 'START_PROCESS', payload: 'manual' });
    
    // Get the actual clip objects for the selected IDs, handling fallback logic
    const selectedClipObjects = state.clips.filter((c, idx) => {
      const clipId = c.id || `clip-${idx}`;
      return clipIds.includes(clipId);
    });
    
    try {
      await VideoRepository.processVideo(
        state.url,
        state.selectedFormat,
        state.burnCaptions,
        state.aiStrategy,
        state.extraContext || null,
        state.clientId,
        clipIds,
        selectedClipObjects,
        state.fullTranscriptWords || undefined,
        state.aiProvider,
        state.aiContentPosition,
        state.aiContentFile
      );
      // No dispatch here - wait for WS 'complete' stage
    } catch (err: any) {
      dispatch({ type: 'PROCESS_ERROR', payload: err.message });
    }
  }, [state.url, state.selectedFormat, state.burnCaptions, state.aiStrategy, state.extraContext, state.clientId, state.clips, state.fullTranscriptWords, state.aiProvider, state.aiContentPosition, state.aiContentFile]);

  const updateClip = useCallback((index: number, clip: Clip) => {
    dispatch({ type: 'UPDATE_CLIP', payload: { index, clip } });
  }, []);

  const addCustomClip = useCallback((clip: Clip) => {
    dispatch({ type: 'ADD_CUSTOM_CLIP', payload: clip });
  }, []);

  const updatePosition = useCallback((pos: 'top' | 'bottom') => {
    dispatch({ type: 'UPDATE_POSITION', payload: pos });
  }, []);

  const updateAiContentFile = useCallback((file: File | null) => {
    dispatch({ type: 'UPDATE_AI_CONTENT_FILE', payload: file });
  }, []);

  return {
    state,
    intents: {
      updateUrl,
      clearInput,
      updateFormat,
      toggleCaptions,
      updateStrategy,
      updateExtraContext,
      updateAiProvider,
      updatePosition,
      updateAiContentFile,
      fetchVideoInfo,
      analyzeVideo,
      processVideo,
      processVideoSelection,
      updateClip,
      addCustomClip,
      resetToVideoInfo,
    }
  };
}
