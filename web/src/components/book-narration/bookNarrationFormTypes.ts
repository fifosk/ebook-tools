import type { ReactNode } from 'react';
import type {
  JobParameterSnapshot,
  PipelineRequestPayload,
  PipelineStatusResponse,
} from '../../api/dtos';

export type BookNarrationFormSection =
  | 'source'
  | 'metadata'
  | 'language'
  | 'output'
  | 'images'
  | 'performance'
  | 'submit';

export type BookNarrationFormProps = {
  onSubmit: (payload: PipelineRequestPayload) => Promise<void> | void;
  isSubmitting?: boolean;
  activeSection?: BookNarrationFormSection;
  onSectionChange?: (section: BookNarrationFormSection) => void;
  externalError?: string | null;
  prefillInputFile?: string | null;
  prefillParameters?: JobParameterSnapshot | null;
  recentJobs?: PipelineStatusResponse[] | null;
  sourceMode?: 'upload' | 'generated';
  submitLabel?: string;
  forcedBaseOutputFile?: string | null;
  customSourceSection?: ReactNode;
  implicitEndOffsetThreshold?: number | null;
  sectionOverrides?: Partial<Record<BookNarrationFormSection, { title: string; description: string }>>;
  showInfoHeader?: boolean;
  showOutputPathControls?: boolean;
  defaultImageSettings?: ImageDefaults | null;
};

export type JsonFields =
  | 'config'
  | 'environment_overrides'
  | 'pipeline_overrides'
  | 'book_metadata';

export type FormState = {
  input_file: string;
  base_output_file: string;
  input_language: string;
  target_languages: string[];
  custom_target_languages: string;
  ollama_model: string;
  sentences_per_output_file: number;
  start_sentence: number;
  end_sentence: string;
  stitch_full: boolean;
  generate_audio: boolean;
  audio_mode: string;
  audio_bitrate_kbps: string;
  written_mode: string;
  selected_voice: string;
  voice_overrides: Record<string, string>;
  output_html: boolean;
  output_pdf: boolean;
  generate_video: boolean;
  add_images: boolean;
  image_prompt_pipeline: string;
  image_style_template: string;
  image_prompt_batching_enabled: boolean;
  image_prompt_batch_size: number;
  image_prompt_plan_batch_size: number;
  image_prompt_context_sentences: number;
  image_seed_with_previous_image: boolean;
  image_blank_detection_enabled: boolean;
  image_api_base_urls: string[];
  image_width: string;
  image_height: string;
  image_steps: string;
  image_cfg_scale: string;
  image_sampler_name: string;
  image_api_timeout_seconds: string;
  include_transliteration: boolean;
  translation_provider: string;
  transliteration_mode: string;
  tempo: number;
  thread_count: string;
  queue_size: string;
  job_max_workers: string;
  image_concurrency: string;
  slide_parallelism: string;
  slide_parallel_workers: string;
  config: string;
  environment_overrides: string;
  pipeline_overrides: string;
  book_metadata: string;
};

export type ImageDefaults = {
  add_images: boolean;
  image_prompt_pipeline?: string;
  image_style_template: string;
  image_prompt_context_sentences: number;
  image_width: string;
  image_height: string;
};
