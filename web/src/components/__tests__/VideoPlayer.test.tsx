import { fireEvent, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { vi } from 'vitest';
import VideoPlayer, { VideoFile } from '../VideoPlayer';

describe('VideoPlayer', () => {
  let playSpy: ReturnType<typeof vi.spyOn>;

  beforeEach(() => {
    playSpy = vi.spyOn(window.HTMLMediaElement.prototype, 'play').mockImplementation(() => Promise.resolve());
  });

  afterEach(() => {
    playSpy.mockRestore();
  });

  it('shows loading message until videos are available', () => {
    render(<VideoPlayer files={[]} activeId={null} onSelectFile={() => {}} />);

    expect(screen.getByRole('status')).toHaveTextContent('Waiting for video files');
  });

  it('renders the active video and notifies when a selection changes', async () => {
    const user = userEvent.setup();
    const trailer: VideoFile = {
      id: 'trailer',
      name: 'Trailer',
      url: 'https://example.com/video/trailer.mp4',
      poster: 'https://example.com/video/trailer.jpg'
    };
    const fullVideo: VideoFile = {
      id: 'full',
      name: 'Full Video',
      url: 'https://example.com/video/full.mp4'
    };
    const onSelect = vi.fn();

    const onEnded = vi.fn();

    const { rerender } = render(
      <VideoPlayer
        files={[trailer]}
        activeId={trailer.id}
        onSelectFile={onSelect}
        autoPlay
        onPlaybackEnded={onEnded}
      />,
    );

    expect(screen.getByRole('button', { name: 'Trailer' })).toHaveAttribute('aria-pressed', 'true');
    expect(screen.getByTestId('video-player')).toHaveAttribute('src', trailer.url);

    rerender(
      <VideoPlayer
        files={[trailer, fullVideo]}
        activeId={trailer.id}
        onSelectFile={onSelect}
        autoPlay
        onPlaybackEnded={onEnded}
      />,
    );

    expect(screen.getByRole('button', { name: 'Trailer' })).toHaveAttribute('aria-pressed', 'true');
    expect(screen.getByTestId('video-player')).toHaveAttribute('src', trailer.url);
    expect(playSpy).toHaveBeenCalled();

    await user.click(screen.getByRole('button', { name: 'Full Video' }));

    expect(onSelect).toHaveBeenCalledWith('full');

    rerender(
      <VideoPlayer
        files={[fullVideo]}
        activeId={fullVideo.id}
        onSelectFile={onSelect}
        autoPlay
        onPlaybackEnded={onEnded}
      />,
    );

    expect(screen.getByRole('button', { name: 'Full Video' })).toHaveAttribute('aria-pressed', 'true');
    expect(screen.getByTestId('video-player')).toHaveAttribute('src', fullVideo.url);
    expect(playSpy.mock.calls.length).toBeGreaterThanOrEqual(2);

    fireEvent.ended(screen.getByTestId('video-player'));

    expect(onEnded).toHaveBeenCalledTimes(1);
  });

  it('requests theater exit when backdrop or Escape is used', async () => {
    const user = userEvent.setup();
    const sample: VideoFile = {
      id: 'sample',
      name: 'Sample',
      url: 'https://example.com/video/sample.mp4'
    };
    const onExit = vi.fn();

    render(
      <VideoPlayer
        files={[sample]}
        activeId={sample.id}
        onSelectFile={() => {}}
        isTheaterMode
        onExitTheaterMode={onExit}
      />,
    );

    await user.click(screen.getByRole('button', { name: /Exit theater mode/i }));
    expect(onExit).toHaveBeenCalledTimes(1);

    fireEvent.keyDown(window, { key: 'Escape' });
    expect(onExit).toHaveBeenCalledTimes(2);
  });
});
