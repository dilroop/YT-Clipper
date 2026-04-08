import React, { useState } from 'react';
import type { HomeState } from '../HomeIntents';

interface Props {
  state: HomeState;
  intents: Record<string, any>;
}

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
    <div className="workflow-buttons" style={{ display: 'flex', gap: '8px', width: '100%' }}>
      <button
        className="workflow-btn auto-btn"
        style={{ flex: 1, padding: '12px 4px', fontSize: '14px', margin: 0 }}
        onClick={() => intents.processVideo()}
        disabled={!state.url}
      >
        <span style={{ fontSize: '20px', display: 'block' }}>🤖</span> Auto Create
      </button>
      <button
        className="workflow-btn manual-btn"
        style={{ flex: 1, padding: '12px 4px', fontSize: '14px', margin: 0 }}
        onClick={() => intents.analyzeVideo(false)}
        disabled={!state.url}
      >
        <span style={{ fontSize: '20px', display: 'block' }}>🔨</span> Manual (AI)
      </button>
      <button
        className="workflow-btn skip-btn"
        style={{ flex: 1, padding: '12px 4px', fontSize: '14px', margin: 0, background: '#6366f1', color: 'white', border: 'none', borderRadius: '12px', cursor: 'pointer', fontWeight: 'bold' }}
        onClick={() => intents.analyzeVideo(true)}
        disabled={!state.url}
      >
        <span style={{ fontSize: '20px', display: 'block' }}>✂️</span> Custom
      </button>
    </div>
  </div>
);


export const FormatSelector: React.FC<Props> = ({ state, intents }) => (
  <div className="option-card option-card-full">
    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
      <h3 style={{ margin: 0 }}>Reels Format:</h3>
      <label className="toggle-label" style={{ margin: 0 }}>
        <input type="checkbox" checked={state.burnCaptions} onChange={e => intents.toggleCaptions(e.target.checked)} />
        <span className="toggle-slider"></span>
        <span className="toggle-text">Burn Captions</span>
      </label>
    </div>
    <div className="format-buttons-multi">
      {[
        { key: 'vertical_9x16', label: 'Vertical', svg: <svg width="40" height="60" viewBox="0 0 40 60" fill="none"><rect x="2" y="2" width="36" height="56" stroke="currentColor" strokeWidth="3" rx="4"/><text x="20" y="35" textAnchor="middle" fill="currentColor" fontSize="10" fontWeight="bold">9:16</text></svg> },
        { 
          key: 'stacked_photo', 
          label: 'Photo', 
          svg: <svg width="48" height="48" viewBox="0 0 48 48" fill="none"><rect x="4" y="4" width="40" height="40" stroke="currentColor" strokeWidth="2.5" rx="8"/><text x="24" y="30" textAnchor="middle" fill="currentColor" fontSize="16" fontWeight="bold">AI</text></svg>,
          hasPosition: true 
        },
        { 
          key: 'stacked_video', 
          label: 'Video', 
          svg: <svg width="48" height="48" viewBox="0 0 48 48" fill="none"><rect x="4" y="4" width="40" height="40" stroke="currentColor" strokeWidth="2.5" rx="8"/><path d="M19 16 L19 32 L33 24 Z" fill="currentColor"/></svg>,
          hasPosition: true
        },
        { key: 'original', label: 'Original', svg: <svg width="60" height="40" viewBox="0 0 60 40" fill="none"><rect x="2" y="2" width="56" height="36" stroke="currentColor" strokeWidth="3" rx="4"/><text x="30" y="25" textAnchor="middle" fill="currentColor" fontSize="9" fontWeight="bold">16:9</text></svg> },
      ].map(({ key, label, svg, hasPosition }) => (
        <div key={key} className={`format-btn-container ${state.selectedFormat === key ? 'active' : ''}`}>
          <button
            className="format-btn-icon"
            onClick={() => intents.updateFormat(key)}
          >
            <div className="format-icon">{svg}</div>
            <span className="format-label">{label}</span>
          </button>
          
          {hasPosition && state.selectedFormat === key && (
             <div className="position-toggle-overlay">
               <button 
                 className={`pos-arrow ${state.aiContentPosition === 'top' ? 'active' : ''}`}
                 onClick={(e) => { e.stopPropagation(); intents.updatePosition('top'); }}
                 title="AI content on top"
               >
                 <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M18 15l-6-6-6 6"/></svg>
               </button>
               <button 
                 className={`pos-arrow ${state.aiContentPosition === 'bottom' ? 'active' : ''}`}
                 onClick={(e) => { e.stopPropagation(); intents.updatePosition('bottom'); }}
                 title="AI content on bottom"
               >
                 <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M6 9l6 6 6-6"/></svg>
               </button>
             </div>
          )}

          {hasPosition && state.selectedFormat === key && (
            <div className="upload-toggle-overlay" onClick={(e) => e.stopPropagation()}>
              <label 
                className={`upload-btn ${state.aiContentFile ? 'has-file' : ''}`} 
                title={state.aiContentFile ? `Selected: ${state.aiContentFile.name}` : "Upload Custom AI Content"}
              >
                <input 
                  type="file" 
                  accept="video/*,image/*" 
                  style={{ display: 'none' }}
                  onChange={(e) => {
                    const file = e.target.files?.[0] || null;
                    if (intents.updateAiContentFile) {
                      intents.updateAiContentFile(file);
                    }
                  }}
                />
                <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"></path>
                  <line x1="12" y1="11" x2="12" y2="17"></line>
                  <line x1="9" y1="14" x2="15" y2="14"></line>
                </svg>
              </label>
            </div>
          )}
        </div>
      ))}
    </div>
  </div>
);

export const StrategySelector: React.FC<Props> = ({ state, intents }) => {
  const [showAdvanced, setShowAdvanced] = useState(!!state.extraContext);
  return (
    <div className="option-card option-card-full">
      <div className="strategy-header">
        <h3>AI Strategy:</h3>
        {/* Segmented provider control — inline with label */}
        <div className="ai-segmented-control">
          {(['openai', 'deepseek'] as const).map(key => (
            <button
              key={key}
              className={`ai-segment ${state.aiProvider === key ? 'active' : ''}`}
              data-provider={key}
              onClick={() => intents.updateAiProvider(key)}
              title={`Use ${key === 'openai' ? 'OpenAI' : 'DeepSeek'}`}
            >
              {key === 'openai' ? '🧠' : '🔮'}{' '}
              {key === 'openai' ? 'OpenAI' : 'DeepSeek'}
            </button>
          ))}
        </div>
        <div className="extra-context-toggle" onClick={() => setShowAdvanced(v => !v)}>
          <span className="toggle-icon">{showAdvanced ? '−' : '＋'}</span> Advanced
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
