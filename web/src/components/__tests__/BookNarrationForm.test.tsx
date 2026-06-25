import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, vi } from 'vitest';
import userEvent from '@testing-library/user-event';
import type {
  AcquisitionArtifactResponse,
  CreationTemplateEntry,
  AcquisitionDiscoveryResponse,
  AcquisitionProviderListResponse,
  PipelineDefaultsResponse,
  PipelineFileBrowserResponse,
  PipelineIntakeStatusResponse,
  PipelineRequestPayload
} from '../../api/dtos';
import {
  fetchPipelineDefaults,
  fetchPipelineFiles,
  fetchPipelineIntakeStatus,
  fetchLlmModels,
  acquireAcquisitionCandidate,
  discoverAcquisitionCandidates,
  fetchAcquisitionProviders,
  fetchVoiceInventory,
  checkImageNodeAvailability,
  lookupBookOpenLibraryMetadataPreview,
  saveCreationTemplate,
  synthesizeVoicePreview,
  uploadEpubFile
} from '../../api/client';
import { LanguageProvider } from '../../context/LanguageProvider';
import { BookNarrationForm } from '../book-narration/BookNarrationForm';

vi.mock('../../api/client', () => ({
  fetchPipelineFiles: vi.fn(),
  fetchPipelineDefaults: vi.fn(),
  fetchPipelineIntakeStatus: vi.fn(),
  fetchLlmModels: vi.fn(),
  acquireAcquisitionCandidate: vi.fn(),
  discoverAcquisitionCandidates: vi.fn(),
  fetchAcquisitionProviders: vi.fn(),
  fetchVoiceInventory: vi.fn(),
  checkImageNodeAvailability: vi.fn(),
  lookupBookOpenLibraryMetadataPreview: vi.fn(),
  saveCreationTemplate: vi.fn(),
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

const mockDiscoveryResponse: AcquisitionDiscoveryResponse = {
  candidates: [
    {
      candidate_id: 'local_epub:discovered.epub',
      provider: 'local_epub',
      media_kind: 'book',
      title: 'Discovered Book',
      rights: 'user_provided',
      capabilities: ['import_local', 'metadata'],
      candidate_token: 'token',
      contributors: [],
      local_path: 'discovered.epub',
      subtitles: [],
      metadata: {},
      requires_confirmation: false,
      policy_notes: []
    }
  ],
  policy_notes: ['Discovery results are candidates only.'],
  providers_queried: ['local_epub']
};

const mockGutenbergDiscoveryResponse: AcquisitionDiscoveryResponse = {
  candidates: [
    {
      candidate_id: 'gutenberg:84',
      provider: 'gutenberg',
      media_kind: 'book',
      title: 'Frankenstein',
      rights: 'public_domain',
      capabilities: ['search', 'metadata', 'acquire'],
      candidate_token: 'gutenberg-token',
      contributors: ['Shelley, Mary Wollstonecraft'],
      language: 'en',
      source_url: 'https://www.gutenberg.org/ebooks/84.html.images',
      cover_url: 'https://www.gutenberg.org/cache/epub/84/pg84.cover.medium.jpg',
      subtitles: [],
      metadata: {
        source_kind: 'gutenberg',
        gutenberg_id: 84,
        epub_url: 'https://www.gutenberg.org/ebooks/84.epub3.images'
      },
      requires_confirmation: true,
      policy_notes: ['Confirm public-domain status before acquisition.']
    }
  ],
  policy_notes: ['Discovery results are candidates only.'],
  providers_queried: ['gutenberg']
};

const mockInternetArchiveDiscoveryResponse: AcquisitionDiscoveryResponse = {
  candidates: [
    {
      candidate_id: 'internet_archive:demo_public_book',
      provider: 'internet_archive',
      media_kind: 'book',
      title: 'Demo Public Book',
      rights: 'public_domain',
      capabilities: ['search', 'metadata', 'acquire'],
      candidate_token: 'internet-archive-token',
      contributors: ['Archive Author'],
      language: 'eng',
      source_url: 'https://archive.org/details/demo_public_book',
      cover_url: 'https://archive.org/services/img/demo_public_book',
      size_bytes: 4567,
      subtitles: [],
      metadata: {
        source_kind: 'internet_archive',
        identifier: 'demo_public_book',
        epub_file: 'demo_public_book.epub',
        epub_url: 'https://archive.org/download/demo_public_book/demo_public_book.epub'
      },
      requires_confirmation: true,
      policy_notes: ['Confirm public or open access before acquisition.']
    }
  ],
  policy_notes: ['Discovery results are candidates only.'],
  providers_queried: ['internet_archive']
};

const mockOpenLibraryDiscoveryResponse: AcquisitionDiscoveryResponse = {
  candidates: [
    {
      candidate_id: 'openlibrary:/works/OL45883W',
      provider: 'openlibrary',
      media_kind: 'book',
      title: 'Demo Metadata Book',
      rights: 'unknown',
      capabilities: ['search', 'metadata'],
      candidate_token: 'openlibrary-token',
      contributors: ['Metadata Author'],
      language: 'eng',
      year: 2003,
      source_url: 'https://openlibrary.org/works/OL45883W',
      cover_url: 'https://covers.openlibrary.org/b/id/12345-L.jpg',
      subtitles: [],
      metadata: {
        source_kind: 'openlibrary',
        openlibrary_work_key: '/works/OL45883W',
        openlibrary_work_url: 'https://openlibrary.org/works/OL45883W',
      },
      requires_confirmation: false,
      policy_notes: ['Metadata-only result.']
    }
  ],
  policy_notes: ['Discovery results are candidates only.'],
  providers_queried: ['openlibrary']
};

const mockAcquisitionArtifact: AcquisitionArtifactResponse = {
  provider: 'gutenberg',
  media_kind: 'book',
  status: 'completed',
  artifact_path: 'Frankenstein.epub',
  local_path: 'Frankenstein.epub',
  filename: 'Frankenstein.epub',
  size_bytes: 12345,
  modified_at: '2026-06-25T12:00:00Z',
  next_actions: ['create_book_job', 'load_content_index'],
  metadata: {
    source_kind: 'gutenberg',
    gutenberg_id: 84
  }
};

const mockInternetArchiveAcquisitionArtifact: AcquisitionArtifactResponse = {
  provider: 'internet_archive',
  media_kind: 'book',
  status: 'completed',
  artifact_path: 'Demo Public Book.epub',
  local_path: 'Demo Public Book.epub',
  filename: 'Demo Public Book.epub',
  size_bytes: 4567,
  modified_at: '2026-06-25T12:30:00Z',
  next_actions: ['create_book_job', 'load_content_index'],
  metadata: {
    source_kind: 'internet_archive',
    identifier: 'demo_public_book'
  }
};

const mockAcquisitionProviders: AcquisitionProviderListResponse = {
  providers: [
    {
      id: 'local_epub',
      label: 'Local EPUB library',
      media_kinds: ['book'],
      capabilities: ['import_local', 'metadata'],
      status: 'available',
      configured: true,
      available: true,
      rights: ['user_provided'],
      policy_notes: [],
      next_actions: []
    },
    {
      id: 'manual_downloads',
      label: 'Manual download folders',
      media_kinds: ['book', 'video'],
      capabilities: ['import_local', 'extract_subtitles', 'metadata'],
      status: 'available',
      configured: true,
      available: true,
      rights: ['user_provided'],
      policy_notes: [],
      next_actions: []
    },
    {
      id: 'gutenberg',
      label: 'Project Gutenberg/Gutendex',
      media_kinds: ['book'],
      capabilities: ['search', 'metadata', 'acquire'],
      status: 'available',
      configured: true,
      available: true,
      rights: ['public_domain', 'open_license'],
      policy_notes: [],
      next_actions: []
    },
    {
      id: 'internet_archive',
      label: 'Internet Archive',
      media_kinds: ['book'],
      capabilities: ['search', 'metadata', 'acquire'],
      status: 'available',
      configured: true,
      available: true,
      rights: ['public_domain', 'open_license', 'unknown'],
      policy_notes: [],
      next_actions: []
    },
    {
      id: 'openlibrary',
      label: 'Open Library metadata',
      media_kinds: ['book'],
      capabilities: ['search', 'metadata'],
      status: 'available',
      configured: true,
      available: true,
      rights: ['unknown'],
      policy_notes: [],
      next_actions: []
    }
  ],
  policy_notes: [],
  paths: {}
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
  vi.mocked(fetchPipelineIntakeStatus).mockResolvedValue(null);
  vi.mocked(fetchLlmModels).mockResolvedValue([]);
  vi.mocked(acquireAcquisitionCandidate).mockResolvedValue(mockAcquisitionArtifact);
  vi.mocked(discoverAcquisitionCandidates).mockResolvedValue(mockDiscoveryResponse);
  vi.mocked(fetchAcquisitionProviders).mockResolvedValue(mockAcquisitionProviders);
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
    await waitFor(() => expect(fetchPipelineIntakeStatus).toHaveBeenCalledTimes(2));
  }, 10000);

  it('saves current narration settings as a sanitized creation template', async () => {
    const user = userEvent.setup();
    vi.mocked(saveCreationTemplate).mockResolvedValue({
      id: 'template-1',
      name: 'output',
      mode: 'narrate_ebook',
      created_at: 1,
      updated_at: 2,
      payload: {}
    });

    await act(async () => {
      renderWithLanguageProvider(<BookNarrationForm onSubmit={vi.fn()} />);
    });

    await waitFor(() => expect(fetchPipelineDefaults).toHaveBeenCalled());
    await waitFor(() => expect(fetchPipelineFiles).toHaveBeenCalled());
    await resolveFetches();

    fireEvent.change(screen.getByLabelText(/Input file path/i), {
      target: { value: '/tmp/input.epub' }
    });
    fireEvent.change(screen.getByLabelText(/Base output file/i), {
      target: { value: 'output' }
    });
    await user.click(screen.getByRole('button', { name: /Save template/i }));

    await waitFor(() => expect(saveCreationTemplate).toHaveBeenCalledTimes(1));
    const [template] = vi.mocked(saveCreationTemplate).mock.calls[0];
    expect(template.name).toBe('output');
    expect(template.mode).toBe('narrate_ebook');
    expect(template.payload.source).toBe('web');
    expect(template.payload.kind).toBe('book_narration_form');
    const savedFormState = template.payload.form_state as Record<string, unknown>;
    expect(savedFormState).toMatchObject({
      input_file: '/tmp/input.epub',
      base_output_file: 'output',
      environment_overrides: '{}'
    });
    expect(await screen.findByText(/Saved template "output"/i)).toBeInTheDocument();
  });

  it('applies a deep-linked narration creation template before backend defaults overwrite it', async () => {
    const user = userEvent.setup();
    const template: CreationTemplateEntry = {
      id: 'template-1',
      name: 'Current book continuation',
      mode: 'narrate_ebook',
      created_at: 1,
      updated_at: 2,
      payload: {
        kind: 'book_narration_form',
        source: 'web',
        source_mode: 'upload',
        active_section: 'source',
        form_state: {
          input_file: '/books/current.epub',
          base_output_file: 'current-continuation',
          input_language: 'Spanish',
          target_languages: ['German', 'French'],
          enable_lookup_cache: false
        }
      }
    };

    await act(async () => {
      renderWithLanguageProvider(
        <BookNarrationForm onSubmit={vi.fn()} creationTemplate={template} />
      );
    });

    await waitFor(() => expect(fetchPipelineDefaults).toHaveBeenCalled());
    await waitFor(() => expect(fetchPipelineFiles).toHaveBeenCalled());
    await resolveFetches({
      defaults: {
        config: {
          input_file: '/books/default.epub',
          base_output_file: 'default-output',
          input_language: 'English',
          target_languages: ['Arabic'],
          enable_lookup_cache: true
        }
      }
    });

    expect(await screen.findByText(/Applied template "Current book continuation"/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Input file path/i)).toHaveValue('/books/current.epub');
    expect(screen.getByLabelText(/Base output file/i)).toHaveValue('current-continuation');

    await openFormTab(user, /Language & translation/i);
    expect(getInputLanguageField()).toHaveValue('Spanish');
    expect(getSelectedTargetLanguages()).toEqual(['German']);
    expect(screen.getByLabelText(/Additional target languages/i)).toHaveValue('French');
    expect(screen.getByLabelText(/Cache word lookups/i)).not.toBeChecked();
  });

  it('includes backend-supported language lists in the narration pickers', async () => {
    await act(async () => {
      renderWithLanguageProvider(
        <BookNarrationForm
          onSubmit={vi.fn()}
          activeSection="language"
          supportedInputLanguages={['Backend Input Language', 'English']}
          supportedTargetLanguages={['Backend Target Language', 'Arabic']}
        />
      );
    });

    await waitFor(() => expect(fetchPipelineDefaults).toHaveBeenCalled());
    await waitFor(() => expect(fetchPipelineFiles).toHaveBeenCalled());
    await resolveFetches();

    const inputOptions = Array.from(getInputLanguageField().options).map((option) => option.value);
    const targetOptions = Array.from(getTargetLanguageSelect().options).map((option) => option.value);

    expect(inputOptions).toContain('Backend Input Language');
    expect(targetOptions).toContain('Backend Target Language');
  });

  it('shows queue capacity and blocks submit when intake is closed', async () => {
    const user = userEvent.setup();
    const handleSubmit = vi.fn<[PipelineRequestPayload], Promise<void>>().mockResolvedValue();
    const intake: PipelineIntakeStatusResponse = {
      acceptingJobs: false,
      isUnderPressure: true,
      queueDepth: 6,
      activeCount: 2,
      softLimit: 3,
      hardLimit: 6,
      delayCount: 5
    };
    vi.mocked(fetchPipelineIntakeStatus).mockResolvedValue(intake);

    await act(async () => {
      renderWithLanguageProvider(<BookNarrationForm onSubmit={handleSubmit} />);
    });

    await waitFor(() => expect(fetchPipelineIntakeStatus).toHaveBeenCalled());
    await resolveFetches();

    await user.clear(screen.getByLabelText(/Input file path/i));
    await user.type(screen.getByLabelText(/Input file path/i), '/tmp/input.txt');
    await user.clear(screen.getByLabelText(/Base output file/i));
    await user.type(screen.getByLabelText(/Base output file/i), 'output');

    const alert = await screen.findByRole('alert');
    expect(alert).toHaveTextContent('Job queue is at capacity');
    expect(alert).toHaveTextContent('Delayed jobs: 5');
    expect(alert).toHaveTextContent('Slowdown starts at 3 pending');
    expect(alert).toHaveTextContent('Capacity limit is 6 pending');
    expect(screen.getByRole('button', { name: /Submit job/i })).toBeDisabled();
    expect(handleSubmit).not.toHaveBeenCalled();
  }, 10000);

  it('shows an intake loading state before the queue snapshot arrives', async () => {
    let resolveIntake: ((value: PipelineIntakeStatusResponse | null) => void) | null = null;
    vi.mocked(fetchPipelineIntakeStatus).mockImplementation(
      () =>
        new Promise<PipelineIntakeStatusResponse | null>((resolve) => {
          resolveIntake = resolve;
        })
    );

    await act(async () => {
      renderWithLanguageProvider(<BookNarrationForm onSubmit={vi.fn()} />);
    });

    expect(await screen.findByText('Checking job intake...')).toBeInTheDocument();

    await act(async () => {
      resolveIntake?.({
        acceptingJobs: true,
        isUnderPressure: false,
        queueDepth: 0,
        activeCount: 1,
        softLimit: 3,
        hardLimit: 6,
        delayCount: 0
      });
      await Promise.resolve();
    });

    expect(await screen.findByText('Job intake is available: 0 pending and 1 running.')).toBeInTheDocument();
    expect(screen.queryByText('Checking job intake...')).not.toBeInTheDocument();
  }, 10000);

  it('does not refresh intake status after a rejected submission', async () => {
    const user = userEvent.setup();
    const handleSubmit = vi
      .fn<[PipelineRequestPayload], Promise<void>>()
      .mockRejectedValue(new Error('Backend refused the job'));

    await act(async () => {
      renderWithLanguageProvider(<BookNarrationForm onSubmit={handleSubmit} />);
    });

    await waitFor(() => expect(fetchPipelineDefaults).toHaveBeenCalled());
    await waitFor(() => expect(fetchPipelineFiles).toHaveBeenCalled());
    await waitFor(() => expect(fetchPipelineIntakeStatus).toHaveBeenCalledTimes(1));
    await resolveFetches();

    await user.clear(screen.getByLabelText(/Input file path/i));
    await user.type(screen.getByLabelText(/Input file path/i), '/tmp/input.txt');
    await user.clear(screen.getByLabelText(/Base output file/i));
    await user.type(screen.getByLabelText(/Base output file/i), 'output');

    await user.click(screen.getByRole('button', { name: /Submit job/i }));

    expect(handleSubmit).toHaveBeenCalled();
    expect(await screen.findByRole('alert')).toHaveTextContent('Backend refused the job');
    expect(fetchPipelineIntakeStatus).toHaveBeenCalledTimes(1);
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
    expect(screen.getByLabelText(/Additional target languages/i)).toHaveValue('French');
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
            target_languages: ['German', 'French', 'german', 'Italian'],
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
    expect(screen.getByLabelText(/Additional target languages/i)).toHaveValue('French, Italian');
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
    expect(payload.inputs.target_languages).toEqual(['German', 'French', 'Italian']);
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

  it('allows selecting backend discovery candidates', async () => {
    const user = userEvent.setup();
    await act(async () => {
      renderWithLanguageProvider(<BookNarrationForm onSubmit={vi.fn()} activeSection="source" />);
    });

    await waitFor(() => expect(fetchPipelineDefaults).toHaveBeenCalled());
    await waitFor(() => expect(fetchPipelineFiles).toHaveBeenCalled());
    await resolveFetches();

    await user.click(screen.getByRole('button', { name: /Discover sources/i }));
    await waitFor(() => expect(discoverAcquisitionCandidates).toHaveBeenCalledWith({
      mediaKind: 'book',
      query: '',
      provider: 'local_epub',
      limit: 25
    }));

    expect(await screen.findByRole('dialog', { name: /Discover ebook sources/i })).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: /Use Discovered Book/i }));

    expect(screen.getByLabelText(/Input file path/i)).toHaveValue('discovered.epub');
    expect(screen.queryByRole('dialog', { name: /Discover ebook sources/i })).not.toBeInTheDocument();
  });

  it('acquires Gutenberg discovery candidates before filling the input path', async () => {
    vi.mocked(discoverAcquisitionCandidates)
      .mockResolvedValueOnce(mockDiscoveryResponse)
      .mockResolvedValueOnce(mockGutenbergDiscoveryResponse);
    const user = userEvent.setup();
    await act(async () => {
      renderWithLanguageProvider(<BookNarrationForm onSubmit={vi.fn()} activeSection="source" />);
    });

    await waitFor(() => expect(fetchPipelineDefaults).toHaveBeenCalled());
    await waitFor(() => expect(fetchPipelineFiles).toHaveBeenCalled());
    await resolveFetches();

    await user.click(screen.getByRole('button', { name: /Discover sources/i }));
    await waitFor(() => expect(discoverAcquisitionCandidates).toHaveBeenCalledWith({
      mediaKind: 'book',
      query: '',
      provider: 'local_epub',
      limit: 25
    }));

    await user.click(await screen.findByRole('button', { name: /Gutenberg/i }));
    await waitFor(() => expect(discoverAcquisitionCandidates).toHaveBeenLastCalledWith({
      mediaKind: 'book',
      query: '',
      provider: 'gutenberg',
      limit: 25
    }));

    await user.click(await screen.findByRole('button', { name: /Acquire Frankenstein/i }));

    await waitFor(() => expect(acquireAcquisitionCandidate).toHaveBeenCalledWith({
      candidate_token: 'gutenberg-token',
      confirmed: true,
      filename: 'Frankenstein.epub'
    }));
    expect(screen.getByLabelText(/Input file path/i)).toHaveValue('Frankenstein.epub');
    expect(screen.queryByRole('dialog', { name: /Discover ebook sources/i })).not.toBeInTheDocument();
  });

  it('acquires Internet Archive discovery candidates before filling the input path', async () => {
    vi.mocked(discoverAcquisitionCandidates)
      .mockResolvedValueOnce(mockDiscoveryResponse)
      .mockResolvedValueOnce(mockInternetArchiveDiscoveryResponse);
    vi.mocked(acquireAcquisitionCandidate).mockResolvedValueOnce(mockInternetArchiveAcquisitionArtifact);
    const user = userEvent.setup();
    await act(async () => {
      renderWithLanguageProvider(<BookNarrationForm onSubmit={vi.fn()} activeSection="source" />);
    });

    await waitFor(() => expect(fetchPipelineDefaults).toHaveBeenCalled());
    await waitFor(() => expect(fetchPipelineFiles).toHaveBeenCalled());
    await resolveFetches();

    await user.click(screen.getByRole('button', { name: /Discover sources/i }));
    await waitFor(() => expect(discoverAcquisitionCandidates).toHaveBeenCalledWith({
      mediaKind: 'book',
      query: '',
      provider: 'local_epub',
      limit: 25
    }));

    await user.click(await screen.findByRole('button', { name: /Internet Archive/i }));
    await waitFor(() => expect(discoverAcquisitionCandidates).toHaveBeenLastCalledWith({
      mediaKind: 'book',
      query: '',
      provider: 'internet_archive',
      limit: 25
    }));

    await user.click(await screen.findByRole('button', { name: /Acquire Demo Public Book/i }));

    await waitFor(() => expect(acquireAcquisitionCandidate).toHaveBeenCalledWith({
      candidate_token: 'internet-archive-token',
      confirmed: true,
      filename: 'Demo Public Book.epub'
    }));
    expect(screen.getByLabelText(/Input file path/i)).toHaveValue('Demo Public Book.epub');
    expect(screen.queryByRole('dialog', { name: /Discover ebook sources/i })).not.toBeInTheDocument();
  });

  it('shows Open Library metadata candidates without acquiring them', async () => {
    vi.mocked(discoverAcquisitionCandidates)
      .mockResolvedValueOnce(mockDiscoveryResponse)
      .mockResolvedValueOnce(mockOpenLibraryDiscoveryResponse);
    const user = userEvent.setup();
    await act(async () => {
      renderWithLanguageProvider(<BookNarrationForm onSubmit={vi.fn()} activeSection="source" />);
    });

    await waitFor(() => expect(fetchPipelineDefaults).toHaveBeenCalled());
    await waitFor(() => expect(fetchPipelineFiles).toHaveBeenCalled());
    await resolveFetches();

    await user.click(screen.getByRole('button', { name: /Discover sources/i }));
    await waitFor(() => expect(discoverAcquisitionCandidates).toHaveBeenCalledWith({
      mediaKind: 'book',
      query: '',
      provider: 'local_epub',
      limit: 25
    }));

    await user.click(await screen.findByRole('button', { name: /Open Library/i }));
    await waitFor(() => expect(discoverAcquisitionCandidates).toHaveBeenLastCalledWith({
      mediaKind: 'book',
      query: '',
      provider: 'openlibrary',
      limit: 25
    }));

    const candidateButton = await screen.findByRole('button', {
      name: /Review Demo Metadata Book/i
    });
    expect(candidateButton).toBeDisabled();
    expect(screen.getByText(/metadata catalog/i)).toBeInTheDocument();
    expect(acquireAcquisitionCandidate).not.toHaveBeenCalled();
    expect(screen.getByLabelText(/Input file path/i)).toHaveValue('example.epub');
  });

  it('searches manual download EPUB candidates from the discovery dialog', async () => {
    const user = userEvent.setup();
    await act(async () => {
      renderWithLanguageProvider(<BookNarrationForm onSubmit={vi.fn()} activeSection="source" />);
    });

    await waitFor(() => expect(fetchPipelineDefaults).toHaveBeenCalled());
    await waitFor(() => expect(fetchPipelineFiles).toHaveBeenCalled());
    await resolveFetches();

    await user.click(screen.getByRole('button', { name: /Discover sources/i }));
    await waitFor(() => expect(discoverAcquisitionCandidates).toHaveBeenCalledWith({
      mediaKind: 'book',
      query: '',
      provider: 'local_epub',
      limit: 25
    }));

    await user.click(await screen.findByRole('button', { name: /Manual downloads/i }));
    await waitFor(() => expect(discoverAcquisitionCandidates).toHaveBeenLastCalledWith({
      mediaKind: 'book',
      query: '',
      provider: 'manual_downloads',
      limit: 25
    }));
  });

  it('shows provider readiness when manual discovery is not configured', async () => {
    vi.mocked(fetchAcquisitionProviders).mockResolvedValue({
      ...mockAcquisitionProviders,
      providers: mockAcquisitionProviders.providers.map((provider) =>
        provider.id === 'manual_downloads'
          ? {
              ...provider,
              status: 'not_configured',
              configured: false,
              available: false
            }
          : provider
      )
    });
    const user = userEvent.setup();
    await act(async () => {
      renderWithLanguageProvider(<BookNarrationForm onSubmit={vi.fn()} activeSection="source" />);
    });

    await waitFor(() => expect(fetchPipelineDefaults).toHaveBeenCalled());
    await waitFor(() => expect(fetchPipelineFiles).toHaveBeenCalled());
    await resolveFetches();

    await user.click(screen.getByRole('button', { name: /Discover sources/i }));
    await waitFor(() => expect(fetchAcquisitionProviders).toHaveBeenCalled());
    await waitFor(() => expect(discoverAcquisitionCandidates).toHaveBeenCalledTimes(1));

    await user.click(await screen.findByRole('button', { name: /Manual downloads/i }));

    expect(await screen.findByRole('alert')).toHaveTextContent(
      /Manual download folders is not configured/i
    );
    expect(screen.getByRole('button', { name: /^Search$/i })).toBeDisabled();
    expect(discoverAcquisitionCandidates).toHaveBeenCalledTimes(1);
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
