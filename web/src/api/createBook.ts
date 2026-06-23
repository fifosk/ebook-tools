import type { PipelineRequestPayload, PipelineSubmissionResponse } from './dtos';
import { apiFetch, handleResponse } from './client';

export interface CreateBookPayload {
  input_language: string;
  output_language: string;
  voice?: string | null;
  num_sentences: number;
  topic: string;
  book_name: string;
  genre: string;
  author?: string;
}

export interface BookCreationResponse {
  job_id?: string | null;
  status: string;
  metadata: Record<string, unknown>;
  messages: string[];
  warnings: string[];
  epub_path: string | null;
  input_file?: string | null;
  sentences_preview: string[];
}

export interface BookCreationOptionsResponse {
  sentence_bounds: {
    min: number;
    max: number;
    default: number;
  };
  defaults: {
    topic: string;
    book_name: string;
    genre: string;
    author: string;
    input_language: string;
    output_language: string;
    voice: string;
  };
  pipeline_defaults: {
    sentences_per_output_file: number;
    stitch_full: boolean;
    audio_mode: string;
    audio_bitrate_kbps: number | null;
    written_mode: string;
    selected_voice: string;
    generate_audio: boolean;
    output_html: boolean;
    output_pdf: boolean;
    include_transliteration: boolean;
    translation_provider: string;
    translation_batch_size: number;
    transliteration_mode: string;
    enable_lookup_cache: boolean;
    lookup_cache_batch_size: number;
    tempo: number;
  };
  generated_source_defaults: {
    add_images: boolean;
    image_prompt_pipeline: string;
    image_style_template: string;
    image_prompt_context_sentences: number;
    image_width: string;
    image_height: string;
  };
  supported_input_languages: string[];
  supported_output_languages: string[];
  supported_voices: string[];
}

export async function fetchBookCreationOptions(): Promise<BookCreationOptionsResponse> {
  const response = await apiFetch('/api/books/options');
  return handleResponse<BookCreationOptionsResponse>(response);
}

export async function createBook(payload: CreateBookPayload): Promise<BookCreationResponse> {
  const response = await apiFetch('/api/books/create', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(payload)
  });

  return handleResponse<BookCreationResponse>(response);
}

export interface BookGenerationJobRequest {
  generator: {
    topic: string;
    book_name: string;
    genre: string;
    author?: string;
    num_sentences: number;
    input_language?: string | null;
    output_language?: string | null;
    voice?: string | null;
  };
  pipeline: PipelineRequestPayload;
}

export async function submitBookJob(
  payload: BookGenerationJobRequest
): Promise<PipelineSubmissionResponse> {
  const response = await apiFetch('/api/books/jobs', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(payload)
  });

  return handleResponse<PipelineSubmissionResponse>(response);
}
