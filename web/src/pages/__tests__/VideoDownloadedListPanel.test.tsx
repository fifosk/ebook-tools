import { fireEvent, render, screen, within } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import type {
  YoutubeInlineSubtitleStream,
  YoutubeNasSubtitle,
  YoutubeNasVideo
} from '../../api/dtos';
import VideoDownloadedListPanel from '../video-dubbing/VideoDownloadedListPanel';

function subtitle(overrides: Partial<YoutubeNasSubtitle> = {}): YoutubeNasSubtitle {
  return {
    path: '/videos/movie.en.srt',
    filename: 'movie.en.srt',
    language: 'en',
    format: 'srt',
    ...overrides
  };
}

function video(overrides: Partial<YoutubeNasVideo> = {}): YoutubeNasVideo {
  return {
    path: '/videos/movie.mkv',
    filename: 'movie.mkv',
    folder: '/videos',
    size_bytes: 2_097_152,
    modified_at: '2026-07-02T12:00:00Z',
    source: 'nas_video',
    linked_job_ids: [],
    subtitles: [subtitle()],
    ...overrides
  };
}

function stream(overrides: Partial<YoutubeInlineSubtitleStream> = {}): YoutubeInlineSubtitleStream {
  return {
    index: 2,
    position: 0,
    language: 'en',
    codec: 'subrip',
    title: 'English',
    can_extract: true,
    ...overrides
  };
}

function renderPanel(overrides: Partial<Parameters<typeof VideoDownloadedListPanel>[0]> = {}) {
  const activeVideo = video();
  const props: Parameters<typeof VideoDownloadedListPanel>[0] = {
    isLoading: false,
    videos: [
      activeVideo,
      video({
        path: '/videos/locked.mkv',
        filename: 'locked.mkv',
        source: 'youtube',
        linked_job_ids: ['job-1'],
        subtitles: []
      })
    ],
    selectedVideoPath: activeVideo.path,
    selectedSubtitlePath: activeVideo.subtitles[0].path,
    selectedVideo: activeVideo,
    playableSubtitles: [
      activeVideo.subtitles[0],
      subtitle({ path: '/videos/movie.nl.ass', filename: 'movie.nl.ass', language: 'nl', format: 'ass' })
    ],
    subtitleNotice: 'Using nearest subtitle.',
    canExtractEmbedded: true,
    isExtractingSubtitles: false,
    isLoadingStreams: false,
    isChoosingStreams: true,
    availableSubtitleStreams: [
      stream(),
      stream({ index: 3, language: null, codec: 'hdmv_pgs_subtitle', can_extract: false })
    ],
    selectedStreamLanguages: new Set(['en']),
    extractableStreams: [stream()],
    extractError: null,
    deletingSubtitlePath: null,
    deletingVideoPath: null,
    onSelectVideo: vi.fn(),
    onSelectSubtitle: vi.fn(),
    onDeleteVideo: vi.fn(),
    onDeleteSubtitle: vi.fn(),
    onExtractSubtitles: vi.fn(),
    onToggleSubtitleStream: vi.fn(),
    onConfirmSubtitleStreams: vi.fn(),
    onCancelStreamSelection: vi.fn(),
    onExtractAllStreams: vi.fn(),
    ...overrides
  };
  const view = render(<VideoDownloadedListPanel {...props} />);
  return { ...view, props };
}

describe('VideoDownloadedListPanel', () => {
  it('renders downloaded videos, subtitle selection, stream chooser, and routes actions', () => {
    const { props } = renderPanel();

    expect(screen.getByText('movie.mkv')).toBeInTheDocument();
    expect(screen.getAllByText('2.0 MiB').length).toBeGreaterThan(0);
    expect(screen.getByText('NAS')).toBeInTheDocument();
    expect(screen.getByText('Using nearest subtitle.')).toBeInTheDocument();
    expect(screen.getByLabelText('Subtitle selection')).toHaveTextContent('movie.en.srt');
    expect(screen.getByLabelText('Subtitle selection')).toHaveTextContent('movie.nl.ass');
    expect(screen.getByRole('button', { name: 'Linked jobs: job-1' })).toBeDisabled();

    fireEvent.click(screen.getByDisplayValue('/videos/locked.mkv'));
    fireEvent.click(screen.getAllByRole('button', { name: 'Inspect and extract subtitle streams from this video' })[0]);
    fireEvent.click(screen.getByDisplayValue('/videos/movie.nl.ass'));
    fireEvent.click(screen.getByRole('button', { name: 'Delete movie.en.srt' }));
    fireEvent.click(screen.getByRole('checkbox', { name: 'Extract English – English stream #2' }));
    fireEvent.click(screen.getByRole('button', { name: 'Extract selected tracks' }));
    fireEvent.click(screen.getByRole('button', { name: 'Cancel' }));
    fireEvent.click(screen.getByRole('button', { name: 'Extract all text tracks' }));

    expect(props.onSelectVideo).toHaveBeenCalledWith(props.videos[1]);
    expect(props.onExtractSubtitles).toHaveBeenCalledTimes(1);
    expect(props.onSelectSubtitle).toHaveBeenCalledWith('/videos/movie.nl.ass');
    expect(props.onDeleteSubtitle).toHaveBeenCalledWith(props.playableSubtitles[0]);
    expect(props.onToggleSubtitleStream).toHaveBeenCalledWith('en', false);
    expect(props.onConfirmSubtitleStreams).toHaveBeenCalledTimes(1);
    expect(props.onCancelStreamSelection).toHaveBeenCalledTimes(1);
    expect(props.onExtractAllStreams).toHaveBeenCalledTimes(1);
  });

  it('shows detached discovered selections and empty states', () => {
    const { rerender, props } = renderPanel({
      videos: [],
      selectedVideoPath: '/manual/remote/movie.mkv',
      selectedSubtitlePath: '/manual/remote/movie.fr.srt',
      selectedVideo: null,
      playableSubtitles: [],
      isChoosingStreams: false,
      extractableStreams: []
    });

    expect(screen.getByText('No downloaded videos found in this directory.')).toBeInTheDocument();
    expect(screen.getByLabelText('Selected discovered video path')).toHaveTextContent('movie.mkv');
    expect(screen.getByLabelText('Selected discovered video path')).toHaveTextContent('movie.fr.srt');

    rerender(<VideoDownloadedListPanel {...props} isLoading videos={[]} selectedVideoPath={null} selectedSubtitlePath={null} />);
    expect(screen.getByText('Loading videos…')).toBeInTheDocument();
  });
});
