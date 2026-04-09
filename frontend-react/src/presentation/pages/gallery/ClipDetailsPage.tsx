import React, { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { VideoRepository } from '../../../data/VideoRepository';

export const ClipDetailsPage: React.FC = () => {
  const { project, format, filename } = useParams();
  const navigate = useNavigate();
  const [clip, setClip] = useState<any>(null);
  const [isLoading, setIsLoading] = useState(true);

  const [clientId, setClientId] = useState('');
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [secondMedia, setSecondMedia] = useState<File | null>(null);
  const [mainPosition, setMainPosition] = useState('top');
  const [text, setText] = useState('');
  const [watermarkText, setWatermarkText] = useState('@MrSinghExperience');
  const [watermarkSize, setWatermarkSize] = useState(45);
  const [watermarkAlpha, setWatermarkAlpha] = useState(0.6);
  const [watermarkTop, setWatermarkTop] = useState(100);
  const [watermarkRight, setWatermarkRight] = useState(40);
  
  const [workflowStatus, setWorkflowStatus] = useState<'idle' | 'running' | 'complete' | 'error'>('idle');
  const [logs, setLogs] = useState<string[]>([]);
  const wsRef = useRef<WebSocket | null>(null);
  const logsEndRef = useRef<HTMLDivElement>(null);
  const [metaGenStatus, setMetaGenStatus] = useState<'idle' | 'loading' | 'done' | 'error'>('idle');

  useEffect(() => {
    if (logsEndRef.current) {
      logsEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [logs]);

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
        } else if (data.type === 'progress') {
          if (data.stage === 'complete') {
            setWorkflowStatus('complete');
          } else if (data.stage === 'error') {
            setWorkflowStatus('error');
            setLogs(prev => [...prev, data.message]);
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
    if (!secondMedia) {
      alert("Please upload a secondary media file.");
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
        secondMedia, mainPosition, text, watermarkText,
        watermarkSize, watermarkAlpha, watermarkTop, watermarkRight
      );
    } catch (e: any) {
      setWorkflowStatus('error');
      setLogs(prev => [...prev, `[ERROR] ${e.message}`]);
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
    <div style={{ minHeight: '100vh', background: '#121212', color: '#fff', padding: '24px 48px', fontFamily: '"Inter", sans-serif' }}>
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
            <video 
              src={`/clips/${encodeURIComponent(project || '')}/${encodeURIComponent(format || '')}/${encodeURIComponent(filename || '')}`} 
              controls
              style={{ width: '100%', borderRadius: '8px', background: '#000', aspectRatio: format === 'reels' ? '9/16' : '16/9' }}
            />
            <button onClick={handleDownload} style={{ width: '100%', padding: '12px', background: '#252525', color: '#fff', border: 'none', borderRadius: '8px', cursor: 'pointer', display: 'flex', justifyContent: 'center', alignItems: 'center', gap: '8px', fontWeight: 'bold' }}>
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
              Download Clip
            </button>
            <button onClick={() => setIsDialogOpen(true)} style={{ width: '100%', padding: '12px', background: '#3b82f6', color: '#fff', border: 'none', borderRadius: '8px', cursor: 'pointer', display: 'flex', justifyContent: 'center', alignItems: 'center', gap: '8px', fontWeight: 'bold' }}>
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polygon points="5 3 19 12 5 21 5 3"></polygon></svg>
              Run Workflow
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
        <div style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, background: 'rgba(0,0,0,0.8)', padding: '48px', display: 'flex', gap: '24px', zIndex: 1000 }}>
          {/* Dialog Form */}
          <div style={{ background: '#1e1e1e', borderRadius: '12px', padding: '24px', flex: '0 0 500px', display: 'flex', flexDirection: 'column', gap: '16px', overflowY: 'auto' }}>
            <h2 style={{ margin: 0 }}>Workflow Settings</h2>
            
            <label style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
              <span>Secondary Media (Video/Photo):</span>
              <input type="file" onChange={e => setSecondMedia(e.target.files?.[0] || null)} style={{ padding: '8px', background: '#252525', border: '1px solid #444', borderRadius: '6px', color: '#fff' }} />
            </label>

            <label style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
              <span>Main Video Position:</span>
              <select value={mainPosition} onChange={e => setMainPosition(e.target.value)} style={{ padding: '8px', background: '#252525', border: '1px solid #444', borderRadius: '6px', color: '#fff' }}>
                <option value="top">Top</option>
                <option value="bottom">Bottom</option>
              </select>
            </label>

            <label style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
              <span>Seam Text:</span>
              <textarea value={text} onChange={e => setText(e.target.value)} style={{ padding: '8px', background: '#252525', border: '1px solid #444', borderRadius: '6px', color: '#fff', minHeight: '60px', fontFamily: 'inherit', resize: 'vertical' }} placeholder="Enter text (multiple lines allowed)" />
            </label>

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
              <button onClick={() => { setIsDialogOpen(false); setWorkflowStatus('idle'); setLogs([]); }} style={{ flex: 1, padding: '12px', background: '#444', color: '#fff', border: 'none', borderRadius: '8px', cursor: 'pointer', fontWeight: 'bold' }}>Close</button>
              <button 
                onClick={handleRunWorkflow} 
                disabled={workflowStatus === 'running' || !secondMedia} 
                style={{ flex: 1, padding: '12px', background: workflowStatus === 'running' || !secondMedia ? '#555' : '#3b82f6', color: '#fff', border: 'none', borderRadius: '8px', cursor: workflowStatus === 'running' || !secondMedia ? 'not-allowed' : 'pointer', fontWeight: 'bold' }}
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
          <div style={{ flex: 1, background: '#121212', borderRadius: '12px', padding: '24px', display: 'flex', flexDirection: 'column', border: '1px solid #333' }}>
            <h3 style={{ margin: '0 0 16px 0', color: '#bbb' }}>Execution Logs</h3>
            <div style={{ flex: 1, overflowY: 'auto', background: '#000', borderRadius: '8px', padding: '16px', fontFamily: 'monospace', fontSize: '0.85rem', color: '#bbb', whiteSpace: 'pre-wrap', wordBreak: 'break-all' }}>
              {logs.length === 0 ? <span style={{ color: '#555' }}>Logs will appear here during execution...</span> : logs.join('\n')}
              <div ref={logsEndRef} />
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
