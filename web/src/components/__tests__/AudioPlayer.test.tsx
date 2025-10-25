import { render, screen } from '@testing-library/react';
import AudioPlayer, { type AudioFile } from '../AudioPlayer';

describe('AudioPlayer', () => {
  it('shows loading message while preparing content', () => {
    render(<AudioPlayer file={null} isLoading />);

    expect(screen.getByRole('status')).toHaveTextContent('Loading audio');
  });

  it('renders an audio element when a file is provided', () => {
    const file: AudioFile = {
      id: 'intro',
      name: 'Introduction',
      url: 'https://example.com/audio/intro.mp3'
    };

    render(<AudioPlayer file={file} />);

    expect(screen.getByTestId('audio-player')).toHaveAttribute('src', file.url);
    expect(screen.getByText('Introduction')).toBeInTheDocument();
  });

  it('shows waiting message when no file has been selected yet', () => {
    render(<AudioPlayer file={null} />);

    expect(screen.getByRole('status')).toHaveTextContent('Waiting for audio files');
  });
});
