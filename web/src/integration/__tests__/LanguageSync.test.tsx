import { act, render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { LanguageProvider } from '../../context/LanguageProvider';
import { BookNarrationForm } from '../../components/book-narration/BookNarrationForm';
import CreateBookPage from '../../pages/CreateBookPage';
import {
  fetchPipelineDefaults,
  fetchPipelineFiles,
  fetchLlmModels,
  fetchVoiceInventory,
  synthesizeVoicePreview,
  uploadEpubFile
} from '../../api/client';
import type { PipelineDefaultsResponse, PipelineFileBrowserResponse } from '../../api/dtos';

vi.mock('../../api/client', () => ({
  fetchPipelineFiles: vi.fn(),
  fetchPipelineDefaults: vi.fn(),
  fetchLlmModels: vi.fn(),
  fetchVoiceInventory: vi.fn(),
  synthesizeVoicePreview: vi.fn(),
  uploadEpubFile: vi.fn()
}));

const mockFileListing: PipelineFileBrowserResponse = {
  ebooks: [
    { name: 'demo.epub', path: 'demo.epub', type: 'file' as const }
  ],
  outputs: [
    { name: 'output', path: 'output/output', type: 'directory' as const }
  ],
  books_root: '/workspace/ebooks',
  output_root: '/workspace/output'
};

let resolveDefaults: ((value: PipelineDefaultsResponse) => void) | null = null;
let resolveFiles: ((value: PipelineFileBrowserResponse) => void) | null = null;

async function resolveFetches({
  defaults = { config: {} },
  files = mockFileListing
}: {
  defaults?: PipelineDefaultsResponse;
  files?: PipelineFileBrowserResponse;
} = {}) {
  await act(async () => {
    resolveDefaults?.(defaults);
    resolveDefaults = null;
    resolveFiles?.(files);
    resolveFiles = null;
    await Promise.resolve();
  });
}

beforeEach(() => {
  vi.mocked(fetchPipelineFiles).mockImplementation(
    () =>
      new Promise<PipelineFileBrowserResponse>((resolve) => {
        resolveFiles = resolve;
      })
  );
  vi.mocked(fetchPipelineDefaults).mockImplementation(
    () =>
      new Promise<PipelineDefaultsResponse>((resolve) => {
        resolveDefaults = resolve;
      })
  );
  vi.mocked(fetchLlmModels).mockResolvedValue([]);
  vi.mocked(fetchVoiceInventory).mockResolvedValue({ macos: [], gtts: [], piper: [] });
  vi.mocked(synthesizeVoicePreview).mockResolvedValue(new Blob());
  vi.mocked(uploadEpubFile).mockResolvedValue({
    name: 'uploaded.epub',
    path: 'uploaded.epub',
    type: 'file'
  });
});

afterEach(() => {
  vi.clearAllMocks();
  resolveDefaults = null;
  resolveFiles = null;
});

describe('LanguageProvider synchronization', () => {
  it('keeps CreateBookPage and BookNarrationForm languages in sync', async () => {
    const user = userEvent.setup();

    await act(async () => {
      render(
        <LanguageProvider>
          <div data-testid="pipeline">
            <BookNarrationForm onSubmit={vi.fn()} activeSection="language" />
          </div>
          <div data-testid="create-book">
            <CreateBookPage />
          </div>
        </LanguageProvider>
      );
    });

    await waitFor(() => expect(fetchPipelineDefaults).toHaveBeenCalled());
    await waitFor(() => expect(fetchPipelineFiles).toHaveBeenCalled());
    await resolveFetches();

    const pipeline = within(screen.getByTestId('pipeline'));
    const create = within(screen.getByTestId('create-book'));

    const pipelineTargetSelect = pipeline.getByLabelText(/^Target languages$/i) as HTMLSelectElement;
    const getPipelineTargets = () =>
      Array.from(pipelineTargetSelect.selectedOptions).map((option) => option.value);

    const createOutputLanguage = create.getByLabelText(/Output language/i) as HTMLInputElement;
    expect(createOutputLanguage.value).toBe('Arabic');
    expect(getPipelineTargets()).toEqual(['Arabic']);

    await user.clear(createOutputLanguage);
    await user.type(createOutputLanguage, 'German');

    await waitFor(() => {
      expect(getPipelineTargets()).toEqual(['German']);
    });
    expect(createOutputLanguage.value).toBe('German');

    const pipelineInputLanguage = pipeline.getByLabelText(/^Input language$/i) as HTMLInputElement;
    await user.clear(pipelineInputLanguage);
    await user.type(pipelineInputLanguage, 'Italian');

    await waitFor(() => {
      const createInputLanguage = create.getByLabelText(/Input language/i) as HTMLInputElement;
      expect(createInputLanguage.value).toBe('Italian');
    });
  });
});
