import React from 'react';
import { useHomeMVI } from './useHomeMVI';
import {
  Header,
  VideoInput,
  VideoInfoPanel,
  ProgressSection,
  ClipSelectionSection,
  ResultsSection,
} from './components/HomeComponents';

export const HomeView: React.FC = () => {
  const { state, intents } = useHomeMVI();

  return (
    <div className="container">
      <Header state={state} intents={intents} />

      <main>
        {/* URL input is ALWAYS visible */}
        <VideoInput state={state} intents={intents} />

        {/* One panel visible at a time below the input */}
        {state.screen === 'videoInfo'      && <VideoInfoPanel state={state} intents={intents} />}
        {state.screen === 'generating'     && <ProgressSection state={state} intents={intents} />}
        {state.screen === 'aiSuggestions'  && <ClipSelectionSection state={state} intents={intents} />}
        {state.screen === 'clipsReady'     && <ResultsSection state={state} intents={intents} />}
      </main>
    </div>
  );
};
