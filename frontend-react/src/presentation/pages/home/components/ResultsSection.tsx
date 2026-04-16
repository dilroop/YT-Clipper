import type { HomeState } from '../HomeIntents';

interface Props {
  state: HomeState;
  intents: Record<string, any>;
}

export const ResultsSection: React.FC<Props> = ({ intents }) => (
  <div className="results-section">
    <h3>✨ Clips Ready!</h3>
    <p style={{ color: 'var(--text-secondary)' }}>Your clips have been generated and saved successfully.</p>
    <div style={{ marginTop: '20px', display: 'flex', gap: '10px' }}>
      <button className="workflow-btn auto-btn" onClick={() => window.location.href = '/gallery'}>Open Gallery</button>
      <button className="workflow-btn manual-btn" onClick={() => intents.resetToVideoInfo()}>Create More</button>
    </div>
  </div>
);
