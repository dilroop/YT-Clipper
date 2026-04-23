import React, { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { VideoRepository } from '../../../data/VideoRepository';
import { ClipScriptEditorPage } from '../clip-editor/ClipScriptEditorPage';
import type { Clip } from '../../../domain/types';

type MediaItem = {
  id: string;
  file: File;
  previewUrl: string | null;
  isVideo: boolean;
  duration: number;
};

export const ClipDetailsPage: React.FC = () => {
  const { project, format, filename } = useParams();
  const navigate = useNavigate();
  const [clip, setClip] = useState<any>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isPlaying, setIsPlaying] = useState(false);

  const [clientId, setClientId] = useState('');
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [mediaItems, setMediaItems] = useState<MediaItem[]>([]);
  const getStoredNumber = (key: string, def: number) => {
    const val = localStorage.getItem(key);
    return val !== null ? Number(val) : def;
  };

  const [mainPosition, setMainPosition] = useState(() => localStorage.getItem('ytc_main_position') || 'bottom');
  const [text, setText] = useState('');
  const [watermarkText, setWatermarkText] = useState(() => localStorage.getItem('ytc_watermark_text') || '@MrSinghExperience');
  const [watermarkSize, setWatermarkSize] = useState(() => getStoredNumber('ytc_watermark_size', 45));
  const [watermarkAlpha, setWatermarkAlpha] = useState(() => getStoredNumber('ytc_watermark_alpha', 0.6));
  const [watermarkTop, setWatermarkTop] = useState(() => getStoredNumber('ytc_watermark_top', 100));
  const [watermarkRight, setWatermarkRight] = useState(() => getStoredNumber('ytc_watermark_right', 40));

  const [fontFamily, setFontFamily] = useState(() => localStorage.getItem('ytc_font_family') || 'Arial');
  const [textColor, setTextColor] = useState(() => localStorage.getItem('ytc_text_color') || '#ffffff');
  const [textBgColor, setTextBgColor] = useState(() => localStorage.getItem('ytc_text_bg_color') || '#000000');
  const [textSize, setTextSize] = useState(() => getStoredNumber('ytc_text_size', 70));
  const [textPosX, setTextPosX] = useState(() => getStoredNumber('ytc_text_pos_x', 50));
  const [textPosY, setTextPosY] = useState(() => getStoredNumber('ytc_text_pos_y', 50));

  useEffect(() => {
    localStorage.setItem('ytc_main_position', mainPosition);
    localStorage.setItem('ytc_watermark_text', watermarkText);
    localStorage.setItem('ytc_watermark_size', watermarkSize.toString());
    localStorage.setItem('ytc_watermark_alpha', watermarkAlpha.toString());
    localStorage.setItem('ytc_watermark_top', watermarkTop.toString());
    localStorage.setItem('ytc_watermark_right', watermarkRight.toString());
    localStorage.setItem('ytc_font_family', fontFamily);
    localStorage.setItem('ytc_text_color', textColor);
    localStorage.setItem('ytc_text_bg_color', textBgColor);
    localStorage.setItem('ytc_text_size', textSize.toString());
    localStorage.setItem('ytc_text_pos_x', textPosX.toString());
    localStorage.setItem('ytc_text_pos_y', textPosY.toString());
  }, [mainPosition, watermarkText, watermarkSize, watermarkAlpha, watermarkTop, watermarkRight, fontFamily, textColor, textBgColor, textSize, textPosX, textPosY]);
  
  const [workflowStatus, setWorkflowStatus] = useState<'idle' | 'running' | 'complete' | 'error'>('idle');
  const [wfDetectionMode, setWfDetectionMode] = useState<'face' | 'torso'>(() => (localStorage.getItem('ytc_wf_detection_mode') as 'face' | 'torso') || 'face');
  const [logs, setLogs] = useState<string[]>([]);
  const wsRef = useRef<WebSocket | null>(null);
  const logsEndRef = useRef<HTMLDivElement>(null);
  const [metaGenStatus, setMetaGenStatus] = useState<'idle' | 'loading' | 'done' | 'error'>('idle');
  const [activePlatform, setActivePlatform] = useState<'youtube' | 'instagram' | 'tiktok'>('youtube');

  // ── Refine workflow state ──────────────────────────────────────────────────
  const [isRefineEditorOpen, setIsRefineEditorOpen] = useState(false);
  const [refineFullTranscript, setRefineFullTranscript] = useState<any[]>([]);
  const [refineLoading, setRefineLoading] = useState(false);
  const [reconstructedClip, setReconstructedClip] = useState<Clip | null>(null);
  const [refineProcessStatus, setRefineProcessStatus] = useState<'idle' | 'running' | 'complete' | 'error'>('idle');
  const [refineLogs, setRefineLogs] = useState<string[]>([]);
  const [refineProgress, setRefineProgress] = useState<{ percent: number; message: string; stage: string } | null>(null);
  const [refineVideoId, setRefineVideoId] = useState<string>("");
  const [refineProject, setRefineProject] = useState<string>("");

  // ── Workflow 2 state ──────────────────────────────────────────────────────
  const [isDialog2Open, setIsDialog2Open] = useState(false);
  const [wf2HeaderImage, setWf2HeaderImage] = useState<File | null>(null);
  const [wf2HeaderPreview, setWf2HeaderPreview] = useState<string | null>(null);
  const [wf2StoryText, setWf2StoryText] = useState(() => localStorage.getItem('ytc_wf2_story_text') || '');
  const [wf2SuffixText1, setWf2SuffixText1] = useState(() => localStorage.getItem('ytc_wf2_suffix1') || '');
  const [wf2SuffixText2, setWf2SuffixText2] = useState(() => localStorage.getItem('ytc_wf2_suffix2') || '');
  const [wf2TopMargin, setWf2TopMargin] = useState(() => getStoredNumber('ytc_wf2_top_margin', 60));
  const [wf2Padding, setWf2Padding] = useState(() => getStoredNumber('ytc_wf2_padding', 40));
  const [wf2HeaderHeight, setWf2HeaderHeight] = useState(() => getStoredNumber('ytc_wf2_header_height', 160));
  const [wf2BgColor, setWf2BgColor] = useState(() => localStorage.getItem('ytc_wf2_bg_color') || '#000000');
  const [wf2FontName, setWf2FontName] = useState(() => localStorage.getItem('ytc_wf2_font_name') || 'Arial');
  const [wf2StorySize, setWf2StorySize] = useState(() => getStoredNumber('ytc_wf2_story_size', 52));
  const [wf2StoryColor, setWf2StoryColor] = useState(() => localStorage.getItem('ytc_wf2_story_color') || '#FFFFFF');
  const [wf2HighlightColor, setWf2HighlightColor] = useState(() => localStorage.getItem('ytc_wf2_highlight_color') || '#22DD66');
  const [wf2Suffix1Size, setWf2Suffix1Size] = useState(() => getStoredNumber('ytc_wf2_suffix1_size', 38));
  const [wf2Suffix1Color, setWf2Suffix1Color] = useState(() => localStorage.getItem('ytc_wf2_suffix1_color') || '#AAAAAA');
  const [wf2Suffix2Size, setWf2Suffix2Size] = useState(() => getStoredNumber('ytc_wf2_suffix2_size', 44));
  const [wf2Suffix2Color, setWf2Suffix2Color] = useState(() => localStorage.getItem('ytc_wf2_suffix2_color') || '#22DD66');
  const [wf2Status, setWf2Status] = useState<'idle' | 'running' | 'complete' | 'error'>('idle');
  const [wf2Logs, setWf2Logs] = useState<string[]>([]);
  const wf2LogsEndRef = useRef<HTMLDivElement>(null);
  
  const [wf2AutoScale, setWf2AutoScale] = useState(() => localStorage.getItem('ytc_wf2_auto_scale') === 'true');
  const [wf2PreviewUrl, setWf2PreviewUrl] = useState<string | null>(null);
  const [isWf2PreviewLoading, setIsWf2PreviewLoading] = useState(false);
  const [wf2Tab, setWf2Tab] = useState<'preview' | 'logs'>('preview');
  const previewAbortControllerRef = useRef<AbortController | null>(null);

  // ── Workflow 3 state ──────────────────────────────────────────────────────
  const [isDialog3Open, setIsDialog3Open] = useState(false);
  const [minSilenceLen, setMinSilenceLen] = useState(() => getStoredNumber('ytc_wf3_min_silence', 500));
  const [keepSilenceLen, setKeepSilenceLen] = useState(() => getStoredNumber('ytc_wf3_keep_silence', 100));
  const [wf3Status, setWf3Status] = useState<'idle' | 'running' | 'complete' | 'error'>('idle');
  const [wf3Logs, setWf3Logs] = useState<string[]>([]);
  const wf3LogsEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (logsEndRef.current) logsEndRef.current.scrollIntoView({ behavior: 'smooth' });
  }, [logs]);

  useEffect(() => {
    if (wf2LogsEndRef.current) wf2LogsEndRef.current.scrollIntoView({ behavior: 'smooth' });
  }, [wf2Logs]);

  useEffect(() => {
    if (wf3LogsEndRef.current) wf3LogsEndRef.current.scrollIntoView({ behavior: 'smooth' });
  }, [wf3Logs]);

  // Persist wf2 text/style prefs
  useEffect(() => {
    localStorage.setItem('ytc_wf2_story_text', wf2StoryText);
    localStorage.setItem('ytc_wf2_suffix1', wf2SuffixText1);
    localStorage.setItem('ytc_wf2_suffix2', wf2SuffixText2);
    localStorage.setItem('ytc_wf2_top_margin', wf2TopMargin.toString());
    localStorage.setItem('ytc_wf2_padding', wf2Padding.toString());
    localStorage.setItem('ytc_wf2_header_height', wf2HeaderHeight.toString());
    localStorage.setItem('ytc_wf2_bg_color', wf2BgColor);
    localStorage.setItem('ytc_wf2_font_name', wf2FontName);
    localStorage.setItem('ytc_wf2_story_size', wf2StorySize.toString());
    localStorage.setItem('ytc_wf2_story_color', wf2StoryColor);
    localStorage.setItem('ytc_wf2_highlight_color', wf2HighlightColor);
    localStorage.setItem('ytc_wf2_suffix1_size', wf2Suffix1Size.toString());
    localStorage.setItem('ytc_wf2_suffix1_color', wf2Suffix1Color);
    localStorage.setItem('ytc_wf2_suffix2_size', wf2Suffix2Size.toString());
    localStorage.setItem('ytc_wf2_suffix2_color', wf2Suffix2Color);
    localStorage.setItem('ytc_wf_detection_mode', wfDetectionMode);
    localStorage.setItem('ytc_wf3_min_silence', minSilenceLen.toString());
    localStorage.setItem('ytc_wf3_keep_silence', keepSilenceLen.toString());
    localStorage.setItem('ytc_wf2_auto_scale', wf2AutoScale.toString());
  }, [wf2StoryText, wf2SuffixText1, wf2SuffixText2, wf2TopMargin, wf2Padding, wf2HeaderHeight, wf2BgColor, wf2FontName, wf2StorySize, wf2StoryColor, wf2HighlightColor, wf2Suffix1Size, wf2Suffix1Color, wf2Suffix2Size, wf2Suffix2Color, wfDetectionMode, minSilenceLen, keepSilenceLen, wf2AutoScale]);

  // Preload default header image
  useEffect(() => {
    fetch('/header.png')
      .then(res => res.blob())
      .then(blob => {
        const file = new File([blob], 'header.png', { type: blob.type || 'image/png' });
        setWf2HeaderImage(file);
        setWf2HeaderPreview(URL.createObjectURL(blob));
      })
      .catch(err => console.error('Failed to preload default header image:', err));
  }, []);

  const refreshWf2Preview = async () => {
    if (!project || !format || !filename || !wf2HeaderImage) return;
    
    // Abort previous request if any
    if (previewAbortControllerRef.current) previewAbortControllerRef.current.abort();
    previewAbortControllerRef.current = new AbortController();

    setIsWf2PreviewLoading(true);
    try {
      const resp = await VideoRepository.getWorkflow2Preview(
        project, format, filename,
        wf2HeaderImage,
        wf2StoryText, wf2SuffixText1, wf2SuffixText2,
        wf2TopMargin, wf2Padding, wf2HeaderHeight,
        wf2BgColor, wf2FontName,
        wf2StorySize, wf2StoryColor, wf2HighlightColor,
        wf2Suffix1Size, wf2Suffix1Color,
        wf2Suffix2Size, wf2Suffix2Color,
        wf2AutoScale,
        previewAbortControllerRef.current.signal
      );
      if (resp.success) {
        setWf2PreviewUrl(`${resp.previewUrl}?t=${Date.now()}`);
      }
    } catch (err: any) {
      if (err.name !== 'AbortError') {
        console.error('Preview error:', err);
      }
    } finally {
      setIsWf2PreviewLoading(false);
    }
  };

  // Debounced auto-preview
  useEffect(() => {
    if (!isDialog2Open) return;
    const timer = setTimeout(() => {
      refreshWf2Preview();
    }, 1000);
    return () => clearTimeout(timer);
  }, [isDialog2Open, wf2StoryText, wf2SuffixText1, wf2SuffixText2, wf2TopMargin, wf2Padding, wf2HeaderHeight, wf2BgColor, wf2FontName, wf2StorySize, wf2StoryColor, wf2HighlightColor, wf2Suffix1Size, wf2Suffix1Color, wf2Suffix2Size, wf2Suffix2Color, wf2AutoScale, wf2HeaderImage]);

  useEffect(() => {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws`;
    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === 'connection' && data.client_id) {
          setClientId(data.client_id);
        } else if (data.type === 'log') {
          setLogs(prev => [...prev, data.line]);
          setWf2Logs(prev => [...prev, data.line]);
          setWf3Logs(prev => [...prev, data.line]);
          setRefineLogs(prev => [...prev, data.line]);
        } else if (data.type === 'progress') {
          // Update refine progress details
          if (data.stage !== 'complete' && data.stage !== 'error') {
            setRefineProgress({ percent: data.percent || 0, message: data.message || '', stage: data.stage || '' });
          }
          if (data.stage === 'complete') {
            setWorkflowStatus('complete');
            setWf2Status('complete');
            setWf3Status('complete');
            setRefineProcessStatus('complete');
            setRefineProgress(null);
          } else if (data.stage === 'error') {
            setWorkflowStatus('error');
            setWf2Status('error');
            setWf3Status('error');
            setRefineProcessStatus('error');
            setLogs(prev => [...prev, data.message]);
            setWf2Logs(prev => [...prev, data.message]);
            setWf3Logs(prev => [...prev, data.message]);
            setRefineLogs(prev => [...prev, data.message]);
          }
        }
      } catch (e) {
        console.error('Failed to parse WS message', e);
      }
    };

    return () => {
      ws.close();
    };
  }, []);

  useEffect(() => {
    if (project && format && filename) {
      VideoRepository.getClipDetails(project, format, filename)
        .then(data => setClip(data))
        .catch(e => {
          console.error(e);
          alert('Failed to load clip details');
        })
        .finally(() => setIsLoading(false));
    }
  }, [project, format, filename]);

  const formatSize = (bytes: number) => {
    return (bytes / (1024 * 1024)).toFixed(2) + ' MB';
  };

  const handleDownload = () => {
    const a = document.createElement('a');
    a.href = `/clips/${encodeURIComponent(project || '')}/${encodeURIComponent(format || '')}/${encodeURIComponent(filename || '')}`;
    a.download = filename || 'clip.mp4';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
  };

  const handleRefine = async () => {
    if (!clip || !clip.info_data) {
      alert("This clip does not have saved metadata to refine.");
      return;
    }
    const clipData = clip.info_data.clip;
    if (!clipData.parts || clipData.parts.length === 0) {
      alert("This clip was generated before parts were saved, or parts are missing. Only newly generated clips can be refined in this version.");
      return;
    }

    try {
      setRefineLoading(true);
      const url = clip.info_data.video.url;
      let videoId = clip.info_data.video.id || clip.info_data.video.video_id;
      
      // Fallback if the ID isn't easily accessible (shouldn't happen with our recent backend fixes)
      if (!videoId) {
        if (url.includes("v=")) {
          videoId = url.split("v=")[1].split("&")[0];
        } else if (url.includes("youtu.be/")) {
          videoId = url.split("youtu.be/")[1].split("?")[0];
        } else {
          videoId = url.split("/").pop() || "";
        }
      }

      let transcript = clipData.full_transcript_words || [];
      if (!transcript || transcript.length === 0) {
          transcript = await VideoRepository.getTranscript(videoId);
      }
      setRefineFullTranscript(transcript);

      const parts = clipData.parts;
      const reconstructed: Clip = {
          id: clipData.title || `refine-${Date.now()}`,
          start: parts[0].start,
          end: parts[parts.length - 1].end,
          duration: clipData.duration_seconds,
          title: clipData.title || "",
          explanation: clipData.description || "",
          score: 1,
          parts: parts,
          words: clipData.words || [],
      };
      setReconstructedClip(reconstructed);
      
      // Pass videoId and project to the editor
      setRefineVideoId(videoId);
      setRefineProject(project || "");
      
      setIsRefineEditorOpen(true);
    } catch (e: any) {
        alert("Could not load refine data: " + e.message);
    } finally {
        setRefineLoading(false);
    }
  };

  const handleRunWorkflow = async () => {
    if (mediaItems.length === 0) {
      alert("Please upload at least one secondary media file.");
      return;
    }
    if (!clientId) {
      alert("Still connecting to server, please wait a moment.");
      return;
    }
    try {
      setWorkflowStatus('running');
      setLogs([]);
      await VideoRepository.runWorkflow(
        project!, format!, filename!, clientId,
        mediaItems.map(m => m.file), 
        mediaItems.map(m => m.duration),
        mainPosition, text, watermarkText,
        watermarkSize, watermarkAlpha, watermarkTop, watermarkRight,
        fontFamily, textColor, textBgColor, textSize, textPosX, textPosY,
        wfDetectionMode
      );
    } catch (e: any) {
      setWorkflowStatus('error');
      setLogs(prev => [...prev, `[ERROR] ${e.message}`]);
    }
  };

  const handleRunWorkflow2 = async () => {
    if (!wf2HeaderImage) { alert('Please upload a header image.'); return; }
    if (!wf2StoryText.trim()) { alert('Please enter story text.'); return; }
    if (!clientId) { alert('Still connecting to server, please wait a moment.'); return; }
    try {
      setWf2Status('running');
      setWf2Logs([]);
      await VideoRepository.runWorkflow2(
        project!, format!, filename!, clientId,
        wf2HeaderImage,
        wf2StoryText, wf2SuffixText1, wf2SuffixText2,
        wf2TopMargin, wf2Padding, wf2HeaderHeight,
        wf2BgColor, wf2FontName,
        wf2StorySize, wf2StoryColor, wf2HighlightColor,
        wf2Suffix1Size, wf2Suffix1Color,
        wf2Suffix2Size, wf2Suffix2Color,
        30,
        wf2AutoScale,
      );
      setWf2Tab('logs'); // Switch to logs when rendering starts
    } catch (e: any) {
      setWf2Status('error');
      setWf2Logs(prev => [...prev, `[ERROR] ${e.message}`]);
    }
  };

  const handleRunWorkflow3 = async () => {
    if (!clientId) return;
    setWf3Status('running');
    setWf3Logs([]);
    setLogs([]);

    try {
      await VideoRepository.runWorkflow3(
        project!,
        format!,
        filename!,
        clientId,
        minSilenceLen,
        keepSilenceLen
      );
    } catch (err: any) {
      setWf3Status('error');
      setWf3Logs(prev => [...prev, `[ERROR] Silence removal failed: ${err.message}`]);
    }
  };

  const handleDelete = async () => {
    if (window.confirm("Are you sure you want to delete this clip and its metadata? This action cannot be undone.")) {
      try {
        await VideoRepository.deleteClip(project!, format!, filename!);
        navigate(-1);
      } catch (e: any) {
        alert(e.message);
      }
    }
  };

  const handleGenerateMetadata = async () => {
    setMetaGenStatus('loading');
    try {
      const result = await VideoRepository.generateMetadata(project!, format!, filename!);
      // Update clip in-place so UI reflects new values immediately
      setClip((prev: any) => ({
        ...prev,
        info_data: {
          ...(prev.info_data || {}),
          clip: result.clip
        }
      }));
      setMetaGenStatus('done');
    } catch (e: any) {
      setMetaGenStatus('error');
      alert(`AI metadata generation failed: ${e.message}`);
    }
  };

  if (isLoading) {
    return <div style={{ minHeight: '100vh', background: '#121212', color: '#fff', padding: '48px', textAlign: 'center' }}>Loading...</div>;
  }

  if (!clip) {
    return <div style={{ minHeight: '100vh', background: '#121212', color: '#fff', padding: '48px', textAlign: 'center' }}>Clip not found</div>;
  }

  return (
    <div className="page-container" style={{ minHeight: '100vh', background: '#121212', color: '#fff', fontFamily: '"Inter", sans-serif' }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '16px', marginBottom: '32px' }}>
        <button onClick={() => navigate(-1)} style={{ background: '#252525', border: 'none', borderRadius: '8px', width: '40px', height: '40px', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#fff', cursor: 'pointer' }}>
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M19 12H5M12 19l-7-7 7-7"/></svg>
        </button>
        <button onClick={() => navigate('/')} style={{ background: '#252525', border: 'none', borderRadius: '8px', width: '40px', height: '40px', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#fff', cursor: 'pointer' }}>
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/></svg>
        </button>
        <h1 style={{ margin: 0, fontSize: '1.25rem', color: '#fff', fontWeight: 'bold' }}>Details</h1>
      </div>

      <div style={{ display: 'flex', gap: '24px', flexWrap: 'wrap' }}>
        {/* Left Column: Player & Download */}
        <div style={{ flex: '1 1 300px', maxWidth: '400px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
          <div style={{ background: '#1e1e1e', borderRadius: '12px', padding: '16px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
            
            <div style={{ position: 'relative', width: '100%', display: 'flex' }}>
              <video 
                src={`/clips/${encodeURIComponent(project || '')}/${encodeURIComponent(format || '')}/${encodeURIComponent(filename || '')}`} 
                controls
                onPlay={() => setIsPlaying(true)}
                onPause={() => setIsPlaying(false)}
                onEnded={() => setIsPlaying(false)}
                style={{ width: '100%', borderRadius: '8px', background: '#000', aspectRatio: (format === 'reels' || filename?.includes('_workflow')) ? '9/16' : '16/9' }}
              />
              
              {!isPlaying && (
                <div style={{ position: 'absolute', top: '8px', left: '8px', display: 'flex', gap: '8px', zIndex: 10 }}>
                  <div 
                    draggable
                    onDragStart={(e) => {
                      const videoSrc = `/clips/${encodeURIComponent(project || '')}/${encodeURIComponent(format || '')}/${encodeURIComponent(filename || '')}`;
                      const absoluteUrl = `${window.location.origin}${videoSrc}`;
                      // OS-level drop fallback
                      e.dataTransfer.setData('DownloadURL', `video/mp4:${filename}:${absoluteUrl}`);
                    }}
                    title="Drag this into a Desktop Folder"
                    style={{
                      background: 'rgba(0,0,0,0.8)',
                      backdropFilter: 'blur(4px)',
                      padding: '8px 12px',
                      borderRadius: '6px',
                      color: 'white',
                      cursor: 'grab',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '6px',
                      fontSize: '0.85rem',
                      fontWeight: 'bold',
                      pointerEvents: 'auto',
                      boxShadow: '0 2px 4px rgba(0,0,0,0.3)',
                      border: '1px solid rgba(255,255,255,0.1)'
                    }}
                  >
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
                    Drop to download
                  </div>

                  <button
                    onClick={async (e) => {
                      e.preventDefault();
                      await fetch(`/api/clips/${encodeURIComponent(project || '')}/${encodeURIComponent(format || '')}/${encodeURIComponent(filename || '')}/show-in-folder`, { method: 'POST' });
                    }}
                    title="Open Finder location to drag directly into Instagram"
                    style={{
                      background: 'rgba(59, 130, 246, 0.9)',
                      backdropFilter: 'blur(4px)',
                      padding: '8px 12px',
                      borderRadius: '6px',
                      color: 'white',
                      cursor: 'pointer',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '6px',
                      fontSize: '0.85rem',
                      fontWeight: 'bold',
                      pointerEvents: 'auto',
                      boxShadow: '0 2px 4px rgba(0,0,0,0.3)',
                      border: '1px solid rgba(255,255,255,0.2)'
                    }}
                  >
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/></svg>
                    Reveal File
                  </button>
                </div>
              )}
            </div>

            <button onClick={handleDownload} style={{ width: '100%', padding: '12px', background: '#252525', color: '#fff', border: 'none', borderRadius: '8px', cursor: 'pointer', display: 'flex', justifyContent: 'center', alignItems: 'center', gap: '8px', fontWeight: 'bold' }}>
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
              Download Clip
            </button>
            <button onClick={() => setIsDialog3Open(true)} style={{ width: '100%', padding: '12px', background: '#3b82f6', color: '#fff', border: 'none', borderRadius: '8px', cursor: 'pointer', display: 'flex', justifyContent: 'center', alignItems: 'center', gap: '8px', fontWeight: 'bold' }}>
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M11 5L6 9H2v6h4l5 4V5z"/><path d="M15.54 8.46a5 5 0 0 1 0 7.07"/><path d="M19.07 4.93a10 10 0 0 1 0 14.14"/></svg>
              Remove Silences
            </button>
            <button onClick={() => setIsDialogOpen(true)} style={{ width: '100%', padding: '12px', background: '#444', color: '#fff', border: 'none', borderRadius: '8px', cursor: 'pointer', display: 'flex', justifyContent: 'center', alignItems: 'center', gap: '8px', fontWeight: 'bold' }}>
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polygon points="5 3 19 12 5 21 5 3"></polygon></svg>
              Run Workflow 1
            </button>
            <button onClick={() => setIsDialog2Open(true)} style={{ width: '100%', padding: '12px', background: '#7c3aed', color: '#fff', border: 'none', borderRadius: '8px', cursor: 'pointer', display: 'flex', justifyContent: 'center', alignItems: 'center', gap: '8px', fontWeight: 'bold' }}>
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><rect x="3" y="3" width="18" height="18" rx="2"/><path d="M3 9h18M9 21V9"/></svg>
              Run Workflow 2
            </button>
            {clip.info_data?.clip?.parts?.length > 0 && (
              <button onClick={handleRefine} disabled={refineLoading} style={{ width: '100%', padding: '12px', background: 'rgba(251, 191, 36, 0.2)', color: '#fbbf24', border: '1px solid rgba(251, 191, 36, 0.5)', borderRadius: '8px', cursor: refineLoading ? 'not-allowed' : 'pointer', display: 'flex', justifyContent: 'center', alignItems: 'center', gap: '8px', fontWeight: 'bold', marginTop: '16px' }}>
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M12 20h9"></path><path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"></path></svg>
                {refineLoading ? 'Loading...' : 'Refine Clip'}
              </button>
            )}
            <button onClick={handleDelete} style={{ width: '100%', padding: '12px', background: 'rgba(239, 68, 68, 0.2)', color: '#ef4444', border: '1px solid rgba(239, 68, 68, 0.5)', borderRadius: '8px', cursor: 'pointer', display: 'flex', justifyContent: 'center', alignItems: 'center', gap: '8px', fontWeight: 'bold', marginTop: '16px' }}>
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polyline points="3 6 5 6 21 6"></polyline><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path></svg>
              Delete Clip
            </button>
          </div>
        </div>

        {/* Right Columns: Info Panels */}
        <div style={{ flex: '2 1 500px', display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '24px', alignContent: 'start' }}>
          {/* Middle Column */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
            {/* Unified Metadata Card */}
            <div style={{ background: '#1e1e1e', borderRadius: '12px', padding: '24px', position: 'relative', overflow: 'hidden' }}>
              {/* Platform Toggle Pills */}
              <div style={{ display: 'flex', gap: '8px', marginBottom: '24px', background: 'rgba(0,0,0,0.2)', padding: '4px', borderRadius: '10px', width: 'fit-content' }}>
                {(['youtube', 'instagram', 'tiktok'] as const).map(p => {
                  const isActive = activePlatform === p;
                  return (
                    <button
                      key={p}
                      onClick={() => setActivePlatform(p)}
                      style={{
                        padding: '6px 16px',
                        borderRadius: '8px',
                        border: 'none',
                        background: isActive ? '#3b82f6' : 'transparent',
                        color: isActive ? '#fff' : '#888',
                        fontSize: '0.75rem',
                        fontWeight: 'bold',
                        textTransform: 'uppercase',
                        letterSpacing: '0.5px',
                        cursor: 'pointer',
                        transition: 'all 0.2s',
                      }}
                    >
                      {p}
                    </button>
                  );
                })}
              </div>

              {/* Title Section */}
              <div style={{ marginBottom: '24px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '12px', alignItems: 'center' }}>
                  <h3 style={{ margin: 0, fontSize: '0.75rem', color: '#666', textTransform: 'uppercase', letterSpacing: '1px', fontWeight: 800 }}>TITLE</h3>
                  <button 
                    style={{ background: 'none', border: 'none', color: '#555', cursor: 'pointer', padding: '4px' }} 
                    onClick={() => {
                      const t = clip?.info_data?.clip?.[activePlatform]?.title || (activePlatform === 'youtube' ? (clip?.info_data?.clip?.title || clip?.info_data?.title || '') : '');
                      navigator.clipboard.writeText(t);
                    }}
                  >
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>
                  </button>
                </div>
                <p style={{ margin: 0, lineHeight: 1.5, fontSize: '1.05rem', fontWeight: 500, color: '#efefef' }}>
                  {clip?.info_data?.clip?.[activePlatform]?.title || (activePlatform === 'youtube' ? (clip?.info_data?.clip?.title || clip?.info_data?.title || 'No Title Generated') : `No ${activePlatform} title generated.`)}
                </p>
              </div>

              {/* Description Section */}
              <div style={{ marginBottom: '24px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '12px', alignItems: 'center' }}>
                  <h3 style={{ margin: 0, fontSize: '0.75rem', color: '#666', textTransform: 'uppercase', letterSpacing: '1px', fontWeight: 800 }}>DESCRIPTION</h3>
                  <button 
                    style={{ background: 'none', border: 'none', color: '#555', cursor: 'pointer', padding: '4px' }} 
                    onClick={() => {
                      const d = clip?.info_data?.clip?.[activePlatform]?.description || (activePlatform === 'youtube' ? (clip?.info_data?.clip?.description || clip?.info_data?.description || '') : '');
                      navigator.clipboard.writeText(d);
                    }}
                  >
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>
                  </button>
                </div>
                <p style={{ margin: 0, lineHeight: 1.6, color: '#bbb', fontSize: '0.9rem', whiteSpace: 'pre-wrap' }}>
                  {clip?.info_data?.clip?.[activePlatform]?.description || (activePlatform === 'youtube' ? (clip?.info_data?.clip?.description || clip?.info_data?.description || 'No Description Generated') : `No ${activePlatform} description generated.`)}
                </p>
              </div>

              {/* Tags/Hashtags Section */}
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '12px', alignItems: 'center' }}>
                  <h3 style={{ margin: 0, fontSize: '0.75rem', color: '#666', textTransform: 'uppercase', letterSpacing: '1px', fontWeight: 800 }}>HASHTAGS & KEYWORDS</h3>
                  <button 
                    style={{ background: 'none', border: 'none', color: '#555', cursor: 'pointer', padding: '4px' }} 
                    onClick={() => {
                      const h = clip?.info_data?.clip?.[activePlatform]?.hashtags || clip?.info_data?.clip?.keywords?.join(', ') || '';
                      navigator.clipboard.writeText(h);
                    }}
                  >
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>
                  </button>
                </div>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
                  {clip?.info_data?.clip?.[activePlatform]?.hashtags ? (
                    clip.info_data.clip[activePlatform].hashtags.split(' ').map((tag: string, idx: number) => (
                      <span key={idx} style={{ background: 'rgba(59,130,246,0.1)', color: '#3b82f6', padding: '4px 10px', borderRadius: '6px', fontSize: '0.75rem', fontWeight: 600 }}>{tag}</span>
                    ))
                  ) : (
                    (clip?.info_data?.clip?.keywords || []).map((tag: string, idx: number) => (
                      <span key={idx} style={{ background: 'rgba(255,255,255,0.05)', color: '#888', padding: '4px 10px', borderRadius: '6px', fontSize: '0.75rem' }}>#{tag}</span>
                    ))
                  )}
                </div>
              </div>
            </div>

            <div style={{ background: '#1e1e1e', borderRadius: '12px', padding: '24px' }}>
              <h3 style={{ margin: '0 0 16px 0', fontSize: '1rem', fontWeight: 'bold' }}>Clip Information</h3>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', fontSize: '0.9rem' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', background: '#252525', padding: '12px', borderRadius: '6px' }}>
                  <span style={{ color: '#888' }}>Filename:</span>
                  <span>{clip.filename}</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', background: '#252525', padding: '12px', borderRadius: '6px' }}>
                  <span style={{ color: '#888' }}>Project:</span>
                  <span style={{ textAlign: 'right', wordBreak: 'break-all', maxWidth: '60%' }}>{clip.project}</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', background: '#252525', padding: '12px', borderRadius: '6px' }}>
                  <span style={{ color: '#888' }}>Format:</span>
                  <span style={{ textTransform: 'uppercase' }}>{clip.format}</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', background: '#252525', padding: '12px', borderRadius: '6px' }}>
                  <span style={{ color: '#888' }}>Size:</span>
                  <span>{formatSize(clip.size)}</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', background: '#252525', padding: '12px', borderRadius: '6px' }}>
                  <span style={{ color: '#888' }}>Created:</span>
                  <span>{new Date(clip.created).toLocaleString()}</span>
                </div>
              </div>
            </div>
          </div>

          {/* Far Right Column: Metadata */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
            {/* Transcript Card (Moved here) */}
            <div style={{ background: '#1e1e1e', borderRadius: '12px', padding: '24px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <h3 style={{ margin: 0, fontSize: '1rem', fontWeight: 'bold' }}>Transcript</h3>
                <button 
                  style={{ background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.1)', color: '#888', cursor: 'pointer', padding: '6px 12px', borderRadius: '6px', fontSize: '0.75rem', fontWeight: 'bold', display: 'flex', alignItems: 'center', gap: '6px' }} 
                  onClick={() => {
                    const info = clip?.info_data;
                    const parts = info?.clip?.parts;
                    let text = "";
                    if (parts && parts.length > 0) {
                      text = parts.map((p: any) => p.text).join('\n');
                    } else {
                      text = info?.transcript || info?.clip?.transcript || info?.clip?.text || 
                             (info?.clip?.words ? info.clip.words.map((w: any) => w.word).join(' ') : '') || 
                             clip?.info_text || "";
                    }
                    navigator.clipboard.writeText(text.trim());
                  }}
                  title="Copy full transcript"
                >
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>
                  Copy
                </button>
              </div>
              <div style={{ maxHeight: '300px', overflowY: 'auto', paddingRight: '8px', borderTop: '1px solid rgba(255,255,255,0.05)', paddingTop: '16px' }}>
                {clip?.info_data?.clip?.parts && clip.info_data.clip.parts.length > 0 ? (
                  clip.info_data.clip.parts.map((part: any, idx: number) => (
                    <div key={idx} style={{ marginBottom: '16px' }}>
                      {clip.info_data.clip.parts.length > 1 && (
                        <div style={{ fontSize: '0.7rem', color: '#555', marginBottom: '4px', fontWeight: 'bold' }}>PART {idx + 1}</div>
                      )}
                      <p style={{ margin: 0, lineHeight: 1.6, color: '#bbb', fontSize: '0.95rem' }}>
                        {part.text}
                      </p>
                    </div>
                  ))
                ) : (
                  <p style={{ margin: 0, lineHeight: 1.6, color: '#bbb', fontSize: '0.95rem', whiteSpace: 'pre-wrap' }}>
                    {clip?.info_data?.transcript || clip?.info_data?.clip?.transcript || clip?.info_data?.clip?.text || 
                     (clip?.info_data?.clip?.words ? clip.info_data.clip.words.map((w: any) => w.word).join(' ') : '') || 
                     clip?.info_text || 'No transcript available for this clip.'}
                  </p>
                )}
              </div>
            </div>

            <div style={{ background: '#1e1e1e', borderRadius: '12px', padding: '24px', display: 'flex', flexDirection: 'column', flex: 1 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
              <h3 style={{ margin: 0, fontSize: '1rem', fontWeight: 'bold' }}>Metadata</h3>
              <button
                onClick={handleGenerateMetadata}
                disabled={metaGenStatus === 'loading'}
                title="Generate AI title, description and tags"
                style={{ padding: '5px 10px', background: metaGenStatus === 'done' ? 'rgba(34,197,94,0.15)' : 'rgba(167,139,250,0.1)', color: metaGenStatus === 'done' ? '#4ade80' : '#a78bfa', border: `1px solid ${metaGenStatus === 'done' ? 'rgba(34,197,94,0.4)' : 'rgba(167,139,250,0.3)'}`, borderRadius: '6px', cursor: metaGenStatus === 'loading' ? 'not-allowed' : 'pointer', display: 'flex', alignItems: 'center', gap: '5px', fontSize: '0.8rem', fontWeight: 'bold', opacity: metaGenStatus === 'loading' ? 0.6 : 1, whiteSpace: 'nowrap' }}
              >
                {metaGenStatus === 'loading' ? (
                  <><svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"><path d="M21 12a9 9 0 1 1-6.219-8.56"/></svg> Generating...</>
                ) : metaGenStatus === 'done' ? (
                  <><svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"><polyline points="20 6 9 17 4 12"/></svg> Updated</>
                ) : (
                  <>✨ Generate AI Metadata</>
                )}
              </button>
            </div>
            <div style={{ background: '#121212', borderRadius: '8px', padding: '16px', overflow: 'auto', flex: 1, maxHeight: '600px', fontSize: '0.85rem', color: '#bbb', fontFamily: 'monospace', whiteSpace: 'pre-wrap' }}>
              {clip.info_data ? JSON.stringify(clip.info_data, null, 2) : clip.info_text || "No metadata found."}
            </div>
          </div>
        </div>
      </div>
    </div>

      {/* Workflow Dialog */}
      {isDialogOpen && (
        <div className="responsive-dialog-overlay" style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, background: 'rgba(0,0,0,0.8)', display: 'flex', gap: '24px', zIndex: 1000 }}>
          {/* Dialog Form */}
          <div className="responsive-dialog" style={{ background: '#1e1e1e', borderRadius: '12px', padding: '24px', display: 'flex', flexDirection: 'column', gap: '16px', overflowY: 'auto' }}>
            <h2 style={{ margin: 0 }}>Workflow Settings</h2>
            
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ fontWeight: 600 }}>Secondary Media:</span>
                <span style={{ fontSize: '0.75rem', color: '#888' }}>Images cycle 2s each · Videos play in full</span>
              </div>
              <label style={{ display: 'flex', alignItems: 'center', gap: '10px', padding: '10px 14px', background: '#252525', border: '1px dashed #555', borderRadius: '8px', cursor: 'pointer', color: '#aaa', fontSize: '0.9rem' }}>
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/></svg>
                Add images or videos…
                <input
                  type="file"
                  multiple
                  accept="image/png,image/jpeg,image/jpg,image/webp,image/gif,image/bmp,video/mp4,video/quicktime,video/x-matroska,video/webm,video/avi,.mp4,.mov,.mkv,.avi,.webm,.png,.jpg,.jpeg,.webp,.gif,.bmp"
                  style={{ display: 'none' }}
                  onChange={e => {
                    const addedFiles = Array.from(e.target.files || []);
                    const newItems: MediaItem[] = addedFiles.map(file => {
                      const isVideo = file.type.startsWith('video/');
                      const pUrl = !isVideo ? URL.createObjectURL(file) : null;
                      return {
                        id: Math.random().toString(36).substring(2, 9),
                        file: file,
                        previewUrl: pUrl,
                        isVideo: isVideo,
                        duration: 2, // default 2s for images
                      };
                    });
                    setMediaItems(prev => [...prev, ...newItems]);
                    e.target.value = '';
                  }}
                />
              </label>
              {mediaItems.length > 0 && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', maxHeight: '180px', overflowY: 'auto' }}>
                  {mediaItems.map((item) => (
                    <div key={item.id} style={{ display: 'flex', alignItems: 'center', gap: '12px', background: '#1a1a1a', borderRadius: '6px', padding: '6px 10px', fontSize: '0.82rem' }}>
                      <div style={{ width: '40px', height: '40px', background: '#000', borderRadius: '4px', overflow: 'hidden', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
                        {item.previewUrl ? <img src={item.previewUrl} style={{ width: '100%', height: '100%', objectFit: 'cover' }} /> : <span style={{ fontSize: '20px' }}>🎬</span>}
                      </div>
                      
                      <div style={{ flex: 1, overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
                        <span style={{ color: '#ccc', textOverflow: 'ellipsis', whiteSpace: 'nowrap', overflow: 'hidden' }}>{item.file.name}</span>
                        <span style={{ color: '#666', fontSize: '0.75rem' }}>{formatSize(item.file.size)}</span>
                      </div>

                      {!item.isVideo && (
                        <div style={{ display: 'flex', alignItems: 'center', background: '#252525', borderRadius: '4px', overflow: 'hidden', flexShrink: 0 }}>
                          <button onClick={() => setMediaItems(prev => prev.map(m => m.id === item.id ? { ...m, duration: Math.max(1, m.duration - 1) } : m))} style={{ background: '#333', color: '#fff', border: 'none', padding: '4px 8px', cursor: 'pointer', fontWeight: 'bold' }}>-</button>
                          <div style={{ padding: '0 8px', color: '#fff', fontSize: '0.85rem', width: '20px', textAlign: 'center' }}>{item.duration}s</div>
                          <button onClick={() => setMediaItems(prev => prev.map(m => m.id === item.id ? { ...m, duration: m.duration + 1 } : m))} style={{ background: '#333', color: '#fff', border: 'none', padding: '4px 8px', cursor: 'pointer', fontWeight: 'bold' }}>+</button>
                        </div>
                      )}

                      <button
                        onClick={() => {
                          if (item.previewUrl) URL.revokeObjectURL(item.previewUrl);
                          setMediaItems(prev => prev.filter(m => m.id !== item.id));
                        }}
                        style={{ background: 'none', border: 'none', color: '#ef4444', cursor: 'pointer', padding: '4px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}
                        title="Remove"
                      >✕</button>
                    </div>
                  ))}
                </div>
              )}
            </div>

            <label style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
              <span>Main Video Position:</span>
              <select value={mainPosition} onChange={e => setMainPosition(e.target.value)} style={{ padding: '8px', background: '#252525', border: '1px solid #444', borderRadius: '6px', color: '#fff' }}>
                <option value="top">Top</option>
                <option value="bottom">Bottom</option>
              </select>
            </label>

            <div style={{ background: '#252525', padding: '16px', borderRadius: '8px', border: '1px solid #333' }}>
              <h3 style={{ margin: '0 0 12px 0', fontSize: '0.9rem', color: '#ccc' }}>Text Overlay Settings</h3>
              
              <label style={{ display: 'flex', flexDirection: 'column', gap: '8px', marginBottom: '12px' }}>
                <span>Overlay Text:</span>
                <textarea value={text} onChange={e => setText(e.target.value)} style={{ padding: '8px', background: '#1e1e1e', border: '1px solid #444', borderRadius: '6px', color: '#fff', minHeight: '60px', fontFamily: 'inherit', resize: 'vertical' }} placeholder="Enter text (multiple lines allowed)" />
              </label>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px', marginBottom: '12px' }}>
                <label style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                  <span style={{ fontSize: '0.85rem' }}>Font Family:</span>
                  <select value={fontFamily} onChange={e => setFontFamily(e.target.value)} style={{ padding: '6px', background: '#1e1e1e', border: '1px solid #444', borderRadius: '6px', color: '#fff' }}>
                    <option value="Arial">Arial</option>
                    <option value="Helvetica">Helvetica</option>
                    <option value="Times New Roman">Times New Roman</option>
                    <option value="Impact">Impact</option>
                    <option value="Courier New">Courier New</option>
                  </select>
                </label>
                <label style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                  <span style={{ fontSize: '0.85rem' }}>Text Size:</span>
                  <input type="number" value={textSize} onChange={e => setTextSize(Number(e.target.value))} style={{ padding: '6px', background: '#1e1e1e', border: '1px solid #444', borderRadius: '6px', color: '#fff' }} />
                </label>
                <label style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                  <span style={{ fontSize: '0.85rem' }}>Tracking Focus:</span>
                  <select value={wfDetectionMode} onChange={e => setWfDetectionMode(e.target.value as 'face' | 'torso')} style={{ padding: '6px', background: '#1e1e1e', border: '1px solid #444', borderRadius: '6px', color: '#fff' }}>
                    <option value="face">Face Tracking</option>
                    <option value="torso">Torso Tracking</option>
                  </select>
                </label>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px', marginBottom: '12px' }}>
                <label style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                  <span style={{ fontSize: '0.85rem' }}>Text Color:</span>
                  <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                    <input type="color" value={textColor} onChange={e => setTextColor(e.target.value)} style={{ width: '32px', height: '32px', padding: 0, border: 'none', background: 'none', cursor: 'pointer' }} />
                    <span style={{ fontSize: '0.8rem', fontFamily: 'monospace' }}>{textColor}</span>
                  </div>
                </label>
                <label style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                  <span style={{ fontSize: '0.85rem' }}>Background Color:</span>
                  <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                    <input type="color" value={textBgColor} onChange={e => setTextBgColor(e.target.value)} style={{ width: '32px', height: '32px', padding: 0, border: 'none', background: 'none', cursor: 'pointer' }} />
                    <span style={{ fontSize: '0.8rem', fontFamily: 'monospace' }}>{textBgColor}</span>
                  </div>
                </label>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                <label style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                  <span style={{ fontSize: '0.85rem' }}>Position X (%):</span>
                  <input type="number" min="0" max="100" value={textPosX} onChange={e => setTextPosX(Number(e.target.value))} style={{ padding: '6px', background: '#1e1e1e', border: '1px solid #444', borderRadius: '6px', color: '#fff' }} />
                </label>
                <label style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                  <span style={{ fontSize: '0.85rem' }}>Position Y (%):</span>
                  <input type="number" min="0" max="100" value={textPosY} onChange={e => setTextPosY(Number(e.target.value))} style={{ padding: '6px', background: '#1e1e1e', border: '1px solid #444', borderRadius: '6px', color: '#fff' }} />
                </label>
              </div>
            </div>

            <label style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
              <span>Watermark Text:</span>
              <input type="text" value={watermarkText} onChange={e => setWatermarkText(e.target.value)} style={{ padding: '8px', background: '#252525', border: '1px solid #444', borderRadius: '6px', color: '#fff' }} />
            </label>

            <div style={{ display: 'flex', gap: '16px' }}>
              <label style={{ display: 'flex', flexDirection: 'column', gap: '8px', flex: 1 }}>
                <span>Watermark Size:</span>
                <input type="number" value={watermarkSize} onChange={e => setWatermarkSize(Number(e.target.value))} style={{ padding: '8px', background: '#252525', border: '1px solid #444', borderRadius: '6px', color: '#fff' }} />
              </label>
              <label style={{ display: 'flex', flexDirection: 'column', gap: '8px', flex: 1 }}>
                <span>Watermark Alpha (0-1):</span>
                <input type="number" step="0.1" max="1" min="0" value={watermarkAlpha} onChange={e => setWatermarkAlpha(Number(e.target.value))} style={{ padding: '8px', background: '#252525', border: '1px solid #444', borderRadius: '6px', color: '#fff' }} />
              </label>
            </div>

            <div style={{ display: 'flex', gap: '16px' }}>
              <label style={{ display: 'flex', flexDirection: 'column', gap: '8px', flex: 1 }}>
                <span>Watermark Top Margin:</span>
                <input type="number" value={watermarkTop} onChange={e => setWatermarkTop(Number(e.target.value))} style={{ padding: '8px', background: '#252525', border: '1px solid #444', borderRadius: '6px', color: '#fff' }} />
              </label>
              <label style={{ display: 'flex', flexDirection: 'column', gap: '8px', flex: 1 }}>
                <span>Watermark Right Margin:</span>
                <input type="number" value={watermarkRight} onChange={e => setWatermarkRight(Number(e.target.value))} style={{ padding: '8px', background: '#252525', border: '1px solid #444', borderRadius: '6px', color: '#fff' }} />
              </label>
            </div>

            <div style={{ display: 'flex', gap: '12px', marginTop: '16px' }}>
              <button onClick={() => { 
                setIsDialogOpen(false); 
                setWorkflowStatus('idle'); 
                setLogs([]); 
                mediaItems.forEach(item => { if (item.previewUrl) URL.revokeObjectURL(item.previewUrl) });
                setMediaItems([]); 
              }} style={{ flex: 1, padding: '12px', background: '#444', color: '#fff', border: 'none', borderRadius: '8px', cursor: 'pointer', fontWeight: 'bold' }}>Close</button>
              <button 
                onClick={handleRunWorkflow} 
                disabled={workflowStatus === 'running' || mediaItems.length === 0} 
                style={{ flex: 1, padding: '12px', background: workflowStatus === 'running' || mediaItems.length === 0 ? '#555' : '#3b82f6', color: '#fff', border: 'none', borderRadius: '8px', cursor: workflowStatus === 'running' || mediaItems.length === 0 ? 'not-allowed' : 'pointer', fontWeight: 'bold' }}
              >
                {workflowStatus === 'running' ? 'Running...' : 'Start Execution'}
              </button>
            </div>
            {workflowStatus === 'complete' && (
              <div style={{ background: 'rgba(34, 197, 94, 0.2)', color: '#4ade80', padding: '12px', borderRadius: '8px', textAlign: 'center', marginTop: '8px' }}>
                Workflow complete! The new clip is now in the Gallery.
              </div>
            )}
            {workflowStatus === 'error' && (
              <div style={{ background: 'rgba(239, 68, 68, 0.2)', color: '#ef4444', padding: '12px', borderRadius: '8px', textAlign: 'center', marginTop: '8px' }}>
                Workflow failed. Check logs for details.
              </div>
            )}
          </div>

          {/* Logs View */}
          <div className="logs-view" style={{ background: '#121212', borderRadius: '12px', padding: '24px', flexDirection: 'column', border: '1px solid #333' }}>
            <h3 style={{ margin: '0 0 16px 0', color: '#bbb' }}>Execution Logs</h3>
            <div style={{ flex: 1, overflowY: 'auto', background: '#000', borderRadius: '8px', padding: '16px', fontFamily: 'monospace', fontSize: '0.85rem', color: '#bbb', whiteSpace: 'pre-wrap', wordBreak: 'break-all' }}>
              {logs.length === 0 ? <span style={{ color: '#555' }}>Logs will appear here during execution...</span> : logs.join('\n')}
              <div ref={logsEndRef} />
            </div>
          </div>
        </div>
      )}

      {/* ── Workflow 2 Dialog ───────────────────────────────────────────────── */}
      {isDialog2Open && (
        <div className="responsive-dialog-overlay" style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, background: 'rgba(0,0,0,0.85)', display: 'flex', gap: '24px', zIndex: 1000 }}>
          {/* Settings panel */}
          <div className="responsive-dialog" style={{ background: '#1e1e1e', borderRadius: '12px', padding: '24px', display: 'flex', flexDirection: 'column', gap: '16px', overflowY: 'auto' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
              <h2 style={{ margin: 0, color: '#a78bfa' }}>Workflow 2</h2>
              <button
                onClick={() => refreshWf2Preview()}
                disabled={isWf2PreviewLoading}
                style={{ 
                  background: 'none', border: 'none', color: isWf2PreviewLoading ? '#555' : '#a78bfa', cursor: isWf2PreviewLoading ? 'not-allowed' : 'pointer',
                  display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.9rem'
                }}
              >
                <svg className={isWf2PreviewLoading ? 'animate-spin' : ''} width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M23 4v6h-6M1 20v-6h6M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15" />
                </svg>
                {isWf2PreviewLoading ? 'Refreshing...' : 'Refresh'}
              </button>
            </div>

            {/* Header image upload */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
              <span style={{ fontWeight: 600 }}>Header Image <span style={{ color: '#ef4444' }}>*</span></span>
              <label style={{ display: 'flex', alignItems: 'center', gap: '10px', padding: '10px 14px', background: '#252525', border: '1px dashed #555', borderRadius: '8px', cursor: 'pointer', color: '#aaa', fontSize: '0.9rem' }}>
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/></svg>
                {wf2HeaderImage ? wf2HeaderImage.name : 'Upload header / profile image…'}
                <input type="file" accept="image/*" style={{ display: 'none' }} onChange={e => {
                  const f = e.target.files?.[0];
                  if (f) {
                    setWf2HeaderImage(f);
                    setWf2HeaderPreview(URL.createObjectURL(f));
                  }
                }} />
              </label>
              {wf2HeaderPreview && <img src={wf2HeaderPreview} style={{ width: '100%', maxHeight: '120px', objectFit: 'contain', borderRadius: '6px', border: '1px solid #333' }} />}
            </div>

            {/* ── Layout ── */}
            <div style={{ background: '#252525', padding: '14px', borderRadius: '8px', border: '1px solid #333' }}>
              <h3 style={{ margin: '0 0 12px 0', fontSize: '0.9rem', color: '#ccc' }}>Layout</h3>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '10px', marginBottom: '10px' }}>
                <label style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                  <span style={{ fontSize: '0.75rem', color: '#888' }}>Top Margin (px)</span>
                  <input type="number" value={wf2TopMargin} onChange={e => setWf2TopMargin(Number(e.target.value))} style={{ padding: '6px', background: '#1e1e1e', border: '1px solid #444', borderRadius: '6px', color: '#fff' }} />
                </label>
                <label style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                  <span style={{ fontSize: '0.75rem', color: '#888' }}>Padding (px)</span>
                  <input type="number" value={wf2Padding} onChange={e => setWf2Padding(Number(e.target.value))} style={{ padding: '6px', background: '#1e1e1e', border: '1px solid #444', borderRadius: '6px', color: '#fff' }} />
                </label>
                <label style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                  <span style={{ fontSize: '0.75rem', color: '#888' }}>Header Height (px)</span>
                  <input type="number" value={wf2HeaderHeight} onChange={e => setWf2HeaderHeight(Number(e.target.value))} style={{ padding: '6px', background: '#1e1e1e', border: '1px solid #444', borderRadius: '6px', color: '#fff' }} />
                </label>
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
                <label style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                  <span style={{ fontSize: '0.75rem', color: '#888' }}>Font</span>
                  <select value={wf2FontName} onChange={e => setWf2FontName(e.target.value)} style={{ padding: '6px', background: '#1e1e1e', border: '1px solid #444', borderRadius: '6px', color: '#fff' }}>
                    <option value="Arial">Arial</option>
                    <option value="Helvetica">Helvetica</option>
                    <option value="Impact">Impact</option>
                    <option value="Times New Roman">Times New Roman</option>
                    <option value="Courier New">Courier New</option>
                  </select>
                </label>
                <label style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                  <span style={{ fontSize: '0.75rem', color: '#888' }}>Background Color</span>
                  <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                    <input type="color" value={wf2BgColor} onChange={e => setWf2BgColor(e.target.value)} style={{ width: '32px', height: '32px', padding: 0, border: 'none', background: 'none', cursor: 'pointer' }} />
                    <span style={{ fontSize: '0.75rem', fontFamily: 'monospace', color: '#ccc' }}>{wf2BgColor}</span>
                  </div>
                </label>
              </div>
            </div>

            {/* ── Story Text ── */}
            <div style={{ background: '#252525', padding: '14px', borderRadius: '8px', border: '1px solid #333', display: 'flex', flexDirection: 'column', gap: '10px' }}>
              <span style={{ fontWeight: 600 }}>Story Text <span style={{ color: '#ef4444' }}>*</span></span>
              <textarea value={wf2StoryText} onChange={e => setWf2StoryText(e.target.value)}
                style={{ padding: '8px', background: '#1e1e1e', border: '1px solid #444', borderRadius: '6px', color: '#fff', minHeight: '80px', fontFamily: 'inherit', resize: 'vertical' }}
                placeholder="Wrap [words] in brackets to highlight them…" />
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '10px' }}>
                <label style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                  <span style={{ fontSize: '0.75rem', color: '#888' }}>Size</span>
                  <input type="number" value={wf2StorySize} onChange={e => setWf2StorySize(Number(e.target.value))} style={{ padding: '6px', background: '#1e1e1e', border: '1px solid #444', borderRadius: '6px', color: '#fff' }} />
                </label>
                <label style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                  <span style={{ fontSize: '0.75rem', color: '#888' }}>Text Color</span>
                  <div style={{ display: 'flex', gap: '6px', alignItems: 'center' }}>
                    <input type="color" value={wf2StoryColor} onChange={e => setWf2StoryColor(e.target.value)} style={{ width: '32px', height: '32px', padding: 0, border: 'none', background: 'none', cursor: 'pointer' }} />
                    <span style={{ fontSize: '0.75rem', fontFamily: 'monospace', color: '#ccc' }}>{wf2StoryColor}</span>
                  </div>
                </label>
                <label style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                  <span style={{ fontSize: '0.75rem', color: '#22DD66' }}>[Highlight] Color</span>
                  <div style={{ display: 'flex', gap: '6px', alignItems: 'center' }}>
                    <input type="color" value={wf2HighlightColor} onChange={e => setWf2HighlightColor(e.target.value)} style={{ width: '32px', height: '32px', padding: 0, border: 'none', background: 'none', cursor: 'pointer' }} />
                    <span style={{ fontSize: '0.75rem', fontFamily: 'monospace', color: '#22DD66' }}>{wf2HighlightColor}</span>
                  </div>
                </label>
              </div>
            </div>

            {/* ── Suffix Text 1 ── */}
            <div style={{ background: '#252525', padding: '14px', borderRadius: '8px', border: '1px solid #333', display: 'flex', flexDirection: 'column', gap: '10px' }}>
              <span style={{ fontWeight: 600, color: '#aaa' }}>Suffix Text 1</span>
              <input type="text" value={wf2SuffixText1} onChange={e => setWf2SuffixText1(e.target.value)}
                style={{ padding: '8px', background: '#1e1e1e', border: '1px solid #444', borderRadius: '6px', color: '#aaa' }}
                placeholder="e.g. Sorry story too long…" />
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
                <label style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                  <span style={{ fontSize: '0.75rem', color: '#888' }}>Size</span>
                  <input type="number" value={wf2Suffix1Size} onChange={e => setWf2Suffix1Size(Number(e.target.value))} style={{ padding: '6px', background: '#1e1e1e', border: '1px solid #444', borderRadius: '6px', color: '#fff' }} />
                </label>
                <label style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                  <span style={{ fontSize: '0.75rem', color: '#888' }}>Color</span>
                  <div style={{ display: 'flex', gap: '6px', alignItems: 'center' }}>
                    <input type="color" value={wf2Suffix1Color} onChange={e => setWf2Suffix1Color(e.target.value)} style={{ width: '32px', height: '32px', padding: 0, border: 'none', background: 'none', cursor: 'pointer' }} />
                    <span style={{ fontSize: '0.75rem', fontFamily: 'monospace', color: '#ccc' }}>{wf2Suffix1Color}</span>
                  </div>
                </label>
              </div>
            </div>

            {/* ── Suffix Text 2 ── */}
            <div style={{ background: '#252525', padding: '14px', borderRadius: '8px', border: '1px solid #333', display: 'flex', flexDirection: 'column', gap: '10px' }}>
              <span style={{ fontWeight: 600, color: '#22DD66' }}>Suffix Text 2</span>
              <input type="text" value={wf2SuffixText2} onChange={e => setWf2SuffixText2(e.target.value)}
                style={{ padding: '8px', background: '#1e1e1e', border: '1px solid #444', borderRadius: '6px', color: '#22DD66' }}
                placeholder="e.g. Part 1" />
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
                <label style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                  <span style={{ fontSize: '0.75rem', color: '#888' }}>Size</span>
                  <input type="number" value={wf2Suffix2Size} onChange={e => setWf2Suffix2Size(Number(e.target.value))} style={{ padding: '6px', background: '#1e1e1e', border: '1px solid #444', borderRadius: '6px', color: '#fff' }} />
                </label>
                <label style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                  <span style={{ fontSize: '0.75rem', color: '#888' }}>Color</span>
                  <div style={{ display: 'flex', gap: '6px', alignItems: 'center' }}>
                    <input type="color" value={wf2Suffix2Color} onChange={e => setWf2Suffix2Color(e.target.value)} style={{ width: '32px', height: '32px', padding: 0, border: 'none', background: 'none', cursor: 'pointer' }} />
                    <span style={{ fontSize: '0.75rem', fontFamily: 'monospace', color: '#22DD66' }}>{wf2Suffix2Color}</span>
                  </div>
                </label>
              </div>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: '10px', background: '#252525', padding: '12px', borderRadius: '8px', border: '1px solid #333', marginBottom: '8px' }}>
              <input 
                type="checkbox" 
                id="wf2-auto-scale" 
                checked={wf2AutoScale} 
                onChange={e => setWf2AutoScale(e.target.checked)} 
                style={{ width: '18px', height: '18px', cursor: 'pointer' }}
              />
              <label htmlFor="wf2-auto-scale" style={{ fontSize: '0.9rem', cursor: 'pointer', color: '#ccc' }}>
                Auto-Scale to Fit (Ignore top margin to fit all)
              </label>
            </div>

            {/* Action buttons */}
            <div style={{ display: 'flex', gap: '12px', marginTop: '8px' }}>
              <button onClick={() => { setIsDialog2Open(false); setWf2Status('idle'); setWf2Logs([]); if (wf2HeaderPreview) { URL.revokeObjectURL(wf2HeaderPreview); setWf2HeaderPreview(null); } setWf2HeaderImage(null); }} style={{ flex: 1, padding: '12px', background: '#444', color: '#fff', border: 'none', borderRadius: '8px', cursor: 'pointer', fontWeight: 'bold' }}>Close</button>
              <button
                onClick={handleRunWorkflow2}
                disabled={wf2Status === 'running' || !wf2HeaderImage || !wf2StoryText.trim()}
                style={{ flex: 1, padding: '12px', background: wf2Status === 'running' || !wf2HeaderImage || !wf2StoryText.trim() ? '#555' : '#7c3aed', color: '#fff', border: 'none', borderRadius: '8px', cursor: wf2Status === 'running' ? 'not-allowed' : 'pointer', fontWeight: 'bold' }}
              >
                {wf2Status === 'running' ? 'Running…' : 'Start Workflow 2'}
              </button>
            </div>
            {wf2Status === 'complete' && <div style={{ background: 'rgba(34,197,94,0.2)', color: '#4ade80', padding: '12px', borderRadius: '8px', textAlign: 'center' }}>Workflow 2 complete! Check the Gallery.</div>}
            {wf2Status === 'error' && <div style={{ background: 'rgba(239,68,68,0.2)', color: '#ef4444', padding: '12px', borderRadius: '8px', textAlign: 'center' }}>Workflow 2 failed. Check logs.</div>}
          </div>

          {/* Preview / Logs panel */}
          <div className="logs-view" style={{ background: '#121212', borderRadius: '12px', padding: '0', display: 'flex', flexDirection: 'column', border: '1px solid #333', overflow: 'hidden' }}>
            <div style={{ display: 'flex', background: '#1a1a1a', borderBottom: '1px solid #333' }}>
              <button 
                onClick={() => setWf2Tab('preview')}
                style={{ 
                  flex: 1, padding: '12px', background: wf2Tab === 'preview' ? '#252525' : 'transparent',
                  color: wf2Tab === 'preview' ? '#a78bfa' : '#666', border: 'none', borderBottom: wf2Tab === 'preview' ? '2px solid #a78bfa' : 'none',
                  cursor: 'pointer', fontWeight: 600, fontSize: '0.9rem'
                }}
              >
                PREVIEW
              </button>
              <button 
                onClick={() => setWf2Tab('logs')}
                style={{ 
                  flex: 1, padding: '12px', background: wf2Tab === 'logs' ? '#252525' : 'transparent',
                  color: wf2Tab === 'logs' ? '#a78bfa' : '#666', border: 'none', borderBottom: wf2Tab === 'logs' ? '2px solid #a78bfa' : 'none',
                  cursor: 'pointer', fontWeight: 600, fontSize: '0.9rem'
                }}
              >
                LOGS
              </button>
            </div>

            <div style={{ flex: 1, position: 'relative', display: 'flex', flexDirection: 'column', height: '100%' }}>
              {wf2Tab === 'preview' ? (
                <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', background: '#252525', padding: '10px', overflow: 'auto' }}>
                  {wf2PreviewUrl ? (
                    <img 
                      src={wf2PreviewUrl} 
                      alt="Preview" 
                      style={{ maxWidth: '100%', maxHeight: '100%', objectFit: 'contain', borderRadius: '4px', boxShadow: '0 0 40px rgba(0,0,0,0.5)' }} 
                    />
                  ) : (
                    <div style={{ color: '#444', textAlign: 'center' }}>
                      <svg style={{ margin: '0 auto 12px', opacity: 0.2 }} width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1"><rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="8.5" cy="8.5" r="1.5"/><polyline points="21 15 16 10 5 21"/></svg>
                      <p>Enter story text to generate preview</p>
                    </div>
                  )}
                  
                  {isWf2PreviewLoading && (
                    <div style={{ position: 'absolute', inset: 0, background: 'rgba(0,0,0,0.4)', backdropFilter: 'blur(2px)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 10 }}>
                      <div className="animate-spin" style={{ width: '32px', height: '32px', border: '3px solid transparent', borderTopColor: '#a78bfa', borderRadius: '50%' }} />
                    </div>
                  )}
                </div>
              ) : (
                <div style={{ flex: 1, display: 'flex', flexDirection: 'column', padding: '24px' }}>
                  <div style={{ flex: 1, overflowY: 'auto', background: '#000', borderRadius: '8px', padding: '16px', fontFamily: 'monospace', fontSize: '0.85rem', color: '#bbb', whiteSpace: 'pre-wrap', wordBreak: 'break-all' }}>
                    {wf2Logs.length === 0 ? <span style={{ color: '#555' }}>Logs will appear here during execution…</span> : wf2Logs.join('\n')}
                    <div ref={wf2LogsEndRef} />
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* ── Workflow 3 Dialog (Silence Removal) ── */}
      {isDialog3Open && (
        <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.85)', backdropFilter: 'blur(8px)', zIndex: 1000, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '20px' }}>
          <div style={{ background: '#1e1e1e', width: '100%', maxWidth: '900px', height: '90vh', borderRadius: '16px', display: 'grid', gridTemplateColumns: 'minmax(350px, 1.2fr) 2fr', border: '1px solid #333', overflow: 'hidden', boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.5)' }}>
            <div style={{ padding: '24px', borderRight: '1px solid #333', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '20px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <h2 style={{ margin: 0, fontSize: '1.25rem', fontWeight: 700 }}>Remove Silences</h2>
                <button onClick={() => setIsDialog3Open(false)} style={{ background: 'none', border: 'none', color: '#666', cursor: 'pointer', padding: '4px' }}>
                  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
                </button>
              </div>

              <p style={{ color: '#aaa', fontSize: '0.9rem', margin: 0 }}>Detect and cut out silent pauses from your video to make it snappy and engaging.</p>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '16px', marginTop: '8px' }}>
                {/* Threshold */}
                <div style={{ background: '#252525', padding: '16px', borderRadius: '12px', border: '1px solid #333' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
                    <span style={{ fontWeight: 600, fontSize: '0.9rem' }}>Silence Threshold</span>
                    <span style={{ color: '#3b82f6', fontWeight: 'bold' }}>{minSilenceLen}ms</span>
                  </div>
                  <input
                    type="range" min="100" max="2000" step="50"
                    value={minSilenceLen}
                    onChange={e => setMinSilenceLen(Number(e.target.value))}
                    style={{ width: '100%', accentColor: '#3b82f6' }}
                  />
                  <p style={{ fontSize: '0.75rem', color: '#777', margin: '8px 0 0' }}>Pauses longer than this will be removed.</p>
                </div>

                {/* Keep */}
                <div style={{ background: '#252525', padding: '16px', borderRadius: '12px', border: '1px solid #333' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
                    <span style={{ fontWeight: 600, fontSize: '0.9rem' }}>Silence to Keep</span>
                    <span style={{ color: '#10b981', fontWeight: 'bold' }}>{keepSilenceLen}ms</span>
                  </div>
                  <input
                    type="range" min="0" max="500" step="10"
                    value={keepSilenceLen}
                    onChange={e => setKeepSilenceLen(Number(e.target.value))}
                    style={{ width: '100%', accentColor: '#10b981' }}
                  />
                  <p style={{ fontSize: '0.75rem', color: '#777', margin: '8px 0 0' }}>Padding left between cuts for natural breathing room.</p>
                </div>
              </div>

              {/* Action buttons */}
              <div style={{ display: 'flex', gap: '12px', marginTop: 'auto', paddingTop: '12px' }}>
                <button onClick={() => { setIsDialog3Open(false); setWf3Status('idle'); setWf3Logs([]); }} style={{ flex: 1, padding: '14px', background: '#333', color: '#fff', border: 'none', borderRadius: '10px', cursor: 'pointer', fontWeight: 'bold' }}>Cancel</button>
                <button
                  onClick={handleRunWorkflow3}
                  disabled={wf3Status === 'running'}
                  style={{ flex: 2, padding: '14px', background: wf3Status === 'running' ? '#444' : '#3b82f6', color: '#fff', border: 'none', borderRadius: '10px', cursor: wf3Status === 'running' ? 'not-allowed' : 'pointer', fontWeight: 'bold', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px' }}
                >
                  {wf3Status === 'running' ? (
                    <>
                      <div style={{ width: '16px', height: '16px', border: '2px solid rgba(255,255,255,0.3)', borderTopColor: '#fff', borderRadius: '50%', animation: 'spin 0.8s linear infinite' }} />
                      Processing...
                    </>
                  ) : 'Start Removal'}
                </button>
              </div>

              {wf3Status === 'complete' && <div style={{ background: 'rgba(16,185,129,0.15)', color: '#10b981', padding: '12px', borderRadius: '10px', textAlign: 'center', border: '1px solid rgba(16,185,129,0.3)', fontSize: '0.9rem' }}>✅ Success! Check the gallery.</div>}
              {wf3Status === 'error' && <div style={{ background: 'rgba(239,68,68,0.15)', color: '#ef4444', padding: '12px', borderRadius: '10px', textAlign: 'center', border: '1px solid rgba(239,68,68,0.3)', fontSize: '0.9rem' }}>❌ Error. Check logs.</div>}
            </div>

            {/* Logs panel */}
            <div style={{ background: '#0e0e0e', display: 'flex', flexDirection: 'column', height: '100%' }}>
              <div style={{ padding: '16px 24px', borderBottom: '1px solid #222', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ fontSize: '0.85rem', fontWeight: 600, color: '#666', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Execution Logs</span>
                {wf3Status === 'running' && <span style={{ fontSize: '0.75rem', color: '#3b82f6', animation: 'pulse 1.5s infinite' }}>● Running</span>}
              </div>
              <div style={{ flex: 1, overflowY: 'auto', padding: '20px', fontFamily: '"Fira Code", "JetBrains Mono", monospace', fontSize: '13px', color: '#888', lineHeight: 1.6 }}>
                {wf3Logs.length === 0 ? (
                  <div style={{ height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#333' }}>Waiting to start...</div>
                ) : (
                  wf3Logs.map((log, i) => (
                    <div key={i} style={{ borderBottom: '1px solid #1a1a1a', paddingBottom: '4px', marginBottom: '4px', color: log.includes('[ERROR]') ? '#ef4444' : log.includes('[SUCCESS]') ? '#10b981' : log.startsWith('>') ? '#3b82f6' : '#888' }}>
                      {log}
                    </div>
                  ))
                )}
                <div ref={wf3LogsEndRef} />
              </div>
            </div>
          </div>
        </div>
      )}
      {/* Refine Editor Overlay */}
      {isRefineEditorOpen && reconstructedClip && (
        <div style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, background: '#121212', zIndex: 1100, overflow: 'auto' }}>
          <ClipScriptEditorPage
            clip={reconstructedClip}
            fullTranscript={refineFullTranscript}
            videoId={refineVideoId}
            project={refineProject}
            onClose={() => setIsRefineEditorOpen(false)}
            onSave={async (updatedClip: Clip) => {
              try {
                setIsRefineEditorOpen(false);
                setRefineProcessStatus('running');
                setRefineLogs([]);
                setRefineProgress(null);
                setWorkflowStatus('running');
                setLogs([]);
                
                const url = clip.info_data.video.url;
                const format = clip.info_data.clip.format || 'original';
                const burnCaptions = clip.info_data.clip.burn_captions !== undefined ? clip.info_data.clip.burn_captions : true;
                
                updatedClip.id = 'refine-target';
                
                await VideoRepository.processVideo(
                  url,
                  format,
                  burnCaptions, // burnCaptions
                  'viral-moments', // strategy
                  null, // extraContext
                  clientId,
                  ['refine-target'], // selectedClips
                  [updatedClip], // preanalyzedClips
                  refineFullTranscript, // fullTranscriptWords
                  'openai', // aiProvider
                  'bottom' // aiContentPosition
                );
              } catch (e: any) {
                setRefineProcessStatus('error');
                setRefineLogs(prev => [...prev, `[ERROR] Refine failed: ${e.message}`]);
                setWorkflowStatus('error');
                setLogs(prev => [...prev, `[ERROR] Refine failed: ${e.message}`]);
              }
            }}
          />
        </div>
      )}

      {/* Refine Progress Overlay */}
      {refineProcessStatus !== 'idle' && !isRefineEditorOpen && (() => {
        const STAGES = [
          { id: 'downloading', icon: '📥', label: 'Downloading' },
          { id: 'transcribing', icon: '🎤', label: 'Transcribing' },
          { id: 'analyzing', icon: '🤖', label: 'AI Analysis' },
          { id: 'clipping', icon: '✂️', label: 'Clipping' },
          { id: 'organizing', icon: '📁', label: 'Organizing' },
        ];
        const currentStage = refineProgress?.stage || (refineProcessStatus === 'complete' ? 'done' : '');
        const activeIdx = currentStage === 'done' ? STAGES.length : STAGES.findIndex(s => s.id === currentStage);
        const pct  = refineProgress?.percent ?? (refineProcessStatus === 'complete' ? 100 : 0);
        return (
          <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.92)', zIndex: 1200, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: '24px', gap: '24px' }}>
            {/* Title */}
            <h2 style={{ margin: 0, fontSize: '1.5rem', color: refineProcessStatus === 'error' ? '#ef4444' : refineProcessStatus === 'complete' ? '#4ade80' : '#fbbf24' }}>
              {refineProcessStatus === 'complete' ? '✅ Refinement Complete!' : refineProcessStatus === 'error' ? '❌ Refinement Failed' : '✍️ Refining Clip…'}
            </h2>

            {/* Progress Bar */}
            {refineProcessStatus === 'running' && (
              <div style={{ width: '100%', maxWidth: '560px' }}>
                <div style={{ background: '#333', borderRadius: '99px', height: '10px', overflow: 'hidden' }}>
                  <div style={{ height: '100%', width: `${pct}%`, background: 'linear-gradient(90deg, #fbbf24, #f59e0b)', borderRadius: '99px', transition: 'width 0.4s ease' }} />
                </div>
                <p style={{ margin: '8px 0 0', color: '#aaa', fontSize: '0.85rem', textAlign: 'center' }}>{refineProgress?.message || 'Initialising…'} ({Math.round(pct)}%)</p>
              </div>
            )}

            {/* Stage pills */}
            <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap', justifyContent: 'center' }}>
              {STAGES.map((s, i) => {
                const done = activeIdx > i || refineProcessStatus === 'complete';
                const active = !done && currentStage === s.id;
                return (
                  <div key={s.id} style={{ display: 'flex', alignItems: 'center', gap: '6px', padding: '6px 14px', borderRadius: '99px', background: done ? 'rgba(74,222,128,0.15)' : active ? 'rgba(251,191,36,0.15)' : '#1e1e1e', border: `1px solid ${done ? '#4ade80' : active ? '#fbbf24' : '#333'}`, color: done ? '#4ade80' : active ? '#fbbf24' : '#666', fontSize: '0.82rem', transition: 'all 0.3s' }}>
                    <span>{done ? '✓' : s.icon}</span>
                    <span>{s.label}</span>
                  </div>
                );
              })}
            </div>

            {/* Logs */}
            <div style={{ width: '100%', maxWidth: '720px', background: '#0a0a0a', borderRadius: '10px', border: '1px solid #222', padding: '12px 16px', maxHeight: '200px', overflowY: 'auto', fontFamily: 'monospace', fontSize: '0.78rem', color: '#888', whiteSpace: 'pre-wrap', wordBreak: 'break-all' }}>
              {refineLogs.length === 0 ? <span style={{ color: '#444' }}>Waiting for logs…</span> : refineLogs.join('\n')}
            </div>

            {/* Actions */}
            <div style={{ display: 'flex', gap: '12px' }}>
              {refineProcessStatus === 'complete' && (
                <button
                  onClick={() => navigate('/gallery')}
                  style={{ padding: '12px 28px', background: '#4ade80', color: '#000', border: 'none', borderRadius: '8px', cursor: 'pointer', fontWeight: 'bold', fontSize: '1rem' }}
                >
                  Go to Gallery →
                </button>
              )}
              {(refineProcessStatus === 'complete' || refineProcessStatus === 'error') && (
                <button
                  onClick={() => { setRefineProcessStatus('idle'); setRefineLogs([]); setRefineProgress(null); }}
                  style={{ padding: '12px 28px', background: '#333', color: '#fff', border: 'none', borderRadius: '8px', cursor: 'pointer', fontWeight: 'bold', fontSize: '1rem' }}
                >
                  Dismiss
                </button>
              )}
              {refineProcessStatus === 'running' && (
                <button
                  onClick={() => { setRefineProcessStatus('idle'); setRefineLogs([]); }}
                  style={{ padding: '12px 24px', background: 'transparent', color: '#888', border: '1px solid #444', borderRadius: '8px', cursor: 'pointer' }}
                >
                  Cancel
                </button>
              )}
            </div>
          </div>
        );
      })()}
    </div>
  );
}
