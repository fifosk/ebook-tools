import { fireEvent, render, screen } from '@testing-library/react';
import type { ComponentProps } from 'react';
import { describe, expect, it, vi } from 'vitest';
import type { LibraryItem } from '../../api/dtos';
import { LibraryFlatTable } from '../library-list/LibraryFlatTable';

vi.mock('../../api/client', () => ({
  appendAccessToken: (url: string) => `token:${url}`,
  resolveLibraryMediaUrl: (jobId: string, relativePath: string) => `library:${jobId}:${relativePath}`,
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

function renderTable(overrides: Partial<ComponentProps<typeof LibraryFlatTable>> = {}) {
  return render(
    <LibraryFlatTable
      items={[item()]}
      flatLayout="books"
      resumeBadges={new Map()}
      onOpen={vi.fn()}
      onRemove={vi.fn()}
      onEditMetadata={vi.fn()}
      {...overrides}
    />,
  );
}

describe('LibraryFlatTable', () => {
  it('renders the book table with language, status, and row selection', () => {
    const onSelect = vi.fn();
    renderTable({
      onSelect,
      selectedJobId: 'job-1',
      resumeBadges: new Map([
        [
          'job-1',
          {
            label: 'Continue 1:23',
            title: 'Continue audio playback from 1:23',
            position: 83,
            updatedAt: 1,
            mediaType: 'audio',
          },
        ],
      ]),
    });

    expect(screen.getByRole('columnheader', { name: 'Book' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Play Book' })).toBeInTheDocument();
    expect(screen.getByText('English')).toBeInTheDocument();
    expect(screen.getByText('Finished')).toBeInTheDocument();
    expect(screen.getByText('Continue 1:23')).toBeInTheDocument();

    fireEvent.click(screen.getAllByRole('row')[1]);

    expect(onSelect).toHaveBeenCalledWith(expect.objectContaining({ jobId: 'job-1' }));
  });

  it('renders mixed rows and does not select rows without view permission', () => {
    const onSelect = vi.fn();
    renderTable({
      items: [
        item({
          jobId: 'job-mixed',
          bookTitle: 'Mixed Media',
          author: 'Creator',
          itemType: 'video',
          language: 'it',
        }),
      ],
      flatLayout: null,
      onSelect,
      resolvePermissions: () => ({ canView: false, canEdit: false, canExport: false }),
    });

    expect(screen.getByRole('columnheader', { name: 'Title' })).toBeInTheDocument();
    expect(screen.getByRole('columnheader', { name: 'Job' })).toBeInTheDocument();
    expect(screen.getByText('Mixed Media')).toBeInTheDocument();
    expect(screen.getByText('Creator')).toBeInTheDocument();
    expect(screen.getByText('Italian')).toBeInTheDocument();

    fireEvent.click(screen.getAllByRole('row')[1]);

    expect(onSelect).not.toHaveBeenCalled();
  });
});
