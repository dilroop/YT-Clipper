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
  text_color?: string;
  outline_color?: string;
  outline_width?: number;
  outline_opacity?: number;
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

  static async uploadLocalVideo(file: File): Promise<VideoData> {
    const formData = new FormData();
    formData.append('file', file);

    const response = await fetch(`${this.API_BASE}/upload-video`, {
      method: 'POST',
      body: formData,
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new Error(error.detail || 'Failed to upload local video');
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

  static async getStrategies(): Promise<string[]> {
    const response = await fetch(`${this.API_BASE}/strategies`);
    if (!response.ok) throw new Error('Failed to fetch strategies');
    const data = await response.json();
    return data.strategies || [];
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

  static async setClipMarker(project: string, format: string, filename: string, markerColor: string | null): Promise<void> {
    const response = await fetch(`${this.API_BASE}/clips/${encodeURIComponent(project)}/${encodeURIComponent(format)}/${encodeURIComponent(filename)}/marker`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ marker_color: markerColor })
    });
    if (!response.ok) throw new Error('Failed to set clip marker');
  }


  static async getTranscript(videoId: string): Promise<any[]> {
    const response = await fetch(`${this.API_BASE}/transcript/${encodeURIComponent(videoId)}`);
    if (!response.ok) throw new Error('Failed to fetch full transcript');
    const data = await response.json();
    return data.full_transcript_words || [];
  }

  static async runWorkflow(
    project: string,
    format: string,
    filename: string,
    clientId: string,
    secondMediaFiles: File[],
    secondMediaDurations: number[],
    mainPosition: string,
    text: string,
    watermarkText: string,
    watermarkSize: number,
    watermarkAlpha: number,
    watermarkTop: number,
    watermarkRight: number,
    fontFamily: string,
    textColor: string,
    textBgColor: string,
    textSize: number,
    text_pos_x: number,
    text_pos_y: number,
    highlightColor: string = '#FFFF00',
    detectionMode: string = "face",
  ): Promise<any> {
    const formData = new FormData();
    formData.append('client_id', clientId);
    for (const file of secondMediaFiles) {
      formData.append('second_media_files', file);
    }
    formData.append('second_media_durations', JSON.stringify(secondMediaDurations));
    formData.append('main_position', mainPosition);
    formData.append('text', text);
    formData.append('watermark_text', watermarkText);
    formData.append('watermark_size', watermarkSize.toString());
    formData.append('watermark_alpha', watermarkAlpha.toString());
    formData.append('watermark_top', watermarkTop.toString());
    formData.append('watermark_right', watermarkRight.toString());
    formData.append('font_family', fontFamily);
    formData.append('text_color', textColor);
    formData.append('text_bg_color', textBgColor);
    formData.append('text_size', textSize.toString());
    formData.append('text_pos_x', text_pos_x.toString());
    formData.append('text_pos_y', text_pos_y.toString());
    formData.append('highlight_color', highlightColor);
    formData.append('detection_mode', detectionMode);

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

  static async getWorkflowPreview(
    project: string,
    format: string,
    filename: string,
    secondMedia: File,
    mainPosition: string,
    text: string,
    fontFamily: string,
    textColor: string,
    textBgColor: string,
    highlightColor: string,
    textSize: number,
    textPosX: number,
    textPosY: number,
    outlineWidth: number,
    watermarkText: string,
    watermarkSize: number,
    watermarkAlpha: number,
    watermarkTop: number,
    watermarkRight: number,
    detectionMode: string,
    signal?: AbortSignal,
  ): Promise<any> {
    const formData = new FormData();
    formData.append('second_media', secondMedia);
    formData.append('main_position', mainPosition);
    formData.append('text', text);
    formData.append('font_family', fontFamily);
    formData.append('text_color', textColor);
    formData.append('text_bg_color', textBgColor);
    formData.append('highlight_color', highlightColor);
    formData.append('text_size', textSize.toString());
    formData.append('text_pos_x', textPosX.toString());
    formData.append('text_pos_y', textPosY.toString());
    formData.append('outline_width', outlineWidth.toString());
    formData.append('watermark_text', watermarkText);
    formData.append('watermark_size', watermarkSize.toString());
    formData.append('watermark_alpha', watermarkAlpha.toString());
    formData.append('watermark_top', watermarkTop.toString());
    formData.append('watermark_right', watermarkRight.toString());
    formData.append('detection_mode', detectionMode);
    const url = `${this.API_BASE}/workflow/preview/${encodeURIComponent(project)}/${encodeURIComponent(format)}/${encodeURIComponent(filename)}`;
    const response = await fetch(url, { method: 'POST', body: formData, signal });
    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new Error(error.detail || 'Failed to get workflow preview');
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

  static async runWorkflow2(
    project: string,
    format: string,
    filename: string,
    clientId: string,
    headerImage: File,
    storyText: string,
    suffixText1: string,
    suffixText2: string,
    topMargin: number,
    padding: number,
    headerHeight: number,
    bgColor: string,
    fontName: string,
    storySize: number,
    storyColor: string,
    highlightColor: string,
    suffix1Size: number,
    suffix1Color: string,
    suffix2Size: number,
    suffix2Color: string,
    fps: number,
    cropMode: string = '9:8',
    autoScale: boolean = false,
  ): Promise<any> {
    const formData = new FormData();
    formData.append('client_id', clientId);
    formData.append('header_image', headerImage);
    formData.append('story_text', storyText);
    formData.append('suffix_text1', suffixText1);
    formData.append('suffix_text2', suffixText2);
    formData.append('top_margin', topMargin.toString());
    formData.append('padding', padding.toString());
    formData.append('header_height', headerHeight.toString());
    formData.append('bg_color', bgColor);
    formData.append('font_name', fontName);
    formData.append('story_size', storySize.toString());
    formData.append('story_color', storyColor);
    formData.append('highlight_color', highlightColor);
    formData.append('suffix1_size', suffix1Size.toString());
    formData.append('suffix1_color', suffix1Color);
    formData.append('suffix2_size', suffix2Size.toString());
    formData.append('suffix2_color', suffix2Color);
    formData.append('fps', fps.toString());
    formData.append('crop_mode', cropMode);
    formData.append('auto_scale', autoScale.toString());

    const url = `${this.API_BASE}/workflow2/run/${encodeURIComponent(project)}/${encodeURIComponent(format)}/${encodeURIComponent(filename)}`;
    const response = await fetch(url, { method: 'POST', body: formData });
    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new Error(error.detail || 'Failed to run Workflow 2');
    }
    return response.json();
  }

  static async getWorkflow2Preview(
    project: string,
    format: string,
    filename: string,
    headerImage: File,
    storyText: string,
    suffixText1: string,
    suffixText2: string,
    topMargin: number,
    padding: number,
    headerHeight: number,
    bgColor: string,
    fontName: string,
    storySize: number,
    storyColor: string,
    highlightColor: string,
    suffix1Size: number,
    suffix1Color: string,
    suffix2Size: number,
    suffix2Color: string,
    cropMode: string = '9:8',
    autoScale: boolean = false,
    signal?: AbortSignal,
  ): Promise<any> {
    const formData = new FormData();
    formData.append('header_image', headerImage);
    formData.append('story_text', storyText);
    formData.append('suffix_text1', suffixText1);
    formData.append('suffix_text2', suffixText2);
    formData.append('top_margin', topMargin.toString());
    formData.append('padding', padding.toString());
    formData.append('header_height', headerHeight.toString());
    formData.append('bg_color', bgColor);
    formData.append('font_name', fontName);
    formData.append('story_size', storySize.toString());
    formData.append('story_color', storyColor);
    formData.append('highlight_color', highlightColor);
    formData.append('suffix1_size', suffix1Size.toString());
    formData.append('suffix1_color', suffix1Color);
    formData.append('suffix2_size', suffix2Size.toString());
    formData.append('suffix2_color', suffix2Color);
    formData.append('crop_mode', cropMode);
    formData.append('auto_scale', autoScale.toString());

    const url = `${this.API_BASE}/workflow2/preview/${encodeURIComponent(project)}/${encodeURIComponent(format)}/${encodeURIComponent(filename)}`;
    const response = await fetch(url, { method: 'POST', body: formData, signal });
    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new Error(error.detail || 'Failed to get preview');
    }
    return response.json();
  }

  static async runWorkflow3(
    project: string,
    format: string,
    filename: string,
    clientId: string,
    threshold: number,
    keep: number,
  ): Promise<any> {
    const formData = new FormData();
    formData.append('client_id', clientId);
    formData.append('min_silence_len', threshold.toString());
    formData.append('keep_silence_len', keep.toString());

    const url = `${this.API_BASE}/workflow3/run/${encodeURIComponent(project)}/${encodeURIComponent(format)}/${encodeURIComponent(filename)}`;
    const response = await fetch(url, { method: 'POST', body: formData });
    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new Error(error.detail || 'Failed to run Workflow 3');
    }
    return response.json();
  }
}
