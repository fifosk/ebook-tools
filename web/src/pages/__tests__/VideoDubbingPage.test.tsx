import {
  fetchYoutubeLibrary,
  fetchVoiceInventory,
  fetchSubtitleModels,
  fetchInlineSubtitleStreams,
  extractInlineSubtitles,
  deleteNasSubtitle,
  fetchPipelineDefaults,
  lookupSubtitleTvMetadataPreview,
  lookupYoutubeVideoMetadataPreview,
  deleteYoutubeVideo,
  clearTvMetadataCache,
  clearYoutubeMetadataCache,
  fetchPipelineIntakeStatus,
  fetchAcquisitionProviders,
  discoverAcquisitionCandidates
} from '../../api/client';
import { fetchBookCreationOptions } from '../../api/createBook';
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { describe, expect, it, vi, beforeEach } from 'vitest';
import { LanguageProvider } from '../../context/LanguageProvider';
import VideoDubbingPage from '../VideoDubbingPage';
import type { JobState } from '../../components/JobList';

vi.mock('../../api/client', () => ({
  fetchYoutubeLibrary: vi.fn(),
  fetchVoiceInventory: vi.fn(),
  generateYoutubeDub: vi.fn(),
  synthesizeVoicePreview: vi.fn(),
  fetchSubtitleModels: vi.fn(),
  fetchInlineSubtitleStreams: vi.fn(),
  extractInlineSubtitles: vi.fn(),
  deleteNasSubtitle: vi.fn(),
  fetchPipelineDefaults: vi.fn(),
  lookupSubtitleTvMetadataPreview: vi.fn(),
  lookupYoutubeVideoMetadataPreview: vi.fn(),
  deleteYoutubeVideo: vi.fn(),
  clearTvMetadataCache: vi.fn(),
  clearYoutubeMetadataCache: vi.fn(),
  fetchPipelineIntakeStatus: vi.fn(),
  fetchAcquisitionProviders: vi.fn(),
  discoverAcquisitionCandidates: vi.fn()
}));

vi.mock('../../api/createBook', () => ({
  fetchBookCreationOptions: vi.fn()
}));

const mockFetchYoutubeLibrary = vi.mocked(fetchYoutubeLibrary);
const mockFetchVoiceInventory = vi.mocked(fetchVoiceInventory);
const mockFetchSubtitleModels = vi.mocked(fetchSubtitleModels);
const mockFetchInlineSubtitleStreams = vi.mocked(fetchInlineSubtitleStreams);
const mockExtractInlineSubtitles = vi.mocked(extractInlineSubtitles);
const mockDeleteNasSubtitle = vi.mocked(deleteNasSubtitle);
const mockFetchPipelineDefaults = vi.mocked(fetchPipelineDefaults);
const mockLookupSubtitleTvMetadataPreview = vi.mocked(lookupSubtitleTvMetadataPreview);
const mockLookupYoutubeVideoMetadataPreview = vi.mocked(lookupYoutubeVideoMetadataPreview);
const mockDeleteYoutubeVideo = vi.mocked(deleteYoutubeVideo);
const mockClearTvMetadataCache = vi.mocked(clearTvMetadataCache);
const mockClearYoutubeMetadataCache = vi.mocked(clearYoutubeMetadataCache);
const mockFetchPipelineIntakeStatus = vi.mocked(fetchPipelineIntakeStatus);
const mockFetchAcquisitionProviders = vi.mocked(fetchAcquisitionProviders);
const mockDiscoverAcquisitionCandidates = vi.mocked(discoverAcquisitionCandidates);
const mockFetchBookCreationOptions = vi.mocked(fetchBookCreationOptions);

describe('VideoDubbingPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockFetchInlineSubtitleStreams.mockResolvedValue({ video_path: '', streams: [] });
    mockExtractInlineSubtitles.mockResolvedValue({ video_path: '', extracted: [] });
    mockDeleteNasSubtitle.mockResolvedValue({ video_path: '', subtitle_path: '', removed: [], missing: [] });
    mockFetchPipelineDefaults.mockResolvedValue({ config: {} });
    mockLookupSubtitleTvMetadataPreview.mockResolvedValue({
      source_name: '',
      parsed: null,
      media_metadata: null
    });
    mockLookupYoutubeVideoMetadataPreview.mockResolvedValue({
      source_name: '',
      parsed: null,
      youtube_metadata: null
    });
    mockDeleteYoutubeVideo.mockResolvedValue({ video_path: '', removed: [], missing: [] });
    mockClearTvMetadataCache.mockResolvedValue({ cleared: 0 });
    mockClearYoutubeMetadataCache.mockResolvedValue({ cleared: 0 });
    mockFetchPipelineIntakeStatus.mockResolvedValue(null);
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
          policy_notes: [],
          next_actions: ['search', 'inspect_url']
        },
        {
          id: 'manual_downloads',
          label: 'Manual downloads',
          media_kinds: ['book', 'video'],
          capabilities: ['search', 'import_local', 'extract_subtitles'],
          status: 'available',
          configured: true,
          available: true,
          rights: ['user_provided'],
          policy_notes: [],
          next_actions: ['select_local']
        }
      ],
      policy_notes: [],
      paths: {}
    });
    mockDiscoverAcquisitionCandidates.mockResolvedValue({
      candidates: [],
      policy_notes: [],
      providers_queried: ['nas_video']
    });
    mockFetchBookCreationOptions.mockResolvedValue({
      sentence_bounds: { min: 1, max: 500, default: 30 },
      defaults: {
        topic: '',
        book_name: '',
        genre: '',
        author: 'Me',
        input_language: 'English',
        output_language: 'Arabic',
        voice: 'gTTS'
      },
      pipeline_defaults: {
        sentences_per_output_file: 10,
        stitch_full: false,
        audio_mode: '4',
        audio_bitrate_kbps: 96,
        written_mode: '4',
        selected_voice: 'gTTS',
        generate_audio: true,
        output_html: false,
        output_pdf: false,
        include_transliteration: true,
        translation_provider: 'llm',
        translation_batch_size: 10,
        transliteration_mode: 'default',
        enable_lookup_cache: true,
        lookup_cache_batch_size: 10,
        tempo: 1
      },
      generated_source_defaults: {
        add_images: false,
        image_prompt_pipeline: 'prompt_plan',
        image_style_template: 'wireframe',
        image_prompt_context_sentences: 0,
        image_width: '256',
        image_height: '256'
      },
      youtube_dub_defaults: {
        original_mix_percent: 5,
        flush_sentences: 10,
        translation_batch_size: 10,
        split_batches: true,
        stitch_batches: true,
        target_height: 480,
        preserve_aspect_ratio: true
      },
      supported_input_languages: ['English'],
      supported_output_languages: ['Arabic'],
      supported_voices: ['gTTS']
    });
  });

  it('renders NAS videos with SUB subtitles listed', async () => {
    const modifiedAt = new Date('2024-01-02T03:04:05Z').toISOString();
    mockFetchYoutubeLibrary.mockResolvedValue({
      base_dir: '/Volumes/Data/Download/DStation',
      videos: [
        {
          path: '/Volumes/Data/Download/DStation/generic-video.mkv',
          filename: 'generic-video.mkv',
          folder: '/Volumes/Data/Download/DStation',
          size_bytes: 2048,
          modified_at: modifiedAt,
          source: 'nas_video',
          subtitles: [
            {
              path: '/Volumes/Data/Download/DStation/generic-video.en.sub',
              filename: 'generic-video.en.sub',
              language: 'en',
              format: 'sub'
            }
          ]
        }
      ]
    });
    mockFetchVoiceInventory.mockResolvedValue({ gtts: [], macos: [], piper: [] });
    mockFetchSubtitleModels.mockResolvedValue([]);

    render(
      <LanguageProvider>
        <VideoDubbingPage
          jobs={[] as JobState[]}
          onJobCreated={() => {}}
          onSelectJob={() => {}}
          onOpenJobMedia={() => {}}
        />
      </LanguageProvider>
    );

    await waitFor(() => expect(mockFetchYoutubeLibrary).toHaveBeenCalled());
    expect(await screen.findByText(/generic-video\.mkv/i)).toBeInTheDocument();
    expect(screen.getAllByTitle(/NAS video/i).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/SUB/i).length).toBeGreaterThan(0);
    expect(screen.getByLabelText(/English \(en\)/i)).toBeInTheDocument();

    fireEvent.click(screen.getByRole('tab', { name: /Options/i }));

    expect(screen.getByLabelText(/Target resolution/i)).toHaveValue('480');
    expect(screen.getByRole('checkbox', { name: /Keep original aspect ratio/i })).toBeChecked();
  });

  it('applies backend YouTube dub defaults to untouched controls', async () => {
    const modifiedAt = new Date('2024-01-02T03:04:05Z').toISOString();
    mockFetchBookCreationOptions.mockResolvedValueOnce({
      sentence_bounds: { min: 1, max: 500, default: 30 },
      defaults: {
        topic: '',
        book_name: '',
        genre: '',
        author: 'Me',
        input_language: 'English',
        output_language: 'Arabic',
        voice: 'gTTS'
      },
      pipeline_defaults: {
        sentences_per_output_file: 10,
        stitch_full: false,
        audio_mode: '4',
        audio_bitrate_kbps: 96,
        written_mode: '4',
        selected_voice: 'gTTS',
        generate_audio: true,
        output_html: false,
        output_pdf: false,
        include_transliteration: true,
        translation_provider: 'llm',
        translation_batch_size: 10,
        transliteration_mode: 'default',
        enable_lookup_cache: true,
        lookup_cache_batch_size: 10,
        tempo: 1
      },
      generated_source_defaults: {
        add_images: false,
        image_prompt_pipeline: 'prompt_plan',
        image_style_template: 'wireframe',
        image_prompt_context_sentences: 0,
        image_width: '256',
        image_height: '256'
      },
      youtube_dub_defaults: {
        original_mix_percent: 20,
        flush_sentences: 24,
        translation_batch_size: 7,
        split_batches: false,
        stitch_batches: false,
        target_height: 720,
        preserve_aspect_ratio: false
      },
      supported_input_languages: ['English'],
      supported_output_languages: ['Arabic'],
      supported_voices: ['gTTS']
    });
    mockFetchYoutubeLibrary.mockResolvedValue({
      base_dir: '/Volumes/Data/Download/DStation',
      videos: [
        {
          path: '/Volumes/Data/Download/DStation/generic-video.mkv',
          filename: 'generic-video.mkv',
          folder: '/Volumes/Data/Download/DStation',
          size_bytes: 2048,
          modified_at: modifiedAt,
          source: 'nas_video',
          subtitles: [
            {
              path: '/Volumes/Data/Download/DStation/generic-video.en.srt',
              filename: 'generic-video.en.srt',
              language: 'en',
              format: 'srt'
            }
          ]
        }
      ]
    });
    mockFetchVoiceInventory.mockResolvedValue({ gtts: [], macos: [], piper: [] });
    mockFetchSubtitleModels.mockResolvedValue([]);

    render(
      <LanguageProvider>
        <VideoDubbingPage
          jobs={[] as JobState[]}
          onJobCreated={() => {}}
          onSelectJob={() => {}}
          onOpenJobMedia={() => {}}
        />
      </LanguageProvider>
    );

    fireEvent.click(await screen.findByRole('tab', { name: /Options/i }));

    await waitFor(() => expect(screen.getByLabelText(/Target resolution/i)).toHaveValue('720'));
    expect(screen.getByLabelText(/Original audio mix/i)).toHaveValue('20');
    expect(screen.getByRole('checkbox', { name: /Keep original aspect ratio/i })).not.toBeChecked();
    expect(screen.getByRole('checkbox', { name: /Create separate video per batch/i })).not.toBeChecked();
    expect(screen.getByRole('checkbox', { name: /Stitch batches into a single final MP4/i })).not.toBeChecked();

    fireEvent.click(screen.getByRole('tab', { name: /Tuning/i }));

    expect(screen.getByLabelText(/LLM batch size/i)).toHaveValue(7);
    expect(screen.getByLabelText(/Flush interval/i)).toHaveValue(24);
  });

  it('shows backend intake pressure before generating a dub', async () => {
    const modifiedAt = new Date('2024-01-02T03:04:05Z').toISOString();
    mockFetchPipelineIntakeStatus.mockResolvedValue({
      acceptingJobs: false,
      isUnderPressure: true,
      queueDepth: 6,
      activeCount: 2,
      softLimit: 3,
      hardLimit: 6,
      delayCount: 5
    });
    mockFetchYoutubeLibrary.mockResolvedValue({
      base_dir: '/Volumes/Data/Download/DStation',
      videos: [
        {
          path: '/Volumes/Data/Download/DStation/generic-video.mkv',
          filename: 'generic-video.mkv',
          folder: '/Volumes/Data/Download/DStation',
          size_bytes: 2048,
          modified_at: modifiedAt,
          source: 'nas_video',
          subtitles: [
            {
              path: '/Volumes/Data/Download/DStation/generic-video.en.srt',
              filename: 'generic-video.en.srt',
              language: 'en',
              format: 'srt'
            }
          ]
        }
      ]
    });
    mockFetchVoiceInventory.mockResolvedValue({ gtts: [], macos: [], piper: [] });
    mockFetchSubtitleModels.mockResolvedValue([]);

    render(
      <LanguageProvider>
        <VideoDubbingPage
          jobs={[] as JobState[]}
          onJobCreated={() => {}}
          onSelectJob={() => {}}
          onOpenJobMedia={() => {}}
        />
      </LanguageProvider>
    );

    const alert = await screen.findByRole('alert');
    expect(alert).toHaveTextContent('Job queue is at capacity');
    expect(alert).toHaveTextContent('Delayed jobs: 5');
    expect(screen.getByRole('button', { name: /Generate dubbed video/i })).toBeDisabled();
  });

  it('discovers NAS video candidates and applies an existing library video selection', async () => {
    const modifiedAt = new Date('2024-01-02T03:04:05Z').toISOString();
    mockFetchYoutubeLibrary.mockResolvedValue({
      base_dir: '/Volumes/Data/Download/DStation',
      videos: [
        {
          path: '/Volumes/Data/Download/DStation/current-video.mkv',
          filename: 'current-video.mkv',
          folder: '/Volumes/Data/Download/DStation',
          size_bytes: 4096,
          modified_at: modifiedAt,
          source: 'nas_video',
          subtitles: [
            {
              path: '/Volumes/Data/Download/DStation/current-video.es.srt',
              filename: 'current-video.es.srt',
              language: 'es',
              format: 'srt'
            }
          ]
        }
      ]
    });
    mockDiscoverAcquisitionCandidates.mockResolvedValue({
      candidates: [
        {
          candidate_id: 'nas_video:/Volumes/Data/Download/DStation/current-video.mkv',
          provider: 'nas_video',
          media_kind: 'video',
          title: 'current-video',
          rights: 'user_provided',
          capabilities: ['import_local', 'extract_subtitles', 'metadata'],
          candidate_token: 'token',
          contributors: [],
          local_path: '/Volumes/Data/Download/DStation/current-video.mkv',
          size_bytes: 4096,
          modified_at: modifiedAt,
          subtitles: [
            {
              path: '/Volumes/Data/Download/DStation/current-video.es.srt',
              filename: 'current-video.es.srt',
              language: 'es',
              format: 'srt'
            }
          ],
          metadata: {},
          requires_confirmation: false,
          policy_notes: []
        }
      ],
      policy_notes: [],
      providers_queried: ['nas_video']
    });
    mockFetchVoiceInventory.mockResolvedValue({ gtts: [], macos: [], piper: [] });
    mockFetchSubtitleModels.mockResolvedValue([]);

    render(
      <LanguageProvider>
        <VideoDubbingPage
          jobs={[] as JobState[]}
          onJobCreated={() => {}}
          onSelectJob={() => {}}
          onOpenJobMedia={() => {}}
        />
      </LanguageProvider>
    );

    await screen.findByText(/current-video\.mkv/i);
    fireEvent.change(screen.getByLabelText(/Video discovery search/i), {
      target: { value: 'current' }
    });
    fireEvent.click(screen.getByRole('button', { name: /^Discover$/i }));

    await waitFor(() =>
      expect(mockDiscoverAcquisitionCandidates).toHaveBeenCalledWith({
        mediaKind: 'video',
        provider: 'nas_video',
        query: 'current',
        limit: 25
      })
    );

    const discoveryPanel = screen.getByLabelText('Video source discovery');
    fireEvent.click(await within(discoveryPanel).findByRole('button', { name: /current-video/i }));

    expect(screen.getByText(/Selected discovered video current-video\.mkv/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Spanish \(es\)/i)).toBeInTheDocument();
  });

  it('discovers manual download videos and applies subtitle hints to the existing selection', async () => {
    const modifiedAt = new Date('2024-02-03T04:05:06Z').toISOString();
    mockFetchYoutubeLibrary.mockResolvedValue({
      base_dir: '/Volumes/Data/Download/DStation',
      videos: []
    });
    mockDiscoverAcquisitionCandidates.mockResolvedValue({
      candidates: [
        {
          candidate_id: 'manual_downloads:/Volumes/Data/Download/DStation/manual/movie.mkv',
          provider: 'manual_downloads',
          media_kind: 'video',
          title: 'Manual Movie',
          rights: 'user_provided',
          capabilities: ['import_local', 'extract_subtitles', 'metadata'],
          candidate_token: 'manual-token',
          contributors: [],
          local_path: '/Volumes/Data/Download/DStation/manual/movie.mkv',
          size_bytes: 8192,
          modified_at: modifiedAt,
          subtitles: [
            {
              path: '/Volumes/Data/Download/DStation/manual/movie.fr.srt',
              filename: 'movie.fr.srt',
              language: 'fr',
              format: 'srt'
            }
          ],
          metadata: {},
          requires_confirmation: false,
          policy_notes: []
        }
      ],
      policy_notes: [],
      providers_queried: ['manual_downloads']
    });
    mockFetchVoiceInventory.mockResolvedValue({ gtts: [], macos: [], piper: [] });
    mockFetchSubtitleModels.mockResolvedValue([]);

    render(
      <LanguageProvider>
        <VideoDubbingPage
          jobs={[] as JobState[]}
          onJobCreated={() => {}}
          onSelectJob={() => {}}
          onOpenJobMedia={() => {}}
        />
      </LanguageProvider>
    );

    await screen.findByText(/No downloaded videos found/i);
    fireEvent.click(screen.getByRole('button', { name: /Manual downloads/i }));
    fireEvent.change(screen.getByLabelText(/Video discovery search/i), {
      target: { value: 'manual movie' }
    });
    fireEvent.click(screen.getByRole('button', { name: /^Discover$/i }));

    await waitFor(() =>
      expect(mockDiscoverAcquisitionCandidates).toHaveBeenCalledWith({
        mediaKind: 'video',
        provider: 'manual_downloads',
        query: 'manual movie',
        limit: 25
      })
    );

    const discoveryPanel = screen.getByLabelText('Video source discovery');
    fireEvent.click(await within(discoveryPanel).findByRole('button', { name: /Manual Movie/i }));

    expect(screen.getByText(/Selected a discovered video path/i)).toBeInTheDocument();
    expect(screen.getByLabelText('Selected discovered video path')).toHaveTextContent(
      '/Volumes/Data/Download/DStation/manual/movie.mkv'
    );
    expect(screen.getByLabelText('Selected discovered video path')).toHaveTextContent('movie.fr.srt');
  });

  it('discovers YouTube search candidates and fills the metadata lookup', async () => {
    const youtubeUrl = 'https://www.youtube.com/watch?v=abc123demo';
    mockFetchYoutubeLibrary.mockResolvedValue({
      base_dir: '/Volumes/Data/Download/DStation',
      videos: []
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
          candidate_token: 'youtube-token',
          contributors: ['History Channel'],
          source_url: youtubeUrl,
          duration_seconds: 612,
          subtitles: [],
          metadata: {
            youtube_url: youtubeUrl,
            youtube_video_id: 'abc123demo'
          },
          requires_confirmation: true,
          policy_notes: ['Review source rights before acquisition.']
        }
      ],
      policy_notes: [],
      providers_queried: ['youtube_search']
    });
    mockFetchVoiceInventory.mockResolvedValue({ gtts: [], macos: [], piper: [] });
    mockFetchSubtitleModels.mockResolvedValue([]);
    mockLookupYoutubeVideoMetadataPreview.mockResolvedValue({
      source_name: youtubeUrl,
      parsed: { video_id: 'abc123demo', pattern: 'url' },
      youtube_metadata: {
        title: 'Readable History Interview',
        channel: 'History Channel',
        webpage_url: youtubeUrl
      }
    });

    render(
      <LanguageProvider>
        <VideoDubbingPage
          jobs={[] as JobState[]}
          onJobCreated={() => {}}
          onSelectJob={() => {}}
          onOpenJobMedia={() => {}}
        />
      </LanguageProvider>
    );

    await screen.findByText(/No downloaded videos found/i);
    fireEvent.click(screen.getByRole('button', { name: /YouTube search/i }));
    fireEvent.change(screen.getByLabelText(/Video discovery search/i), {
      target: { value: 'readable history' }
    });
    fireEvent.click(screen.getByRole('button', { name: /^Discover$/i }));

    await waitFor(() =>
      expect(mockDiscoverAcquisitionCandidates).toHaveBeenCalledWith({
        mediaKind: 'video',
        provider: 'youtube_search',
        query: 'readable history',
        limit: 25
      })
    );

    const discoveryPanel = screen.getByLabelText('Video source discovery');
    fireEvent.click(await within(discoveryPanel).findByRole('button', { name: /Readable History Interview/i }));

    expect(await screen.findByText(/Selected YouTube discovery result Readable History Interview/i)).toBeInTheDocument();
    await waitFor(() => expect(mockLookupYoutubeVideoMetadataPreview).toHaveBeenCalledWith({
      source_name: youtubeUrl,
      force: false
    }));
    expect(screen.getByLabelText(/Lookup video id \/ filename/i)).toHaveValue(youtubeUrl);
  });

  it('disables YouTube discovery when the provider is not configured', async () => {
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
          policy_notes: ['Search uses the YouTube Data API when configured.'],
          next_actions: ['search', 'inspect_url']
        }
      ],
      policy_notes: [],
      paths: {}
    });
    mockFetchYoutubeLibrary.mockResolvedValue({
      base_dir: '/Volumes/Data/Download/DStation',
      videos: []
    });
    mockFetchVoiceInventory.mockResolvedValue({ gtts: [], macos: [], piper: [] });
    mockFetchSubtitleModels.mockResolvedValue([]);

    render(
      <LanguageProvider>
        <VideoDubbingPage
          jobs={[] as JobState[]}
          onJobCreated={() => {}}
          onSelectJob={() => {}}
          onOpenJobMedia={() => {}}
        />
      </LanguageProvider>
    );

    expect(await screen.findByRole('button', { name: /YouTube search/i })).toBeDisabled();
    expect(screen.getByText(/YouTube search is not configured/i)).toBeInTheDocument();
  });

  it('allows deleting a subtitle and refreshes the library', async () => {
    const modifiedAt = new Date('2024-01-02T03:04:05Z').toISOString();
    mockFetchYoutubeLibrary.mockResolvedValue({
      base_dir: '/Volumes/Data/Download/DStation',
      videos: [
        {
          path: '/Volumes/Data/Download/DStation/generic-video.mkv',
          filename: 'generic-video.mkv',
          folder: '/Volumes/Data/Download/DStation',
          size_bytes: 2048,
          modified_at: modifiedAt,
          source: 'nas_video',
          subtitles: [
            {
              path: '/Volumes/Data/Download/DStation/generic-video.en.sub',
              filename: 'generic-video.en.sub',
              language: 'en',
              format: 'sub'
            },
            {
              path: '/Volumes/Data/Download/DStation/generic-video.es.srt',
              filename: 'generic-video.es.srt',
              language: 'es',
              format: 'srt'
            }
          ]
        }
      ]
    });
    mockFetchVoiceInventory.mockResolvedValue({ gtts: [], macos: [], piper: [] });
    mockFetchSubtitleModels.mockResolvedValue([]);

    const confirmSpy = vi.spyOn(window, 'confirm').mockReturnValue(true);

    render(
      <LanguageProvider>
        <VideoDubbingPage
          jobs={[] as JobState[]}
          onJobCreated={() => {}}
          onSelectJob={() => {}}
          onOpenJobMedia={() => {}}
        />
      </LanguageProvider>
    );

    await waitFor(() => expect(mockFetchYoutubeLibrary).toHaveBeenCalled());

    const deleteButton = await screen.findByRole('button', { name: /Delete generic-video\.en\.sub/i });
    fireEvent.click(deleteButton);

    await waitFor(() => expect(mockDeleteNasSubtitle).toHaveBeenCalled());
    expect(mockDeleteNasSubtitle).toHaveBeenCalledWith(
      '/Volumes/Data/Download/DStation/generic-video.mkv',
      '/Volumes/Data/Download/DStation/generic-video.en.sub'
    );
    expect(mockFetchYoutubeLibrary).toHaveBeenCalledTimes(2);
    confirmSpy.mockRestore();
  });
});
