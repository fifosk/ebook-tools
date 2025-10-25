import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import VideoPlayer, { VideoFile } from '../VideoPlayer';

describe('VideoPlayer', () => {
  it('shows loading message until videos are available', () => {
    render(<VideoPlayer files={[]} />);

    expect(screen.getByRole('status')).toHaveTextContent('Waiting for video files');
  });

  it('updates the active video as new files arrive', async () => {
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

    const { rerender } = render(<VideoPlayer files={[trailer]} />);

    expect(screen.getByRole('button', { name: 'Trailer' })).toHaveAttribute('aria-pressed', 'true');
    expect(screen.getByTestId('video-player')).toHaveAttribute('src', trailer.url);

    rerender(<VideoPlayer files={[trailer, fullVideo]} />);

    expect(screen.getByRole('button', { name: 'Trailer' })).toHaveAttribute('aria-pressed', 'true');
    expect(screen.getByTestId('video-player')).toHaveAttribute('src', trailer.url);

    await user.click(screen.getByRole('button', { name: 'Full Video' }));

    expect(screen.getByRole('button', { name: 'Full Video' })).toHaveAttribute('aria-pressed', 'true');
    expect(screen.getByTestId('video-player')).toHaveAttribute('src', fullVideo.url);

    rerender(<VideoPlayer files={[fullVideo]} />);

    expect(screen.getByRole('button', { name: 'Full Video' })).toHaveAttribute('aria-pressed', 'true');
    expect(screen.getByTestId('video-player')).toHaveAttribute('src', fullVideo.url);
  });
});
