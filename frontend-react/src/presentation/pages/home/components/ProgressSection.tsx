import type { HomeState } from '../HomeIntents';

interface Props {
  state: HomeState;
  intents: Record<string, any>;
}

const STAGES = [
  { id: 'downloading', icon: '📥', name: 'Downloading Video' },
  { id: 'transcribing', icon: '🎤', name: 'Transcribing Audio' },
  { id: 'analyzing', icon: '🤖', name: 'AI Analysis' },
  { id: 'clipping', icon: '✂️', name: 'Creating Clips' },
  { id: 'organizing', icon: '📁', name: 'Organizing Files' },
];

export const ProgressSection: React.FC<Props> = ({ state, intents }) => {
  const p = state.progress;
  const percent = p ? p.percent : 0;
  const currentStage = p?.stage || '';
  const isActuallyClipping = currentStage === 'clipping' || currentStage === 'organizing' || currentStage === 'complete';
  const activeIdx = currentStage === 'complete' ? STAGES.length : STAGES.findIndex(s => s.id === currentStage);

  return (
    <div className="progress-section">
      <h3>{isActuallyClipping ? 'Creating Clips...' : (state.generationMode === 'manual' ? 'Analyzing Video...' : 'Creating Clips...')}</h3>
      <div className="progress-bar">
        <div className="progress-fill" style={{ width: `${percent}%` }}></div>
        <span className="progress-percent">{Math.round(percent)}%</span>
      </div>
      <div className="progress-stages">
        {STAGES.map((stage, idx) => {
          const isDone = activeIdx > idx;
          const isCurrentlyActive = currentStage === stage.id;
          return (
            <div key={stage.id} className={`progress-stage ${isCurrentlyActive ? 'active' : ''} ${isDone ? 'done' : ''}`}>
              <div className="stage-header">
                <span className="stage-icon">{isDone ? '✅' : stage.icon}</span>
                <span className="stage-name">{stage.name}</span>
                <span className={`stage-status ${isDone ? 'stage-done' : ''}`}>
                  {isCurrentlyActive ? (p?.message ?? 'In progress...') : isDone ? 'Done' : 'Waiting...'}
                </span>
              </div>
            </div>
          );
        })}
      </div>
      <button className="cancel-btn" onClick={() => intents.resetToVideoInfo()}>Cancel</button>
    </div>
  );
};
