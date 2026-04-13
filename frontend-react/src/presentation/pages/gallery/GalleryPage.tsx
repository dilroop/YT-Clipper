import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { VideoRepository } from '../../../data/VideoRepository';

export const GalleryPage: React.FC = () => {
  const navigate = useNavigate();
  const [clips, setClips] = useState<any[]>([]);
  const [filter, setFilter] = useState<'All' | 'Original' | 'Reels'>('All');
  const [isLoading, setIsLoading] = useState(true);
  const [activePlayIndex, setActivePlayIndex] = useState<number | null>(null);

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
    <div className="page-container" style={{ minHeight: '100vh', background: '#121212', color: '#fff', fontFamily: '"Inter", sans-serif' }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '32px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
          <button onClick={() => navigate('/')} style={{ background: '#252525', border: 'none', borderRadius: '8px', width: '40px', height: '40px', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#fff', cursor: 'pointer' }}>
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M19 12H5M12 19l-7-7 7-7"/></svg>
          </button>
          <button onClick={() => navigate('/')} style={{ background: '#252525', border: 'none', borderRadius: '8px', width: '40px', height: '40px', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#fff', cursor: 'pointer' }}>
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/></svg>
          </button>
          <h1 style={{ margin: 0, fontSize: '1.5rem', color: '#ff0000', fontWeight: 'bold' }}>Gallery</h1>
        </div>
        <button onClick={fetchClips} style={{ background: '#252525', border: 'none', borderRadius: '8px', width: '40px', height: '40px', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#fff', cursor: 'pointer' }}>
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
              borderRadius: '10px',
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
              onClick={() => navigate(`/gallery/${encodeURIComponent(clip.project)}/${encodeURIComponent(clip.format)}/${encodeURIComponent(clip.filename)}`)}
              style={{
                background: '#1e1e1e',
                borderRadius: '12px',
                overflow: 'hidden',
                cursor: 'pointer',
                position: 'relative',
                aspectRatio: (clip.format === 'reels' || clip.filename.includes('_workflow') || clip.filename.includes('_story_')) ? '9/16' : '16/9',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center'
              }}
            >
              {/* Fallback layout if no thumbnail: we just render the video element without controls to act as thumbnail */}
              <video 
                src={`/clips/${encodeURIComponent(clip.project)}/${encodeURIComponent(clip.format)}/${encodeURIComponent(clip.filename)}`} 
                style={{ width: '100%', height: '100%', objectFit: 'cover' }}
                preload="metadata"
                controls={activePlayIndex === i}
                muted={activePlayIndex !== i}
                onClick={e => {
                  if (activePlayIndex === i) {
                    e.stopPropagation();
                  }
                }}
                onMouseOver={e => {
                  if (activePlayIndex !== i) {
                    (e.target as HTMLVideoElement).play().catch(() => {});
                  }
                }}
                onMouseOut={e => {
                  if (activePlayIndex !== i) {
                    const v = e.target as HTMLVideoElement;
                    v.pause();
                    v.currentTime = 0;
                  }
                }}
              />
              <div style={{ position: 'absolute', inset: 0, background: activePlayIndex === i ? 'transparent' : 'linear-gradient(to top, rgba(0,0,0,0.8), transparent 50%)', pointerEvents: 'none', transition: 'background 0.3s' }} />

              {/* Marker Color Dot / Pill */}
              <div 
                className="clip-marker-container"
                style={{
                  position: 'absolute',
                  top: '16px',
                  left: '16px',
                  zIndex: 4,
                  display: 'flex',
                  alignItems: 'center',
                  background: 'rgba(30, 30, 30, 0)',
                  borderRadius: '24px',
                  transition: 'background 0.2s',
                  padding: '2px', // space for expansion
                }}
                onMouseEnter={e => {
                  e.currentTarget.style.background = 'rgba(30, 30, 30, 0.9)';
                  const dots = e.currentTarget.querySelectorAll('.marker-option');
                  dots.forEach((dot: any) => dot.style.display = 'block');
                }}
                onMouseLeave={e => {
                  e.currentTarget.style.background = 'rgba(30, 30, 30, 0)';
                  const dots = e.currentTarget.querySelectorAll('.marker-option:not(.marker-active)');
                  dots.forEach((dot: any) => dot.style.display = 'none');
                }}
              >
                {/* 
                  Colors: red, yellow, green, blue, purple, none (white/transparent)
                  Default active is yellow if null
                */}
                {[
                  { id: '#ef4444', label: 'Red' },
                  { id: '#eab308', label: 'Yellow' },
                  { id: '#22c55e', label: 'Green' },
                  { id: '#0ea5e9', label: 'Blue' },
                  { id: '#a855f7', label: 'Purple' },
                  { id: '#f97316', label: 'Orange' },
                  { id: '#ffffff', label: 'White' }
                ].map(opt => {
                  const actualColor = clip.marker_color || '#eab308';
                  const isActive = (actualColor === opt.id);
                  return (
                    <div
                      key={opt.id}
                      className={`marker-option ${isActive ? 'marker-active' : ''}`}
                      onClick={async (e) => {
                        e.stopPropagation();
                        try {
                          await VideoRepository.setClipMarker(clip.project, clip.format, clip.filename, opt.id);
                          setClips(prev => {
                            const newClips = [...prev];
                            newClips[i].marker_color = opt.id;
                            return newClips;
                          });
                        } catch (err) {
                          console.error("Failed to update marker", err);
                        }
                      }}
                      style={{
                        width: '20px',
                        height: '20px',
                        borderRadius: '50%',
                        background: opt.id,
                        border: isActive ? '3px solid #fff' : '2px solid rgba(0,0,0,0.5)',
                        cursor: 'pointer',
                        boxShadow: isActive ? '0 0 0 1px rgba(0,0,0,0.5), 0 2px 4px rgba(0,0,0,0.5)' : '0 2px 4px rgba(0,0,0,0.5)',
                        transition: 'transform 0.1s',
                        display: isActive ? 'block' : 'none',
                        margin: '0 4px',
                      }}
                      title={opt.label}
                      onMouseOver={e => (e.target as HTMLDivElement).style.transform = 'scale(1.2)'}
                      onMouseOut={e => (e.target as HTMLDivElement).style.transform = 'scale(1)'}
                    />
                  );
                })}
              </div>
              
              {/* Play Button Overlay */}
              {activePlayIndex !== i ? (
                <div 
                  onClick={(e) => {
                    e.stopPropagation();
                    setActivePlayIndex(i);
                    const v = e.currentTarget.parentElement?.querySelector('video');
                    if (v) {
                      v.currentTime = 0;
                      v.muted = false;
                      v.play().catch(() => {});
                    }
                  }}
                  style={{ position: 'absolute', top: '50%', left: '50%', transform: 'translate(-50%, -50%)', background: 'rgba(0,0,0,0.6)', borderRadius: '50%', width: '48px', height: '48px', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 2 }}
                >
                  <svg width="24" height="24" viewBox="0 0 24 24" fill="#fff" stroke="none"><polygon points="5 3 19 12 5 21 5 3"/></svg>
                </div>
              ) : (
                /* Details Button Overlay (shown only when playing) */
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    navigate(`/gallery/${encodeURIComponent(clip.project)}/${encodeURIComponent(clip.format)}/${encodeURIComponent(clip.filename)}`);
                  }}
                  style={{ position: 'absolute', top: '16px', right: '16px', background: 'rgba(0,0,0,0.8)', color: '#fff', border: 'none', borderRadius: '8px', padding: '8px 16px', cursor: 'pointer', fontSize: '0.85rem', fontWeight: 'bold', display: 'flex', alignItems: 'center', gap: '6px', zIndex: 3, backdropFilter: 'blur(4px)', boxShadow: '0 4px 6px rgba(0,0,0,0.3)' }}
                >
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/><polyline points="15 3 21 3 21 9"/><line x1="10" y1="14" x2="21" y2="3"/></svg>
                  Details
                </button>
              )}

              {/* Title overlay */}
              <div style={{ position: 'absolute', bottom: 0, left: 0, right: 0, padding: '16px', pointerEvents: 'none', opacity: activePlayIndex === i ? 0 : 1, transition: 'opacity 0.3s' }}>
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
