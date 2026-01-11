import { DEFAULT_IMAGE_API_BASE_URLS } from '../../constants/imageNodes';
import type { BookNarrationFormSection, FormState } from './bookNarrationFormTypes';

export const PREFERRED_SAMPLE_EBOOK = 'test-agatha-poirot-30sentences.epub';

export const IMAGE_DEFAULT_FIELDS = new Set<keyof FormState>([
  'add_images',
  'image_prompt_pipeline',
  'image_style_template',
  'image_prompt_context_sentences',
  'image_width',
  'image_height',
]);

export const DEFAULT_FORM_STATE: FormState = {
  input_file: '',
  base_output_file: '',
  input_language: 'English',
  target_languages: ['Arabic'],
  custom_target_languages: '',
  ollama_model: 'kimi-k2-thinking:cloud',
  sentences_per_output_file: 1,
  start_sentence: 1,
  end_sentence: '',
  stitch_full: false,
  generate_audio: true,
  audio_mode: '4',
  audio_bitrate_kbps: '96',
  written_mode: '4',
  selected_voice: 'gTTS',
  voice_overrides: {},
  output_html: false,
  output_pdf: false,
  generate_video: false,
  add_images: false,
  image_prompt_pipeline: 'prompt_plan',
  image_style_template: 'comics',
  image_prompt_batching_enabled: true,
  image_prompt_batch_size: 10,
  image_prompt_plan_batch_size: 50,
  image_prompt_context_sentences: 2,
  image_seed_with_previous_image: false,
  image_blank_detection_enabled: false,
  image_api_base_urls: [...DEFAULT_IMAGE_API_BASE_URLS],
  image_width: '',
  image_height: '',
  image_steps: '',
  image_cfg_scale: '',
  image_sampler_name: '',
  image_api_timeout_seconds: '300',
  include_transliteration: true,
  translation_provider: 'llm',
  translation_batch_size: 10,
  transliteration_mode: 'default',
  tempo: 1,
  thread_count: '',
  queue_size: '',
  job_max_workers: '',
  image_concurrency: '',
  slide_parallelism: '',
  slide_parallel_workers: '',
  config: '{}',
  environment_overrides: '{}',
  pipeline_overrides: '{}',
  book_metadata: '{}',
};

export const BOOK_NARRATION_TAB_SECTIONS: BookNarrationFormSection[] = [
  'source',
  'metadata',
  'language',
  'output',
  'images',
  'performance',
];

export const BOOK_NARRATION_SECTION_META: Record<
  BookNarrationFormSection,
  { title: string; description: string }
> = {
  source: {
    title: 'Source',
    description: 'Select the EPUB to ingest and where generated files should be written.',
  },
  metadata: {
    title: 'Metadata',
    description: 'Load book metadata from Open Library (no API key) and edit it before submitting the job.',
  },
  language: {
    title: 'Language & translation',
    description: 'Configure the input language, target translations, and processing window.',
  },
  output: {
    title: 'Output & narration',
    description: 'Control narration voices, written formats, and presentation options.',
  },
  images: {
    title: 'Images',
    description: 'Generate sentence images and tune the diffusion settings.',
  },
  performance: {
    title: 'Performance tuning',
    description: 'Adjust concurrency and orchestration parameters to fit your environment.',
  },
  submit: {
    title: 'Submit book job',
    description: 'Review the configured settings and enqueue the book job for processing.',
  },
};

export const ESTIMATED_AUDIO_SECONDS_PER_SENTENCE = 6.4;
