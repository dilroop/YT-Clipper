import type { HomeState } from '../HomeIntents';

interface Props {
  state: HomeState;
  intents: Record<string, any>;
}

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
