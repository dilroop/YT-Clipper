import type { HomeState } from '../HomeIntents';

interface Props {
  state: HomeState;
  intents: Record<string, any>;
}

export const ProgressSection: React.FC<Props> = ({ state, intents }) => {
  const p = state.progress;
  const percent = p ? p.percent : 0;
  const stage = p?.stage || '';
  const isActuallyClipping = stage === 'clipping' || stage === 'organizing' || stage === 'complete';
  const isActive = (stageName: string) => p?.stage === stageName;

  return (
    <div className="progress-section">
      <h3>{isActuallyClipping ? 'Creating Clips...' : (state.generationMode === 'manual' ? 'Analyzing Video...' : 'Creating Clips...')}</h3>
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
