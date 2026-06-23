import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import CreateBookPage from '../CreateBookPage';
import {
  fetchBookCreationOptions,
  submitBookJob,
  type BookCreationOptionsResponse,
} from '../../api/createBook';

vi.mock('../../api/createBook', () => ({
  fetchBookCreationOptions: vi.fn(),
  submitBookJob: vi.fn(),
}));

vi.mock('../../components/book-narration/BookNarrationForm', () => ({
  default: vi.fn((props) => (
    <div data-testid="book-narration-form">
      <div data-testid="forced-base-output">{props.forcedBaseOutputFile}</div>
      <div data-testid="image-defaults">
        {JSON.stringify(props.defaultImageSettings)}
      </div>
      <div data-testid="pipeline-defaults">
        {JSON.stringify(props.defaultPipelineSettings)}
      </div>
      {props.customSourceSection}
    </div>
  )),
}));

const creationOptions: BookCreationOptionsResponse = {
  sentence_bounds: {
    min: 3,
    max: 120,
    default: 45,
  },
  defaults: {
    topic: '',
    book_name: '',
    genre: '',
    author: 'Pipeline Author',
    input_language: 'English',
    output_language: 'Arabic',
    voice: 'gTTS',
  },
  pipeline_defaults: {
    sentences_per_output_file: 12,
    stitch_full: true,
    audio_mode: '2',
    audio_bitrate_kbps: 128,
    written_mode: '3',
    selected_voice: 'macOS-auto',
    generate_audio: false,
    output_html: true,
    output_pdf: false,
    include_transliteration: false,
    translation_provider: 'googletrans',
    translation_batch_size: 8,
    transliteration_mode: 'python',
    enable_lookup_cache: false,
    lookup_cache_batch_size: 6,
    tempo: 1.1,
  },
  generated_source_defaults: {
    add_images: true,
    image_prompt_pipeline: 'prompt_plan',
    image_style_template: 'ink',
    image_prompt_context_sentences: 1,
    image_width: '384',
    image_height: '512',
  },
  supported_input_languages: ['English'],
  supported_output_languages: ['Arabic'],
  supported_voices: ['gTTS'],
};

describe('CreateBookPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(fetchBookCreationOptions).mockResolvedValue(creationOptions);
    vi.mocked(submitBookJob).mockResolvedValue({
      job_id: 'job-1',
      status: 'pending',
      created_at: new Date(0).toISOString(),
      job_type: 'book',
    });
  });

  it('uses backend creation options for generated-book prompt defaults', async () => {
    vi.mocked(fetchBookCreationOptions).mockResolvedValue({
      ...creationOptions,
      defaults: {
        ...creationOptions.defaults,
        topic: 'Backend topic',
        book_name: 'Backend Book',
        genre: 'Backend genre',
      },
    });

    render(<CreateBookPage />);

    await waitFor(() => expect(fetchBookCreationOptions).toHaveBeenCalled());

    expect(screen.getByLabelText(/Topic/i)).toHaveValue('Backend topic');
    expect(screen.getByLabelText(/Book name/i)).toHaveValue('Backend Book');
    expect(screen.getByLabelText(/Genre/i)).toHaveValue('Backend genre');
    const sentenceInput = screen.getByLabelText(/Number of sentences/i);
    expect(sentenceInput).toHaveAttribute('min', '3');
    expect(sentenceInput).toHaveAttribute('max', '120');
    expect(sentenceInput).toHaveValue(45);
    expect(screen.getByLabelText(/Author/i)).toHaveValue('Pipeline Author');
    expect(screen.getByTestId('forced-base-output')).toHaveTextContent('backend-book');
    expect(screen.getByTestId('image-defaults')).toHaveTextContent('"image_style_template":"ink"');
    expect(screen.getByTestId('image-defaults')).toHaveTextContent('"image_width":"384"');
    expect(screen.getByTestId('pipeline-defaults')).toHaveTextContent('"target_languages":["Arabic"]');
    expect(screen.getByTestId('pipeline-defaults')).toHaveTextContent('"sentences_per_output_file":12');
    expect(screen.getByTestId('pipeline-defaults')).toHaveTextContent('"audio_bitrate_kbps":128');
    expect(screen.getByTestId('pipeline-defaults')).toHaveTextContent('"translation_provider":"googletrans"');
    expect(screen.getByTestId('pipeline-defaults')).toHaveTextContent('"enable_lookup_cache":false');
  });

  it('preserves generated-book prompt edits when backend defaults arrive late', async () => {
    let resolveOptions: ((value: BookCreationOptionsResponse) => void) | null = null;
    vi.mocked(fetchBookCreationOptions).mockImplementationOnce(
      () =>
        new Promise<BookCreationOptionsResponse>((resolve) => {
          resolveOptions = resolve;
        }),
    );

    render(<CreateBookPage />);

    await act(async () => {
      fireEvent.change(screen.getByLabelText(/Topic/i), { target: { value: 'My topic' } });
      fireEvent.change(screen.getByLabelText(/Book name/i), { target: { value: 'My Book' } });
      fireEvent.change(screen.getByLabelText(/Genre/i), { target: { value: 'My genre' } });
      await Promise.resolve();
    });

    await act(async () => {
      resolveOptions?.({
        ...creationOptions,
        defaults: {
          ...creationOptions.defaults,
          topic: 'Backend topic',
          book_name: 'Backend Book',
          genre: 'Backend genre',
        },
      });
      await Promise.resolve();
    });

    await waitFor(() => expect(screen.getByLabelText(/Author/i)).toHaveValue('Pipeline Author'));

    expect(screen.getByLabelText(/Topic/i)).toHaveValue('My topic');
    expect(screen.getByLabelText(/Book name/i)).toHaveValue('My Book');
    expect(screen.getByLabelText(/Genre/i)).toHaveValue('My genre');
    expect(screen.getByTestId('forced-base-output')).toHaveTextContent('my-book');
  });

  it('preserves cleared generated-book prompt edits when backend defaults arrive late', async () => {
    let resolveOptions: ((value: BookCreationOptionsResponse) => void) | null = null;
    vi.mocked(fetchBookCreationOptions).mockImplementationOnce(
      () =>
        new Promise<BookCreationOptionsResponse>((resolve) => {
          resolveOptions = resolve;
        }),
    );

    render(<CreateBookPage />);

    await act(async () => {
      fireEvent.change(screen.getByLabelText(/Topic/i), { target: { value: 'Temporary topic' } });
      fireEvent.change(screen.getByLabelText(/Topic/i), { target: { value: '' } });
      await Promise.resolve();
    });

    await act(async () => {
      resolveOptions?.({
        ...creationOptions,
        defaults: {
          ...creationOptions.defaults,
          topic: 'Backend topic',
          book_name: 'Backend Book',
          genre: 'Backend genre',
        },
      });
      await Promise.resolve();
    });

    await waitFor(() => expect(screen.getByLabelText(/Book name/i)).toHaveValue('Backend Book'));

    expect(screen.getByLabelText(/Topic/i)).toHaveValue('');
    expect(screen.getByLabelText(/Genre/i)).toHaveValue('Backend genre');
  });
});
