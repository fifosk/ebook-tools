import {
  deleteYoutubeVideo,
  discoverAcquisitionCandidates,
  downloadYoutubeSubtitle,
  downloadYoutubeVideo,
  fetchAcquisitionProviders,
  fetchYoutubeLibrary,
  fetchYoutubeSubtitleTracks
} from '../../api/client';
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import YoutubeVideoPage from '../YoutubeVideoPage';

vi.mock('../../api/client', () => ({
  deleteYoutubeVideo: vi.fn(),
  discoverAcquisitionCandidates: vi.fn(),
  downloadYoutubeSubtitle: vi.fn(),
  downloadYoutubeVideo: vi.fn(),
  fetchAcquisitionProviders: vi.fn(),
  fetchYoutubeLibrary: vi.fn(),
  fetchYoutubeSubtitleTracks: vi.fn()
}));

const mockDeleteYoutubeVideo = vi.mocked(deleteYoutubeVideo);
const mockDiscoverAcquisitionCandidates = vi.mocked(discoverAcquisitionCandidates);
const mockDownloadYoutubeSubtitle = vi.mocked(downloadYoutubeSubtitle);
const mockDownloadYoutubeVideo = vi.mocked(downloadYoutubeVideo);
const mockFetchAcquisitionProviders = vi.mocked(fetchAcquisitionProviders);
const mockFetchYoutubeLibrary = vi.mocked(fetchYoutubeLibrary);
const mockFetchYoutubeSubtitleTracks = vi.mocked(fetchYoutubeSubtitleTracks);

describe('YoutubeVideoPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockDeleteYoutubeVideo.mockResolvedValue({ video_path: '', removed: [], missing: [] });
    mockDownloadYoutubeSubtitle.mockResolvedValue({ output_path: '/tmp/sub.srt', filename: 'sub.srt' });
    mockDownloadYoutubeVideo.mockResolvedValue({
      output_path: '/tmp/video.mp4',
      filename: 'video.mp4',
      folder: '/tmp'
    });
    mockFetchAcquisitionProviders.mockResolvedValue({
      providers: [
        {
          id: 'youtube_search',
          label: 'YouTube search',
          media_kinds: ['video'],
          capabilities: ['search', 'metadata'],
          status: 'available',
          configured: true,
          available: true,
          rights: ['unknown', 'restricted'],
          discovery_media_kinds: ['video'],
          default_eligible_media_kinds: ['video'],
          policy_notes: [],
          next_actions: ['search', 'inspect_url']
        }
      ],
      policy_notes: [],
      paths: {},
      default_provider_ids: {}
    });
    mockFetchYoutubeLibrary.mockResolvedValue({
      base_dir: '/Volumes/Data/Download/DStation',
      videos: []
    });
    mockFetchYoutubeSubtitleTracks.mockResolvedValue({
      video_id: 'abc123demo',
      title: 'Readable History Interview',
      tracks: [
        {
          language: 'en',
          kind: 'manual',
          name: 'English',
          formats: ['srt']
        }
      ],
      video_formats: [
        {
          format_id: '22',
          ext: 'mp4',
          resolution: '720p'
        }
      ]
    });
    mockDiscoverAcquisitionCandidates.mockResolvedValue({
      candidates: [
        {
          candidate_id: 'youtube_search:abc123demo',
          provider: 'youtube_search',
          media_kind: 'video',
          title: 'Readable History Interview',
          rights: 'unknown',
          capabilities: ['metadata', 'extract_subtitles'],
          candidate_token: 'candidate-token',
          contributors: ['History Channel'],
          source_url: 'https://www.youtube.com/watch?v=abc123demo',
          duration_seconds: 612,
          subtitles: [],
          metadata: {
            youtube_video_id: 'abc123demo'
          },
          requires_confirmation: true,
          policy_notes: []
        }
      ],
      policy_notes: [],
      providers_queried: ['youtube_search']
    });
  });

  it('searches YouTube discovery and reuses the selected URL for subtitle inspection', async () => {
    render(<YoutubeVideoPage />);

    await waitFor(() => expect(mockFetchYoutubeLibrary).toHaveBeenCalled());
    fireEvent.change(screen.getByLabelText(/YouTube discovery search/i), {
      target: { value: 'readable history' }
    });
    fireEvent.click(screen.getByRole('button', { name: /^Search$/i }));

    await waitFor(() =>
      expect(mockDiscoverAcquisitionCandidates).toHaveBeenCalledWith({
        mediaKind: 'video',
        provider: 'youtube_search',
        query: 'readable history',
        limit: 12
      })
    );

    const discoveryPanel = screen.getByLabelText('YouTube discovery panel');
    fireEvent.click(await within(discoveryPanel).findByRole('button', { name: /Readable History Interview/i }));

    const urlInput = screen.getByLabelText(/YouTube URL/i);
    expect(urlInput).toHaveValue('https://www.youtube.com/watch?v=abc123demo');
    expect(screen.getByText(/List subtitles to inspect available tracks/i)).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: /List subtitles/i }));

    await waitFor(() =>
      expect(mockFetchYoutubeSubtitleTracks).toHaveBeenCalledWith('https://www.youtube.com/watch?v=abc123demo')
    );
    expect(await screen.findByText(/1 track available/i)).toBeInTheDocument();
    expect(screen.getByText(/en · Manual captions/i)).toBeInTheDocument();
  });

  it('disables YouTube discovery when the backend provider is not configured', async () => {
    mockFetchAcquisitionProviders.mockResolvedValue({
      providers: [
        {
          id: 'youtube_search',
          label: 'YouTube search',
          media_kinds: ['video'],
          capabilities: ['search', 'metadata'],
          status: 'not_configured',
          configured: false,
          available: false,
          rights: ['unknown', 'restricted'],
          discovery_media_kinds: ['video'],
          default_eligible_media_kinds: ['video'],
          policy_notes: ['Search uses the YouTube Data API when configured.'],
          next_actions: ['search', 'inspect_url']
        }
      ],
      policy_notes: [],
      paths: {},
      default_provider_ids: {}
    });

    render(<YoutubeVideoPage />);

    await screen.findByText(/YouTube search is not configured/i);
    expect(screen.getAllByRole('button', { name: /^Search$/i }).some((button) => button.hasAttribute('disabled'))).toBe(true);
    expect(screen.getByLabelText(/YouTube URL/i)).toBeEnabled();
    expect(mockDiscoverAcquisitionCandidates).not.toHaveBeenCalled();
  });
});
