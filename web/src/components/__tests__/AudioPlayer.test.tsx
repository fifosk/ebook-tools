import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import AudioPlayer, { AudioFile } from '../AudioPlayer';

describe('AudioPlayer', () => {
  it('shows loading message until tracks are available', () => {
    render(<AudioPlayer files={[]} />);

    expect(screen.getByRole('status')).toHaveTextContent('Waiting for audio files');
  });

  it('keeps the selected track during progressive updates and switches when removed', async () => {
    const user = userEvent.setup();
    const intro: AudioFile = {
      id: 'intro',
      name: 'Introduction',
      url: 'https://example.com/audio/intro.mp3'
    };
    const chapter: AudioFile = {
      id: 'chapter-1',
      name: 'Chapter 1',
      url: 'https://example.com/audio/chapter-1.mp3'
    };

    const { rerender } = render(<AudioPlayer files={[intro]} />);

    expect(screen.getByRole('button', { name: 'Introduction' })).toHaveAttribute('aria-pressed', 'true');
    expect(screen.getByTestId('audio-player')).toHaveAttribute('src', intro.url);

    rerender(<AudioPlayer files={[intro, chapter]} />);

    expect(screen.getByRole('button', { name: 'Introduction' })).toHaveAttribute('aria-pressed', 'true');
    expect(screen.getByTestId('audio-player')).toHaveAttribute('src', intro.url);

    await user.click(screen.getByRole('button', { name: 'Chapter 1' }));

    expect(screen.getByRole('button', { name: 'Chapter 1' })).toHaveAttribute('aria-pressed', 'true');
    expect(screen.getByTestId('audio-player')).toHaveAttribute('src', chapter.url);

    rerender(<AudioPlayer files={[chapter]} />);

    expect(screen.getByRole('button', { name: 'Chapter 1' })).toHaveAttribute('aria-pressed', 'true');
    expect(screen.getByTestId('audio-player')).toHaveAttribute('src', chapter.url);
  });
});
