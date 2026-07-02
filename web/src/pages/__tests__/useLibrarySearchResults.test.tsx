import { act, renderHook, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import type { LibraryItem, ResumePositionEntry } from '../../api/dtos';
import { searchLibrary } from '../../api/client';
import { fetchResumePositions } from '../../api/client/resume';
import { useLibrarySearchResults } from '../library/useLibrarySearchResults';

vi.mock('../../api/client', () => ({
  searchLibrary: vi.fn(),
}));

vi.mock('../../api/client/resume', () => ({
  fetchResumePositions: vi.fn(),
}));

function item(overrides: Partial<LibraryItem> = {}): LibraryItem {
  return {
    jobId: 'job-1',
    author: 'Author',
    bookTitle: 'Book',
    itemType: 'book',
    genre: 'Novel',
    language: 'en',
    status: 'finished',
    mediaCompleted: true,
    createdAt: '2026-07-01T10:00:00Z',
    updatedAt: '2026-07-01T10:00:00Z',
    libraryPath: '/library/job-1',
    metadata: {},
    ...overrides,
  };
}

function resumeEntry(overrides: Partial<ResumePositionEntry> = {}): ResumePositionEntry {
  return {
    job_id: 'job-1',
    kind: 'time',
    updated_at: 1,
    position: 12,
    ...overrides,
  };
}

function renderSearchHook(overrides: Partial<Parameters<typeof useLibrarySearchResults>[0]> = {}) {
  return renderHook((props: Parameters<typeof useLibrarySearchResults>[0]) =>
    useLibrarySearchResults(props),
    {
      initialProps: {
        effectiveQuery: '',
        page: 1,
        pageSize: 25,
        refreshKey: 0,
        view: 'flat',
        ...overrides,
      },
    },
  );
}

describe('useLibrarySearchResults', () => {
  beforeEach(() => {
    vi.mocked(searchLibrary).mockReset();
    vi.mocked(fetchResumePositions).mockReset();
  });

  it('loads library rows and batched resume evidence for visible jobs', async () => {
    const libraryItems = [item({ jobId: 'job-1' }), item({ jobId: 'job-2' })];
    const resume = [resumeEntry({ job_id: 'job-1' })];
    vi.mocked(searchLibrary).mockResolvedValue({
      total: 2,
      page: 1,
      limit: 25,
      view: 'flat',
      items: libraryItems,
      groups: null,
    });
    vi.mocked(fetchResumePositions).mockResolvedValue({ entries: resume });

    const { result } = renderSearchHook({ effectiveQuery: 'dan brown' });

    await waitFor(() => expect(result.current.items).toEqual(libraryItems));
    await waitFor(() => expect(result.current.resumeEntries).toEqual(resume));

    expect(searchLibrary).toHaveBeenCalledWith({
      query: 'dan brown',
      view: 'flat',
      page: 1,
      limit: 25,
    });
    expect(fetchResumePositions).toHaveBeenCalledWith(['job-1', 'job-2']);
    expect(result.current.total).toBe(2);
    expect(result.current.error).toBeNull();
    expect(result.current.isLoading).toBe(false);
  });

  it('reconciles the selected item when refreshed results include an update', async () => {
    const first = item({ jobId: 'job-1', bookTitle: 'Original' });
    const updated = item({ jobId: 'job-1', bookTitle: 'Updated' });
    vi.mocked(searchLibrary)
      .mockResolvedValueOnce({
        total: 1,
        page: 1,
        limit: 25,
        view: 'flat',
        items: [first],
        groups: null,
      })
      .mockResolvedValueOnce({
        total: 1,
        page: 1,
        limit: 25,
        view: 'flat',
        items: [updated],
        groups: null,
      });
    vi.mocked(fetchResumePositions).mockResolvedValue({ entries: [] });

    const { result, rerender } = renderSearchHook();
    await waitFor(() => expect(result.current.items).toEqual([first]));

    act(() => {
      result.current.setSelectedItem(first);
    });
    expect(result.current.selectedItem).toBe(first);

    rerender({
      effectiveQuery: '',
      page: 1,
      pageSize: 25,
      refreshKey: 1,
      view: 'flat',
    });

    await waitFor(() => expect(result.current.items).toEqual([updated]));
    await waitFor(() => expect(result.current.selectedItem).toBe(updated));
  });

  it('clears rows, selection, and resume evidence on search failure', async () => {
    vi.mocked(searchLibrary).mockRejectedValue(new Error('NAS unavailable'));

    const { result } = renderSearchHook();

    await waitFor(() => expect(result.current.error).toBe('NAS unavailable'));

    expect(result.current.items).toEqual([]);
    expect(result.current.resumeEntries).toEqual([]);
    expect(result.current.selectedItem).toBeNull();
    expect(result.current.total).toBe(0);
    expect(result.current.isLoading).toBe(false);
    expect(fetchResumePositions).not.toHaveBeenCalled();
  });
});
