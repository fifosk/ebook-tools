import { render, screen } from '@testing-library/react';
import VideoPlayer, { type VideoFile } from '../VideoPlayer';

describe('VideoPlayer', () => {
  it('shows loading message when fetching new videos', () => {
    render(<VideoPlayer file={null} isLoading />);

    expect(screen.getByRole('status')).toHaveTextContent('Loading video');
  });

  it('renders the active video when available', () => {
    const trailer: VideoFile = {
      id: 'trailer',
      name: 'Trailer',
      url: 'https://example.com/video/trailer.mp4',
      poster: 'https://example.com/video/trailer.jpg'
    };

    render(<VideoPlayer file={trailer} />);

    expect(screen.getByTestId('video-player')).toHaveAttribute('src', trailer.url);
    expect(screen.getByText('Trailer')).toBeInTheDocument();
  });

  it('shows waiting message when there is nothing to play', () => {
    render(<VideoPlayer file={null} />);

    expect(screen.getByRole('status')).toHaveTextContent('Waiting for video files');
  });
});
