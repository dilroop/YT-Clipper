import type { VideoData, Clip, TranscriptWord } from '../domain/types';

export interface AnalyzeResult {
  video: VideoData;
  clips: Clip[];
  full_transcript_words?: TranscriptWord[];
}

export interface HistoryEntry {
  id: number;
  url: string;
  video_id: string;
  title: string;
  channel: string;
  duration: number;
  thumbnail: string;
  view_count: number;
  last_viewed: string;
}

export interface CaptionSettings {
  words_per_caption: number;
  font_family: string;
  font_size: number;
  vertical_position: number;
}

export interface AIValidation {
  min_clip_duration: number;
  max_clip_duration: number;
}

export interface AIProviderSettings {
  api_key?: string;
  model?: string;
  temperature?: number;
}

export interface AppConfig {
  caption_settings: CaptionSettings;
  ai_validation: AIValidation;
  downloader_backend?: string;
  ai_settings?: {
    openai?: AIProviderSettings;
    deepseek?: AIProviderSettings;
  };
}

export class VideoRepository {
  private static readonly API_BASE = '/api';

  static async fetchThumbnail(url: string): Promise<VideoData> {
    const response = await fetch(`${this.API_BASE}/thumbnail`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url }),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to fetch video thumbnail');
    }

    return response.json();
  }

  static async analyzeVideo(url: string, strategy: string, extraContext: string | null = null, clientId: string, aiProvider: string = 'openai', skipAi: boolean = false): Promise<AnalyzeResult> {
    const response = await fetch(`${this.API_BASE}/analyze`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        url,
        ai_strategy: strategy,
        extra_context: extraContext,
        client_id: clientId,
        ai_provider: aiProvider,
        skip_ai: skipAi,
      }),
    });

    if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to analyze video');
    }

    return response.json();
  }

  static async processVideo(
    url: string,
    format: string,
    burnCaptions: boolean,
    strategy: string,
    extraContext: string | null = null,
    clientId: string,
    selectedClips?: string[],
    preanalyzedClips?: Clip[],
    fullTranscriptWords?: TranscriptWord[],
    aiProvider: string = 'openai',
    aiContentPosition: 'top' | 'bottom' = 'top',
    aiContentFile: File | null = null,
  ): Promise<void> {

    let aiContentPath: string | undefined = undefined;

    // If an AI content file is provided, upload it first
    if (aiContentFile && (format === 'stacked_photo' || format === 'stacked_video')) {
      const formData = new FormData();
      formData.append('file', aiContentFile);

      const uploadRes = await fetch(`${this.API_BASE}/upload`, {
        method: 'POST',
        body: formData,
      });

      if (!uploadRes.ok) {
        const error = await uploadRes.json().catch(() => ({}));
        throw new Error(error.detail || 'Failed to upload custom AI content file');
      }

      const uploadData = await uploadRes.json();
      aiContentPath = uploadData.path;
    }

    const response = await fetch(`${this.API_BASE}/process`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        url,
        format,
        burn_captions: burnCaptions,
        ai_strategy: strategy,
        extra_context: extraContext,
        client_id: clientId,
        ai_provider: aiProvider,
        ai_content_position: aiContentPosition,
        ...(aiContentPath ? { ai_content_path: aiContentPath } : {}),
        ...(selectedClips ? { selected_clips: selectedClips } : {}),
        ...(preanalyzedClips ? { preanalyzed_clips: preanalyzedClips } : {}),
        ...(fullTranscriptWords ? { full_transcript_words: fullTranscriptWords } : {}),
      }),
    });

    if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to process video');
    }
  }

  // ─── History ─────────────────────────────────────────────────────────────

  static async getHistory(limit: number = 50): Promise<HistoryEntry[]> {
    const response = await fetch(`${this.API_BASE}/history?limit=${limit}`);
    if (!response.ok) throw new Error('Failed to fetch history');
    const data = await response.json();
    return data.history || [];
  }

  static async clearHistory(): Promise<void> {
    const response = await fetch(`${this.API_BASE}/history`, { method: 'DELETE' });
    if (!response.ok) throw new Error('Failed to clear history');
  }

  static async deleteHistoryEntry(videoId: string): Promise<void> {
    const response = await fetch(`${this.API_BASE}/history/${videoId}`, { method: 'DELETE' });
    if (!response.ok) throw new Error('Failed to delete history entry');
  }

  // ─── Config ──────────────────────────────────────────────────────────────

  static async getConfig(): Promise<AppConfig> {
    const response = await fetch(`${this.API_BASE}/config`);
    if (!response.ok) throw new Error('Failed to fetch config');
    return response.json();
  }

  static async saveConfig(configUpdate: Partial<AppConfig>): Promise<AppConfig> {
    const response = await fetch(`${this.API_BASE}/config`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(configUpdate),
    });
    if (!response.ok) throw new Error('Failed to save config');
    const data = await response.json();
    return data.config;
  }

  // ─── Generated Clips (Gallery) ───────────────────────────────────────────

  static async getGeneratedClips(): Promise<any[]> {
    const response = await fetch(`${this.API_BASE}/clips`);
    if (!response.ok) throw new Error('Failed to fetch generated clips');
    const data = await response.json();
    return data.clips || [];
  }

  static async getClipDetails(project: string, format: string, filename: string): Promise<any> {
    const response = await fetch(`${this.API_BASE}/clips/${encodeURIComponent(project)}/${encodeURIComponent(format)}/${encodeURIComponent(filename)}`);
    if (!response.ok) throw new Error('Failed to fetch clip details');
    const data = await response.json();
    return data.clip;
  }

  static async runWorkflow(
    project: string,
    format: string,
    filename: string,
    clientId: string,
    secondMedia: File,
    mainPosition: string,
    text: string,
    watermarkText: string,
    watermarkSize: number,
    watermarkAlpha: number,
    watermarkTop: number,
    watermarkRight: number
  ): Promise<any> {
    const formData = new FormData();
    formData.append('client_id', clientId);
    formData.append('second_media', secondMedia);
    formData.append('main_position', mainPosition);
    formData.append('text', text);
    formData.append('watermark_text', watermarkText);
    formData.append('watermark_size', watermarkSize.toString());
    formData.append('watermark_alpha', watermarkAlpha.toString());
    formData.append('watermark_top', watermarkTop.toString());
    formData.append('watermark_right', watermarkRight.toString());

    const url = `${this.API_BASE}/workflow/run/${encodeURIComponent(project)}/${encodeURIComponent(format)}/${encodeURIComponent(filename)}`;
    
    const response = await fetch(url, {
      method: 'POST',
      body: formData,
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new Error(error.detail || 'Failed to run workflow');
    }

    return response.json();
  }

  static async deleteClip(project: string, format: string, filename: string): Promise<{success: boolean, message: string}> {
    const res = await fetch(`${this.API_BASE}/clips/${encodeURIComponent(project)}/${encodeURIComponent(format)}/${encodeURIComponent(filename)}`, {
      method: 'DELETE'
    });
    const data = await res.json();
    if (!res.ok) {
      throw new Error(data.detail || 'Failed to delete clip');
    }
    return data;
  }

  static async generateMetadata(project: string, format: string, filename: string): Promise<{success: boolean, clip: {title: string, description: string, keywords: string[]}}> {
    const res = await fetch(`${this.API_BASE}/clips/${encodeURIComponent(project)}/${encodeURIComponent(format)}/${encodeURIComponent(filename)}/generate-metadata`, {
      method: 'POST'
    });
    const data = await res.json();
    if (!res.ok) {
      throw new Error(data.detail || 'Failed to generate metadata');
    }
    return data;
  }
}
