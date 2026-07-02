import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import type { SubtitleTvMetadataPreviewResponse } from '../../api/dtos';
import VideoTvMetadataPreview from '../video-dubbing/VideoTvMetadataPreview';

const preview: SubtitleTvMetadataPreviewResponse = {
  source_name: 'Readable.History.S02E03.mkv',
  parsed: {
    series: 'Readable History',
    season: 2,
    episode: 3,
    pattern: 'sxxexx'
  },
  media_metadata: null
};

const draft = {
  job_label: 'Readable History S02E03',
  show: {
    name: 'Readable History',
    tmdb_id: 12345,
    imdb_id: 'tt1234567',
    image: {
      medium: 'https://example.invalid/poster-medium.jpg',
      original: 'https://example.invalid/poster-original.jpg'
    }
  },
  episode: {
    season: 2,
    number: 3,
    name: 'Source Maps',
    airdate: '2026-07-01',
    url: 'https://example.invalid/episode',
    image: {
      medium: 'https://example.invalid/still-medium.jpg',
      original: 'https://example.invalid/still-original.jpg'
    }
  }
};

describe('VideoTvMetadataPreview', () => {
  it('renders TV metadata summary, artwork, editable fields, and raw payload', () => {
    render(
      <VideoTvMetadataPreview
        metadataSourceName="Fallback.mkv"
        metadataPreview={preview}
        mediaMetadataDraft={draft}
        onUpdateMediaMetadataDraft={vi.fn()}
        onUpdateMediaMetadataSection={vi.fn()}
      />
    );

    expect(screen.getByRole('img', { name: 'Readable History poster' })).toHaveAttribute(
      'src',
      'https://example.invalid/poster-medium.jpg'
    );
    expect(screen.getByRole('img', { name: 'Source Maps still' })).toHaveAttribute(
      'src',
      'https://example.invalid/still-medium.jpg'
    );
    expect(screen.getByText('Readable.History.S02E03.mkv')).toBeInTheDocument();
    expect(screen.getByText('Readable History S02E03')).toBeInTheDocument();
    expect(screen.getByText('S02E03 — Source Maps')).toBeInTheDocument();
    expect(screen.getByLabelText('Job label')).toHaveValue('Readable History S02E03');
    expect(screen.getByLabelText('TMDB ID')).toHaveValue(12345);
    expect(screen.getByText('Raw payload')).toBeInTheDocument();
  });

  it('passes trimmed field updates to the metadata draft helpers', () => {
    const draftUpdates: Record<string, unknown>[] = [];
    const sectionUpdates: Array<{ section: string; value: Record<string, unknown> }> = [];
    const onUpdateMediaMetadataDraft = vi.fn((updater: (draft: Record<string, unknown>) => void) => {
      const nextDraft: Record<string, unknown> = { job_label: 'Old label' };
      updater(nextDraft);
      draftUpdates.push(nextDraft);
    });
    const onUpdateMediaMetadataSection = vi.fn((
      section: string,
      updater: (draft: Record<string, unknown>) => void
    ) => {
      const nextSection: Record<string, unknown> = {};
      updater(nextSection);
      sectionUpdates.push({ section, value: nextSection });
    });

    render(
      <VideoTvMetadataPreview
        metadataSourceName="Fallback.mkv"
        metadataPreview={preview}
        mediaMetadataDraft={draft}
        onUpdateMediaMetadataDraft={onUpdateMediaMetadataDraft}
        onUpdateMediaMetadataSection={onUpdateMediaMetadataSection}
      />
    );

    fireEvent.change(screen.getByLabelText('Job label'), { target: { value: '  Updated Label  ' } });
    fireEvent.change(screen.getByLabelText('Show'), { target: { value: '  Updated Show  ' } });
    fireEvent.change(screen.getByLabelText('Season'), { target: { value: '4' } });
    fireEvent.change(screen.getByLabelText('Episode'), { target: { value: '' } });

    expect(draftUpdates.at(-1)).toEqual({ job_label: 'Updated Label' });
    expect(sectionUpdates).toContainEqual({ section: 'show', value: { name: 'Updated Show' } });
    expect(sectionUpdates).toContainEqual({ section: 'episode', value: { season: 4 } });
    expect(sectionUpdates).toContainEqual({ section: 'episode', value: {} });
  });
});
