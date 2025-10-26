import { fireEvent, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { vi } from 'vitest';
import AudioPlayer, { AudioFile } from '../AudioPlayer';

describe('AudioPlayer', () => {
  it('shows loading message until tracks are available', () => {
    render(<AudioPlayer files={[]} activeId={null} onSelectFile={() => {}} />);

    expect(screen.getByRole('status')).toHaveTextContent('Waiting for audio files');
  });

  it('renders the active track and notifies when a selection changes', async () => {
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
    const onSelect = vi.fn();

    const onEnded = vi.fn();

    const { rerender } = render(
      <AudioPlayer
        files={[intro]}
        activeId={intro.id}
        onSelectFile={onSelect}
        autoPlay
        onPlaybackEnded={onEnded}
      />,
    );

    expect(screen.getByRole('button', { name: 'Introduction' })).toHaveAttribute('aria-pressed', 'true');
    expect(screen.getByTestId('audio-player')).toHaveAttribute('src', intro.url);

    rerender(
      <AudioPlayer
        files={[intro, chapter]}
        activeId={intro.id}
        onSelectFile={onSelect}
        autoPlay
        onPlaybackEnded={onEnded}
      />,
    );

    expect(screen.getByRole('button', { name: 'Introduction' })).toHaveAttribute('aria-pressed', 'true');
    expect(screen.getByTestId('audio-player')).toHaveAttribute('src', intro.url);

    await user.click(screen.getByRole('button', { name: 'Chapter 1' }));

    expect(onSelect).toHaveBeenCalledWith('chapter-1');

    rerender(
      <AudioPlayer
        files={[chapter]}
        activeId={chapter.id}
        onSelectFile={onSelect}
        autoPlay
        onPlaybackEnded={onEnded}
      />,
    );

    expect(screen.getByRole('button', { name: 'Chapter 1' })).toHaveAttribute('aria-pressed', 'true');
    expect(screen.getByTestId('audio-player')).toHaveAttribute('src', chapter.url);

    fireEvent.ended(screen.getByTestId('audio-player'));

    expect(onEnded).toHaveBeenCalledTimes(1);
  });
});
