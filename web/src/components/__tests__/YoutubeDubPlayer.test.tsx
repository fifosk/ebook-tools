import { act, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { MyLinguistProvider } from '../../context/MyLinguistProvider';
import YoutubeDubPlayer from '../YoutubeDubPlayer';
import type { LiveMediaState } from '../../hooks/useLiveMedia';

vi.mock('../../api/client/resume', () => ({
  fetchResumePosition: vi.fn().mockResolvedValue({ entry: null }),
  saveResumePosition: vi.fn().mockResolvedValue({ ok: true }),
}));

vi.mock('../VideoPlayer', async () => {
  const { SleepTimerControl } = await vi.importActual<typeof import('../SleepTimerControl')>('../SleepTimerControl');
  return {
    default: ({
      activeId,
      onPlaybackStateChange,
    }: {
      activeId: string | null;
      onPlaybackStateChange?: (state: 'playing' | 'paused') => void;
    }) => (
      <div data-testid="video-player-mock">
        <button type="button" onClick={() => onPlaybackStateChange?.('playing')}>
          Mark playing
        </button>
        <SleepTimerControl
          onExpire={() => onPlaybackStateChange?.('paused')}
          resetKey={activeId}
          className="video-player__sleep-timer"
        />
      </div>
    ),
  };
});

const media: LiveMediaState = {
  text: [],
  audio: [],
  video: [
    {
      type: 'video',
      name: 'Segment 1',
      url: 'https://media.example/video/segment-1.mp4',
      source: 'completed',
    },
  ],
};

function renderYoutubeDubPlayer(onPlaybackStateChange = vi.fn()) {
  render(
    <MyLinguistProvider>
      <YoutubeDubPlayer
        jobId="youtube-dub-job"
        media={media}
        mediaComplete
        isLoading={false}
        error={null}
        playerMode="export"
        onPlaybackStateChange={onPlaybackStateChange}
      />
    </MyLinguistProvider>,
  );
  return { onPlaybackStateChange };
}

describe('YoutubeDubPlayer', () => {
  beforeEach(() => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date('2026-06-25T20:00:00Z'));
  });

  afterEach(() => {
    vi.useRealTimers();
    window.localStorage.clear();
    window.sessionStorage.clear();
  });

  it('inherits the shared video sleep timer and pauses YouTube dub playback when it expires', async () => {
    const { onPlaybackStateChange } = renderYoutubeDubPlayer();

    expect(screen.getAllByRole('button', { name: /set sleep timer/i })).toHaveLength(1);

    act(() => {
      fireEvent.click(screen.getByRole('button', { name: /mark playing/i }));
    });
    expect(onPlaybackStateChange).toHaveBeenCalledWith(true);

    fireEvent.click(screen.getByRole('button', { name: /set sleep timer/i }));
    fireEvent.click(screen.getByRole('menuitem', { name: '5m' }));

    expect(screen.getByRole('button', { name: /5:00 remaining/i })).toBeInTheDocument();

    act(() => {
      vi.advanceTimersByTime(300_000);
    });

    expect(onPlaybackStateChange).toHaveBeenLastCalledWith(false);
    expect(screen.getByRole('button', { name: /set sleep timer/i })).toBeInTheDocument();
  });
});
