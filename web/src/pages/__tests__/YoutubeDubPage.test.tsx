import {
  fetchYoutubeLibrary,
  fetchVoiceInventory,
  fetchSubtitleModels,
  extractInlineSubtitles
} from '../../api/client';
import { render, screen, waitFor } from '@testing-library/react';
import { describe, expect, it, vi, beforeEach } from 'vitest';
import YoutubeDubPage from '../YoutubeDubPage';
import type { JobState } from '../../components/JobList';

vi.mock('../../api/client', () => ({
  fetchYoutubeLibrary: vi.fn(),
  fetchVoiceInventory: vi.fn(),
  generateYoutubeDub: vi.fn(),
  synthesizeVoicePreview: vi.fn(),
  fetchSubtitleModels: vi.fn(),
  extractInlineSubtitles: vi.fn()
}));

const mockFetchYoutubeLibrary = vi.mocked(fetchYoutubeLibrary);
const mockFetchVoiceInventory = vi.mocked(fetchVoiceInventory);
const mockFetchSubtitleModels = vi.mocked(fetchSubtitleModels);
const mockExtractInlineSubtitles = vi.mocked(extractInlineSubtitles);

describe('YoutubeDubPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockExtractInlineSubtitles.mockResolvedValue({ video_path: '', extracted: [] });
  });

  it('renders NAS videos with SUB subtitles listed', async () => {
    const modifiedAt = new Date('2024-01-02T03:04:05Z').toISOString();
    mockFetchYoutubeLibrary.mockResolvedValue({
      base_dir: '/Volumes/Data/Video/Youtube',
      videos: [
        {
          path: '/Volumes/Data/Video/Youtube/generic-video.mkv',
          filename: 'generic-video.mkv',
          folder: '/Volumes/Data/Video/Youtube',
          size_bytes: 2048,
          modified_at: modifiedAt,
          source: 'nas_video',
          subtitles: [
            {
              path: '/Volumes/Data/Video/Youtube/generic-video.en.sub',
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
      <YoutubeDubPage
        jobs={[] as JobState[]}
        onJobCreated={() => {}}
        onSelectJob={() => {}}
        onOpenJobMedia={() => {}}
      />
    );

    await waitFor(() => expect(mockFetchYoutubeLibrary).toHaveBeenCalled());
    expect(await screen.findByText(/generic-video\.mkv/i)).toBeInTheDocument();
    expect(screen.getAllByText(/NAS video/i).length).toBeGreaterThan(0);
    expect(screen.getByText(/SUB \(en\)/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Target resolution/i)).toHaveValue('480');
    expect(screen.getByRole('checkbox', { name: /Keep original aspect ratio/i })).toBeChecked();
  });
});
