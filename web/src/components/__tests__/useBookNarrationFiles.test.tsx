import { act, renderHook, waitFor } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { useRef, useState } from 'react';
import { deletePipelineEbook, fetchPipelineFiles, uploadEpubFile } from '../../api/client';
import type { PipelineFileBrowserResponse } from '../../api/dtos';
import { DEFAULT_FORM_STATE } from '../book-narration/bookNarrationFormDefaults';
import type { FormState } from '../book-narration/bookNarrationFormTypes';
import { useBookNarrationFiles } from '../book-narration/useBookNarrationFiles';

vi.mock('../../api/client', () => ({
  deletePipelineEbook: vi.fn(),
  fetchPipelineFiles: vi.fn(),
  uploadEpubFile: vi.fn(),
}));

const mockFetchPipelineFiles = vi.mocked(fetchPipelineFiles);
const mockDeletePipelineEbook = vi.mocked(deletePipelineEbook);
const mockUploadEpubFile = vi.mocked(uploadEpubFile);

const fileListing: PipelineFileBrowserResponse = {
  ebooks: [
    {
      name: 'Older Source.epub',
      path: '/nas/books/Older Source.epub',
      type: 'file',
      modified_at: '2026-06-23T10:00:00Z',
    },
    {
      name: 'Newest NAS Book.epub',
      path: '/nas/books/Newest NAS Book.epub',
      type: 'file',
      modified_at: '2026-06-25T10:00:00Z',
    },
  ],
  outputs: [],
  books_root: '/nas/books',
  output_root: '/nas/output',
};

function renderFilesHook(
  overrides: Partial<Parameters<typeof useBookNarrationFiles>[0]> = {},
) {
  const markUserEditedField = vi.fn();
  const resolveStartFromHistory = vi.fn((inputPath: string) =>
    inputPath.includes('Newest NAS Book') ? 42 : null,
  );
  const result = renderHook(() => {
    const [formState, setFormState] = useState<FormState>(DEFAULT_FORM_STATE);
    const prefillAppliedRef = useRef<string | null>(null);
    const userEditedStartRef = useRef(false);
    const userEditedInputRef = useRef(false);
    const userEditedEndRef = useRef(false);
    const lastAutoEndSentenceRef = useRef<string | null>(null);
    const hook = useBookNarrationFiles({
      isGeneratedSource: false,
      forcedBaseOutputFile: null,
      markUserEditedField,
      normalizePath: (value) => value?.trim().toLowerCase() ?? null,
      resolveStartFromHistory,
      setFormState,
      prefillAppliedRef,
      userEditedStartRef,
      userEditedInputRef,
      userEditedEndRef,
      lastAutoEndSentenceRef,
      ...overrides,
    });
    return {
      formState,
      hook,
      refs: {
        lastAutoEndSentenceRef,
        prefillAppliedRef,
        userEditedEndRef,
        userEditedInputRef,
        userEditedStartRef,
      },
    };
  });

  return { ...result, markUserEditedField, resolveStartFromHistory };
}

describe('useBookNarrationFiles', () => {
  afterEach(() => {
    vi.clearAllMocks();
  });

  it('loads backend-visible EPUBs and selects the newest default source', async () => {
    mockFetchPipelineFiles.mockResolvedValue(fileListing);

    const { result, resolveStartFromHistory } = renderFilesHook();

    await waitFor(() => expect(result.current.hook.isLoadingFiles).toBe(false));
    await waitFor(() =>
      expect(result.current.formState.input_file).toBe('/nas/books/Newest NAS Book.epub'),
    );

    expect(mockFetchPipelineFiles).toHaveBeenCalledTimes(1);
    expect(result.current.hook.fileOptions).toEqual(fileListing);
    expect(result.current.formState.base_output_file).toBe('newest-nas-book');
    expect(result.current.formState.start_sentence).toBe(42);
    expect(result.current.refs.userEditedStartRef.current).toBe(false);
    expect(resolveStartFromHistory).toHaveBeenCalledWith('/nas/books/Newest NAS Book.epub');
  });

  it('skips server file discovery for generated-book sources', async () => {
    const { result } = renderFilesHook({ isGeneratedSource: true });

    await waitFor(() => expect(result.current.hook.isLoadingFiles).toBe(false));

    expect(mockFetchPipelineFiles).not.toHaveBeenCalled();
    expect(result.current.hook.fileOptions).toBeNull();
    expect(result.current.formState.input_file).toBe('');
  });

  it('rejects non-EPUB uploads before calling the backend', async () => {
    mockFetchPipelineFiles.mockResolvedValue(fileListing);
    const { result } = renderFilesHook();

    await waitFor(() => expect(result.current.hook.isLoadingFiles).toBe(false));
    await act(async () => {
      await result.current.hook.processFileUpload(new File(['not an epub'], 'notes.txt'));
    });

    await waitFor(() =>
      expect(result.current.hook.uploadError).toBe('Only EPUB files can be imported.'),
    );
    expect(mockUploadEpubFile).not.toHaveBeenCalled();
    expect(mockDeletePipelineEbook).not.toHaveBeenCalled();
  });
});
