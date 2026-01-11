import type { ReactNode } from 'react';
import type { DragEvent } from 'react';
import type { BookOpenLibraryMetadataPreviewResponse } from '../../api/dtos';
import type { MenuOption } from '../../constants/menuOptions';
import BookNarrationSourceSection from './BookNarrationSourceSection';
import BookNarrationLanguageSection, {
  BookNarrationChapterOption,
} from './BookNarrationLanguageSection';
import BookNarrationOutputSection from './BookNarrationOutputSection';
import BookNarrationImageSection from './BookNarrationImageSection';
import BookNarrationPerformanceSection from './BookNarrationPerformanceSection';
import BookMetadataSection from './BookMetadataSection';
import type { BookNarrationFormSection, FormState } from './bookNarrationFormTypes';

type BookNarrationFormSectionsProps = {
  section: BookNarrationFormSection;
  sectionMeta: Record<BookNarrationFormSection, { title: string; description: string }>;
  customSourceSection: ReactNode | null;
  formState: FormState;
  handleChange: <K extends keyof FormState>(key: K, value: FormState[K]) => void;
  handleInputFileChange: (value: string) => void;
  setActiveFileDialog: (dialog: 'input' | 'output' | null) => void;
  canBrowseFiles: boolean;
  isLoadingFiles: boolean;
  fileDialogError: string | null;
  isDraggingFile: boolean;
  isUploadingFile: boolean;
  uploadError: string | null;
  recentUploadName: string | null;
  onDropzoneDragOver: (event: DragEvent<HTMLDivElement>) => void;
  onDropzoneDragLeave: (event: DragEvent<HTMLDivElement>) => void;
  onDropzoneDrop: (event: DragEvent<HTMLDivElement>) => void;
  onUploadFile: (file: File) => void | Promise<void>;
  metadataSourceName: string;
  metadataLookupQuery: string;
  metadataPreview: BookOpenLibraryMetadataPreviewResponse | null;
  metadataLoading: boolean;
  metadataError: string | null;
  cachedCoverDataUrl: string | null;
  onMetadataLookupQueryChange: (value: string) => void;
  onLookupMetadata: (query: string, force: boolean) => void | Promise<void>;
  onClearMetadata: () => void;
  availableLlmModels: string[];
  isLoadingLlmModels: boolean;
  llmModelError: string | null;
  displayStartSentence: number;
  displayEndSentence: string;
  chapterSelectionMode: 'range' | 'chapters';
  chapterOptions: BookNarrationChapterOption[];
  selectedChapterIds: string[];
  chapterSelectionSummary: string;
  chaptersLoading: boolean;
  chaptersError: string | null;
  chaptersDisabled: boolean;
  estimatedAudioDurationLabel: string | null;
  onProcessingModeChange: (mode: 'range' | 'chapters') => void;
  onChapterToggle: (chapterId: string) => void;
  onChapterClear: () => void;
  availableAudioModes: MenuOption[];
  availableAudioQualities: MenuOption[];
  availableVoices: MenuOption[];
  availableWrittenModes: MenuOption[];
  languagesForOverride: Array<{ label: string; code: string | null }>;
  voicePreviewStatus: Record<string, 'idle' | 'loading' | 'playing'>;
  voicePreviewError: Record<string, string>;
  isLoadingVoiceInventory: boolean;
  voiceInventoryError: string | null;
  buildVoiceOptions: (languageLabel: string, languageCode: string | null) => MenuOption[];
  onVoiceOverrideChange: (languageCode: string, voiceValue: string) => void;
  onPlayVoicePreview: (languageCode: string, languageLabel: string) => void;
  showOutputPathControls: boolean;
  isGeneratedSource: boolean;
  forcedBaseOutputFile: string | null;
};

export function BookNarrationFormSections({
  section,
  sectionMeta,
  customSourceSection,
  formState,
  handleChange,
  handleInputFileChange,
  setActiveFileDialog,
  canBrowseFiles,
  isLoadingFiles,
  fileDialogError,
  isDraggingFile,
  isUploadingFile,
  uploadError,
  recentUploadName,
  onDropzoneDragOver,
  onDropzoneDragLeave,
  onDropzoneDrop,
  onUploadFile,
  metadataSourceName,
  metadataLookupQuery,
  metadataPreview,
  metadataLoading,
  metadataError,
  cachedCoverDataUrl,
  onMetadataLookupQueryChange,
  onLookupMetadata,
  onClearMetadata,
  availableLlmModels,
  isLoadingLlmModels,
  llmModelError,
  displayStartSentence,
  displayEndSentence,
  chapterSelectionMode,
  chapterOptions,
  selectedChapterIds,
  chapterSelectionSummary,
  chaptersLoading,
  chaptersError,
  chaptersDisabled,
  estimatedAudioDurationLabel,
  onProcessingModeChange,
  onChapterToggle,
  onChapterClear,
  availableAudioModes,
  availableAudioQualities,
  availableVoices,
  availableWrittenModes,
  languagesForOverride,
  voicePreviewStatus,
  voicePreviewError,
  isLoadingVoiceInventory,
  voiceInventoryError,
  buildVoiceOptions,
  onVoiceOverrideChange,
  onPlayVoicePreview,
  showOutputPathControls,
  isGeneratedSource,
  forcedBaseOutputFile,
}: BookNarrationFormSectionsProps) {
  switch (section) {
    case 'source':
      return (
        customSourceSection ?? (
          <BookNarrationSourceSection
            key="source"
            headingId="pipeline-card-source"
            title={sectionMeta.source.title}
            description={sectionMeta.source.description}
            inputFile={formState.input_file}
            baseOutputFile={formState.base_output_file}
            onInputFileChange={handleInputFileChange}
            onBaseOutputFileChange={(value) => handleChange('base_output_file', value)}
            onBrowseClick={(dialogType) => setActiveFileDialog(dialogType)}
            canBrowseFiles={canBrowseFiles}
            isLoadingFiles={isLoadingFiles}
            fileDialogError={fileDialogError}
            isDraggingFile={isDraggingFile}
            isUploadingFile={isUploadingFile}
            onDropzoneDragOver={onDropzoneDragOver}
            onDropzoneDragLeave={onDropzoneDragLeave}
            onDropzoneDrop={onDropzoneDrop}
            onUploadFile={onUploadFile}
            uploadError={uploadError}
            recentUploadName={recentUploadName}
            configOverrides={formState.config}
            environmentOverrides={formState.environment_overrides}
            pipelineOverrides={formState.pipeline_overrides}
            bookMetadata={formState.book_metadata}
            onConfigOverridesChange={(value) => handleChange('config', value)}
            onEnvironmentOverridesChange={(value) => handleChange('environment_overrides', value)}
            onPipelineOverridesChange={(value) => handleChange('pipeline_overrides', value)}
            onBookMetadataChange={(value) => handleChange('book_metadata', value)}
            showAdvancedOverrides={false}
            disableBaseOutput={isGeneratedSource || Boolean(forcedBaseOutputFile)}
            showOutputPathControls={showOutputPathControls}
          />
        )
      );
    case 'metadata':
      return (
        <BookMetadataSection
          key="metadata"
          headingId="pipeline-card-metadata"
          title={sectionMeta.metadata.title}
          description={sectionMeta.metadata.description}
          metadataSourceName={metadataSourceName}
          metadataLookupQuery={metadataLookupQuery}
          metadataPreview={metadataPreview}
          metadataLoading={metadataLoading}
          metadataError={metadataError}
          bookMetadataJson={formState.book_metadata}
          cachedCoverDataUrl={cachedCoverDataUrl}
          onMetadataLookupQueryChange={(value) => onMetadataLookupQueryChange(value)}
          onLookupMetadata={onLookupMetadata}
          onClearMetadata={onClearMetadata}
          onBookMetadataJsonChange={(value) => handleChange('book_metadata', value)}
        />
      );
    case 'language':
      return (
        <BookNarrationLanguageSection
          key="language"
          headingId="pipeline-card-language"
          title={sectionMeta.language.title}
          description={sectionMeta.language.description}
          inputLanguage={formState.input_language}
          targetLanguages={formState.target_languages}
          customTargetLanguages={formState.custom_target_languages}
          ollamaModel={formState.ollama_model}
          translationProvider={formState.translation_provider}
          transliterationMode={formState.transliteration_mode}
          llmModels={availableLlmModels}
          llmModelsLoading={isLoadingLlmModels}
          llmModelsError={llmModelError}
          sentencesPerOutputFile={formState.sentences_per_output_file}
          startSentence={displayStartSentence}
          endSentence={displayEndSentence}
          stitchFull={formState.stitch_full}
          disableProcessingWindow={isGeneratedSource}
          processingMode={chapterSelectionMode}
          chapterOptions={chapterOptions}
          selectedChapterIds={selectedChapterIds}
          chapterSummary={chapterSelectionSummary || undefined}
          chaptersLoading={chaptersLoading}
          chaptersError={chaptersError}
          chaptersDisabled={chaptersDisabled}
          estimatedAudioDurationLabel={estimatedAudioDurationLabel}
          onProcessingModeChange={onProcessingModeChange}
          onChapterToggle={onChapterToggle}
          onChapterClear={onChapterClear}
          onInputLanguageChange={(value) => handleChange('input_language', value)}
          onTargetLanguagesChange={(value) => handleChange('target_languages', value)}
          onCustomTargetLanguagesChange={(value) => handleChange('custom_target_languages', value)}
          onOllamaModelChange={(value) => handleChange('ollama_model', value)}
          onTranslationProviderChange={(value) => handleChange('translation_provider', value)}
          onTransliterationModeChange={(value) => handleChange('transliteration_mode', value)}
          onSentencesPerOutputFileChange={(value) =>
            handleChange('sentences_per_output_file', value)
          }
          onStartSentenceChange={(value) => handleChange('start_sentence', value)}
          onEndSentenceChange={(value) => handleChange('end_sentence', value)}
          onStitchFullChange={(value) => handleChange('stitch_full', value)}
        />
      );
    case 'output':
      return (
        <BookNarrationOutputSection
          key="output"
          headingId="pipeline-card-output"
          title={sectionMeta.output.title}
          description={sectionMeta.output.description}
          generateAudio={formState.generate_audio}
          audioMode={formState.audio_mode}
          audioBitrateKbps={formState.audio_bitrate_kbps}
          selectedVoice={formState.selected_voice}
          writtenMode={formState.written_mode}
          outputHtml={formState.output_html}
          outputPdf={formState.output_pdf}
          includeTransliteration={formState.include_transliteration}
          tempo={formState.tempo}
          generateVideo={formState.generate_video}
          availableAudioModes={availableAudioModes}
          availableAudioQualities={availableAudioQualities}
          availableVoices={availableVoices}
          availableWrittenModes={availableWrittenModes}
          languagesForOverride={languagesForOverride}
          voiceOverrides={formState.voice_overrides}
          voicePreviewStatus={voicePreviewStatus}
          voicePreviewError={voicePreviewError}
          isLoadingVoiceInventory={isLoadingVoiceInventory}
          voiceInventoryError={voiceInventoryError}
          buildVoiceOptions={buildVoiceOptions}
          onGenerateAudioChange={(value) => handleChange('generate_audio', value)}
          onAudioModeChange={(value) => handleChange('audio_mode', value)}
          onAudioBitrateChange={(value) => handleChange('audio_bitrate_kbps', value)}
          onSelectedVoiceChange={(value) => handleChange('selected_voice', value)}
          onVoiceOverrideChange={onVoiceOverrideChange}
          onWrittenModeChange={(value) => handleChange('written_mode', value)}
          onOutputHtmlChange={(value) => handleChange('output_html', value)}
          onOutputPdfChange={(value) => handleChange('output_pdf', value)}
          onIncludeTransliterationChange={(value) => handleChange('include_transliteration', value)}
          onTempoChange={(value) => handleChange('tempo', value)}
          onGenerateVideoChange={(value) => handleChange('generate_video', value)}
          onPlayVoicePreview={onPlayVoicePreview}
        />
      );
    case 'images':
      return (
        <BookNarrationImageSection
          key="images"
          headingId="pipeline-card-images"
          title={sectionMeta.images.title}
          description={sectionMeta.images.description}
          addImages={formState.add_images}
          imagePromptPipeline={formState.image_prompt_pipeline}
          imageStyleTemplate={formState.image_style_template}
          imagePromptBatchingEnabled={formState.image_prompt_batching_enabled}
          imagePromptBatchSize={formState.image_prompt_batch_size}
          imagePromptPlanBatchSize={formState.image_prompt_plan_batch_size}
          imagePromptContextSentences={formState.image_prompt_context_sentences}
          imageSeedWithPreviousImage={formState.image_seed_with_previous_image}
          imageBlankDetectionEnabled={formState.image_blank_detection_enabled}
          imageApiBaseUrls={formState.image_api_base_urls}
          imageConcurrency={formState.image_concurrency}
          imageWidth={formState.image_width}
          imageHeight={formState.image_height}
          imageSteps={formState.image_steps}
          imageCfgScale={formState.image_cfg_scale}
          imageSamplerName={formState.image_sampler_name}
          imageApiTimeoutSeconds={formState.image_api_timeout_seconds}
          onAddImagesChange={(value) => handleChange('add_images', value)}
          onImagePromptPipelineChange={(value) => handleChange('image_prompt_pipeline', value)}
          onImageStyleTemplateChange={(value) => handleChange('image_style_template', value)}
          onImagePromptBatchingEnabledChange={(value) =>
            handleChange('image_prompt_batching_enabled', value)
          }
          onImagePromptBatchSizeChange={(value) => handleChange('image_prompt_batch_size', value)}
          onImagePromptPlanBatchSizeChange={(value) =>
            handleChange('image_prompt_plan_batch_size', value)
          }
          onImagePromptContextSentencesChange={(value) =>
            handleChange('image_prompt_context_sentences', value)
          }
          onImageSeedWithPreviousImageChange={(value) =>
            handleChange('image_seed_with_previous_image', value)
          }
          onImageBlankDetectionEnabledChange={(value) =>
            handleChange('image_blank_detection_enabled', value)
          }
          onImageApiBaseUrlsChange={(value) => handleChange('image_api_base_urls', value)}
          onImageConcurrencyChange={(value) => handleChange('image_concurrency', value)}
          onImageWidthChange={(value) => handleChange('image_width', value)}
          onImageHeightChange={(value) => handleChange('image_height', value)}
          onImageStepsChange={(value) => handleChange('image_steps', value)}
          onImageCfgScaleChange={(value) => handleChange('image_cfg_scale', value)}
          onImageSamplerNameChange={(value) => handleChange('image_sampler_name', value)}
          onImageApiTimeoutSecondsChange={(value) =>
            handleChange('image_api_timeout_seconds', value)
          }
        />
      );
    case 'performance':
      return (
        <BookNarrationPerformanceSection
          key="performance"
          headingId="pipeline-card-performance"
          title={sectionMeta.performance.title}
          description={sectionMeta.performance.description}
          threadCount={formState.thread_count}
          queueSize={formState.queue_size}
          jobMaxWorkers={formState.job_max_workers}
          translationBatchSize={formState.translation_batch_size}
          slideParallelism={formState.slide_parallelism}
          slideParallelWorkers={formState.slide_parallel_workers}
          onThreadCountChange={(value) => handleChange('thread_count', value)}
          onQueueSizeChange={(value) => handleChange('queue_size', value)}
          onJobMaxWorkersChange={(value) => handleChange('job_max_workers', value)}
          onTranslationBatchSizeChange={(value) => handleChange('translation_batch_size', value)}
          onSlideParallelismChange={(value) => handleChange('slide_parallelism', value)}
          onSlideParallelWorkersChange={(value) => handleChange('slide_parallel_workers', value)}
        />
      );
    case 'submit':
    default:
      return null;
  }
}
