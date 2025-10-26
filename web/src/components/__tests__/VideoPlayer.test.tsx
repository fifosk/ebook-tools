import { fireEvent, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { vi } from 'vitest';
import VideoPlayer, { VideoFile } from '../VideoPlayer';

describe('VideoPlayer', () => {
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

    fireEvent.ended(screen.getByTestId('video-player'));

    expect(onEnded).toHaveBeenCalledTimes(1);
  });
});
