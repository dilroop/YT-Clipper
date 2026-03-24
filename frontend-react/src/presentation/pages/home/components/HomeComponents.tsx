import React, { useState, useEffect } from 'react';
import type { HomeState } from '../HomeIntents';
import { VideoRepository, type HistoryEntry, type AppConfig } from '../../../../data/VideoRepository';

interface Props {
  state: HomeState;
  intents: Record<string, any>;
}

// ─── Video Info Panel ─────────────────────────────────────────────────────────
// Shown after URL metadata is fetched. Contains thumbnail, config, and workflow buttons.
export const VideoInfoPanel: React.FC<Props> = ({ state, intents }) => (
  <div className="preview-section" id="previewSection">
    {/* Video metadata header */}
    {state.videoInfo && (
      <div className="video-header">
        <div className="thumbnail-wrapper-compact">
          <img src={state.videoInfo.thumbnail} alt="Video thumbnail" />
        </div>
        <div className="video-info-compact">
          <h2>{state.videoInfo.title}</h2>
          <p className="channel-name">{state.videoInfo.channel}</p>
          <p className="duration">
            Duration: {Math.floor((state.videoInfo.duration || 0) / 60)}:{String((state.videoInfo.duration || 0) % 60).padStart(2, '0')}
          </p>
        </div>
      </div>
    )}

    {/* Config grid */}
    <div className="options-grid">
      <FormatSelector state={state} intents={intents} />
      <StrategySelector state={state} intents={intents} />
    </div>

    {state.error && <div className="error-msg">{state.error}</div>}

    {/* Workflow buttons */}
    <div className="workflow-buttons">
      <button
        className="workflow-btn auto-btn"
        onClick={() => intents.processVideo()}
        disabled={!state.url}
      >
        <span style={{ fontSize: '24px' }}>🤖</span> Auto Create
      </button>
      <button
        className="workflow-btn manual-btn"
        onClick={() => intents.analyzeVideo()}
        disabled={!state.url}
      >
        <span style={{ fontSize: '24px' }}>🔨</span> Manually Choose
      </button>
    </div>
  </div>
);

// ─── Header ──────────────────────────────────────────────────────────────────
export const Header: React.FC<Props> = ({ intents }) => {
  const [isHistoryOpen, setHistoryOpen] = useState(false);
  const [isSettingsOpen, setSettingsOpen] = useState(false);

  // History State
  const [history, setHistory] = useState<HistoryEntry[]>([]);
  const [isLoadingHistory, setIsLoadingHistory] = useState(false);

  // Config State
  const [configDraft, setConfigDraft] = useState<AppConfig | null>(null);

  // Fetch History when modal opens
  useEffect(() => {
    if (isHistoryOpen) {
      setIsLoadingHistory(true);
      VideoRepository.getHistory().then((data: HistoryEntry[]) => setHistory(data))
        .catch((e: any) => console.error("Failed to fetch history:", e))
        .finally(() => setIsLoadingHistory(false));
    }
  }, [isHistoryOpen]);

  // Fetch Config when modal opens
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
        <button className="icon-btn" aria-label="Gallery" title="View All Clips" onClick={() => window.open('/gallery', '_blank')}>
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

// ─── Video Input ──────────────────────────────────────────────────────────────
// Always visible — URL bar with clear button.
export const VideoInput: React.FC<Props> = ({ state, intents }) => (
  <div className="input-section">
    <div className="input-wrapper">
      <input
        type="url"
        id="urlInput"
        placeholder="Paste YouTube URL here..."
        aria-label="YouTube URL"
        value={state.url}
        onChange={e => intents.updateUrl(e.target.value)}
      />
      {state.url && (
        <button className="clear-btn" aria-label="Clear input" onClick={intents.clearInput}>✕</button>
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

// ─── Format Selector ─────────────────────────────────────────────────────────
export const FormatSelector: React.FC<Props> = ({ state, intents }) => (
  <>
    <div className="option-card option-card-full">
      <h3>Reels Format:</h3>
      <div className="format-buttons-multi">
        {[
          { key: 'vertical_9x16', label: 'Vertical', svg: <svg width="40" height="60" viewBox="0 0 40 60" fill="none"><rect x="2" y="2" width="36" height="56" stroke="currentColor" strokeWidth="3" rx="4"/><text x="20" y="35" textAnchor="middle" fill="currentColor" fontSize="10" fontWeight="bold">9:16</text></svg> },
          { key: 'stacked_photo', label: 'Photo', svg: <svg width="48" height="48" viewBox="0 0 48 48" fill="none"><rect x="4" y="4" width="40" height="40" stroke="currentColor" strokeWidth="2.5" rx="8"/><text x="24" y="30" textAnchor="middle" fill="currentColor" fontSize="16" fontWeight="bold">AI</text></svg> },
          { key: 'stacked_video', label: 'Video', svg: <svg width="48" height="48" viewBox="0 0 48 48" fill="none"><rect x="4" y="4" width="40" height="40" stroke="currentColor" strokeWidth="2.5" rx="8"/><path d="M19 16 L19 32 L33 24 Z" fill="currentColor"/></svg> },
          { key: 'original', label: 'Original', svg: <svg width="60" height="40" viewBox="0 0 60 40" fill="none"><rect x="2" y="2" width="56" height="36" stroke="currentColor" strokeWidth="3" rx="4"/><text x="30" y="25" textAnchor="middle" fill="currentColor" fontSize="9" fontWeight="bold">16:9</text></svg> },
        ].map(({ key, label, svg }) => (
          <button
            key={key}
            className={`format-btn-icon ${state.selectedFormat === key ? 'active' : ''}`}
            onClick={() => intents.updateFormat(key)}
          >
            <div className="format-icon">{svg}</div>
            <span className="format-label">{label}</span>
          </button>
        ))}
      </div>
    </div>

    <div className="option-card">
      <h3>Captions:</h3>
      <label className="toggle-label">
        <input type="checkbox" checked={state.burnCaptions} onChange={e => intents.toggleCaptions(e.target.checked)} />
        <span className="toggle-slider"></span>
        <span className="toggle-text">Burn into Video</span>
      </label>
    </div>
  </>
);

// ─── Strategy Selector ────────────────────────────────────────────────────────
export const StrategySelector: React.FC<Props> = ({ state, intents }) => {
  const [showAdvanced, setShowAdvanced] = useState(!!state.extraContext);
  return (
    <div className="option-card option-card-full">
      <div className="strategy-header">
        <h3>AI Strategy:</h3>
        <div className="extra-context-toggle" onClick={() => setShowAdvanced(v => !v)}>
          <span className="toggle-icon">{showAdvanced ? '−' : '＋'}</span> Advanced Instructions
        </div>
      </div>
      <select className="strategy-dropdown" value={state.aiStrategy} onChange={e => intents.updateStrategy(e.target.value)}>
        <option value="viral-moments">Viral Moments</option>
        <option value="multi-part-narrative">Multi-Part Story Narrative</option>
        <option value="educational-insights">Educational Highlights</option>
      </select>
      {showAdvanced && (
        <div className="extra-context-container">
          <textarea
            className="extra-context-textarea"
            value={state.extraContext || ''}
            onChange={e => intents.updateExtraContext(e.target.value)}
            placeholder="Tell the AI exactly what story to extract or which themes to focus on..."
          />
        </div>
      )}
    </div>
  );
};

// ─── Progress Section ─────────────────────────────────────────────────────────
export const ProgressSection: React.FC<Props> = ({ state, intents }) => {
  const p = state.progress;
  const percent = p ? p.percent : 0;
  const isActive = (stageName: string) => p?.stage === stageName;

  return (
    <div className="progress-section">
      <h3>{state.generationMode === 'manual' ? 'Analyzing Video...' : 'Creating Clips...'}</h3>
      <div className="progress-bar">
        <div className="progress-fill" style={{ width: `${percent}%` }}></div>
        <span className="progress-percent">{Math.round(percent)}%</span>
      </div>
      <div className="progress-stages">
        {[
          { id: 'downloading', icon: '📥', name: 'Downloading Video' },
          { id: 'transcribing', icon: '🎤', name: 'Transcribing Audio' },
          { id: 'analyzing', icon: '🤖', name: 'AI Analysis' },
          { id: 'clipping', icon: '✂️', name: 'Creating Clips' },
          { id: 'organizing', icon: '📁', name: 'Organizing Files' }
        ].map(stage => (
          <div key={stage.id} className={`progress-stage ${isActive(stage.id) ? 'active' : ''}`}>
            <div className="stage-header">
              <span className="stage-icon">{stage.icon}</span>
              <span className="stage-name">{stage.name}</span>
              <span className="stage-status">{isActive(stage.id) ? p?.message : 'Waiting...'}</span>
            </div>
          </div>
        ))}
      </div>
      <button className="cancel-btn" onClick={() => intents.resetToVideoInfo()}>Cancel</button>
    </div>
  );
};

// ─── Clip Selection Section ───────────────────────────────────────────────────
// Shown after "Manually Choose" analysis completes.
export const ClipSelectionSection: React.FC<Props> = ({ state, intents }) => {
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [editorClip, setEditorClip] = useState<{ clip: any; index: number } | null>(null);

  if (!state.clips) return null;

  const toggleSelect = (id: string) => {
    setSelectedIds(prev => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id); else next.add(id);
      return next;
    });
  };

  const allSelected = state.clips.length > 0 && selectedIds.size === state.clips.length;

  const toggleAll = () => {
    if (allSelected) setSelectedIds(new Set());
    else setSelectedIds(new Set(state.clips!.map(c => c.id)));
  };

  const formatTime = (secs: number) => {
    const h = Math.floor(secs / 3600);
    const m = Math.floor((secs % 3600) / 60);
    const s = Math.floor(secs % 60);
    if (h > 0) return `${String(h).padStart(2,'0')}:${String(m).padStart(2,'0')}:${String(s).padStart(2,'0')}`;
    return `${String(m).padStart(2,'0')}:${String(s).padStart(2,'0')}`;
  };

  return (
    <>
    <div className="clip-selection-section">
      <div className="clip-selection-header">
        <h3>Select Clips to Generate</h3>
        <button className="select-all-btn" onClick={toggleAll}>{allSelected ? 'Deselect All' : 'Select All'}</button>
      </div>
      <div className="clips-grid">
        {state.clips.map((clip, idx) => {
          const isSelected = selectedIds.has(clip.id);
          const validStatus = clip.validation_status || 'valid';
          const validMsg = clip.validation_message || 'No validation errors — clip is good to use';
          const partCount = clip.parts?.length ?? 1;

          return (
            <div
              key={clip.id}
              className={`clip-card ${isSelected ? 'clip-card--selected' : ''} clip-card--${validStatus}`}
              onClick={() => toggleSelect(clip.id)}
            >
              <div className="clip-card-header">
                <input type="checkbox" className="clip-checkbox" checked={isSelected}
                  onClick={e => e.stopPropagation()} onChange={() => toggleSelect(clip.id)} />
                <span className={`clip-validation-dot clip-validation-dot--${validStatus}`}>✓</span>
                <span className="clip-card-title">{clip.title}</span>
                <span className="clip-card-duration">{(clip.duration || 0).toFixed(1)}s</span>
                <button className="clip-edit-btn" title="Open Clip Script Editor"
                  onClick={e => { e.stopPropagation(); setEditorClip({ clip, index: idx }); }}>
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/>
                    <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/>
                  </svg>
                </button>
              </div>

              <div className={`clip-validation-msg clip-validation-msg--${validStatus}`}>{validMsg}</div>
              <p className="clip-card-desc">{clip.explanation}</p>

              {clip.parts && clip.parts.length > 0 ? (
                <div className="clip-parts-list">
                  {clip.parts.map((part, pi) => (
                    <div key={pi} className="clip-part">
                      <span className="clip-part-time">
                        [{formatTime(part.start)} — {formatTime(part.end)}] Part {pi + 1} ({part.duration.toFixed(1)}s)
                      </span>
                      <p className="clip-part-text">{part.text}</p>
                    </div>
                  ))}
                </div>
              ) : clip.words && clip.words.length > 0 ? (
                <div className="clip-parts-list">
                  <div className="clip-part">
                    <span className="clip-part-time">
                      [{formatTime(clip.start)} — {formatTime(clip.end)}] {partCount} part · {(clip.duration || 0).toFixed(1)}s
                    </span>
                    <p className="clip-part-text">{clip.words.slice(0, 30).map(w => w.word).join(' ')}{clip.words.length > 30 ? '…' : ''}</p>
                  </div>
                </div>
              ) : null}
            </div>
          );
        })}
      </div>
    </div>

    {/* Sticky generate bar */}
    <div className="clip-generate-bar">
      <span className="clip-generate-count">{selectedIds.size} of {state.clips.length} selected</span>
      <button className="generate-btn" disabled={selectedIds.size === 0}
        onClick={() => intents.processVideoSelection(Array.from(selectedIds))}>
        Generate Selected Clips
      </button>
    </div>

    {/* Clip Script Editor — full-screen overlay */}
    {editorClip && (
      <ClipEditorOverlay
        clip={editorClip.clip}
        clipIndex={editorClip.index}
        onSave={(updatedClip) => {
          intents.updateClip(editorClip.index, updatedClip);
          setEditorClip(null);
        }}
        onClose={() => setEditorClip(null)}
      />
    )}
    </>
  );
};

// ─── Clip Editor Overlay (full screen) ───────────────────────────────────────
import { ClipScriptEditorPage } from '../../clip-editor/ClipScriptEditorPage';

const ClipEditorOverlay: React.FC<{
  clip: any;
  clipIndex: number;
  onSave: (clip: any) => void;
  onClose: () => void;
}> = ({ clip, onSave, onClose }) => (
  <div className="clip-editor-fullscreen">
    <ClipScriptEditorPage clip={clip} onSave={onSave} onClose={onClose} />
  </div>
);

// ─── Results Section ──────────────────────────────────────────────────────────
export const ResultsSection: React.FC<Props> = ({ intents }) => (
  <div className="results-section">
    <h3>✨ Clips Ready!</h3>
    <p style={{ color: 'var(--text-secondary)' }}>Your clips have been generated and saved successfully.</p>
    <div style={{ marginTop: '20px', display: 'flex', gap: '10px' }}>
      <button className="workflow-btn auto-btn" onClick={() => window.open('/gallery', '_blank')}>Open Gallery</button>
      <button className="workflow-btn manual-btn" onClick={() => intents.resetToVideoInfo()}>Create More</button>
    </div>
  </div>
);
