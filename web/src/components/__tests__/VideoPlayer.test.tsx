import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { vi } from 'vitest';
import type { Mock } from 'vitest';
import VideoPlayer, { VideoFile } from '../VideoPlayer';

describe('VideoPlayer', () => {
  let playSpy: ReturnType<typeof vi.spyOn>;
  const fullscreenPrototype = HTMLElement.prototype as HTMLElement & {
    requestFullscreen?: () => Promise<void>;
  };
  const documentPrototype = Document.prototype as Document & {
    exitFullscreen?: () => Promise<void>;
  };
  const originalRequestFullscreen = fullscreenPrototype.requestFullscreen;
  const originalExitFullscreen = documentPrototype.exitFullscreen;
  const originalFullscreenDescriptor = Object.getOwnPropertyDescriptor(document, 'fullscreenElement');
  let requestFullscreenMock: Mock<[], Promise<void>>;
  let exitFullscreenMock: Mock<[], Promise<void>>;
  let fullscreenElementSlot: Element | null = null;

  beforeEach(() => {
    playSpy = vi.spyOn(window.HTMLMediaElement.prototype, 'play').mockImplementation(() => Promise.resolve());
    requestFullscreenMock = vi.fn<[], Promise<void>>().mockImplementation(function (this: HTMLElement) {
      fullscreenElementSlot = this;
      return Promise.resolve();
    });
    exitFullscreenMock = vi.fn<[], Promise<void>>().mockImplementation(() => {
      fullscreenElementSlot = null;
      return Promise.resolve();
    });
    fullscreenPrototype.requestFullscreen = requestFullscreenMock as typeof fullscreenPrototype.requestFullscreen;
    documentPrototype.exitFullscreen = exitFullscreenMock as typeof documentPrototype.exitFullscreen;
    Object.defineProperty(document, 'fullscreenElement', {
      configurable: true,
      get() {
        return fullscreenElementSlot;
      },
      set(value) {
        fullscreenElementSlot = value as Element | null;
      },
    });
  });

  afterEach(() => {
    playSpy.mockRestore();
    if (originalRequestFullscreen) {
      fullscreenPrototype.requestFullscreen = originalRequestFullscreen;
    } else {
      Reflect.deleteProperty(fullscreenPrototype, 'requestFullscreen');
    }
    if (originalExitFullscreen) {
      documentPrototype.exitFullscreen = originalExitFullscreen;
    } else {
      Reflect.deleteProperty(documentPrototype, 'exitFullscreen');
    }
    if (originalFullscreenDescriptor) {
      Object.defineProperty(document, 'fullscreenElement', originalFullscreenDescriptor);
    } else {
      Reflect.deleteProperty(document as Document & { fullscreenElement?: Element | null }, 'fullscreenElement');
    }
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

    expect(screen.getByRole('combobox', { name: 'Video' })).toHaveValue('trailer');
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

    expect(screen.getByRole('combobox', { name: 'Video' })).toHaveValue('trailer');
    expect(screen.getByTestId('video-player')).toHaveAttribute('src', trailer.url);
    expect(playSpy).toHaveBeenCalled();

    await user.selectOptions(screen.getByRole('combobox', { name: 'Video' }), 'full');

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

    expect(screen.getByRole('combobox', { name: 'Video' })).toHaveValue('full');
    expect(screen.getByTestId('video-player')).toHaveAttribute('src', fullVideo.url);
    expect(playSpy.mock.calls.length).toBeGreaterThanOrEqual(2);

    fireEvent.ended(screen.getByTestId('video-player'));

    expect(onEnded).toHaveBeenCalledTimes(1);
  });

  it('requests immersive exit when backdrop or Escape is used', async () => {
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

    await user.click(screen.getByRole('button', { name: /Exit immersive mode/i }));
    expect(onExit).toHaveBeenCalledTimes(1);

    fireEvent.keyDown(window, { key: 'Escape' });
    expect(onExit).toHaveBeenCalledTimes(2);
  });

  it('requests fullscreen while immersive mode is active and exits when disabled', async () => {
    const sample: VideoFile = {
      id: 'sample',
      name: 'Sample',
      url: 'https://example.com/video/sample.mp4'
    };

    const { rerender } = render(
      <VideoPlayer
        files={[sample]}
        activeId={sample.id}
        onSelectFile={() => {}}
        isTheaterMode
      />,
    );

    await waitFor(() => expect(requestFullscreenMock).toHaveBeenCalled());
    const fullscreenTarget = screen.getByTestId('video-player').closest('.video-player__stage');
    expect(document.fullscreenElement).toBe(fullscreenTarget);

    rerender(
      <VideoPlayer
        files={[sample]}
        activeId={sample.id}
        onSelectFile={() => {}}
        isTheaterMode={false}
      />,
    );

    await waitFor(() => expect(exitFullscreenMock).toHaveBeenCalled());
  });

  it('invokes exit handler if fullscreen is closed externally', () => {
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

    const element = screen.getByTestId('video-player');
    fullscreenElementSlot = element;
    fullscreenElementSlot = null;
    document.dispatchEvent(new Event('fullscreenchange'));

    expect(onExit).toHaveBeenCalledTimes(1);
  });
});
