import React, { useState, useEffect, useRef } from 'react';
import type { HomeState } from '../HomeIntents';
import { VideoRepository, type HistoryEntry } from '../../../../data/VideoRepository';

interface Props {
  state: HomeState;
  intents: Record<string, any>;
}

export const VideoInput: React.FC<Props> = ({ state, intents }) => {
  const [isHistoryOpen, setHistoryOpen] = useState(false);
  const [history, setHistory] = useState<HistoryEntry[]>([]);
  const [isLoadingHistory, setIsLoadingHistory] = useState(false);
  const [hoveredVideoId, setHoveredVideoId] = useState<string | null>(null);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    // Focus input on initial load and open history
    if (inputRef.current) {
      inputRef.current.focus();
      setHistoryOpen(true);
    }
  }, []);

  useEffect(() => {
    if (isHistoryOpen) {
      setIsLoadingHistory(true);
      VideoRepository.getHistory().then((data: HistoryEntry[]) => setHistory(data))
        .catch((e: any) => console.error("Failed to fetch history:", e))
        .finally(() => setIsLoadingHistory(false));
    }
  }, [isHistoryOpen]);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setHistoryOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const handleClearHistory = async () => {
    if (confirm("Are you sure you want to clear all history?")) {
      await VideoRepository.clearHistory();
      setHistory([]);
    }
  };

  const handleOpenLink = (e: React.MouseEvent, url: string) => {
    e.stopPropagation();
    window.open(url, '_blank', 'noopener,noreferrer');
  };

  const handleHistoryItemClick = (url: string) => {
    intents.updateUrl(url);
    setHistoryOpen(false);
  };

  const handleDeleteHistoryItem = async (e: React.MouseEvent, videoId: string) => {
    e.stopPropagation();
    try {
      await VideoRepository.deleteHistoryEntry(videoId);
      setHistory(prev => prev.filter(item => item.video_id !== videoId));
    } catch (error) {
      console.error("Failed to delete history item:", error);
      alert("Could not remove history item.");
    }
  };

  const formatTimeAgo = (isoString: string) => {
    const diff = Date.now() - new Date(isoString).getTime();
    const minutes = Math.floor(diff / 60000);
    if (minutes < 60) return `${minutes}m ago`;
    const hours = Math.floor(minutes / 60);
    if (hours < 24) return `${hours}h ago`;
    return `${Math.floor(hours / 24)}d ago`;
  };

  return (
    <div className="input-section">
      <div className="input-wrapper" ref={dropdownRef} style={{ position: 'relative' }}>
        <input
          ref={inputRef}
          type="url"
          id="urlInput"
          placeholder="Paste YouTube URL here..."
          aria-label="YouTube URL"
          value={state.url}
          onChange={e => intents.updateUrl(e.target.value)}
          onFocus={() => setHistoryOpen(true)}
          onClick={() => setHistoryOpen(true)}
        />
        {state.url && (
          <button className="clear-btn" aria-label="Clear input" onClick={intents.clearInput}>✕</button>
        )}
        
        {/* History Dropdown */}
        {isHistoryOpen && (
          <div style={{
            position: 'absolute',
            top: 'calc(100% + 8px)',
            left: 0,
            right: 0,
            background: 'var(--surface, #121212)',
            border: '1px solid #333',
            borderRadius: '12px',
            boxShadow: '0 8px 24px rgba(0,0,0,0.5)',
            zIndex: 1000,
            display: 'flex',
            flexDirection: 'column',
            overflow: 'hidden'
          }}>
            <div style={{ padding: '12px' }}>
              {isLoadingHistory ? (
                <p style={{ color: 'var(--text-secondary)', textAlign: 'center', padding: '20px' }}>Loading history...</p>
              ) : history.length === 0 ? (
                <p style={{ color: 'var(--text-secondary)', textAlign: 'center', padding: '20px' }}>No history yet.</p>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                  {history.map(item => (
                    <div 
                      key={item.video_id} 
                      style={{ display: 'flex', gap: '12px', padding: '10px', background: '#1e1e2e', borderRadius: '8px', cursor: 'pointer', position: 'relative' }} 
                      onClick={() => handleHistoryItemClick(item.url)}
                      onMouseEnter={() => setHoveredVideoId(item.video_id)}
                      onMouseLeave={() => setHoveredVideoId(null)}
                    >
                      <div style={{ width: '100px', height: '56px', borderRadius: '4px', overflow: 'hidden', flexShrink: 0 }}>
                        <img src={item.thumbnail} alt={item.title} style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
                      </div>
                      <div style={{ flex: 1, minWidth: 0, display: 'flex', flexDirection: 'column', gap: '2px', paddingRight: hoveredVideoId === item.video_id ? '30px' : '0' }}>
                        <h4 style={{ margin: 0, fontSize: '0.9rem', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', color: '#fff' }}>{item.title}</h4>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
                          <span>{item.channel}</span>
                          <span>•</span>
                          <span>{Math.floor(item.duration / 3600) > 0 ? `${Math.floor(item.duration / 3600)}:${String(Math.floor((item.duration % 3600) / 60)).padStart(2, '0')}:${String(item.duration % 60).padStart(2, '0')}` : `${Math.floor(item.duration / 60)}:${String(item.duration % 60).padStart(2, '0')}`}</span>
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.75rem', color: 'var(--text-secondary)', marginTop: 'auto' }}>
                          <span style={{ fontStyle: 'italic' }}>{formatTimeAgo(item.last_viewed)}</span>
                        </div>
                      </div>
                      
                      {/* Action Buttons (Hover Only) */}
                      {hoveredVideoId === item.video_id && (
                        <div style={{ position: 'absolute', right: '10px', top: '10px', display: 'flex', flexDirection: 'column', gap: '8px' }}>
                          <button style={{ background: 'rgba(239, 83, 80, 0.2)', border: 'none', borderRadius: '4px', padding: '4px', color: '#ef5350', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center' }} onClick={e => handleDeleteHistoryItem(e, item.video_id)} title="Remove from History">
                            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>
                          </button>
                          <button style={{ background: 'rgba(255,255,255,0.1)', border: 'none', borderRadius: '4px', padding: '4px', color: '#fff', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center' }} onClick={e => handleOpenLink(e, item.url)} title="Open in YouTube">
                            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"></path><polyline points="15 3 21 3 21 9"></polyline><line x1="10" y1="14" x2="21" y2="3"></line></svg>
                          </button>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>

            {history.length > 0 && (
              <div style={{ padding: '8px 12px', borderTop: '1px solid #222', textAlign: 'center' }}>
                <button onClick={handleClearHistory} style={{ background: 'transparent', border: 'none', color: '#ef5350', cursor: 'pointer', fontSize: '0.85rem', padding: '4px' }}>
                  Clear History
                </button>
              </div>
            )}
          </div>
        )}
      </div>

      {state.infoStatus === 'loading' && (
        <div className="loading-indicator">
          <div className="spinner"></div>
          <span>Fetching video info...</span>
        </div>
      )}
      {state.infoStatus === 'error' && state.error && (
        <div className="error-msg" style={{ marginTop: 8 }}>{state.error}</div>
      )}
    </div>
  );
};
