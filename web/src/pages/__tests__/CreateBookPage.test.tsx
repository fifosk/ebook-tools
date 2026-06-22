import { render, screen, waitFor } from '@testing-library/react';
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
    sentences_per_output_file: 10,
    audio_mode: '4',
    audio_bitrate_kbps: 96,
    written_mode: '4',
    selected_voice: 'gTTS',
    generate_audio: true,
    output_html: false,
    output_pdf: false,
    include_transliteration: true,
    translation_provider: 'llm',
    translation_batch_size: 10,
    transliteration_mode: 'default',
    enable_lookup_cache: true,
    lookup_cache_batch_size: 10,
    tempo: 1,
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
    render(<CreateBookPage />);

    await waitFor(() => expect(fetchBookCreationOptions).toHaveBeenCalled());

    const sentenceInput = screen.getByLabelText(/Number of sentences/i);
    expect(sentenceInput).toHaveAttribute('min', '3');
    expect(sentenceInput).toHaveAttribute('max', '120');
    expect(sentenceInput).toHaveValue(45);
    expect(screen.getByLabelText(/Author/i)).toHaveValue('Pipeline Author');
    expect(screen.getByTestId('image-defaults')).toHaveTextContent('"image_style_template":"ink"');
    expect(screen.getByTestId('image-defaults')).toHaveTextContent('"image_width":"384"');
  });
});
