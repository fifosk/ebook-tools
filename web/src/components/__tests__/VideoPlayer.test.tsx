import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { useState } from 'react';
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

  it('restores fullscreen when selecting a new video while fullscreen is active', async () => {
    const user = userEvent.setup();
    const files: VideoFile[] = [
      {
        id: 'intro',
        name: 'Intro',
        url: 'https://example.com/video/intro.mp4'
      },
      {
        id: 'chapter-1',
        name: 'Chapter 1',
        url: 'https://example.com/video/chapter-1.mp4'
      }
    ];

    const originalRequestFullscreen = window.HTMLVideoElement.prototype.requestFullscreen;
    const requestFullscreenMock = vi.fn(() => Promise.resolve());
    Object.defineProperty(window.HTMLVideoElement.prototype, 'requestFullscreen', {
      configurable: true,
      writable: true,
      value: requestFullscreenMock
    });

    let fullscreenElement: Element | null = null;
    Object.defineProperty(document, 'fullscreenElement', {
      configurable: true,
      get: () => fullscreenElement
    });

    const Harness = () => {
      const [activeId, setActiveId] = useState(files[0].id);
      return (
        <VideoPlayer files={files} activeId={activeId} onSelectFile={setActiveId} autoPlay />
      );
    };

    render(<Harness />);

    const videoElement = screen.getByTestId('video-player');
    fullscreenElement = videoElement;

    await act(async () => {
      await user.click(screen.getByRole('button', { name: 'Chapter 1' }));
    });

    fullscreenElement = null;

    await waitFor(() => {
      expect(requestFullscreenMock).toHaveBeenCalled();
    });

    if (originalRequestFullscreen) {
      Object.defineProperty(window.HTMLVideoElement.prototype, 'requestFullscreen', {
        configurable: true,
        writable: true,
        value: originalRequestFullscreen
      });
    } else {
      delete (window.HTMLVideoElement.prototype as { requestFullscreen?: typeof requestFullscreenMock }).requestFullscreen;
    }

    delete (document as { fullscreenElement?: Element | null }).fullscreenElement;
  });

  it('restores fullscreen when advancing after playback ends', async () => {
    const files: VideoFile[] = [
      {
        id: 'part-1',
        name: 'Part 1',
        url: 'https://example.com/video/part-1.mp4'
      },
      {
        id: 'part-2',
        name: 'Part 2',
        url: 'https://example.com/video/part-2.mp4'
      }
    ];

    const originalRequestFullscreen = window.HTMLVideoElement.prototype.requestFullscreen;
    const requestFullscreenMock = vi.fn(() => Promise.resolve());
    Object.defineProperty(window.HTMLVideoElement.prototype, 'requestFullscreen', {
      configurable: true,
      writable: true,
      value: requestFullscreenMock
    });

    let fullscreenElement: Element | null = null;
    Object.defineProperty(document, 'fullscreenElement', {
      configurable: true,
      get: () => fullscreenElement
    });

    const Harness = () => {
      const [index, setIndex] = useState(0);

      return (
        <VideoPlayer
          files={files}
          activeId={files[index]?.id ?? null}
          onSelectFile={(fileId) => setIndex(files.findIndex((file) => file.id === fileId))}
          autoPlay
          onPlaybackEnded={() => setIndex((value) => Math.min(value + 1, files.length - 1))}
        />
      );
    };

    render(<Harness />);

    const videoElement = screen.getByTestId('video-player');
    fullscreenElement = videoElement;

    await act(async () => {
      fireEvent.ended(videoElement);
    });

    fullscreenElement = null;

    await waitFor(() => {
      expect(requestFullscreenMock).toHaveBeenCalled();
    });

    if (originalRequestFullscreen) {
      Object.defineProperty(window.HTMLVideoElement.prototype, 'requestFullscreen', {
        configurable: true,
        writable: true,
        value: originalRequestFullscreen
      });
    } else {
      delete (window.HTMLVideoElement.prototype as { requestFullscreen?: typeof requestFullscreenMock }).requestFullscreen;
    }

    delete (document as { fullscreenElement?: Element | null }).fullscreenElement;
  });
});
