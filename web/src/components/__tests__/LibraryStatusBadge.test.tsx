import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import type { LibraryItem } from '../../api/dtos';
import { LibraryStatusBadge } from '../library-list/LibraryStatusBadge';

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

describe('LibraryStatusBadge', () => {
  it('renders completed, paused, and missing media states', () => {
    const { rerender } = render(<LibraryStatusBadge item={item()} />);

    expect(screen.getByText('Finished')).toBeInTheDocument();
    expect(screen.getByTitle('Completed')).toHaveAttribute('data-variant', 'ready');

    rerender(<LibraryStatusBadge item={item({ status: 'paused' })} />);

    expect(screen.getByText('Paused')).toBeInTheDocument();
    expect(screen.getByTitle('Paused')).toHaveAttribute('data-variant', 'ready');

    rerender(<LibraryStatusBadge item={item({ mediaCompleted: false })} />);

    expect(screen.getByText('Media removed')).toBeInTheDocument();
    expect(screen.getByTitle('Cancelled')).toHaveAttribute('data-variant', 'missing');
  });
});
