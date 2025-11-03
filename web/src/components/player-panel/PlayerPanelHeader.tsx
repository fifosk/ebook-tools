import { TabsList, TabsTrigger } from '../ui/Tabs';
import type { MediaCategory, NavigationIntent, TabDefinition } from './constants';
import type { InlineAudioOption } from './utils';

type PlayerPanelTabInfo = TabDefinition & { count: number };

interface NavigationState {
  first: boolean;
  previous: boolean;
  play: boolean;
  pause: boolean;
  next: boolean;
  last: boolean;
}

interface InlineAudioProps {
  visible: boolean;
  options: InlineAudioOption[];
  selection: string | null;
  onSelect: (url: string) => void;
  disableSelect: boolean;
}

interface ImmersiveToggleProps {
  visible: boolean;
  disabled: boolean;
  pressed: boolean;
  label: string;
  onToggle: () => void;
}

interface InteractiveFullscreenProps {
  visible: boolean;
  disabled: boolean;
  pressed: boolean;
  label: string;
  onToggle: () => void;
}

interface PlayerPanelHeaderProps {
  headingLabel: string;
  jobLabel: string;
  showCover: boolean;
  coverUrl: string;
  coverAltText: string;
  onCoverError?: () => void;
  selectedMediaType: MediaCategory;
  onNavigate: (intent: NavigationIntent) => void;
  onPlay: () => void;
  onPause: () => void;
  navigationState: NavigationState;
  tabs: PlayerPanelTabInfo[];
  inlineAudio?: InlineAudioProps;
  immersiveToggle?: ImmersiveToggleProps;
  interactiveFullscreen?: InteractiveFullscreenProps;
}

export function PlayerPanelHeader({
  headingLabel,
  jobLabel,
  showCover,
  coverUrl,
  coverAltText,
  onCoverError,
  selectedMediaType,
  onNavigate,
  onPlay,
  onPause,
  navigationState,
  tabs,
  inlineAudio,
  immersiveToggle,
  interactiveFullscreen,
}: PlayerPanelHeaderProps) {
  const showInlineAudio = inlineAudio?.visible && selectedMediaType === 'text';

  return (
    <header className="player-panel__header">
      <div className="player-panel__heading">
        {showCover ? (
          <div className="player-panel__cover" aria-hidden={false}>
            <img
              src={coverUrl}
              alt={coverAltText}
              data-testid="player-cover-image"
              onError={onCoverError}
            />
          </div>
        ) : null}
        <div className="player-panel__heading-text">
          <h2>{headingLabel}</h2>
          <span className="player-panel__job">{jobLabel}</span>
        </div>
      </div>
      <div className="player-panel__tabs-row">
        <div className="player-panel__navigation-group">
          <div className="player-panel__navigation" role="group" aria-label="Navigate media items">
            <button
              type="button"
              className="player-panel__nav-button"
              onClick={() => onNavigate('first')}
              disabled={navigationState.first}
              aria-label="Go to first item"
            >
              <span aria-hidden="true">⏮</span>
            </button>
            <button
              type="button"
              className="player-panel__nav-button"
              onClick={() => onNavigate('previous')}
              disabled={navigationState.previous}
              aria-label="Go to previous item"
            >
              <span aria-hidden="true">⏪</span>
            </button>
            <button
              type="button"
              className="player-panel__nav-button"
              onClick={onPlay}
              disabled={navigationState.play}
              aria-label="Play playback"
            >
              <span aria-hidden="true">▶</span>
            </button>
            <button
              type="button"
              className="player-panel__nav-button"
              onClick={onPause}
              disabled={navigationState.pause}
              aria-label="Pause playback"
            >
              <span aria-hidden="true">⏸</span>
            </button>
            <button
              type="button"
              className="player-panel__nav-button"
              onClick={() => onNavigate('next')}
              disabled={navigationState.next}
              aria-label="Go to next item"
            >
              <span aria-hidden="true">⏩</span>
            </button>
            <button
              type="button"
              className="player-panel__nav-button"
              onClick={() => onNavigate('last')}
              disabled={navigationState.last}
              aria-label="Go to last item"
            >
              <span aria-hidden="true">⏭</span>
            </button>
            {interactiveFullscreen?.visible ? (
              <button
                type="button"
                className="player-panel__nav-button"
                onClick={interactiveFullscreen.onToggle}
                disabled={interactiveFullscreen.disabled}
                aria-pressed={interactiveFullscreen.pressed}
                aria-label={interactiveFullscreen.label}
              >
                <span aria-hidden="true">⛶</span>
              </button>
            ) : null}
          </div>
          {showInlineAudio && inlineAudio ? (
            <div className="player-panel__inline-audio" role="group" aria-label="Synchronized audio">
              <label className="player-panel__inline-audio-label" htmlFor="player-panel-inline-audio">
                Synchronized audio
              </label>
              <select
                id="player-panel-inline-audio"
                value={inlineAudio.selection ?? inlineAudio.options[0]?.url ?? ''}
                onChange={(event) => inlineAudio.onSelect(event.target.value)}
                disabled={inlineAudio.disableSelect}
              >
                {inlineAudio.options.map((option) => (
                  <option key={option.url} value={option.url}>
                    {option.label}
                  </option>
                ))}
              </select>
            </div>
          ) : null}
        </div>
        {immersiveToggle?.visible ? (
          <button
            type="button"
            className="player-panel__immersive-toggle"
            onClick={immersiveToggle.onToggle}
            disabled={immersiveToggle.disabled}
            aria-pressed={immersiveToggle.pressed}
            aria-label={immersiveToggle.label}
            data-testid="player-panel-immersive-toggle"
          >
            {immersiveToggle.label}
          </button>
        ) : null}
        <TabsList className="player-panel__tabs" aria-label="Media categories">
          {tabs.map((tab) => (
            <TabsTrigger
              key={tab.key}
              className="player-panel__tab"
              value={tab.key}
              data-testid={`media-tab-${tab.key}`}
            >
              {tab.label} ({tab.count})
            </TabsTrigger>
          ))}
        </TabsList>
      </div>
    </header>
  );
}
