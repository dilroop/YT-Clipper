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
  const [customFonts, setCustomFonts] = useState<string[]>([]);



  useEffect(() => {
    if (isSettingsOpen) {
      VideoRepository.getConfig().then((data: AppConfig) => {
        setConfigDraft(data);
      }).catch((e: any) => console.error("Failed to fetch config:", e));

      VideoRepository.getFonts().then(fonts => {
        setCustomFonts(fonts.map(f => f.name));
      }).catch(err => console.error("Failed to load custom fonts:", err));
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

        <button className="icon-btn" aria-label="Story Maker" title="Story Maker" onClick={() => navigate('/story-maker')} style={{ position: 'relative' }}>
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <rect x="3" y="3" width="18" height="18" rx="2"/>
            <path d="M3 9h18M9 21V9"/>
            <circle cx="15.5" cy="14.5" r="1.5" fill="currentColor" stroke="none"/>
            <path d="M8 15l2-2 2 2 3-3"/>
          </svg>
          <span style={{ position: 'absolute', top: -4, right: -4, background: 'linear-gradient(135deg,#7c3aed,#4f46e5)', borderRadius: '50%', width: 10, height: 10, display: 'block' }} />
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
                
                <div style={{ display: 'flex', gap: '16px', marginBottom: '16px' }}>
                  <div className="form-group" style={{ flex: 1 }}>
                    <label style={{ display: 'block', marginBottom: '8px', color: 'var(--text-secondary)' }}>Words Per Caption:</label>
                    <select 
                      style={{ width: '100%', padding: '12px', background: '#1e1e2e', border: '1px solid #333', borderRadius: '8px', color: '#fff', fontSize: '1rem' }}
                      value={configDraft.caption_settings?.words_per_caption || 2}
                      onChange={e => updateDraft('caption_settings', 'words_per_caption', parseInt(e.target.value))}
                    >
                      <option value="1">1 word</option>
                      <option value="2">2 words</option>
                      <option value="3">3 words</option>
                      <option value="4">4 words</option>
                    </select>
                  </div>

                  <div className="form-group" style={{ flex: 1 }}>
                    <label style={{ display: 'block', marginBottom: '8px', color: 'var(--text-secondary)' }}>Font Family:</label>
                    <select 
                      style={{ width: '100%', padding: '12px', background: '#1e1e2e', border: '1px solid #333', borderRadius: '8px', color: '#fff', fontSize: '1rem' }}
                      value={configDraft.caption_settings?.font_family || 'Arial'}
                      onChange={e => updateDraft('caption_settings', 'font_family', e.target.value)}
                    >
                      <optgroup label="Custom Project Fonts">
                        {customFonts.map(f => <option key={f} value={f}>{f}</option>)}
                      </optgroup>
                      <optgroup label="Standard Fonts">
                        <option value="Montserrat-Bold">Montserrat Bold</option>
                        <option value="Impact">Impact</option>
                        <option value="Arial">Arial</option>
                      </optgroup>
                    </select>
                  </div>
                </div>

                <div style={{ display: 'flex', gap: '16px', marginBottom: '24px' }}>
                  <div className="form-group" style={{ flex: 1 }}>
                    <label style={{ display: 'block', marginBottom: '8px', color: 'var(--text-secondary)' }}>Font Size: {configDraft.caption_settings?.font_size || 80}px</label>
                    <input 
                      type="range" min="30" max="150" step="1" 
                      value={configDraft.caption_settings?.font_size || 80}
                      onChange={e => updateDraft('caption_settings', 'font_size', parseInt(e.target.value))}
                      style={{ width: '100%', accentColor: '#2196f3' }}
                    />
                  </div>

                  <div className="form-group" style={{ flex: 1 }}>
                    <label style={{ display: 'block', marginBottom: '8px', color: 'var(--text-secondary)' }}>Vertical Position: {configDraft.caption_settings?.vertical_position || 80}%</label>
                    <input 
                      type="range" min="10" max="90" step="1" 
                      value={configDraft.caption_settings?.vertical_position || 80}
                      onChange={e => updateDraft('caption_settings', 'vertical_position', parseInt(e.target.value))}
                      style={{ width: '100%', accentColor: '#2196f3' }}
                    />
                  </div>
                </div>

                {/* New Colors and Opacity Row */}
                <div style={{ display: 'flex', gap: '16px', marginBottom: '24px', flexWrap: 'wrap' }}>
                  <div className="form-group" style={{ flex: '1 1 120px' }}>
                    <label style={{ display: 'block', marginBottom: '8px', color: 'var(--text-secondary)' }}>Text Color:</label>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <input 
                        type="color" 
                        value={configDraft.caption_settings?.text_color || '#FFFFFF'}
                        onChange={e => updateDraft('caption_settings', 'text_color', e.target.value)}
                        style={{ width: '40px', height: '40px', cursor: 'pointer', padding: 0, border: 'none', borderRadius: '4px', background: 'transparent' }}
                      />
                      <span style={{ fontSize: '0.9rem', color: '#aaa', fontFamily: 'monospace' }}>{configDraft.caption_settings?.text_color || '#FFFFFF'}</span>
                    </div>
                  </div>

                  <div className="form-group" style={{ flex: '1 1 120px' }}>
                    <label style={{ display: 'block', marginBottom: '8px', color: 'var(--text-secondary)' }}>Outline Color:</label>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <input 
                        type="color" 
                        value={configDraft.caption_settings?.outline_color || '#000000'}
                        onChange={e => updateDraft('caption_settings', 'outline_color', e.target.value)}
                        style={{ width: '40px', height: '40px', cursor: 'pointer', padding: 0, border: 'none', borderRadius: '4px', background: 'transparent' }}
                      />
                      <span style={{ fontSize: '0.9rem', color: '#aaa', fontFamily: 'monospace' }}>{configDraft.caption_settings?.outline_color || '#000000'}</span>
                    </div>
                  </div>
                  
                  <div className="form-group" style={{ flex: '1 1 120px' }}>
                    <label style={{ display: 'block', marginBottom: '8px', color: 'var(--text-secondary)' }}>Outline Width: {configDraft.caption_settings?.outline_width ?? 3}px</label>
                    <input 
                      type="range" min="0" max="15" step="0.5" 
                      value={configDraft.caption_settings?.outline_width ?? 3}
                      onChange={e => updateDraft('caption_settings', 'outline_width', parseFloat(e.target.value))}
                      style={{ width: '100%', accentColor: '#2196f3' }}
                    />
                  </div>

                  <div className="form-group" style={{ flex: '1 1 150px' }}>
                    <label style={{ display: 'block', marginBottom: '8px', color: 'var(--text-secondary)' }}>Outline Opacity: {configDraft.caption_settings?.outline_opacity ?? 100}%</label>
                    <input 
                      type="range" min="0" max="100" step="1" 
                      value={configDraft.caption_settings?.outline_opacity ?? 100}
                      onChange={e => updateDraft('caption_settings', 'outline_opacity', parseInt(e.target.value))}
                      style={{ width: '100%', accentColor: '#2196f3' }}
                    />
                  </div>
                </div>

                {/* Live Preview Box */}
                <div style={{ background: '#2a2a3a', borderRadius: '8px', padding: '24px 16px', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', minHeight: '140px', position: 'relative', overflow: 'hidden' }}>
                  
                  {/* Checkerboard background for transparency preview */}
                  <div style={{ position: 'absolute', top: 0, left: 0, right: 0, bottom: 0, opacity: 0.15, backgroundImage: 'linear-gradient(45deg, #808080 25%, transparent 25%), linear-gradient(-45deg, #808080 25%, transparent 25%), linear-gradient(45deg, transparent 75%, #808080 75%), linear-gradient(-45deg, transparent 75%, #808080 75%)', backgroundSize: '20px 20px', backgroundPosition: '0 0, 0 10px, 10px -10px, -10px 0px' }} />
                  
                  {/* Video-like background */}
                  <div style={{ position: 'absolute', top: '10%', left: '10%', right: '10%', bottom: '10%', background: 'linear-gradient(135deg, #4ade8033, #3b82f633)', borderRadius: '8px', filter: 'blur(20px)', zIndex: 1 }} />
                  
                  {(() => {
                    const c = configDraft.caption_settings || {};
                    const tColor = c.text_color || '#FFFFFF';
                    const oColor = c.outline_color || '#000000';
                    const oWidth = c.outline_width ?? 3;
                    const oOpac = c.outline_opacity ?? 100;
                    
                    // Convert hex to rgb to apply opacity
                    const hexToRgb = (hex: string) => {
                      const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
                      return result ? `${parseInt(result[1], 16)}, ${parseInt(result[2], 16)}, ${parseInt(result[3], 16)}` : '0, 0, 0';
                    };
                    
                    const rgbaOutline = `rgba(${hexToRgb(oColor)}, ${oOpac / 100})`;
                    
                    return (
                      <div style={{ 
                        zIndex: 2,
                        fontFamily: c.font_family || 'Arial', 
                        fontSize: `clamp(28px, ${c.font_size ? c.font_size * 0.6 : 48}px, 72px)`, // scaled roughly for preview
                        fontWeight: 'bold',
                        textAlign: 'center',
                        textTransform: 'uppercase',
                        padding: '10px',
                        position: 'relative'
                      }}>
                        {/* Stroke Layer (Behind) */}
                        <div style={{
                          position: 'absolute',
                          left: 0, right: 0, top: '10px', // matches padding
                          color: 'transparent',
                          WebkitTextStroke: `${oWidth * 2}px ${rgbaOutline}`,
                          zIndex: 1
                        }}>
                          CAPTION PREVIEW
                        </div>
                        {/* Text Layer (Front) */}
                        <div style={{
                          position: 'relative',
                          color: tColor,
                          zIndex: 2,
                          textShadow: `0px 2px 4px rgba(0,0,0, 0.4)`
                        }}>
                          CAPTION PREVIEW
                        </div>
                      </div>
                    );
                  })()}
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
