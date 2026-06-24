import { act, renderHook, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import {
  clearMediaMetadataCache,
  lookupBookOpenLibraryMetadata
} from '../../api/client';
import { useJobProgressMetadataLookup } from '../job-progress/useJobProgressMetadataLookup';

vi.mock('../../api/client', () => ({
  clearMediaMetadataCache: vi.fn(),
  lookupBookOpenLibraryMetadata: vi.fn()
}));

const mockClearMediaMetadataCache = vi.mocked(clearMediaMetadataCache);
const mockLookupBookOpenLibraryMetadata = vi.mocked(lookupBookOpenLibraryMetadata);

function lookupResponse(mediaMetadataLookup: Record<string, unknown> | null) {
  return {
    job_id: 'job-123',
    source_name: 'job-123',
    query: null,
    media_metadata_lookup: mediaMetadataLookup
  };
}

function renderLookupHook(
  overrides: Partial<Parameters<typeof useJobProgressMetadataLookup>[0]> = {}
) {
  const onReload = vi.fn();
  const result = renderHook((props: Parameters<typeof useJobProgressMetadataLookup>[0]) =>
    useJobProgressMetadataLookup(props),
    {
      initialProps: {
        jobId: 'job-123',
        metadata: {},
        onReload,
        ...overrides
      }
    }
  );

  return { ...result, onReload };
}

describe('useJobProgressMetadataLookup', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockClearMediaMetadataCache.mockResolvedValue({ cleared: 1 });
    mockLookupBookOpenLibraryMetadata.mockResolvedValue(lookupResponse(null));
  });

  it('resolves an existing ISBN from book metadata for placeholders and clearing', async () => {
    const { onReload, result } = renderLookupHook({
      metadata: {
        book_isbn: ' 978-0-14-032872-1 ',
        isbn: 'legacy-isbn'
      }
    });

    expect(result.current.existingIsbn).toBe('978-0-14-032872-1');

    await act(async () => {
      await result.current.handleClearMetadata();
    });

    expect(mockClearMediaMetadataCache).toHaveBeenCalledWith('9780140328721');
    expect(onReload).toHaveBeenCalledTimes(1);
    expect(result.current.isbnLookupQuery).toBe('');
    expect(result.current.lookupError).toBeNull();
    expect(result.current.lookupResult).toBeNull();
  });

  it('looks up OpenLibrary metadata and reloads after a successful title result', async () => {
    mockLookupBookOpenLibraryMetadata.mockResolvedValueOnce(
      lookupResponse({
        provider: 'openlibrary',
        confidence: 'high',
        book: {
          title: 'Matilda'
        }
      })
    );
    const { onReload, result } = renderLookupHook();

    await act(async () => {
      await result.current.handleLookupMetadata(true);
    });

    expect(mockLookupBookOpenLibraryMetadata).toHaveBeenCalledWith('job-123', { force: true });
    expect(result.current.lookupResult).toEqual({
      success: true,
      source: 'openlibrary',
      confidence: 'high'
    });
    expect(result.current.lookupError).toBeNull();
    expect(result.current.isLookingUp).toBe(false);
    expect(onReload).toHaveBeenCalledTimes(1);
  });

  it('surfaces backend lookup errors without reloading', async () => {
    mockLookupBookOpenLibraryMetadata.mockResolvedValueOnce(
      lookupResponse({
        error: 'No ISBN candidate'
      })
    );
    const { onReload, result } = renderLookupHook();

    await act(async () => {
      await result.current.handleLookupMetadata(false);
    });

    expect(result.current.lookupError).toBe('No ISBN candidate');
    expect(result.current.lookupResult).toEqual({ success: false });
    expect(onReload).not.toHaveBeenCalled();
  });

  it('reports missing title results as not found', async () => {
    mockLookupBookOpenLibraryMetadata.mockResolvedValueOnce(
      lookupResponse({
        provider: 'openlibrary',
        book: {
          author: 'Someone'
        }
      })
    );
    const { onReload, result } = renderLookupHook();

    await act(async () => {
      await result.current.handleLookupMetadata(false);
    });

    expect(result.current.lookupError).toBe('No book metadata found.');
    expect(result.current.lookupResult).toEqual({ success: false });
    expect(onReload).not.toHaveBeenCalled();
  });

  it('reports thrown lookup errors and clears loading state', async () => {
    mockLookupBookOpenLibraryMetadata.mockRejectedValueOnce(new Error('network failed'));
    const { result } = renderLookupHook();

    await act(async () => {
      await result.current.handleLookupMetadata(false);
    });

    expect(result.current.lookupError).toBe('network failed');
    expect(result.current.lookupResult).toBeNull();
    expect(result.current.isLookingUp).toBe(false);
  });

  it('clears frontend state even when backend cache clear fails', async () => {
    mockClearMediaMetadataCache.mockRejectedValueOnce(new Error('cache unavailable'));
    const { onReload, result } = renderLookupHook();

    act(() => {
      result.current.setIsbnLookupQuery(' 978-0-14-032872-1 ');
    });
    await waitFor(() => expect(result.current.isbnLookupQuery).toBe(' 978-0-14-032872-1 '));

    await act(async () => {
      await result.current.handleClearMetadata();
    });

    expect(mockClearMediaMetadataCache).toHaveBeenCalledWith('9780140328721');
    expect(result.current.isbnLookupQuery).toBe('');
    expect(result.current.lookupError).toBeNull();
    expect(result.current.lookupResult).toBeNull();
    expect(onReload).toHaveBeenCalledTimes(1);
  });
});
