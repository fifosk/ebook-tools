import { act, renderHook, waitFor } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { fetchBookContentIndex } from '../../api/client';
import { useBookNarrationChapters } from '../book-narration/useBookNarrationChapters';

vi.mock('../../api/client', () => ({
  fetchBookContentIndex: vi.fn(),
}));

const mockFetchBookContentIndex = vi.mocked(fetchBookContentIndex);

function renderChaptersHook(
  overrides: Partial<Parameters<typeof useBookNarrationChapters>[0]> = {},
) {
  return renderHook((props: Parameters<typeof useBookNarrationChapters>[0]) =>
    useBookNarrationChapters(props),
  {
    initialProps: {
      inputFile: '/nas/books/Dan Brown Continuation.epub',
      startSentence: 1,
      endSentence: '',
      isGeneratedSource: false,
      implicitEndOffsetThreshold: null,
      normalizedInputPath: '/nas/books/Dan Brown Continuation.epub',
      ...overrides,
    },
  });
}

describe('useBookNarrationChapters', () => {
  afterEach(() => {
    vi.clearAllMocks();
  });

  it('loads backend content-index chapters and estimates the full book duration', async () => {
    mockFetchBookContentIndex.mockResolvedValue({
      input_file: '/nas/books/Dan Brown Continuation.epub',
      content_index: {
        total_sentences: 75,
        chapters: [
          { id: 'prologue', title: 'Prologue', start_sentence: 1, end_sentence: 12 },
          { id: 'chapter-1', title: 'Chapter 1', start_sentence: 13, end_sentence: 40 },
          { id: 'reckoning', title: 'Reckoning', start: 41, sentence_count: 20 },
        ],
      },
    });

    const { result } = renderChaptersHook();

    await waitFor(() => expect(result.current.chaptersLoading).toBe(false));

    expect(mockFetchBookContentIndex).toHaveBeenCalledWith('/nas/books/Dan Brown Continuation.epub');
    expect(result.current.chaptersError).toBeNull();
    expect(result.current.chaptersDisabled).toBe(false);
    expect(result.current.chapterOptions).toEqual([
      { id: 'prologue', title: 'Prologue', startSentence: 1, endSentence: 12 },
      { id: 'chapter-1', title: 'Chapter 1', startSentence: 13, endSentence: 40 },
      { id: 'reckoning', title: 'Reckoning', startSentence: 41, endSentence: 60 },
    ]);
    expect(result.current.estimatedAudioDurationLabel).toBe(
      'Estimated audio duration: ~00:08:00 (75 sentences, 6.4s/sentence)',
    );
  });

  it('selects consecutive chapter ranges for the processing window', async () => {
    mockFetchBookContentIndex.mockResolvedValue({
      input_file: '/nas/books/Dan Brown Continuation.epub',
      content_index: {
        chapters: [
          { id: 'prologue', title: 'Prologue', start_sentence: 1, end_sentence: 12 },
          { id: 'chapter-1', title: 'Chapter 1', start_sentence: 13, end_sentence: 40 },
          { id: 'reckoning', title: 'Reckoning', start_sentence: 41, end_sentence: 60 },
        ],
      },
    });

    const { result } = renderChaptersHook();

    await waitFor(() => expect(result.current.chaptersLoading).toBe(false));
    act(() => {
      result.current.handleChapterModeChange('chapters');
      result.current.handleChapterToggle('chapter-1');
      result.current.handleChapterToggle('reckoning');
    });

    expect(result.current.selectedChapterIds).toEqual(['chapter-1', 'reckoning']);
    expect(result.current.chapterSelection).toEqual({
      startIndex: 1,
      endIndex: 2,
      startSentence: 13,
      endSentence: 60,
      count: 2,
    });
    expect(result.current.chapterSelectionSummary).toBe(
      'Chapter 1 – Reckoning • sentences 13-60',
    );
    expect(result.current.displayStartSentence).toBe(13);
    expect(result.current.displayEndSentence).toBe('60');
  });

  it('skips content-index loading for generated sources', async () => {
    const { result } = renderChaptersHook({
      inputFile: 'Generated in Web Create',
      isGeneratedSource: true,
      normalizedInputPath: null,
    });

    await waitFor(() => expect(result.current.chaptersLoading).toBe(false));

    expect(mockFetchBookContentIndex).not.toHaveBeenCalled();
    expect(result.current.chapterOptions).toEqual([]);
    expect(result.current.chaptersDisabled).toBe(true);
    expect(result.current.chaptersError).toBeNull();
  });

  it('surfaces backend content-index load failures', async () => {
    mockFetchBookContentIndex.mockRejectedValueOnce(new Error('content index unavailable'));

    const { result } = renderChaptersHook();

    await waitFor(() => expect(result.current.chaptersLoading).toBe(false));

    expect(result.current.chaptersError).toBe('content index unavailable');
    expect(result.current.chapterOptions).toEqual([]);
    expect(result.current.estimatedAudioDurationLabel).toBeNull();
  });
});
