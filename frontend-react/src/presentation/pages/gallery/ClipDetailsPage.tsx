import React, { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { VideoRepository } from '../../../data/VideoRepository';

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
  const [logs, setLogs] = useState<string[]>([]);
  const wsRef = useRef<WebSocket | null>(null);
  const logsEndRef = useRef<HTMLDivElement>(null);
  const [metaGenStatus, setMetaGenStatus] = useState<'idle' | 'loading' | 'done' | 'error'>('idle');

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

  useEffect(() => {
    if (logsEndRef.current) logsEndRef.current.scrollIntoView({ behavior: 'smooth' });
  }, [logs]);

  useEffect(() => {
    if (wf2LogsEndRef.current) wf2LogsEndRef.current.scrollIntoView({ behavior: 'smooth' });
  }, [wf2Logs]);

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
  }, [wf2StoryText, wf2SuffixText1, wf2SuffixText2, wf2TopMargin, wf2Padding, wf2HeaderHeight, wf2BgColor, wf2FontName, wf2StorySize, wf2StoryColor, wf2HighlightColor, wf2Suffix1Size, wf2Suffix1Color, wf2Suffix2Size, wf2Suffix2Color]);

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
        } else if (data.type === 'progress') {
          if (data.stage === 'complete') {
            setWorkflowStatus('complete');
            setWf2Status('complete');
          } else if (data.stage === 'error') {
            setWorkflowStatus('error');
            setWf2Status('error');
            setLogs(prev => [...prev, data.message]);
            setWf2Logs(prev => [...prev, data.message]);
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
        fontFamily, textColor, textBgColor, textSize, textPosX, textPosY
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
      );
    } catch (e: any) {
      setWf2Status('error');
      setWf2Logs(prev => [...prev, `[ERROR] ${e.message}`]);
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

  const title = clip.info_data?.clip?.title || clip.title || 'Untitled Clip';
  const description = clip.info_data?.clip?.description || clip.info_text || 'No description available.';
  const keywords = clip.info_data?.clip?.keywords?.join(', ') || 'None';

  return (
    <div className="page-container" style={{ minHeight: '100vh', background: '#121212', color: '#fff', fontFamily: '"Inter", sans-serif' }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '16px', marginBottom: '32px' }}>
        <button onClick={() => navigate(-1)} style={{ background: '#252525', border: 'none', borderRadius: '50%', width: '40px', height: '40px', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#fff', cursor: 'pointer' }}>
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M19 12H5M12 19l-7-7 7-7"/></svg>
        </button>
        <button onClick={() => navigate('/')} style={{ background: '#252525', border: 'none', borderRadius: '50%', width: '40px', height: '40px', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#fff', cursor: 'pointer' }}>
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/></svg>
        </button>
        <h1 style={{ margin: 0, fontSize: '1.5rem', color: '#ff0000', fontWeight: 'bold' }}>Details</h1>
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
            <button onClick={() => setIsDialogOpen(true)} style={{ width: '100%', padding: '12px', background: '#3b82f6', color: '#fff', border: 'none', borderRadius: '8px', cursor: 'pointer', display: 'flex', justifyContent: 'center', alignItems: 'center', gap: '8px', fontWeight: 'bold' }}>
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polygon points="5 3 19 12 5 21 5 3"></polygon></svg>
              Run Workflow
            </button>
            <button onClick={() => setIsDialog2Open(true)} style={{ width: '100%', padding: '12px', background: '#7c3aed', color: '#fff', border: 'none', borderRadius: '8px', cursor: 'pointer', display: 'flex', justifyContent: 'center', alignItems: 'center', gap: '8px', fontWeight: 'bold' }}>
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><rect x="3" y="3" width="18" height="18" rx="2"/><path d="M3 9h18M9 21V9"/></svg>
              Run Workflow 2
            </button>
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
            <div style={{ background: '#1e1e1e', borderRadius: '12px', padding: '24px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '16px' }}>
                <h3 style={{ margin: 0, fontSize: '0.85rem', color: '#888', textTransform: 'uppercase', letterSpacing: '1px' }}>TITLE</h3>
                <button style={{ background: 'none', border: 'none', color: '#888', cursor: 'pointer' }} onClick={() => navigator.clipboard.writeText(title)}><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg></button>
              </div>
              <p style={{ margin: 0, lineHeight: 1.5 }}>{title}</p>
            </div>

            <div style={{ background: '#1e1e1e', borderRadius: '12px', padding: '24px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '16px' }}>
                <h3 style={{ margin: 0, fontSize: '0.85rem', color: '#888', textTransform: 'uppercase', letterSpacing: '1px' }}>DESCRIPTION</h3>
                <button style={{ background: 'none', border: 'none', color: '#888', cursor: 'pointer' }} onClick={() => navigator.clipboard.writeText(description)}><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg></button>
              </div>
              <p style={{ margin: 0, lineHeight: 1.5, color: '#ccc' }}>{description}</p>
            </div>

            <div style={{ background: '#1e1e1e', borderRadius: '12px', padding: '24px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '16px' }}>
                <h3 style={{ margin: 0, fontSize: '0.85rem', color: '#888', textTransform: 'uppercase', letterSpacing: '1px' }}>TAGS</h3>
                <button style={{ background: 'none', border: 'none', color: '#888', cursor: 'pointer' }} onClick={() => navigator.clipboard.writeText(keywords)}><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg></button>
              </div>
              <p style={{ margin: 0, lineHeight: 1.5 }}>{keywords}</p>
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
          <div style={{ background: '#1e1e1e', borderRadius: '12px', padding: '24px', display: 'flex', flexDirection: 'column' }}>
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
                  {mediaItems.map((item, i) => (
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
            <h2 style={{ margin: 0, color: '#a78bfa' }}>Workflow 2 — Story Card</h2>

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

          {/* Logs panel */}
          <div className="logs-view" style={{ background: '#121212', borderRadius: '12px', padding: '24px', flexDirection: 'column', border: '1px solid #333' }}>
            <h3 style={{ margin: '0 0 16px 0', color: '#bbb' }}>Execution Logs</h3>
            <div style={{ flex: 1, overflowY: 'auto', background: '#000', borderRadius: '8px', padding: '16px', fontFamily: 'monospace', fontSize: '0.85rem', color: '#bbb', whiteSpace: 'pre-wrap', wordBreak: 'break-all' }}>
              {wf2Logs.length === 0 ? <span style={{ color: '#555' }}>Logs will appear here during execution…</span> : wf2Logs.join('\n')}
              <div ref={wf2LogsEndRef} />
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
