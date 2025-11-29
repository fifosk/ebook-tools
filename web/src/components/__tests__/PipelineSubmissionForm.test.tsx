import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, vi } from 'vitest';
import userEvent from '@testing-library/user-event';
import {
  PipelineDefaultsResponse,
  PipelineFileBrowserResponse,
  PipelineRequestPayload
} from '../../api/dtos';
import {
  fetchPipelineDefaults,
  fetchPipelineFiles,
  fetchLlmModels,
  fetchVoiceInventory,
  synthesizeVoicePreview,
  uploadEpubFile
} from '../../api/client';
import { LanguageProvider } from '../../context/LanguageProvider';
import { PipelineSubmissionForm } from '../PipelineSubmissionForm';

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
    { name: 'example.epub', path: 'example.epub', type: 'file' as const }
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
  vi.mocked(fetchVoiceInventory).mockResolvedValue({ macos: [], gtts: [] });
  vi.mocked(synthesizeVoicePreview).mockResolvedValue(new Blob());
});

afterEach(() => {
  vi.clearAllMocks();
  resolveDefaults = null;
  resolveFiles = null;
});

function renderWithLanguageProvider(ui: Parameters<typeof render>[0]) {
  return render(<LanguageProvider>{ui}</LanguageProvider>);
}

function getTargetLanguageSelect(): HTMLSelectElement {
  const element = document.getElementById('target_languages');
  if (!element) {
    throw new Error('Unable to locate the target languages control');
  }
  return element as HTMLSelectElement;
}

function getSelectedTargetLanguages(selectElement: HTMLSelectElement = getTargetLanguageSelect()) {
  return Array.from(selectElement.selectedOptions).map((option) => option.value);
}

function getInputLanguageField(): HTMLInputElement {
  const element = document.getElementById('input_language');
  if (!element) {
    throw new Error('Unable to locate the input language field');
  }
  return element as HTMLInputElement;
}

describe('PipelineSubmissionForm', () => {
  it('submits normalized payloads when valid', async () => {
    const user = userEvent.setup();
    const handleSubmit = vi.fn<[PipelineRequestPayload], Promise<void>>().mockResolvedValue();

    await act(async () => {
      renderWithLanguageProvider(<PipelineSubmissionForm onSubmit={handleSubmit} />);
    });

    await waitFor(() => expect(fetchPipelineDefaults).toHaveBeenCalled());
    await waitFor(() => expect(fetchPipelineFiles).toHaveBeenCalled());
    await resolveFetches();

    await user.clear(screen.getByLabelText(/Input file path/i));
    await user.type(screen.getByLabelText(/Input file path/i), '/tmp/input.txt');
    await user.clear(screen.getByLabelText(/Base output file/i));
    await user.type(screen.getByLabelText(/Base output file/i), 'output');
    await user.clear(getInputLanguageField());
    await user.type(getInputLanguageField(), 'English');
    const targetSelect = getTargetLanguageSelect();
    expect(getSelectedTargetLanguages(targetSelect)).toEqual(['Arabic']);
    await user.selectOptions(targetSelect, ['Arabic', 'German']);

    const overrideSelect = await screen.findByLabelText(/Voice override for English/i);
    await user.selectOptions(overrideSelect, 'macOS-auto');

    fireEvent.change(screen.getByLabelText(/Config overrides JSON/i), {
      target: { value: '{"debug":true}' }
    });

    await user.click(screen.getByRole('button', { name: /Submit job/i }));
    expect(handleSubmit).toHaveBeenCalled();

    const firstCall = handleSubmit.mock.calls[0];
    expect(firstCall).toBeDefined();
    if (!firstCall) {
      throw new Error('Expected the form submission handler to receive a payload');
    }
    const [payload] = firstCall;
    expect(payload.inputs.target_languages).toEqual(['Arabic', 'German']);
    expect(payload.config).toEqual({ debug: true });
    expect(payload.inputs.generate_audio).toBe(true);
    expect(payload.inputs.voice_overrides).toEqual({ en: 'macOS-auto' });
    expect(payload.pipeline_overrides.voice_overrides).toEqual({ en: 'macOS-auto' });
  }, 10000);

  it('shows an error when JSON input cannot be parsed', async () => {
    const user = userEvent.setup();
    const handleSubmit = vi.fn();

    await act(async () => {
      renderWithLanguageProvider(<PipelineSubmissionForm onSubmit={handleSubmit} />);
    });

    await waitFor(() => expect(fetchPipelineDefaults).toHaveBeenCalled());
    await waitFor(() => expect(fetchPipelineFiles).toHaveBeenCalled());
    await resolveFetches();

    await user.clear(screen.getByLabelText(/Input file path/i));
    await user.type(screen.getByLabelText(/Input file path/i), '/tmp/input.txt');
    await user.clear(screen.getByLabelText(/Base output file/i));
    await user.type(screen.getByLabelText(/Base output file/i), 'output');
    await user.clear(getInputLanguageField());
    await user.type(getInputLanguageField(), 'English');
    expect(getSelectedTargetLanguages()).toEqual(['Arabic']);

    fireEvent.change(screen.getByLabelText(/Config overrides JSON/i), {
      target: { value: '{broken' }
    });

    await user.click(screen.getByRole('button', { name: /Submit job/i }));

    expect(await screen.findByRole('alert')).toHaveTextContent(/invalid json/i);
    expect(handleSubmit).not.toHaveBeenCalled();
  });

  it('prefills the form with defaults from the API response', async () => {
    await act(async () => {
      renderWithLanguageProvider(<PipelineSubmissionForm onSubmit={vi.fn()} />);
    });

    await waitFor(() => expect(fetchPipelineDefaults).toHaveBeenCalled());
    await waitFor(() => expect(fetchPipelineFiles).toHaveBeenCalled());
    await resolveFetches({
      defaults: {
        config: {
          input_file: '/storage/ebooks/default.epub',
          base_output_file: '/output/result',
          input_language: 'Spanish',
          target_languages: ['German', 'French'],
          sentences_per_output_file: 8,
          start_sentence: 2,
          end_sentence: 42,
          stitch_full: true,
          generate_audio: false,
          audio_mode: '2',
          written_mode: '3',
          selected_voice: 'macOS-auto-male',
          output_html: false,
          output_pdf: true,
          generate_video: true,
          include_transliteration: true,
          tempo: 1.25,
          book_title: 'Example Book',
          book_author: 'Jane Doe'
        }
      }
    });

    await waitFor(() =>
      expect(screen.getByLabelText(/Input file path/i)).toHaveValue('/storage/ebooks/default.epub')
    );

    expect(screen.getByLabelText(/Base output file/i)).toHaveValue('/output/result');
    expect(getInputLanguageField()).toHaveValue('Spanish');
    const prefilledTargets = getSelectedTargetLanguages();
    expect(prefilledTargets).toHaveLength(2);
    expect(prefilledTargets).toEqual(expect.arrayContaining(['German', 'French']));
    expect(screen.getByLabelText(/Sentences per output file/i)).toHaveValue(8);
    expect(screen.getByLabelText(/Start sentence/i)).toHaveValue(2);
    expect(screen.getByLabelText(/End sentence/i)).toHaveValue('42');
    expect(screen.getByLabelText(/Stitch full document once complete/i)).toBeChecked();
    expect(screen.getByLabelText(/Generate narration tracks/i)).not.toBeChecked();
    expect(screen.getByLabelText(/Generate HTML output/i)).not.toBeChecked();
    expect(screen.getByLabelText(/Generate PDF output/i)).toBeChecked();
    expect(screen.getByLabelText(/Generate stitched video assets/i)).toBeChecked();
    expect(screen.getByLabelText(/Include transliteration in written output/i)).toBeChecked();
    expect(screen.getByLabelText(/Tempo/i)).toHaveValue(1.25);

    const metadataField = screen.getByLabelText(/Book metadata JSON/i) as HTMLTextAreaElement;
    expect(metadataField.value).toContain('"book_title": "Example Book"');
    expect(metadataField.value).toContain('"book_author": "Jane Doe"');
  });

  it('allows selecting files from the dialog', async () => {
    const user = userEvent.setup();
    await act(async () => {
      renderWithLanguageProvider(<PipelineSubmissionForm onSubmit={vi.fn()} />);
    });

    await waitFor(() => expect(fetchPipelineDefaults).toHaveBeenCalled());
    await waitFor(() => expect(fetchPipelineFiles).toHaveBeenCalled());
    await resolveFetches();

    await user.click(screen.getByRole('button', { name: /browse ebooks/i }));
    await user.click(screen.getByRole('button', { name: /select example.epub/i }));

    expect(screen.getByLabelText(/Input file path/i)).toHaveValue('example.epub');

    await user.click(screen.getByRole('button', { name: /browse output paths/i }));
    await user.click(screen.getByRole('button', { name: /select output/i }));

    expect(screen.getByLabelText(/Base output file/i)).toHaveValue('output/output');
  });

  it('uploads an EPUB via drag and drop', async () => {
    vi.mocked(uploadEpubFile).mockResolvedValue({
      name: 'dropped.epub',
      path: 'dropped.epub',
      type: 'file'
    });

    await act(async () => {
      renderWithLanguageProvider(<PipelineSubmissionForm onSubmit={vi.fn()} activeSection="source" />);
    });

    await waitFor(() => expect(fetchPipelineDefaults).toHaveBeenCalled());
    await waitFor(() => expect(fetchPipelineFiles).toHaveBeenCalled());
    await resolveFetches();

    const dropLabel = screen.getByText(/Drag & drop an EPUB file/i);
    const dropzone = dropLabel.closest('.file-dropzone');
    expect(dropzone).not.toBeNull();

    const file = new File(['ebook'], 'dropped.epub', { type: 'application/epub+zip' });
    fireEvent.drop(dropzone!, {
      dataTransfer: {
        files: [file]
      }
    });

    await waitFor(() => expect(uploadEpubFile).toHaveBeenCalledWith(file));
    resolveFiles?.(mockFileListing);

    await waitFor(() =>
      expect(screen.getByLabelText(/Input file path/i)).toHaveValue('dropped.epub')
    );
  });

  it('converts +offset end sentence values relative to the start sentence', async () => {
    const user = userEvent.setup();
    const handleSubmit = vi.fn<[PipelineRequestPayload], Promise<void>>().mockResolvedValue();

    await act(async () => {
      renderWithLanguageProvider(<PipelineSubmissionForm onSubmit={handleSubmit} />);
    });

    await waitFor(() => expect(fetchPipelineDefaults).toHaveBeenCalled());
    await waitFor(() => expect(fetchPipelineFiles).toHaveBeenCalled());
    await resolveFetches();

    await user.clear(screen.getByLabelText(/Input file path/i));
    await user.type(screen.getByLabelText(/Input file path/i), '/tmp/input.txt');
    await user.clear(screen.getByLabelText(/Base output file/i));
    await user.type(screen.getByLabelText(/Base output file/i), 'output');

    const startField = screen.getByLabelText(/Start sentence/i);
    await user.clear(startField);
    await user.type(startField, '200');

    const endField = screen.getByLabelText(/End sentence/i);
    await user.clear(endField);
    await user.type(endField, '+100');

    await user.click(screen.getByRole('button', { name: /Submit job/i }));

    expect(handleSubmit).toHaveBeenCalled();
    const [payload] = handleSubmit.mock.calls[0];
    expect(payload.inputs.start_sentence).toBe(200);
    expect(payload.inputs.end_sentence).toBe(299);
  });
});
