import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { VideoRepository } from '../../../data/VideoRepository';

export const GalleryPage: React.FC = () => {
  const navigate = useNavigate();
  const [clips, setClips] = useState<any[]>([]);
  const [filter, setFilter] = useState<'All' | 'Original' | 'Reels'>('All');
  const [isLoading, setIsLoading] = useState(true);

  const fetchClips = async () => {
    setIsLoading(true);
    try {
      const data = await VideoRepository.getGeneratedClips();
      setClips(data);
    } catch (e) {
      console.error(e);
      alert('Failed to fetch clips');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchClips();
  }, []);

  const formatSize = (bytes: number) => {
    return (bytes / (1024 * 1024)).toFixed(2) + ' MB';
  };

  const filteredClips = clips.filter(c => {
    if (filter === 'All') return true;
    return c.format.toLowerCase() === filter.toLowerCase();
  });

  const totalSize = filteredClips.reduce((acc, c) => acc + c.size, 0);

  return (
    <div style={{ minHeight: '100vh', background: '#121212', color: '#fff', padding: '24px 48px', fontFamily: '"Inter", sans-serif' }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '32px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
          <button onClick={() => navigate('/')} style={{ background: '#252525', border: 'none', borderRadius: '50%', width: '40px', height: '40px', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#fff', cursor: 'pointer' }}>
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M19 12H5M12 19l-7-7 7-7"/></svg>
          </button>
          <button onClick={() => navigate('/')} style={{ background: '#252525', border: 'none', borderRadius: '50%', width: '40px', height: '40px', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#fff', cursor: 'pointer' }}>
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/></svg>
          </button>
          <h1 style={{ margin: 0, fontSize: '1.5rem', color: '#ff0000', fontWeight: 'bold' }}>Gallery</h1>
        </div>
        <button onClick={fetchClips} style={{ background: '#252525', border: 'none', borderRadius: '50%', width: '40px', height: '40px', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#fff', cursor: 'pointer' }}>
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/><path d="M3 3v5h5"/></svg>
        </button>
      </div>

      {/* Stats Cards */}
      <div style={{ display: 'flex', gap: '24px', marginBottom: '32px' }}>
        <div style={{ flex: 1, background: '#1e1e1e', borderRadius: '12px', padding: '24px', textAlign: 'center' }}>
          <div style={{ fontSize: '2rem', fontWeight: 'bold', color: '#ff0000', marginBottom: '8px' }}>{filteredClips.length}</div>
          <div style={{ fontSize: '0.85rem', color: '#888', textTransform: 'uppercase', letterSpacing: '1px' }}>TOTAL CLIPS</div>
        </div>
        <div style={{ flex: 1, background: '#1e1e1e', borderRadius: '12px', padding: '24px', textAlign: 'center' }}>
          <div style={{ fontSize: '2rem', fontWeight: 'bold', color: '#ff0000', marginBottom: '8px' }}>{formatSize(totalSize)}</div>
          <div style={{ fontSize: '0.85rem', color: '#888', textTransform: 'uppercase', letterSpacing: '1px' }}>TOTAL SIZE</div>
        </div>
      </div>

      {/* Filter Pills */}
      <div style={{ display: 'flex', gap: '12px', marginBottom: '32px' }}>
        {['All', 'Original', 'Reels'].map(f => (
          <button 
            key={f}
            onClick={() => setFilter(f as any)}
            style={{
              background: filter === f ? '#ff0000' : '#252525',
              color: '#fff',
              border: 'none',
              borderRadius: '20px',
              padding: '8px 24px',
              fontSize: '0.9rem',
              fontWeight: filter === f ? 'bold' : 'normal',
              cursor: 'pointer',
              transition: 'background 0.2s'
            }}
          >
            {f}
          </button>
        ))}
      </div>

      {/* Grid */}
      {isLoading ? (
        <div style={{ textAlign: 'center', padding: '40px', color: '#888' }}>Loading clips...</div>
      ) : filteredClips.length === 0 ? (
        <div style={{ textAlign: 'center', padding: '40px', color: '#888' }}>No clips found.</div>
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: '24px' }}>
          {filteredClips.map((clip, i) => (
            <div 
              key={i}
              onClick={() => navigate(`/gallery/${clip.project}/${clip.format}/${clip.filename}`)}
              style={{
                background: '#1e1e1e',
                borderRadius: '12px',
                overflow: 'hidden',
                cursor: 'pointer',
                position: 'relative',
                aspectRatio: clip.format === 'reels' ? '9/16' : '16/9',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center'
              }}
            >
              {/* Fallback layout if no thumbnail: we just render the video element without controls to act as thumbnail */}
              <video 
                src={`/clips/${clip.project}/${clip.format}/${clip.filename}`} 
                style={{ width: '100%', height: '100%', objectFit: 'cover' }}
                preload="metadata"
                muted
                onMouseOver={e => (e.target as HTMLVideoElement).play().catch(() => {})}
                onMouseOut={e => {
                  const v = e.target as HTMLVideoElement;
                  v.pause();
                  v.currentTime = 0;
                }}
              />
              <div style={{ position: 'absolute', inset: 0, background: 'linear-gradient(to top, rgba(0,0,0,0.8), transparent 50%)' }} />
              
              {/* Play Button Overlay */}
              <div style={{ position: 'absolute', top: '50%', left: '50%', transform: 'translate(-50%, -50%)', background: 'rgba(0,0,0,0.6)', borderRadius: '50%', width: '48px', height: '48px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                <svg width="24" height="24" viewBox="0 0 24 24" fill="#fff" stroke="none"><polygon points="5 3 19 12 5 21 5 3"/></svg>
              </div>

              {/* Title overlay */}
              <div style={{ position: 'absolute', bottom: 0, left: 0, right: 0, padding: '16px' }}>
                <div style={{ fontSize: '1rem', fontWeight: 'bold', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', textShadow: '0 2px 4px rgba(0,0,0,0.8)' }}>
                  {clip.title || clip.filename}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
