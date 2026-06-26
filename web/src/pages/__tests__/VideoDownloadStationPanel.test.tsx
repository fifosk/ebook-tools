import { fireEvent, render, screen, within } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import type {
  AcquisitionCandidate,
  AcquisitionJobStatusResponse
} from '../../api/dtos';
import VideoDownloadStationPanel from '../video-dubbing/VideoDownloadStationPanel';

function candidate(overrides: Partial<AcquisitionCandidate> = {}): AcquisitionCandidate {
  return {
    candidate_id: 'candidate-1',
    provider: 'newznab_torznab',
    media_kind: 'video',
    title: 'Indexer episode',
    rights: 'unknown',
    capabilities: ['acquire'],
    candidate_token: 'candidate-token',
    contributors: [],
    subtitles: [],
    metadata: { handoff_provider: 'download_station' },
    requires_confirmation: true,
    policy_notes: [],
    ...overrides
  };
}

function job(overrides: Partial<AcquisitionJobStatusResponse> = {}): AcquisitionJobStatusResponse {
  return {
    provider: 'download_station',
    task_id: 'task-1',
    status: 'completed',
    progress: 1,
    message: 'Download Station task is finished.',
    external_task_id: null,
    raw_status: 'finished',
    started_at: null,
    updated_at: '2026-06-26T12:00:00Z',
    completed_files: ['/downloads/Demo.mkv'],
    next_actions: ['discover_manual_downloads'],
    metadata: {},
    ...overrides
  };
}

function renderPanel(overrides: Partial<Parameters<typeof VideoDownloadStationPanel>[0]> = {}) {
  const props: Parameters<typeof VideoDownloadStationPanel>[0] = {
    unavailableMessage: null,
    isAvailable: true,
    sourceUri: '',
    candidate: null,
    destination: '',
    confirmed: false,
    job: null,
    error: null,
    isSubmitting: false,
    isPolling: false,
    onSourceUriChange: vi.fn(),
    onClearCandidate: vi.fn(),
    onDestinationChange: vi.fn(),
    onConfirmedChange: vi.fn(),
    onSubmit: vi.fn(),
    onPoll: vi.fn(),
    ...overrides
  };
  const view = render(<VideoDownloadStationPanel {...props} />);
  return { ...view, props };
}

describe('VideoDownloadStationPanel', () => {
  it('requires confirmation and a reviewed source before enabling submit', () => {
    renderPanel({ sourceUri: 'https://example.test/video', confirmed: false });

    expect(screen.getByRole('button', { name: 'Send' })).toBeDisabled();
  });

  it('routes manual source, destination, confirmation, submit, and poll actions', () => {
    const { props } = renderPanel({
      sourceUri: 'https://example.test/video',
      destination: '/downloads',
      confirmed: true,
      job: job({ status: 'running', progress: 0.5, completed_files: [] })
    });
    const panel = screen.getByLabelText('Download Station handoff');

    fireEvent.change(within(panel).getByLabelText(/source URI/i), {
      target: { value: 'magnet:?xt=urn:btih:demo' }
    });
    fireEvent.change(within(panel).getByLabelText(/destination/i), {
      target: { value: '/downloads/new' }
    });
    fireEvent.click(within(panel).getByLabelText(/authorized/i));
    fireEvent.click(within(panel).getByRole('button', { name: 'Send' }));
    fireEvent.click(within(panel).getByRole('button', { name: 'Poll' }));

    expect(props.onSourceUriChange).toHaveBeenCalledWith('magnet:?xt=urn:btih:demo');
    expect(props.onDestinationChange).toHaveBeenCalledWith('/downloads/new');
    expect(props.onConfirmedChange).toHaveBeenCalledWith(false);
    expect(props.onSubmit).toHaveBeenCalledTimes(1);
    expect(props.onPoll).toHaveBeenCalledTimes(1);
    expect(panel).toHaveTextContent('running · 50%');
  });

  it('renders selected indexer candidate and completed file hints', () => {
    const { props } = renderPanel({
      candidate: candidate(),
      confirmed: true,
      job: job(),
      error: 'Unable to poll task.'
    });
    const panel = screen.getByLabelText('Download Station handoff');

    expect(within(panel).getByLabelText('Selected Download Station candidate')).toHaveTextContent(
      'Indexer episode'
    );
    expect(panel).toHaveTextContent('Unable to poll task.');
    expect(panel).toHaveTextContent('Download Station task is finished.');
    expect(panel).toHaveTextContent('Completed: Demo.mkv');

    fireEvent.click(within(panel).getByRole('button', { name: 'Clear' }));
    expect(props.onClearCandidate).toHaveBeenCalledTimes(1);
  });
});
