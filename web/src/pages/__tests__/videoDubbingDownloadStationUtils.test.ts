import { describe, expect, it } from 'vitest';
import type {
  AcquisitionJobStatusResponse,
  YoutubeNasSubtitle,
  YoutubeNasVideo
} from '../../api/dtos';
import {
  findDownloadStationCompletedVideo,
  isDownloadStationHandoffCandidate,
  resolveDownloadStationCompletedFiles
} from '../video-dubbing/videoDubbingDownloadStationUtils';

function subtitle(overrides: Partial<YoutubeNasSubtitle>): YoutubeNasSubtitle {
  return {
    path: '/subs/example.ass',
    filename: 'example.ass',
    language: 'en',
    format: 'ass',
    ...overrides
  };
}

function video(overrides: Partial<YoutubeNasVideo>): YoutubeNasVideo {
  return {
    path: '/videos/example.mkv',
    filename: 'example.mkv',
    folder: '/videos',
    size_bytes: 100,
    modified_at: '2026-06-23T00:00:00Z',
    subtitles: [],
    ...overrides
  };
}

function acquisitionJob(
  overrides: Partial<AcquisitionJobStatusResponse> = {}
): AcquisitionJobStatusResponse {
  return {
    provider: 'download_station',
    task_id: 'task-1',
    status: 'completed',
    progress: 1,
    message: null,
    external_task_id: null,
    raw_status: 'finished',
    started_at: null,
    updated_at: '2026-06-26T12:00:00Z',
    completed_files: [],
    next_actions: ['discover_manual_downloads'],
    metadata: {},
    ...overrides
  };
}

describe('videoDubbingDownloadStationUtils', () => {
  it('detects explicit Download Station handoff candidates with legacy fallback', () => {
    expect(
      isDownloadStationHandoffCandidate({
        provider: 'newznab_torznab',
        metadata: { handoff_provider: 'download_station' }
      })
    ).toBe(true);
    expect(
      isDownloadStationHandoffCandidate({
        provider: 'newznab_torznab',
        metadata: { handoff_provider: ' Download_Station ' }
      })
    ).toBe(true);
    expect(
      isDownloadStationHandoffCandidate({
        provider: 'newznab_torznab',
        metadata: { has_download_url: true }
      })
    ).toBe(true);
    expect(
      isDownloadStationHandoffCandidate({
        provider: 'newznab_torznab',
        metadata: { has_download_url: ' true ' }
      })
    ).toBe(true);
    expect(
      isDownloadStationHandoffCandidate({
        provider: 'youtube_search',
        metadata: { handoff_provider: 'download_station' }
      })
    ).toBe(false);
  });

  it('resolves completed files from top-level status before metadata fallbacks', () => {
    expect(resolveDownloadStationCompletedFiles(null)).toEqual([]);
    expect(
      resolveDownloadStationCompletedFiles(acquisitionJob({
        completed_files: ['/downloads/top-level.mkv'],
        metadata: { completed_files: ['/downloads/metadata.mkv'] }
      }))
    ).toEqual(['/downloads/top-level.mkv']);
    expect(
      resolveDownloadStationCompletedFiles(acquisitionJob({
        metadata: { completed_files: ['/downloads/metadata.mkv'] }
      }))
    ).toEqual(['/downloads/metadata.mkv']);
    expect(
      resolveDownloadStationCompletedFiles(acquisitionJob({
        metadata: { files: ['/downloads/files-array.mkv'] }
      }))
    ).toEqual(['/downloads/files-array.mkv']);
    expect(
      resolveDownloadStationCompletedFiles(acquisitionJob({
        metadata: { completed_file: '/downloads/single.mkv' }
      }))
    ).toEqual(['/downloads/single.mkv']);
  });

  it('matches completed file hints to refreshed NAS videos', () => {
    const videos = [
      video({
        path: '/nas/videos/Other Episode/other.mkv',
        filename: 'other.mkv',
        folder: '/nas/videos/Other Episode'
      }),
      video({
        path: '/nas/videos/Demo Episode/Demo Episode.mkv',
        filename: 'Demo Episode.mkv',
        folder: '/nas/videos/Demo Episode',
        subtitles: [subtitle({ path: '/nas/videos/Demo Episode/Demo Episode.en.srt' })]
      })
    ];

    expect(
      findDownloadStationCompletedVideo(videos, ['/downloads/Demo Episode.mkv'])?.path
    ).toBe('/nas/videos/Demo Episode/Demo Episode.mkv');
    expect(
      findDownloadStationCompletedVideo(videos, ['/downloads/Demo Episode'])?.path
    ).toBe('/nas/videos/Demo Episode/Demo Episode.mkv');
    expect(findDownloadStationCompletedVideo(videos, ['/downloads/missing.mkv'])).toBeNull();
  });
});
