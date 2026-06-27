import { act, renderHook, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import type {
  AcquisitionCandidate,
  AcquisitionPreparedArtifactResponse,
  YoutubeNasSubtitle,
  YoutubeNasVideo
} from '../../api/dtos';
import { prepareAcquisitionArtifact } from '../../api/client';
import { useVideoDubbingSourceSelection } from '../video-dubbing/useVideoDubbingSourceSelection';

vi.mock('../../api/client', () => ({
  prepareAcquisitionArtifact: vi.fn()
}));

const englishSubtitle: YoutubeNasSubtitle = {
  path: '/media/episode.en.ass',
  filename: 'episode.en.ass',
  language: 'en',
  format: 'ass'
};

const turkishSubtitle: YoutubeNasSubtitle = {
  path: '/media/episode.tr.ass',
  filename: 'episode.tr.ass',
  language: 'tr',
  format: 'ass'
};

const video: YoutubeNasVideo = {
  path: '/media/episode.mkv',
  filename: 'episode.mkv',
  folder: '/media',
  size_bytes: 123,
  modified_at: '2026-06-26T12:00:00Z',
  subtitles: [turkishSubtitle, englishSubtitle]
};

function candidate(overrides: Partial<AcquisitionCandidate> = {}): AcquisitionCandidate {
  return {
    candidate_id: 'candidate-1',
    provider: 'nas_video',
    media_kind: 'video',
    title: 'Episode candidate',
    rights: 'user_provided',
    capabilities: ['import_local'],
    candidate_token: 'candidate-token',
    contributors: [],
    source_url: null,
    local_path: '/media/episode.mkv',
    subtitles: [englishSubtitle],
    metadata: {},
    requires_confirmation: false,
    policy_notes: [],
    ...overrides
  };
}

function preparedArtifact(
  overrides: Partial<AcquisitionPreparedArtifactResponse> = {}
): AcquisitionPreparedArtifactResponse {
  return {
    provider: 'nas_video',
    media_kind: 'video',
    source_kind: 'nas_video',
    local_path: '/media/episode.mkv',
    input_file: null,
    video_path: '/media/episode.mkv',
    subtitle_path: englishSubtitle.path,
    subtitles: [englishSubtitle],
    next_actions: ['extract_subtitles', 'create_dub_job'],
    metadata: {},
    ...overrides
  };
}

function renderSourceSelection(
  overrides: Partial<Parameters<typeof useVideoDubbingSourceSelection>[0]> = {}
) {
  let templateState: Record<string, unknown> | null = { selected_subtitle_path: '/old.ass' };
  const onSelectedVideoDiscoveryTemplateStateChange = vi.fn((next) => {
    templateState = typeof next === 'function' ? next(templateState) : next;
  });
  const props: Parameters<typeof useVideoDubbingSourceSelection>[0] = {
    selectedVideoPath: video.path,
    selectedVideo: video,
    selectedSubtitlePath: null,
    playableSubtitles: [turkishSubtitle, englishSubtitle],
    videos: [video],
    videoDiscoveryProvider: 'nas_video',
    discoveryQuery: 'episode',
    onSelectedVideoPathChange: vi.fn(),
    onSelectedSubtitlePathChange: vi.fn(),
    onSelectedVideoDiscoveryTemplateStateChange,
    onTargetLanguageEnsure: vi.fn(),
    onDiscoveryErrorChange: vi.fn(),
    onYoutubeLookupSourceNameChange: vi.fn(),
    onMetadataSectionChange: vi.fn(),
    onActiveTabChange: vi.fn(),
    onYoutubeMetadataLookup: vi.fn().mockResolvedValue(undefined),
    onDownloadStationCandidateChange: vi.fn(),
    onDownloadStationSourceUriChange: vi.fn(),
    onStatusMessageChange: vi.fn(),
    ...overrides
  };
  const result = renderHook((hookProps: Parameters<typeof useVideoDubbingSourceSelection>[0]) =>
    useVideoDubbingSourceSelection(hookProps),
    { initialProps: props }
  );
  return {
    ...result,
    props,
    get templateState() {
      return templateState;
    }
  };
}

describe('useVideoDubbingSourceSelection', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(prepareAcquisitionArtifact).mockResolvedValue(preparedArtifact());
  });

  it('defaults to the preferred playable subtitle when selection is missing', async () => {
    const { props } = renderSourceSelection();

    await waitFor(() => expect(props.onSelectedSubtitlePathChange).toHaveBeenCalledWith(englishSubtitle.path));
    expect(props.onTargetLanguageEnsure).toHaveBeenCalledWith('en');
  });

  it('selects a NAS video and clears saved discovery state', () => {
    const { result, props } = renderSourceSelection({
      selectedSubtitlePath: englishSubtitle.path
    });

    act(() => {
      result.current.handleSelectVideo(video);
    });

    expect(props.onSelectedVideoDiscoveryTemplateStateChange).toHaveBeenCalledWith(null);
    expect(props.onSelectedVideoPathChange).toHaveBeenCalledWith(video.path);
    expect(props.onSelectedSubtitlePathChange).toHaveBeenLastCalledWith(englishSubtitle.path);
    expect(props.onTargetLanguageEnsure).toHaveBeenLastCalledWith('en');
  });

  it('updates saved discovery state and target language when selecting a subtitle', () => {
    const hook = renderSourceSelection({
      selectedSubtitlePath: englishSubtitle.path
    });

    act(() => {
      hook.result.current.handleSelectSubtitle(turkishSubtitle.path);
    });

    expect(hook.props.onSelectedSubtitlePathChange).toHaveBeenCalledWith(turkishSubtitle.path);
    expect(hook.templateState).toEqual({ selected_subtitle_path: turkishSubtitle.path });
    expect(hook.props.onTargetLanguageEnsure).toHaveBeenLastCalledWith('tr');
  });

  it('routes YouTube discovery candidates to metadata lookup', () => {
    const { result, props } = renderSourceSelection({
      videoDiscoveryProvider: 'youtube_search'
    });
    const youtubeCandidate = candidate({
      provider: 'youtube_search',
      title: 'YouTube episode',
      source_url: ' https://youtube.test/watch?v=1 ',
      local_path: null,
      metadata: {}
    });

    act(() => {
      result.current.handleSelectDiscoveryCandidate(youtubeCandidate);
    });

    expect(props.onYoutubeLookupSourceNameChange).toHaveBeenCalledWith('https://youtube.test/watch?v=1');
    expect(props.onMetadataSectionChange).toHaveBeenCalledWith('youtube');
    expect(props.onActiveTabChange).toHaveBeenCalledWith('metadata');
    expect(props.onYoutubeMetadataLookup).toHaveBeenCalledWith('https://youtube.test/watch?v=1', false);
    expect(props.onStatusMessageChange).toHaveBeenCalledWith(
      'Selected YouTube discovery result YouTube episode. Review metadata before downloading or dubbing.'
    );
  });

  it('hands indexer candidates to Download Station when a handoff is available', () => {
    const { result, props } = renderSourceSelection({
      videoDiscoveryProvider: 'newznab_torznab'
    });
    const indexerCandidate = candidate({
      provider: 'newznab_torznab',
      title: 'Indexer episode',
      local_path: null,
      metadata: { handoff_provider: 'download_station' },
      requires_confirmation: true
    });

    act(() => {
      result.current.handleSelectDiscoveryCandidate(indexerCandidate);
    });

    expect(props.onDownloadStationCandidateChange).toHaveBeenCalledWith(indexerCandidate);
    expect(props.onDownloadStationSourceUriChange).toHaveBeenCalledWith('');
    expect(props.onStatusMessageChange).toHaveBeenCalledWith(
      'Selected indexer result Indexer episode. Confirm lawful access before any downloader handoff.'
    );
  });

  it('prepares local video discovery candidates before selecting a library video', async () => {
    const { result, props } = renderSourceSelection({
      selectedSubtitlePath: englishSubtitle.path
    });

    await act(async () => {
      await result.current.handleSelectDiscoveryCandidate(candidate());
    });

    expect(prepareAcquisitionArtifact).toHaveBeenCalledWith('candidate-token');
    expect(props.onSelectedVideoPathChange).toHaveBeenCalledWith(video.path);
    expect(props.onSelectedSubtitlePathChange).toHaveBeenLastCalledWith(englishSubtitle.path);
    expect(props.onSelectedVideoDiscoveryTemplateStateChange).toHaveBeenCalledWith(
      expect.objectContaining({
        selected_video_path: video.path,
        selected_subtitle_path: englishSubtitle.path
      })
    );
    expect(props.onStatusMessageChange).toHaveBeenCalledWith('Selected discovered video episode.mkv.');
  });

  it('honors prepared subtitle choices for existing library videos', async () => {
    vi.mocked(prepareAcquisitionArtifact).mockResolvedValue(
      preparedArtifact({
        subtitle_path: turkishSubtitle.path,
        subtitles: [turkishSubtitle]
      })
    );
    const { result, props } = renderSourceSelection({
      selectedSubtitlePath: englishSubtitle.path
    });

    await act(async () => {
      await result.current.handleSelectDiscoveryCandidate(candidate());
    });

    expect(props.onSelectedVideoPathChange).toHaveBeenCalledWith(video.path);
    expect(props.onSelectedSubtitlePathChange).toHaveBeenLastCalledWith(turkishSubtitle.path);
    expect(props.onTargetLanguageEnsure).toHaveBeenLastCalledWith('tr');
    expect(props.onSelectedVideoDiscoveryTemplateStateChange).toHaveBeenCalledWith(
      expect.objectContaining({
        selected_video_path: video.path,
        selected_subtitle_path: turkishSubtitle.path
      })
    );
  });

  it('uses prepared video paths instead of raw discovery paths for new video candidates', async () => {
    vi.mocked(prepareAcquisitionArtifact).mockResolvedValue(
      preparedArtifact({
        local_path: '/prepared/new-video.mkv',
        video_path: '/prepared/new-video.mkv',
        subtitle_path: '/prepared/new-video.en.srt',
        subtitles: [{ ...englishSubtitle, path: '/prepared/new-video.en.srt' }]
      })
    );
    const { result, props } = renderSourceSelection({
      selectedSubtitlePath: englishSubtitle.path,
      videos: []
    });

    await act(async () => {
      await result.current.handleSelectDiscoveryCandidate(
        candidate({
          local_path: '/raw/untrusted-video.mkv',
          subtitles: [{ ...englishSubtitle, path: '/raw/untrusted-video.en.srt' }]
        })
      );
    });

    expect(prepareAcquisitionArtifact).toHaveBeenCalledWith('candidate-token');
    expect(props.onSelectedVideoPathChange).toHaveBeenCalledWith('/prepared/new-video.mkv');
    expect(props.onSelectedSubtitlePathChange).toHaveBeenCalledWith('/prepared/new-video.en.srt');
    expect(props.onTargetLanguageEnsure).toHaveBeenLastCalledWith('en');
    expect(props.onSelectedVideoDiscoveryTemplateStateChange).toHaveBeenCalledWith(
      expect.objectContaining({
        selected_video_path: '/prepared/new-video.mkv',
        selected_subtitle_path: '/prepared/new-video.en.srt'
      })
    );
  });

  it('shows a discovery error when a local video candidate is missing a prepare token', async () => {
    const { result, props } = renderSourceSelection({
      selectedSubtitlePath: englishSubtitle.path
    });

    await act(async () => {
      await result.current.handleSelectDiscoveryCandidate(candidate({ candidate_token: '  ' }));
    });

    expect(prepareAcquisitionArtifact).not.toHaveBeenCalled();
    expect(props.onDiscoveryErrorChange).toHaveBeenCalledWith(
      'Selected video discovery result is missing a prepared artifact token.'
    );
    expect(props.onSelectedVideoPathChange).not.toHaveBeenCalled();
  });

  it('shows a discovery error when video candidate preparation fails', async () => {
    vi.mocked(prepareAcquisitionArtifact).mockRejectedValue(new Error('prepare failed'));
    const { result, props } = renderSourceSelection({
      selectedSubtitlePath: englishSubtitle.path
    });

    await act(async () => {
      await result.current.handleSelectDiscoveryCandidate(candidate());
    });

    expect(prepareAcquisitionArtifact).toHaveBeenCalledWith('candidate-token');
    expect(props.onDiscoveryErrorChange).toHaveBeenLastCalledWith('prepare failed');
    expect(props.onSelectedVideoPathChange).not.toHaveBeenCalled();
  });
});
