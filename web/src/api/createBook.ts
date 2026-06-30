import type { PipelineRequestPayload, PipelineSubmissionResponse } from './dtos';
import { apiFetch, handleResponse } from './client';
import { WEB_CREATE_RUNTIME_CONTRACT } from './client/runtimeContract';

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
    target_languages?: string[];
    output_languages?: string[];
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
  sentence_splitter_capabilities?: {
    default_mode: string;
    supported_modes: Array<{
      id: string;
      label: string;
      cache_version: string;
      stable: boolean;
    }>;
    comparison_metric_fields: string[];
  } | null;
  generated_source_defaults: {
    add_images: boolean;
    image_prompt_pipeline: string;
    image_style_template: string;
    image_prompt_context_sentences: number;
    image_width: string;
    image_height: string;
  };
  subtitle_defaults?: {
    worker_count: number;
    batch_size: number;
    translation_batch_size: number;
    ass_font_size: number;
    ass_emphasis_scale: number;
  };
  youtube_dub_defaults?: {
    original_mix_percent: number;
    flush_sentences: number;
    translation_batch_size: number;
    split_batches: boolean;
    stitch_batches: boolean;
    target_height: number;
    preserve_aspect_ratio: boolean;
  };
  supported_input_languages: string[];
  supported_output_languages: string[];
  supported_voices: string[];
}

export async function fetchBookCreationOptions(): Promise<BookCreationOptionsResponse> {
  const response = await apiFetch(WEB_CREATE_RUNTIME_CONTRACT.bookOptionsPath);
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
    source_book_title?: string | null;
    source_book_author?: string | null;
    source_book_genre?: string | null;
    source_book_summary?: string | null;
  };
  pipeline: PipelineRequestPayload;
}

export async function submitBookJob(
  payload: BookGenerationJobRequest
): Promise<PipelineSubmissionResponse> {
  const response = await apiFetch(WEB_CREATE_RUNTIME_CONTRACT.bookJobsPath, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(payload)
  });

  return handleResponse<PipelineSubmissionResponse>(response);
}
