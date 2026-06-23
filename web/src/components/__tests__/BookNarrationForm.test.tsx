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
  checkImageNodeAvailability,
  lookupBookOpenLibraryMetadataPreview,
  synthesizeVoicePreview,
  uploadEpubFile
} from '../../api/client';
import { LanguageProvider } from '../../context/LanguageProvider';
import { BookNarrationForm } from '../book-narration/BookNarrationForm';

vi.mock('../../api/client', () => ({
  fetchPipelineFiles: vi.fn(),
  fetchPipelineDefaults: vi.fn(),
  fetchLlmModels: vi.fn(),
  fetchVoiceInventory: vi.fn(),
  checkImageNodeAvailability: vi.fn(),
  lookupBookOpenLibraryMetadataPreview: vi.fn(),
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

function installMemoryLocalStorage() {
  const values = new Map<string, string>();
  const storage: Storage = {
    get length() {
      return values.size;
    },
    clear: () => values.clear(),
    getItem: (key) => values.get(key) ?? null,
    key: (index) => Array.from(values.keys())[index] ?? null,
    removeItem: (key) => {
      values.delete(key);
    },
    setItem: (key, value) => {
      values.set(key, String(value));
    }
  };
  Object.defineProperty(window, 'localStorage', {
    configurable: true,
    value: storage
  });
  Object.defineProperty(globalThis, 'localStorage', {
    configurable: true,
    value: storage
  });
}

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
  installMemoryLocalStorage();
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
  vi.mocked(checkImageNodeAvailability).mockResolvedValue({
    nodes: [],
    available: [],
    unavailable: []
  });
  vi.mocked(lookupBookOpenLibraryMetadataPreview).mockResolvedValue({
    source_name: null,
    query: null,
    media_metadata_lookup: null
  });
  vi.mocked(synthesizeVoicePreview).mockResolvedValue(new Blob());
});

afterEach(() => {
  vi.clearAllMocks();
  window.localStorage.clear();
  resolveDefaults = null;
  resolveFiles = null;
});

function renderWithLanguageProvider(ui: Parameters<typeof render>[0]) {
  return render(<LanguageProvider>{ui}</LanguageProvider>);
}

async function openFormTab(user: ReturnType<typeof userEvent.setup>, name: RegExp | string) {
  await user.click(screen.getByRole('tab', { name }));
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

function getInputLanguageField(): HTMLSelectElement {
  const element = document.getElementById('input_language');
  if (!element) {
    throw new Error('Unable to locate the input language field');
  }
  return element as HTMLSelectElement;
}

describe('BookNarrationForm', () => {
  it('submits normalized payloads when valid', async () => {
    const user = userEvent.setup();
    const handleSubmit = vi.fn<[PipelineRequestPayload], Promise<void>>().mockResolvedValue();

    await act(async () => {
      renderWithLanguageProvider(<BookNarrationForm onSubmit={handleSubmit} />);
    });

    await waitFor(() => expect(fetchPipelineDefaults).toHaveBeenCalled());
    await waitFor(() => expect(fetchPipelineFiles).toHaveBeenCalled());
    await resolveFetches();

    await user.clear(screen.getByLabelText(/Input file path/i));
    await user.type(screen.getByLabelText(/Input file path/i), '/tmp/input.txt');
    await user.clear(screen.getByLabelText(/Base output file/i));
    await user.type(screen.getByLabelText(/Base output file/i), 'output');

    await openFormTab(user, /Language & translation/i);
    await user.selectOptions(getInputLanguageField(), 'English');
    const targetSelect = getTargetLanguageSelect();
    expect(getSelectedTargetLanguages(targetSelect)).toEqual(['Arabic']);
    await user.selectOptions(targetSelect, 'German');
    await user.type(
      screen.getByLabelText(/Additional target languages/i),
      'French, Italian, german',
    );

    await openFormTab(user, /Output & narration/i);
    const overrideSelect = await screen.findByLabelText(/Voice override for English/i);
    await user.selectOptions(overrideSelect, 'macOS-auto');

    await user.click(screen.getByRole('button', { name: /Submit job/i }));
    expect(handleSubmit).toHaveBeenCalled();

    const firstCall = handleSubmit.mock.calls[0];
    expect(firstCall).toBeDefined();
    if (!firstCall) {
      throw new Error('Expected the form submission handler to receive a payload');
    }
    const [payload] = firstCall;
    expect(payload.inputs.target_languages).toEqual(['German', 'French', 'Italian']);
    expect(payload.config).toEqual({});
    expect(payload.inputs.generate_audio).toBe(true);
    expect(payload.inputs.voice_overrides).toEqual({ en: 'macOS-auto' });
    expect(payload.pipeline_overrides.voice_overrides).toEqual({ en: 'macOS-auto' });
  }, 10000);

  it('promotes edited genre and ISBN metadata into config overrides on submit', async () => {
    const user = userEvent.setup();
    const handleSubmit = vi.fn<[PipelineRequestPayload], Promise<void>>().mockResolvedValue();

    await act(async () => {
      renderWithLanguageProvider(<BookNarrationForm onSubmit={handleSubmit} />);
    });

    await waitFor(() => expect(fetchPipelineDefaults).toHaveBeenCalled());
    await waitFor(() => expect(fetchPipelineFiles).toHaveBeenCalled());
    await resolveFetches();

    await user.clear(screen.getByLabelText(/Input file path/i));
    await user.type(screen.getByLabelText(/Input file path/i), '/tmp/input.epub');
    await user.clear(screen.getByLabelText(/Base output file/i));
    await user.type(screen.getByLabelText(/Base output file/i), 'output');

    await openFormTab(user, /Metadata/i);
    fireEvent.change(screen.getByLabelText(/^Title$/i), { target: { value: 'Example Book' } });
    fireEvent.change(screen.getByLabelText(/^Author$/i), { target: { value: 'Jane Doe' } });
    fireEvent.change(screen.getByLabelText(/^ISBN$/i), { target: { value: '9780140328721' } });
    fireEvent.change(screen.getByLabelText(/^Genre$/i), { target: { value: 'Adventure, Fantasy' } });
    fireEvent.change(screen.getByLabelText(/^Language$/i), { target: { value: 'eng' } });

    await user.click(screen.getByRole('button', { name: /Submit job/i }));

    expect(handleSubmit).toHaveBeenCalled();
    const [payload] = handleSubmit.mock.calls[0];
    expect(payload.config).toMatchObject({
      book_title: 'Example Book',
      book_author: 'Jane Doe',
      book_genre: 'Adventure, Fantasy',
      book_genres: ['Adventure', 'Fantasy'],
      book_language: 'eng',
      book_isbn: '9780140328721',
    });
    expect(payload.inputs.book_metadata).toMatchObject({
      book_title: 'Example Book',
      book_author: 'Jane Doe',
      book_genre: 'Adventure, Fantasy',
      book_genres: ['Adventure', 'Fantasy'],
      book_language: 'eng',
      book_isbn: '9780140328721',
      isbn: '9780140328721',
    });
  }, 10000);

  it('promotes lookup genre metadata into config overrides on submit', async () => {
    const user = userEvent.setup();
    const handleSubmit = vi.fn<[PipelineRequestPayload], Promise<void>>().mockResolvedValue();
    vi.mocked(lookupBookOpenLibraryMetadataPreview).mockResolvedValue({
      source_name: 'input.epub',
      query: {
        title: 'Lookup Book',
        author: 'Jane Doe',
        isbn: '9780140328721',
      },
      media_metadata_lookup: {
        book: {
          title: 'Lookup Book',
          author: 'Jane Doe',
          isbn: '9780140328721',
          genre: ['Adventure', 'Fantasy'],
          language: 'eng',
          summary: 'Lookup summary',
        },
      },
    });

    await act(async () => {
      renderWithLanguageProvider(<BookNarrationForm onSubmit={handleSubmit} />);
    });

    await waitFor(() => expect(fetchPipelineDefaults).toHaveBeenCalled());
    await waitFor(() => expect(fetchPipelineFiles).toHaveBeenCalled());
    await resolveFetches();

    await user.clear(screen.getByLabelText(/Input file path/i));
    await user.type(screen.getByLabelText(/Input file path/i), '/tmp/input.epub');
    await user.clear(screen.getByLabelText(/Base output file/i));
    await user.type(screen.getByLabelText(/Base output file/i), 'output');

    await openFormTab(user, /Metadata/i);
    await waitFor(() => expect(lookupBookOpenLibraryMetadataPreview).toHaveBeenCalled());
    await waitFor(() => expect(screen.getByLabelText(/^Genre$/i)).toHaveValue('Adventure, Fantasy'));
    await waitFor(() => expect(screen.getByLabelText(/^Language$/i)).toHaveValue('eng'));

    await user.click(screen.getByRole('button', { name: /Submit job/i }));

    expect(handleSubmit).toHaveBeenCalled();
    const [payload] = handleSubmit.mock.calls[0];
    expect(payload.config).toMatchObject({
      book_title: 'Lookup Book',
      book_author: 'Jane Doe',
      book_genre: 'Adventure, Fantasy',
      book_genres: ['Adventure', 'Fantasy'],
      book_language: 'eng',
      book_isbn: '9780140328721',
    });
    expect(payload.inputs.book_metadata).toMatchObject({
      book_title: 'Lookup Book',
      book_author: 'Jane Doe',
      book_genre: 'Adventure, Fantasy',
      book_genres: ['Adventure', 'Fantasy'],
      book_language: 'eng',
      book_isbn: '9780140328721',
      isbn: '9780140328721',
    });
  }, 10000);

  it('prefills the form with defaults from the API response', async () => {
    await act(async () => {
      renderWithLanguageProvider(<BookNarrationForm onSubmit={vi.fn()} />);
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
          add_images: true,
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

    const user = userEvent.setup();
    await openFormTab(user, /Metadata/i);
    expect(screen.getByLabelText(/^Title$/i)).toHaveValue('Example Book');
    expect(screen.getByLabelText(/^Author$/i)).toHaveValue('Jane Doe');

    await openFormTab(user, /Language & translation/i);
    expect(getInputLanguageField()).toHaveValue('Spanish');
    const prefilledTargets = getSelectedTargetLanguages();
    expect(prefilledTargets).toEqual(['German']);
    expect(screen.getByLabelText(/Sentences per chunk/i)).toHaveValue(8);
    expect(screen.getByLabelText(/Start sentence/i)).toHaveValue(2);
    expect(screen.getByLabelText(/End sentence/i)).toHaveValue('42');
    expect(screen.getByLabelText(/Stitch full document once complete/i)).toBeChecked();

    await openFormTab(user, /Output & narration/i);
    expect(screen.getByLabelText(/Generate narration tracks/i)).not.toBeChecked();
    expect(screen.getByLabelText(/Generate HTML output/i)).not.toBeChecked();
    expect(screen.getByLabelText(/Generate PDF output/i)).toBeChecked();
    expect(screen.getByLabelText(/Include transliteration in written output/i)).toBeChecked();
    expect(screen.getByLabelText(/Tempo/i)).toHaveValue(1.25);

    await openFormTab(user, /Images/i);
    expect(screen.getByLabelText(/Add AI-generated images/i)).toBeChecked();
  });

  it('applies create-specific pipeline defaults without waiting for global defaults', async () => {
    const handleSubmit = vi.fn<[PipelineRequestPayload], Promise<void>>().mockResolvedValue();
    const user = userEvent.setup();

    await act(async () => {
      renderWithLanguageProvider(
        <BookNarrationForm
          onSubmit={handleSubmit}
          forcedBaseOutputFile="generated-source"
          defaultPipelineSettings={{
            input_language: 'Spanish',
            target_languages: ['German'],
            sentences_per_output_file: 14,
            audio_mode: '2',
            audio_bitrate_kbps: 128,
            written_mode: '3',
            selected_voice: 'macOS-auto-male',
            generate_audio: false,
            output_html: true,
            output_pdf: true,
            include_transliteration: false,
            translation_provider: 'googletrans',
            translation_batch_size: 7,
            transliteration_mode: 'python',
            enable_lookup_cache: false,
            lookup_cache_batch_size: 4,
            tempo: 1.2,
          }}
        />
      );
    });

    await waitFor(() => expect(fetchPipelineDefaults).toHaveBeenCalled());
    await waitFor(() => expect(fetchPipelineFiles).toHaveBeenCalled());
    await resolveFetches();

    await openFormTab(user, /Language & translation/i);
    await waitFor(() => expect(getInputLanguageField()).toHaveValue('Spanish'));
    expect(getSelectedTargetLanguages()).toEqual(['German']);
    expect(screen.getByLabelText(/Sentences per chunk/i)).toHaveValue(14);
    expect(screen.getByLabelText(/Use Google Translate/i)).toBeChecked();
    expect(screen.getByLabelText(/^Transliteration mode$/i)).toHaveValue('python');
    expect(screen.getByLabelText(/Cache word lookups/i)).not.toBeChecked();

    await openFormTab(user, /Output & narration/i);
    expect(screen.getByLabelText(/Generate narration tracks/i)).not.toBeChecked();
    expect(screen.getByLabelText(/Audio quality/i)).toHaveValue('128');
    expect(screen.getByLabelText(/Narration voice/i)).toHaveValue('macOS-auto-male');
    expect(screen.getByLabelText(/Generate HTML output/i)).toBeChecked();
    expect(screen.getByLabelText(/Generate PDF output/i)).toBeChecked();
    expect(screen.getByLabelText(/Include transliteration in written output/i)).not.toBeChecked();
    expect(screen.getByLabelText(/Tempo/i)).toHaveValue(1.2);

    await openFormTab(user, /Performance tuning/i);
    expect(screen.getByLabelText(/LLM batch size/i)).toHaveValue(7);

    await openFormTab(user, /^Source$/i);
    await user.clear(screen.getByLabelText(/Input file path/i));
    await user.type(screen.getByLabelText(/Input file path/i), '/tmp/generated.epub');
    await user.click(screen.getByRole('button', { name: /Submit job/i }));

    expect(handleSubmit).toHaveBeenCalled();
    const [payload] = handleSubmit.mock.calls[0];
    expect(payload.inputs.base_output_file).toBe('generated-source');
    expect(payload.inputs.input_language).toBe('Spanish');
    expect(payload.inputs.target_languages).toEqual(['German']);
    expect(payload.inputs.enable_lookup_cache).toBe(false);
    expect(payload.inputs.lookup_cache_batch_size).toBe(4);
  });

  it('allows selecting files from the dialog', async () => {
    const user = userEvent.setup();
    await act(async () => {
      renderWithLanguageProvider(<BookNarrationForm onSubmit={vi.fn()} />);
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
      renderWithLanguageProvider(<BookNarrationForm onSubmit={vi.fn()} activeSection="source" />);
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
      renderWithLanguageProvider(<BookNarrationForm onSubmit={handleSubmit} />);
    });

    await waitFor(() => expect(fetchPipelineDefaults).toHaveBeenCalled());
    await waitFor(() => expect(fetchPipelineFiles).toHaveBeenCalled());
    await resolveFetches();

    await user.clear(screen.getByLabelText(/Input file path/i));
    await user.type(screen.getByLabelText(/Input file path/i), '/tmp/input.txt');
    await user.clear(screen.getByLabelText(/Base output file/i));
    await user.type(screen.getByLabelText(/Base output file/i), 'output');

    await openFormTab(user, /Language & translation/i);
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

  it('treats small end sentence values as offsets when configured', async () => {
    const user = userEvent.setup();
    const handleSubmit = vi.fn<[PipelineRequestPayload], Promise<void>>().mockResolvedValue();

    await act(async () => {
      renderWithLanguageProvider(
        <BookNarrationForm onSubmit={handleSubmit} implicitEndOffsetThreshold={200} />
      );
    });

    await waitFor(() => expect(fetchPipelineDefaults).toHaveBeenCalled());
    await waitFor(() => expect(fetchPipelineFiles).toHaveBeenCalled());
    await resolveFetches();

    await user.clear(screen.getByLabelText(/Input file path/i));
    await user.type(screen.getByLabelText(/Input file path/i), '/tmp/input.txt');
    await user.clear(screen.getByLabelText(/Base output file/i));
    await user.type(screen.getByLabelText(/Base output file/i), 'output');

    await openFormTab(user, /Language & translation/i);
    const startField = screen.getByLabelText(/Start sentence/i);
    await user.clear(startField);
    await user.type(startField, '500');

    const endField = screen.getByLabelText(/End sentence/i);
    await user.clear(endField);
    await user.type(endField, '50');

    await user.click(screen.getByRole('button', { name: /Submit job/i }));

    expect(handleSubmit).toHaveBeenCalled();
    const [payload] = handleSubmit.mock.calls[0];
    expect(payload.inputs.start_sentence).toBe(500);
    expect(payload.inputs.end_sentence).toBe(549);
  });
});
