import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import type { HomeState } from '../HomeIntents';
import { VideoRepository, type HistoryEntry, type AppConfig } from '../../../../data/VideoRepository';

interface Props {
  state: HomeState;
  intents: Record<string, any>;
}

export const Header: React.FC<Props> = ({ intents }) => {
  const navigate = useNavigate();
  const [isHistoryOpen, setHistoryOpen] = useState(false);
  const [isSettingsOpen, setSettingsOpen] = useState(false);
  const [history, setHistory] = useState<HistoryEntry[]>([]);
  const [isLoadingHistory, setIsLoadingHistory] = useState(false);
  const [configDraft, setConfigDraft] = useState<AppConfig | null>(null);

  useEffect(() => {
    if (isHistoryOpen) {
      setIsLoadingHistory(true);
      VideoRepository.getHistory().then((data: HistoryEntry[]) => setHistory(data))
        .catch((e: any) => console.error("Failed to fetch history:", e))
        .finally(() => setIsLoadingHistory(false));
    }
  }, [isHistoryOpen]);

  useEffect(() => {
    if (isSettingsOpen) {
      VideoRepository.getConfig().then((data: AppConfig) => {
        setConfigDraft(data);
      }).catch((e: any) => console.error("Failed to fetch config:", e));
    }
  }, [isSettingsOpen]);

  const handleClearHistory = async () => {
    if (confirm("Are you sure you want to clear all history?")) {
      await VideoRepository.clearHistory();
      setHistory([]);
    }
  };

  const handleCopyHistoryUrl = (e: React.MouseEvent, url: string) => {
    e.stopPropagation();
    navigator.clipboard.writeText(url);
    alert('URL copied to clipboard!');
  };

  const handleHistoryItemClick = (url: string) => {
    intents.updateUrl(url);
    setHistoryOpen(false);
  };

  const handleSaveSettings = async () => {
    if (configDraft) {
      try {
        await VideoRepository.saveConfig(configDraft);
        setSettingsOpen(false);
      } catch (e) {
        alert("Failed to save config: " + e);
      }
    }
  };

  const updateDraft = (section: keyof AppConfig, key: string, value: any) => {
    if (!configDraft) return;
    setConfigDraft({
      ...configDraft,
      [section]: {
        ...((configDraft[section] as any) || {}),
        [key]: value
      }
    });
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
    <>
    <header>
      <div className="header-left">
        <a href="/" className="title-link"><h1>YTClipper</h1></a>
      </div>
      <div className="header-buttons">
        <button className="icon-btn" aria-label="Gallery" title="View All Clips" onClick={() => navigate('/gallery')}>
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/>
            <rect x="14" y="14" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/>
          </svg>
        </button>
        <button className="icon-btn" aria-label="History" onClick={() => setHistoryOpen(true)}>
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/>
          </svg>
        </button>
        <button className="icon-btn" aria-label="Settings" onClick={() => setSettingsOpen(true)}>
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z"/>
            <circle cx="12" cy="12" r="3"/>
          </svg>
        </button>
      </div>
    </header>

    {/* History Modal */}
    <div className="modal" style={{ display: isHistoryOpen ? 'flex' : 'none', opacity: isHistoryOpen ? 1 : 0 }} onClick={e => { if (e.target === e.currentTarget) setHistoryOpen(false); }}>
      <div className="modal-content">
        <div className="modal-header">
          <h2>History</h2>
          <button className="modal-close" onClick={() => setHistoryOpen(false)}>✕</button>
        </div>
        <div className="modal-body history-body" style={{ padding: '0 20px', maxHeight: '60vh', overflowY: 'auto' }}>
          {isLoadingHistory ? (
            <p style={{ color: 'var(--text-secondary)', textAlign: 'center', padding: '40px 20px' }}>Loading history...</p>
          ) : history.length === 0 ? (
            <p style={{ color: 'var(--text-secondary)', textAlign: 'center', padding: '40px 20px' }}>No history yet. Process a video to see it here.</p>
          ) : (
            <div className="history-list" style={{ display: 'flex', flexDirection: 'column', gap: '12px', marginTop: '16px' }}>
              {history.map(item => (
                <div key={item.video_id} className="history-card" style={{ display: 'flex', gap: '16px', padding: '12px', background: 'var(--surface-elevated, #1e1e2e)', borderRadius: '12px', cursor: 'pointer', position: 'relative' }} onClick={() => handleHistoryItemClick(item.url)}>
                  <div className="history-thumbnail" style={{ width: '140px', height: '80px', borderRadius: '6px', overflow: 'hidden', flexShrink: 0 }}>
                    <img src={item.thumbnail} alt={item.title} style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
                  </div>
                  <div className="history-info" style={{ flex: 1, minWidth: 0, display: 'flex', flexDirection: 'column', gap: '4px' }}>
                    <h4 style={{ margin: 0, fontSize: '1rem', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{item.title}</h4>
                    <div className="history-channel-time" style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                      <span>{item.channel}</span>
                      <span>•</span>
                      <span>{Math.floor(item.duration / 3600) > 0 ? `${Math.floor(item.duration / 3600)}:${String(Math.floor((item.duration % 3600) / 60)).padStart(2, '0')}:${String(item.duration % 60).padStart(2, '0')}` : `${Math.floor(item.duration / 60)}:${String(item.duration % 60).padStart(2, '0')}`}</span>
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.8rem', color: 'var(--text-secondary)', marginTop: 'auto' }}>
                      <span className="history-time-ago" style={{ fontStyle: 'italic' }}>{formatTimeAgo(item.last_viewed)}</span>
                      <span className="history-views" style={{ display: 'flex', alignItems: 'center', gap: '4px', background: 'rgba(124, 77, 255, 0.2)', padding: '2px 6px', borderRadius: '10px', color: '#b39ddb' }}>
                        👁 {item.view_count}
                      </span>
                    </div>
                  </div>
                  <button className="copy-url-btn" style={{ position: 'absolute', right: '12px', bottom: '12px', background: 'rgba(255,255,255,0.1)', border: 'none', borderRadius: '6px', padding: '6px', color: '#fff', cursor: 'pointer' }} onClick={e => handleCopyHistoryUrl(e, item.url)} title="Copy URL">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
        <div className="modal-footer">
          <button className="clear-history-btn" onClick={handleClearHistory} disabled={history.length === 0} style={{ background: 'transparent', border: '1px solid #ef5350', color: '#ef5350', padding: '10px 20px', borderRadius: '8px', cursor: 'pointer', opacity: history.length === 0 ? 0.5 : 1 }}>Clear History</button>
        </div>
      </div>
    </div>

    {/* Settings Modal */}
    <div className="modal" style={{ display: isSettingsOpen ? 'flex' : 'none', opacity: isSettingsOpen ? 1 : 0 }} onClick={e => { if (e.target === e.currentTarget) setSettingsOpen(false); }}>
      <div className="modal-content">
        <div className="modal-header">
          <h2>Settings</h2>
          <button className="modal-close" onClick={() => setSettingsOpen(false)}>✕</button>
        </div>
        <div className="modal-body settings-body" style={{ padding: '0 20px', maxHeight: '60vh', overflowY: 'auto' }}>
          {configDraft ? (
            <div className="settings-form" style={{ display: 'flex', flexDirection: 'column', gap: '24px', padding: '16px 0' }}>
              
              <div className="setting-section">
                <h3 style={{ margin: '0 0 12px 0', fontSize: '1.1rem' }}>Caption Styling</h3>
                <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem', marginBottom: '16px', fontStyle: 'italic' }}>Use the "Burn Captions" toggle on main screen to enable/disable</p>
                
                <div className="form-group" style={{ marginBottom: '16px' }}>
                  <label style={{ display: 'block', marginBottom: '8px', color: 'var(--text-secondary)' }}>Words Per Caption:</label>
                  <select 
                    style={{ width: '100%', padding: '12px', background: '#1e1e2e', border: '1px solid #333', borderRadius: '8px', color: '#fff', fontSize: '1rem' }}
                    value={configDraft.caption_settings?.words_per_caption || 1}
                    onChange={e => updateDraft('caption_settings', 'words_per_caption', parseInt(e.target.value))}
                  >
                    <option value="1">1 word</option>
                    <option value="2">2 words</option>
                    <option value="3">3 words</option>
                    <option value="4">4 words</option>
                  </select>
                </div>

                <div className="form-group" style={{ marginBottom: '16px' }}>
                  <label style={{ display: 'block', marginBottom: '8px', color: 'var(--text-secondary)' }}>Font Family:</label>
                  <select 
                    style={{ width: '100%', padding: '12px', background: '#1e1e2e', border: '1px solid #333', borderRadius: '8px', color: '#fff', fontSize: '1rem' }}
                    value={configDraft.caption_settings?.font_family || 'Montserrat-Bold'}
                    onChange={e => updateDraft('caption_settings', 'font_family', e.target.value)}
                  >
                    <option value="Montserrat-Bold">Montserrat Bold</option>
                    <option value="Impact">Impact</option>
                    <option value="Arial">Arial</option>
                  </select>
                </div>

                <div className="form-group" style={{ marginBottom: '24px' }}>
                  <label style={{ display: 'block', marginBottom: '8px', color: 'var(--text-secondary)' }}>Font Size: {configDraft.caption_settings?.font_size || 80}px</label>
                  <input 
                    type="range" min="30" max="150" step="1" 
                    value={configDraft.caption_settings?.font_size || 80}
                    onChange={e => updateDraft('caption_settings', 'font_size', parseInt(e.target.value))}
                    style={{ width: '100%', accentColor: '#2196f3' }}
                  />
                </div>

                <div className="form-group" style={{ marginBottom: '16px' }}>
                  <label style={{ display: 'block', marginBottom: '8px', color: 'var(--text-secondary)' }}>Vertical Position: {configDraft.caption_settings?.vertical_position || 76}%</label>
                  <input 
                    type="range" min="10" max="90" step="1" 
                    value={configDraft.caption_settings?.vertical_position || 76}
                    onChange={e => updateDraft('caption_settings', 'vertical_position', parseInt(e.target.value))}
                    style={{ width: '100%', accentColor: '#2196f3' }}
                  />
                </div>
              </div>

              <div className="setting-section">
                <h3 style={{ margin: '0 0 12px 0', fontSize: '1.1rem' }}>AI Clip Validation</h3>
                <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem', marginBottom: '16px', fontStyle: 'italic' }}>Set duration limits for AI-generated clips</p>

                <div className="form-group" style={{ marginBottom: '24px' }}>
                  <label style={{ display: 'block', marginBottom: '8px', color: 'var(--text-secondary)' }}>Minimum Duration: {configDraft.ai_validation?.min_clip_duration || 16}s</label>
                  <input 
                    type="range" min="5" max="60" step="1" 
                    value={configDraft.ai_validation?.min_clip_duration || 16}
                    onChange={e => updateDraft('ai_validation', 'min_clip_duration', parseInt(e.target.value))}
                    style={{ width: '100%', accentColor: '#2196f3' }}
                  />
                </div>

                <div className="form-group" style={{ marginBottom: '16px' }}>
                  <label style={{ display: 'block', marginBottom: '8px', color: 'var(--text-secondary)' }}>Maximum Duration: {configDraft.ai_validation?.max_clip_duration || 90}s</label>
                  <input 
                    type="range" min="15" max="300" step="1" 
                    value={configDraft.ai_validation?.max_clip_duration || 90}
                    onChange={e => updateDraft('ai_validation', 'max_clip_duration', parseInt(e.target.value))}
                    style={{ width: '100%', accentColor: '#2196f3' }}
                  />
                </div>
              </div>

            </div>
          ) : (
            <p style={{ color: 'var(--text-secondary)', textAlign: 'center', padding: '40px 20px' }}>Loading settings...</p>
          )}
        </div>
        <div className="modal-footer">
          <button className="save-btn" onClick={handleSaveSettings} style={{ width: '100%', background: '#ff0000', color: '#fff', border: 'none', padding: '14px', borderRadius: '8px', fontSize: '1rem', fontWeight: 'bold', cursor: 'pointer' }}>Save Settings</button>
        </div>
      </div>
    </div>
    </>
  );
};
