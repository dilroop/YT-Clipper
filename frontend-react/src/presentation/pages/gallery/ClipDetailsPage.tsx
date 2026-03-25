import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { VideoRepository } from '../../../data/VideoRepository';

export const ClipDetailsPage: React.FC = () => {
  const { project, format, filename } = useParams();
  const navigate = useNavigate();
  const [clip, setClip] = useState<any>(null);
  const [isLoading, setIsLoading] = useState(true);

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
    a.href = `/clips/${project}/${format}/${filename}`;
    a.download = filename || 'clip.mp4';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
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
              src={`/clips/${project}/${format}/${filename}`} 
              controls
              style={{ width: '100%', borderRadius: '8px', background: '#000', aspectRatio: format === 'reels' ? '9/16' : '16/9' }}
            />
            <button onClick={handleDownload} style={{ width: '100%', padding: '12px', background: '#252525', color: '#fff', border: 'none', borderRadius: '8px', cursor: 'pointer', display: 'flex', justifyContent: 'center', alignItems: 'center', gap: '8px', fontWeight: 'bold' }}>
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
              Download Clip
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
            <h3 style={{ margin: '0 0 16px 0', fontSize: '1rem', fontWeight: 'bold' }}>Metadata</h3>
            <div style={{ background: '#121212', borderRadius: '8px', padding: '16px', overflow: 'auto', flex: 1, maxHeight: '600px', fontSize: '0.85rem', color: '#bbb', fontFamily: 'monospace', whiteSpace: 'pre-wrap' }}>
              {clip.info_data ? JSON.stringify(clip.info_data, null, 2) : clip.info_text || "No metadata found."}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
