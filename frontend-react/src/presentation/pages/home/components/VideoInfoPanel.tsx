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
