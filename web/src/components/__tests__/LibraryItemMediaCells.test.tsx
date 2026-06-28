import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import type { LibraryItem } from '../../api/dtos';
import {
  LibraryBookCell,
  LibraryJobTypeGlyph,
  LibrarySubtitleCell,
  LibraryVideoCell
} from '../library-list/LibraryItemMediaCells';
import { LibraryItemStatusStack } from '../library-list/LibraryItemStatusStack';

vi.mock('../../api/client', () => ({
  appendAccessToken: (url: string) => `token:${url}`,
  resolveLibraryMediaUrl: (jobId: string, relativePath: string) => `library:${jobId}:${relativePath}`
}));

function item(overrides: Partial<LibraryItem> = {}): LibraryItem {
  return {
    jobId: 'job-1',
    author: 'Author',
    bookTitle: 'Book',
    itemType: 'book',
    language: 'en',
    status: 'finished',
    mediaCompleted: true,
    createdAt: '2026-06-23T10:00:00Z',
    updatedAt: '2026-06-23T10:00:00Z',
    libraryPath: '/library/job-1',
    metadata: {},
    ...overrides,
  };
}

describe('LibraryItemMediaCells', () => {
  it('renders book metadata and opens without bubbling to the row', () => {
    const onOpen = vi.fn();
    const onParentClick = vi.fn();
    render(
      <div onClick={onParentClick}>
        <LibraryBookCell
          item={item({
            bookTitle: 'The Test Book',
            author: 'Ada Reader',
            metadata: { media_metadata: { summary: 'A compact summary.' } },
          })}
          onOpen={onOpen}
          disabled={false}
        />
      </div>,
    );

    expect(screen.getByText('The Test Book')).toBeInTheDocument();
    expect(screen.getByText('Ada Reader')).toBeInTheDocument();
    expect(screen.getByText('A compact summary.')).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: 'Play The Test Book' }));

    expect(onOpen).toHaveBeenCalledTimes(1);
    expect(onParentClick).not.toHaveBeenCalled();
  });

  it('renders subtitle episode metadata', () => {
    render(
      <LibrarySubtitleCell
        item={item({
          itemType: 'narrated_subtitle',
          author: '',
          metadata: {
            series_title: 'Series Name',
            episode_title: 'Episode Name',
            series_genres: ['Drama'],
            media_metadata: {
              episode: { season: 1, number: 2, airdate: '2026-06-01', summary: 'Episode summary' },
            },
          },
        })}
        onOpen={vi.fn()}
        disabled={false}
      />,
    );

    expect(screen.getByText('Series Name')).toBeInTheDocument();
    expect(screen.getByText('S01E02')).toBeInTheDocument();
    expect(screen.getByText('Episode Name')).toBeInTheDocument();
    expect(screen.getByText('Drama')).toBeInTheDocument();
    expect(screen.getByText('Episode summary')).toBeInTheDocument();
  });

  it('renders YouTube video metadata and source badges', () => {
    render(
      <LibraryVideoCell
        item={item({
          itemType: 'video',
          author: '',
          metadata: {
            request: { source_kind: 'youtube' },
            media_metadata: {
              youtube: {
                title: 'Travel Clip',
                uploader: 'Channel Name',
                description: 'Video summary',
              },
            },
          },
        })}
        onOpen={vi.fn()}
        disabled={false}
      />,
    );

    expect(screen.getByText('Travel Clip')).toBeInTheDocument();
    expect(screen.getByText('Channel Name')).toBeInTheDocument();
    expect(screen.getByText('Video summary')).toBeInTheDocument();
    expect(screen.getByText('YT')).toBeInTheDocument();
    expect(screen.getByText('Dub')).toBeInTheDocument();
  });

  it('renders job glyph and status with resume badge as row atoms', () => {
    const libraryItem = item({ metadata: { job_type: 'youtube_dub' } });
    render(
      <>
        <LibraryJobTypeGlyph item={libraryItem} />
        <LibraryItemStatusStack
          item={libraryItem}
          resumeBadge={{
            label: 'Continue 1:23',
            title: 'Continue video playback from 1:23',
            position: 83,
            updatedAt: 1_782_234_000,
            mediaType: 'video',
          }}
        />
      </>,
    );

    expect(screen.getByText('Finished')).toBeInTheDocument();
    expect(screen.getByText('Continue 1:23')).toBeInTheDocument();
    expect(screen.queryByText('Newly completed')).not.toBeInTheDocument();
    expect(screen.getByTitle('YouTube dub job')).toBeInTheDocument();
  });

  it('renders smart attention badges for fresh and missing library rows', () => {
    const freshItem = item({
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
    });
    const missingItem = item({ mediaCompleted: false });
    const { rerender } = render(<LibraryItemStatusStack item={freshItem} />);

    expect(screen.getByText('Newly completed')).toBeInTheDocument();
    expect(screen.getByTitle('Completed recently; ready to start listening.')).toHaveAttribute(
      'data-variant',
      'new',
    );

    rerender(<LibraryItemStatusStack item={missingItem} />);

    expect(screen.getByText('Needs attention')).toBeInTheDocument();
    expect(screen.getByTitle('Media is missing; re-sync or regenerate before playback.')).toHaveAttribute(
      'data-variant',
      'attention',
    );
  });
});
