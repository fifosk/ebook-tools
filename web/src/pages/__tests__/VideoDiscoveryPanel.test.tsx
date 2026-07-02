import { fireEvent, render, screen, within } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import type {
  AcquisitionCandidate,
  AcquisitionJobStatusResponse
} from '../../api/dtos';
import VideoDiscoveryPanel from '../video-dubbing/VideoDiscoveryPanel';
import type {
  VideoDiscoveryProvider,
  VideoDiscoveryProviderOption
} from '../video-dubbing/videoDubbingDiscovery';

function candidate(overrides: Partial<AcquisitionCandidate> = {}): AcquisitionCandidate {
  return {
    candidate_id: 'youtube-1',
    provider: 'youtube_search',
    media_kind: 'video',
    title: 'Readable History episode',
    rights: 'unknown',
    capabilities: ['metadata'],
    candidate_token: 'token-1',
    contributors: ['Example Channel'],
    subtitles: [{ path: '/captions/en.vtt', filename: 'English captions.vtt', language: 'en', format: 'vtt' }],
    metadata: {
      duration: 1240,
      source_url: 'https://youtube.example/watch?v=demo'
    },
    requires_confirmation: false,
    policy_notes: [],
    ...overrides
  };
}

function job(overrides: Partial<AcquisitionJobStatusResponse> = {}): AcquisitionJobStatusResponse {
  return {
    provider: 'download_station',
    task_id: 'task-1',
    status: 'running',
    progress: 0.25,
    message: 'Download Station task is running.',
    external_task_id: null,
    raw_status: 'running',
    started_at: null,
    updated_at: '2026-07-02T00:00:00Z',
    completed_files: [],
    next_actions: [],
    metadata: {},
    ...overrides
  };
}

function providerOption(
  id: VideoDiscoveryProvider,
  label: string,
  available = true
): VideoDiscoveryProviderOption {
  return {
    id,
    label,
    available
  };
}

function renderPanel(overrides: Partial<Parameters<typeof VideoDiscoveryPanel>[0]> = {}) {
  const props: Parameters<typeof VideoDiscoveryPanel>[0] = {
    discoveryProvider: 'youtube_search',
    discoveryProviderOptions: [
      providerOption('backend_defaults', 'Default sources'),
      providerOption('youtube_search', 'YouTube'),
      providerOption('manual_downloads', 'Manual downloads', false)
    ],
    discoveryQuery: 'history',
    discoveryCandidates: [candidate()],
    discoveryError: null,
    discoveryPolicyNotes: ['Review metadata before downloading.'],
    acquisitionProviderError: null,
    youtubeSearchUnavailableMessage: null,
    manualDownloadsUnavailableMessage: 'Manual downloads are not configured.',
    downloadStationUnavailableMessage: null,
    isDownloadStationAvailable: true,
    indexerSearchUnavailableMessage: null,
    downloadStationSourceUri: 'magnet:?xt=urn:btih:demo',
    downloadStationCandidate: null,
    downloadStationDestination: '/downloads',
    downloadStationConfirmed: true,
    downloadStationJob: job(),
    downloadStationError: null,
    isSubmittingDownloadStation: false,
    isPollingDownloadStation: false,
    isDiscoveryProviderAvailable: true,
    isDiscoveringVideos: false,
    onDiscoveryProviderChange: vi.fn(),
    onDiscoveryQueryChange: vi.fn(),
    onDiscoverVideos: vi.fn(),
    onSelectDiscoveryCandidate: vi.fn(),
    onDownloadStationSourceUriChange: vi.fn(),
    onClearDownloadStationCandidate: vi.fn(),
    onDownloadStationDestinationChange: vi.fn(),
    onDownloadStationConfirmedChange: vi.fn(),
    onSubmitDownloadStation: vi.fn(),
    onPollDownloadStation: vi.fn(),
    ...overrides
  };
  const view = render(<VideoDiscoveryPanel {...props} />);
  return { ...view, props };
}

describe('VideoDiscoveryPanel', () => {
  it('routes provider, query, discovery, candidate, and Download Station actions', () => {
    const { props } = renderPanel();
    const panel = screen.getByLabelText('Video source discovery');

    expect(within(panel).getByText('Discover video sources')).toBeInTheDocument();
    expect(within(panel).getByText('Review metadata before downloading.')).toBeInTheDocument();
    expect(within(panel).getByText('Manual downloads are not configured.')).toBeInTheDocument();
    expect(within(panel).getByRole('button', { name: 'YouTube' })).toHaveAttribute('aria-pressed', 'true');
    expect(within(panel).getByRole('button', { name: 'Manual downloads' })).toBeDisabled();
    expect(within(panel).getByLabelText('Video discovery search')).toHaveAttribute(
      'placeholder',
      'Search YouTube videos by title or channel'
    );

    fireEvent.click(within(panel).getByRole('button', { name: 'Default sources' }));
    fireEvent.change(within(panel).getByLabelText('Video discovery search'), {
      target: { value: 'new query' }
    });
    fireEvent.click(within(panel).getByRole('button', { name: 'Discover' }));
    fireEvent.click(within(panel).getByRole('button', { name: /Readable History episode/i }));

    const downloadStation = within(panel).getByLabelText('Download Station handoff');
    fireEvent.change(within(downloadStation).getByLabelText(/source URI/i), {
      target: { value: 'https://example.test/file.torrent' }
    });
    fireEvent.click(within(downloadStation).getByRole('button', { name: 'Send' }));
    fireEvent.click(within(downloadStation).getByRole('button', { name: 'Poll' }));

    expect(props.onDiscoveryProviderChange).toHaveBeenCalledWith('backend_defaults');
    expect(props.onDiscoveryQueryChange).toHaveBeenCalledWith('new query');
    expect(props.onDiscoverVideos).toHaveBeenCalledTimes(1);
    expect(props.onSelectDiscoveryCandidate).toHaveBeenCalledWith(props.discoveryCandidates[0]);
    expect(props.onDownloadStationSourceUriChange).toHaveBeenCalledWith('https://example.test/file.torrent');
    expect(props.onSubmitDownloadStation).toHaveBeenCalledTimes(1);
    expect(props.onPollDownloadStation).toHaveBeenCalledTimes(1);
    expect(downloadStation).toHaveTextContent('running · 25%');
  });

  it('shows empty and disabled discovery states', () => {
    renderPanel({
      discoveryProvider: 'indexer_search',
      discoveryCandidates: [],
      discoveryQuery: '',
      discoveryError: 'Search failed.',
      isDiscoveryProviderAvailable: false,
      isDiscoveringVideos: false,
      indexerSearchUnavailableMessage: 'Indexer search is not configured.',
      downloadStationUnavailableMessage: 'Download Station is not configured.',
      isDownloadStationAvailable: false
    });
    const panel = screen.getByLabelText('Video source discovery');

    expect(panel).toHaveTextContent('Search failed.');
    expect(panel).toHaveTextContent('Indexer search is not configured.');
    expect(panel).toHaveTextContent('Download Station is not configured.');
    expect(panel).toHaveTextContent('No discovery results loaded yet.');
    expect(within(panel).getByRole('button', { name: 'Discover' })).toBeDisabled();
  });
});
