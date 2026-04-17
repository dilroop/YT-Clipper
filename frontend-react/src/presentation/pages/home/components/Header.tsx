import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import type { HomeState } from '../HomeIntents';
import { VideoRepository, type AppConfig } from '../../../../data/VideoRepository';

interface Props {
  state: HomeState;
  intents: Record<string, any>;
}

export const Header: React.FC<Props> = () => {
  const navigate = useNavigate();
  const [isSettingsOpen, setSettingsOpen] = useState(false);
  const [configDraft, setConfigDraft] = useState<AppConfig | null>(null);



  useEffect(() => {
    if (isSettingsOpen) {
      VideoRepository.getConfig().then((data: AppConfig) => {
        setConfigDraft(data);
      }).catch((e: any) => console.error("Failed to fetch config:", e));
    }
  }, [isSettingsOpen]);



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

        <button className="icon-btn" aria-label="Settings" onClick={() => setSettingsOpen(true)}>
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z"/>
            <circle cx="12" cy="12" r="3"/>
          </svg>
        </button>
      </div>
    </header>



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

              {/* ── AI Providers ─────────────────────────────────────────── */}
              <div className="setting-section">
                <h3 style={{ margin: '0 0 4px 0', fontSize: '1.1rem' }}>🤖 AI Providers</h3>
                <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem', marginBottom: '16px', fontStyle: 'italic' }}>
                  API keys are stored locally on the server. Select your active provider on the video panel.
                </p>

                {/* OpenAI */}
                <div style={{ background: '#111', borderRadius: '10px', padding: '14px', marginBottom: '14px', border: '1px solid #222' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '12px' }}>
                    <span style={{ fontSize: '1.1rem' }}>🧠</span>
                    <strong style={{ fontSize: '1rem' }}>OpenAI</strong>
                  </div>
                  <div className="form-group" style={{ marginBottom: '12px' }}>
                    <label style={{ display: 'block', marginBottom: '6px', color: 'var(--text-secondary)', fontSize: '0.85rem' }}>API Key:</label>
                    <input type="password" placeholder="sk-..." value={configDraft.ai_settings?.openai?.api_key || ''}
                      onChange={e => updateDraft('ai_settings' as any, 'openai', { ...(configDraft.ai_settings?.openai || {}), api_key: e.target.value })}
                      style={{ width: '100%', padding: '10px 12px', background: '#1a1a2e', border: '1px solid #333', borderRadius: '8px', color: '#fff', fontSize: '0.9rem' }} />
                  </div>
                  <div className="form-group" style={{ marginBottom: '12px' }}>
                    <label style={{ display: 'block', marginBottom: '6px', color: 'var(--text-secondary)', fontSize: '0.85rem' }}>Model:</label>
                    <select value={configDraft.ai_settings?.openai?.model || 'gpt-4o-mini'}
                      onChange={e => updateDraft('ai_settings' as any, 'openai', { ...(configDraft.ai_settings?.openai || {}), model: e.target.value })}
                      style={{ width: '100%', padding: '10px 12px', background: '#1a1a2e', border: '1px solid #333', borderRadius: '8px', color: '#fff', fontSize: '0.9rem' }}>
                      <option value="gpt-4o">gpt-4o</option>
                      <option value="gpt-4o-mini">gpt-4o-mini</option>
                      <option value="gpt-4-turbo">gpt-4-turbo</option>
                      <option value="gpt-3.5-turbo">gpt-3.5-turbo</option>
                    </select>
                  </div>
                  <div className="form-group">
                    <label style={{ display: 'block', marginBottom: '6px', color: 'var(--text-secondary)', fontSize: '0.85rem' }}>
                      Temperature: {(configDraft.ai_settings?.openai?.temperature ?? 0.7).toFixed(1)}
                    </label>
                    <input type="range" min="0" max="2" step="0.1"
                      value={configDraft.ai_settings?.openai?.temperature ?? 0.7}
                      onChange={e => updateDraft('ai_settings' as any, 'openai', { ...(configDraft.ai_settings?.openai || {}), temperature: parseFloat(e.target.value) })}
                      style={{ width: '100%', accentColor: '#4ade80' }} />
                  </div>
                </div>

                {/* DeepSeek */}
                <div style={{ background: '#111', borderRadius: '10px', padding: '14px', border: '1px solid #222' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '12px' }}>
                    <span style={{ fontSize: '1.1rem' }}>🔮</span>
                    <strong style={{ fontSize: '1rem' }}>DeepSeek</strong>
                  </div>
                  <div className="form-group" style={{ marginBottom: '12px' }}>
                    <label style={{ display: 'block', marginBottom: '6px', color: 'var(--text-secondary)', fontSize: '0.85rem' }}>API Key:</label>
                    <input type="password" placeholder="sk-..." value={configDraft.ai_settings?.deepseek?.api_key || ''}
                      onChange={e => updateDraft('ai_settings' as any, 'deepseek', { ...(configDraft.ai_settings?.deepseek || {}), api_key: e.target.value })}
                      style={{ width: '100%', padding: '10px 12px', background: '#1a1a2e', border: '1px solid #333', borderRadius: '8px', color: '#fff', fontSize: '0.9rem' }} />
                  </div>
                  <div className="form-group" style={{ marginBottom: '12px' }}>
                    <label style={{ display: 'block', marginBottom: '6px', color: 'var(--text-secondary)', fontSize: '0.85rem' }}>Model:</label>
                    <select value={configDraft.ai_settings?.deepseek?.model || 'deepseek-chat'}
                      onChange={e => updateDraft('ai_settings' as any, 'deepseek', { ...(configDraft.ai_settings?.deepseek || {}), model: e.target.value })}
                      style={{ width: '100%', padding: '10px 12px', background: '#1a1a2e', border: '1px solid #333', borderRadius: '8px', color: '#fff', fontSize: '0.9rem' }}>
                      <option value="deepseek-chat">deepseek-chat</option>
                      <option value="deepseek-reasoner">deepseek-reasoner</option>
                    </select>
                  </div>
                  <div className="form-group">
                    <label style={{ display: 'block', marginBottom: '6px', color: 'var(--text-secondary)', fontSize: '0.85rem' }}>
                      Temperature: {(configDraft.ai_settings?.deepseek?.temperature ?? 0.7).toFixed(1)}
                    </label>
                    <input type="range" min="0" max="2" step="0.1"
                      value={configDraft.ai_settings?.deepseek?.temperature ?? 0.7}
                      onChange={e => updateDraft('ai_settings' as any, 'deepseek', { ...(configDraft.ai_settings?.deepseek || {}), temperature: parseFloat(e.target.value) })}
                      style={{ width: '100%', accentColor: '#818cf8' }} />
                  </div>
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
