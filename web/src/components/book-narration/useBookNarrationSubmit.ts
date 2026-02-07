import { useCallback } from 'react';
import type { FormEvent } from 'react';
import type { PipelineRequestPayload } from '../../api/dtos';
import type { FormState } from './bookNarrationFormTypes';
import { normalizeTextValue, parseJsonField } from './bookNarrationUtils';
import {
  normalizeImagePromptPipeline,
  parseEndSentenceInput,
  parseOptionalNumberInput,
  resolveImageBaseUrlsForSubmission,
} from './bookNarrationFormUtils';

type ChapterSelection = {
  startSentence: number;
  endSentence: number;
};

type UseBookNarrationSubmitOptions = {
  formState: FormState;
  normalizedTargetLanguages: string[];
  chapterSelectionMode: 'range' | 'chapters';
  chapterSelection: ChapterSelection | null;
  isGeneratedSource: boolean;
  forcedBaseOutputFile: string | null;
  implicitEndOffsetThreshold: number | null;
  onSubmit: (payload: PipelineRequestPayload) => Promise<void> | void;
  setError: (error: string | null) => void;
};

type JsonFields = 'config' | 'environment_overrides' | 'pipeline_overrides' | 'book_metadata';

export function useBookNarrationSubmit({
  formState,
  normalizedTargetLanguages,
  chapterSelectionMode,
  chapterSelection,
  isGeneratedSource,
  forcedBaseOutputFile,
  implicitEndOffsetThreshold,
  onSubmit,
  setError,
}: UseBookNarrationSubmitOptions) {
  const handleSubmit = useCallback(
    async (event: FormEvent<HTMLFormElement>) => {
      event.preventDefault();
      setError(null);

      try {
        const json: Record<JsonFields, Record<string, unknown>> = {
          config: parseJsonField('config', formState.config),
          environment_overrides: parseJsonField(
            'environment_overrides',
            formState.environment_overrides,
          ),
          pipeline_overrides: parseJsonField('pipeline_overrides', formState.pipeline_overrides),
          book_metadata: parseJsonField('book_metadata', formState.book_metadata),
        };

        if (normalizedTargetLanguages.length === 0) {
          throw new Error('Please choose at least one target language.');
        }

        const pipelineOverrides = { ...json.pipeline_overrides };

        const threadCount = parseOptionalNumberInput(formState.thread_count);
        if (threadCount !== undefined) {
          pipelineOverrides.thread_count = threadCount;
        }

        const queueSize = parseOptionalNumberInput(formState.queue_size);
        if (queueSize !== undefined) {
          pipelineOverrides.queue_size = queueSize;
        }

        const jobMaxWorkers = parseOptionalNumberInput(formState.job_max_workers);
        if (jobMaxWorkers !== undefined) {
          pipelineOverrides.job_max_workers = jobMaxWorkers;
        }

        const slideParallelism = formState.slide_parallelism.trim();
        if (slideParallelism) {
          pipelineOverrides.slide_parallelism = slideParallelism;
        }

        const slideParallelWorkers = parseOptionalNumberInput(formState.slide_parallel_workers);
        if (slideParallelWorkers !== undefined) {
          pipelineOverrides.slide_parallel_workers = slideParallelWorkers;
        }

        const sanitizedVoiceOverrides: Record<string, string> = {};
        for (const [code, value] of Object.entries(formState.voice_overrides)) {
          if (typeof code !== 'string' || typeof value !== 'string') {
            continue;
          }
          const trimmedCode = code.trim();
          const trimmedValue = value.trim();
          if (!trimmedCode || !trimmedValue) {
            continue;
          }
          sanitizedVoiceOverrides[trimmedCode] = trimmedValue;
        }
        if (Object.keys(sanitizedVoiceOverrides).length > 0) {
          pipelineOverrides.voice_overrides = sanitizedVoiceOverrides;
        }
        if (typeof formState.audio_mode === 'string' && formState.audio_mode.trim()) {
          pipelineOverrides.audio_mode = formState.audio_mode.trim();
        }
        const audioBitrate = parseOptionalNumberInput(formState.audio_bitrate_kbps);
        if (audioBitrate !== undefined) {
          pipelineOverrides.audio_bitrate_kbps = Math.max(32, Math.trunc(audioBitrate));
        }
        const rawTranslationBatchSize = Number(formState.translation_batch_size);
        const normalizedTranslationBatchSize = Number.isFinite(rawTranslationBatchSize)
          ? Math.trunc(rawTranslationBatchSize)
          : 10;
        if (formState.add_images) {
          pipelineOverrides.image_prompt_pipeline =
            normalizeImagePromptPipeline(formState.image_prompt_pipeline) ?? 'prompt_plan';
          if (typeof formState.image_style_template === 'string' && formState.image_style_template.trim()) {
            pipelineOverrides.image_style_template = formState.image_style_template.trim();
          }

          pipelineOverrides.image_prompt_batching_enabled = Boolean(formState.image_prompt_batching_enabled);
          const rawBatchSize = Number(formState.image_prompt_batch_size);
          const normalizedBatchSize = Number.isFinite(rawBatchSize) ? Math.trunc(rawBatchSize) : 10;
          pipelineOverrides.image_prompt_batch_size = Math.min(50, Math.max(1, normalizedBatchSize));

          const rawPromptPlanBatchSize = Number(formState.image_prompt_plan_batch_size);
          const normalizedPromptPlanBatchSize = Number.isFinite(rawPromptPlanBatchSize)
            ? Math.trunc(rawPromptPlanBatchSize)
            : 50;
          pipelineOverrides.image_prompt_plan_batch_size = Math.min(50, Math.max(1, normalizedPromptPlanBatchSize));

          const rawContext = Number(formState.image_prompt_context_sentences);
          const normalizedContext = Number.isFinite(rawContext) ? Math.trunc(rawContext) : 0;
          pipelineOverrides.image_prompt_context_sentences = Math.min(50, Math.max(0, normalizedContext));
          pipelineOverrides.image_seed_with_previous_image = Boolean(formState.image_seed_with_previous_image);
          pipelineOverrides.image_blank_detection_enabled = Boolean(formState.image_blank_detection_enabled);

          const normalizedImageBaseUrls = await resolveImageBaseUrlsForSubmission(
            formState.image_api_base_urls,
          );
          pipelineOverrides.image_api_base_urls = normalizedImageBaseUrls;
          pipelineOverrides.image_api_base_url = normalizedImageBaseUrls[0] ?? '';

          const imageConcurrency = parseOptionalNumberInput(formState.image_concurrency);
          if (imageConcurrency !== undefined) {
            pipelineOverrides.image_concurrency = Math.max(1, Math.trunc(imageConcurrency));
          }

          const imageTimeout = parseOptionalNumberInput(formState.image_api_timeout_seconds);
          if (imageTimeout !== undefined) {
            pipelineOverrides.image_api_timeout_seconds = Math.max(1, imageTimeout);
          }

          const imageWidth = parseOptionalNumberInput(formState.image_width);
          if (imageWidth !== undefined) {
            pipelineOverrides.image_width = Math.max(64, Math.trunc(imageWidth));
          }

          const imageHeight = parseOptionalNumberInput(formState.image_height);
          if (imageHeight !== undefined) {
            pipelineOverrides.image_height = Math.max(64, Math.trunc(imageHeight));
          }

          const imageSteps = parseOptionalNumberInput(formState.image_steps);
          if (imageSteps !== undefined) {
            pipelineOverrides.image_steps = Math.max(1, Math.trunc(imageSteps));
          }

          const imageCfgScale = parseOptionalNumberInput(formState.image_cfg_scale);
          if (imageCfgScale !== undefined) {
            pipelineOverrides.image_cfg_scale = Math.max(0, imageCfgScale);
          }

          pipelineOverrides.image_sampler_name = formState.image_sampler_name;
        }

        const configOverrides = { ...json.config };
        const metadataBookTitle = normalizeTextValue(json.book_metadata?.['book_title']);
        const metadataBookAuthor = normalizeTextValue(json.book_metadata?.['book_author']);
        const metadataBookYear = normalizeTextValue(json.book_metadata?.['book_year']);
        const metadataBookSummary = normalizeTextValue(json.book_metadata?.['book_summary']);
        const metadataCoverFile = normalizeTextValue(json.book_metadata?.['book_cover_file']);
        if (metadataBookTitle) {
          configOverrides['book_title'] = metadataBookTitle;
        }
        if (metadataBookAuthor) {
          configOverrides['book_author'] = metadataBookAuthor;
        }
        if (metadataBookYear) {
          configOverrides['book_year'] = metadataBookYear;
        }
        if (metadataBookSummary) {
          configOverrides['book_summary'] = metadataBookSummary;
        }
        if (metadataCoverFile) {
          configOverrides['book_cover_file'] = metadataCoverFile;
        }
        const selectedModel = formState.ollama_model.trim();
        if (selectedModel) {
          pipelineOverrides.ollama_model = selectedModel;
        }

        const chapterRange = chapterSelectionMode === 'chapters' ? chapterSelection : null;
        if (!isGeneratedSource && chapterSelectionMode === 'chapters' && !chapterRange) {
          throw new Error('Select at least one chapter.');
        }
        const normalizedStartSentence = isGeneratedSource
          ? 1
          : chapterRange
          ? chapterRange.startSentence
          : Math.max(1, Math.trunc(Number(formState.start_sentence)));
        if (!Number.isFinite(normalizedStartSentence)) {
          throw new Error('Start sentence must be a valid number.');
        }
        const normalizedEndSentence = isGeneratedSource
          ? null
          : chapterRange
          ? chapterRange.endSentence
          : parseEndSentenceInput(
              formState.end_sentence,
              normalizedStartSentence,
              implicitEndOffsetThreshold,
            );
        const resolvedBaseOutput = (forcedBaseOutputFile ?? formState.base_output_file).trim();
        const trimmedInputFile = formState.input_file.trim();
        const fallbackInputFile = resolvedBaseOutput || 'generated-book';
        const resolvedInputFile =
          trimmedInputFile || (isGeneratedSource ? `${fallbackInputFile}.epub` : trimmedInputFile);

        const payload: PipelineRequestPayload = {
          config: configOverrides,
          environment_overrides: json.environment_overrides,
          pipeline_overrides: pipelineOverrides,
          inputs: {
            input_file: resolvedInputFile,
            base_output_file: resolvedBaseOutput,
            input_language: formState.input_language.trim(),
            target_languages: normalizedTargetLanguages,
            sentences_per_output_file: Number(formState.sentences_per_output_file),
            start_sentence: normalizedStartSentence,
            end_sentence: normalizedEndSentence,
            stitch_full: formState.stitch_full,
            generate_audio: formState.generate_audio,
            audio_mode: formState.audio_mode.trim(),
            audio_bitrate_kbps: audioBitrate !== undefined ? Math.max(32, Math.trunc(audioBitrate)) : null,
            written_mode: formState.written_mode.trim(),
            selected_voice: formState.selected_voice.trim(),
            voice_overrides: sanitizedVoiceOverrides,
            output_html: formState.output_html,
            output_pdf: formState.output_pdf,
            add_images: formState.add_images,
            include_transliteration: formState.include_transliteration,
            translation_provider: formState.translation_provider,
            translation_batch_size: Math.max(1, normalizedTranslationBatchSize),
            transliteration_mode: formState.transliteration_mode,
            transliteration_model: formState.transliteration_model.trim() || null,
            enable_lookup_cache: formState.enable_lookup_cache,
            lookup_cache_batch_size: Math.max(1, Math.trunc(Number(formState.lookup_cache_batch_size) || 10)),
            tempo: Number(formState.tempo),
            book_metadata: json.book_metadata,
          },
        };

        await onSubmit(payload);
      } catch (submissionError) {
        const message =
          submissionError instanceof Error
            ? submissionError.message
            : 'Unable to submit pipeline request';
        setError(message);
      }
    },
    [
      chapterSelection,
      chapterSelectionMode,
      formState,
      forcedBaseOutputFile,
      implicitEndOffsetThreshold,
      isGeneratedSource,
      normalizedTargetLanguages,
      onSubmit,
      setError,
    ],
  );

  return { handleSubmit };
}
