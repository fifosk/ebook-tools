import {
  fetchYoutubeLibrary,
  fetchVoiceInventory,
  fetchSubtitleModels,
  fetchInlineSubtitleStreams,
  extractInlineSubtitles,
  deleteNasSubtitle,
  fetchPipelineDefaults
} from '../../api/client';
import { render, screen, waitFor } from '@testing-library/react';
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
  fetchPipelineDefaults: vi.fn()
}));

const mockFetchYoutubeLibrary = vi.mocked(fetchYoutubeLibrary);
const mockFetchVoiceInventory = vi.mocked(fetchVoiceInventory);
const mockFetchSubtitleModels = vi.mocked(fetchSubtitleModels);
const mockFetchInlineSubtitleStreams = vi.mocked(fetchInlineSubtitleStreams);
const mockExtractInlineSubtitles = vi.mocked(extractInlineSubtitles);
const mockDeleteNasSubtitle = vi.mocked(deleteNasSubtitle);
const mockFetchPipelineDefaults = vi.mocked(fetchPipelineDefaults);

describe('VideoDubbingPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockFetchInlineSubtitleStreams.mockResolvedValue({ video_path: '', streams: [] });
    mockExtractInlineSubtitles.mockResolvedValue({ video_path: '', extracted: [] });
    mockDeleteNasSubtitle.mockResolvedValue({ video_path: '', subtitle_path: '', removed: [], missing: [] });
    mockFetchPipelineDefaults.mockResolvedValue({ config: {} });
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
    mockFetchVoiceInventory.mockResolvedValue({ gtts: [], macos: [] });
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
    expect(screen.getByText(/SUB/i)).toBeInTheDocument();
    expect(screen.getByText(/English \(en\)/i)).toBeInTheDocument();

    screen.getByRole('tab', { name: /Options/i }).click();

    expect(screen.getByLabelText(/Target resolution/i)).toHaveValue('480');
    expect(screen.getByRole('checkbox', { name: /Keep original aspect ratio/i })).toBeChecked();
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
    mockFetchVoiceInventory.mockResolvedValue({ gtts: [], macos: [] });
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

    const deleteButtons = await screen.findAllByRole('button', { name: /delete/i });
    deleteButtons[0].click();

    await waitFor(() => expect(mockDeleteNasSubtitle).toHaveBeenCalled());
    expect(mockDeleteNasSubtitle).toHaveBeenCalledWith(
      '/Volumes/Data/Download/DStation/generic-video.mkv',
      '/Volumes/Data/Download/DStation/generic-video.en.sub'
    );
    expect(mockFetchYoutubeLibrary).toHaveBeenCalledTimes(2);
    confirmSpy.mockRestore();
  });
});
