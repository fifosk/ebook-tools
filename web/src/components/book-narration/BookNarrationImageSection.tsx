type BookNarrationImageSectionProps = {
  headingId: string;
  title: string;
  description: string;
  addImages: boolean;
  imageStyleTemplate: string;
  imagePromptBatchingEnabled: boolean;
  imagePromptBatchSize: number;
  imagePromptContextSentences: number;
  imageSeedWithPreviousImage: boolean;
  imageBlankDetectionEnabled: boolean;
  imageConcurrency: string;
  imageWidth: string;
  imageHeight: string;
  imageSteps: string;
  imageCfgScale: string;
  imageSamplerName: string;
  imageApiTimeoutSeconds: string;
  onAddImagesChange: (value: boolean) => void;
  onImageStyleTemplateChange: (value: string) => void;
  onImagePromptBatchingEnabledChange: (value: boolean) => void;
  onImagePromptBatchSizeChange: (value: number) => void;
  onImagePromptContextSentencesChange: (value: number) => void;
  onImageSeedWithPreviousImageChange: (value: boolean) => void;
  onImageBlankDetectionEnabledChange: (value: boolean) => void;
  onImageConcurrencyChange: (value: string) => void;
  onImageWidthChange: (value: string) => void;
  onImageHeightChange: (value: string) => void;
  onImageStepsChange: (value: string) => void;
  onImageCfgScaleChange: (value: string) => void;
  onImageSamplerNameChange: (value: string) => void;
  onImageApiTimeoutSecondsChange: (value: string) => void;
};

type ImageStyleOption = {
  id: string;
  label: string;
  description: string;
  minSteps: number;
  maxSteps: number;
  defaultSteps: number;
  secondsAtDefault: number;
};

const IMAGE_STYLE_OPTIONS: ImageStyleOption[] = [
  {
    id: 'photorealistic',
    label: 'Photorealistic',
    description: 'Cinematic film-still story reel (slowest, highest fidelity).',
    minSteps: 12,
    maxSteps: 40,
    defaultSteps: 24,
    secondsAtDefault: 18
  },
  {
    id: 'comics',
    label: 'Comics',
    description: 'Graphic novel comic-panel look with ink lines and halftone shading.',
    minSteps: 8,
    maxSteps: 30,
    defaultSteps: 18,
    secondsAtDefault: 12
  },
  {
    id: 'children_book',
    label: "Children's book",
    description: 'Soft watercolor storybook illustration with warm pastel colours.',
    minSteps: 8,
    maxSteps: 32,
    defaultSteps: 20,
    secondsAtDefault: 14
  },
  {
    id: 'wireframe',
    label: 'Wireframe',
    description: 'Blueprint-style monochrome line drawing (fastest).',
    minSteps: 6,
    maxSteps: 20,
    defaultSteps: 12,
    secondsAtDefault: 8
  }
];

function clamp(value: number, min: number, max: number): number {
  return Math.min(Math.max(value, min), max);
}

function parseNumberField(value: string): number | null {
  const trimmed = value.trim();
  if (!trimmed) {
    return null;
  }
  const parsed = Number(trimmed);
  return Number.isFinite(parsed) ? parsed : null;
}

function stepsFromQuality(quality: number, style: ImageStyleOption): number {
  const bounded = clamp(quality, 0, 100);
  const range = style.maxSteps - style.minSteps;
  if (range <= 0) {
    return style.defaultSteps;
  }
  const steps = Math.round(style.minSteps + (bounded / 100) * range);
  return clamp(steps, style.minSteps, style.maxSteps);
}

function qualityFromSteps(steps: number, style: ImageStyleOption): number {
  const boundedSteps = clamp(Math.round(steps), style.minSteps, style.maxSteps);
  const range = style.maxSteps - style.minSteps;
  if (range <= 0) {
    return 50;
  }
  const ratio = (boundedSteps - style.minSteps) / range;
  return Math.round(clamp(ratio * 100, 0, 100));
}

function formatSeconds(seconds: number): string {
  if (!Number.isFinite(seconds)) {
    return '—';
  }
  if (seconds < 1) {
    return `${seconds.toFixed(2)}s`;
  }
  if (seconds < 10) {
    return `${seconds.toFixed(1)}s`;
  }
  return `${Math.round(seconds)}s`;
}

const BookNarrationImageSection = ({
  headingId,
  title,
  description,
  addImages,
  imageStyleTemplate,
  imagePromptBatchingEnabled,
  imagePromptBatchSize,
  imagePromptContextSentences,
  imageSeedWithPreviousImage,
  imageBlankDetectionEnabled,
  imageConcurrency,
  imageWidth,
  imageHeight,
  imageSteps,
  imageCfgScale,
  imageSamplerName,
  imageApiTimeoutSeconds,
  onAddImagesChange,
  onImageStyleTemplateChange,
  onImagePromptBatchingEnabledChange,
  onImagePromptBatchSizeChange,
  onImagePromptContextSentencesChange,
  onImageSeedWithPreviousImageChange,
  onImageBlankDetectionEnabledChange,
  onImageConcurrencyChange,
  onImageWidthChange,
  onImageHeightChange,
  onImageStepsChange,
  onImageCfgScaleChange,
  onImageSamplerNameChange,
  onImageApiTimeoutSecondsChange
}: BookNarrationImageSectionProps) => {
  const style =
    IMAGE_STYLE_OPTIONS.find((option) => option.id === imageStyleTemplate) ??
    IMAGE_STYLE_OPTIONS[0];
  const stepsValue = parseNumberField(imageSteps) ?? style.defaultSteps;
  const qualityValue = qualityFromSteps(stepsValue, style);
  const widthValue = parseNumberField(imageWidth) ?? 512;
  const heightValue = parseNumberField(imageHeight) ?? 512;
  const concurrencyValue = Math.max(1, Math.trunc(parseNumberField(imageConcurrency) ?? 1));
  const resolutionFactor = Math.max(0.25, (widthValue * heightValue) / (512 * 512));
  const secondsPerImage = (style.secondsAtDefault * resolutionFactor * stepsValue) / style.defaultSteps;
  const imagesPerMinute = concurrencyValue > 0 ? (60 * concurrencyValue) / secondsPerImage : 0;

  return (
    <section className="pipeline-card" aria-labelledby={headingId}>
      <header className="pipeline-card__header">
        <h3 id={headingId}>{title}</h3>
        <p>{description}</p>
      </header>
      <div className="pipeline-card__body">
        <label className="checkbox">
          <input
            type="checkbox"
            name="add_images"
            checked={addImages}
            onChange={(event) => onAddImagesChange(event.target.checked)}
          />
          Add AI-generated images to interactive reader
        </label>
        {addImages ? (
          <>
            <label htmlFor={`${headingId}-image-style-template`}>
              Style template
              <select
                id={`${headingId}-image-style-template`}
                name="image_style_template"
                value={style.id}
                onChange={(event) => {
                  const nextValue = event.target.value;
                  onImageStyleTemplateChange(nextValue);
                  const nextStyle = IMAGE_STYLE_OPTIONS.find((option) => option.id === nextValue) ?? style;
                  onImageStepsChange(String(nextStyle.defaultSteps));
                }}
              >
                {IMAGE_STYLE_OPTIONS.map((option) => (
                  <option key={option.id} value={option.id}>
                    {option.label}
                  </option>
                ))}
              </select>
            </label>
            <p className="form-help-text">{style.description}</p>
            <label htmlFor={`${headingId}-image-quality-slider`}>
              Quality vs speed
              <input
                id={`${headingId}-image-quality-slider`}
                type="range"
                min={0}
                max={100}
                step={1}
                value={qualityValue}
                onChange={(event) => {
                  const nextQuality = Number(event.target.value);
                  onImageStepsChange(String(stepsFromQuality(nextQuality, style)));
                }}
                aria-label="Image quality vs speed"
                aria-valuemin={0}
                aria-valuemax={100}
                aria-valuenow={qualityValue}
                aria-valuetext={`${qualityValue}%`}
              />
            </label>
            <p className="form-help-text">
              Estimate: ~{formatSeconds(secondsPerImage)} per image; with {concurrencyValue} worker
              {concurrencyValue === 1 ? '' : 's'} ≈ {Number.isFinite(imagesPerMinute) ? imagesPerMinute.toFixed(1) : '—'}{' '}
              images/min (rough).
            </p>
            <label className="checkbox">
              <input
                type="checkbox"
                name="image_prompt_batching_enabled"
                checked={imagePromptBatchingEnabled}
                onChange={(event) => onImagePromptBatchingEnabledChange(event.target.checked)}
              />
              Group sentences into image batches
            </label>
            {imagePromptBatchingEnabled ? (
              <>
                <label htmlFor={`${headingId}-image-prompt-batch-size`}>
                  Sentences per image
                  <input
                    id={`${headingId}-image-prompt-batch-size`}
                    name="image_prompt_batch_size"
                    type="number"
                    step={1}
                    min={1}
                    max={50}
                    value={imagePromptBatchSize}
                    onChange={(event) => onImagePromptBatchSizeChange(Number(event.target.value))}
                  />
                </label>
                <p className="form-help-text">
                  Generates one prompt + image per batch and reuses it across the batch in the player (faster, fewer images).
                </p>
              </>
            ) : (
              <p className="form-help-text">Generates one prompt + image per sentence (more images, slower).</p>
            )}
            <label htmlFor={`${headingId}-image-prompt-context`}>
              Image prompt context (surrounding sentences)
              <input
                id={`${headingId}-image-prompt-context`}
                name="image_prompt_context_sentences"
                type="number"
                step={1}
                min={0}
                max={50}
                value={imagePromptContextSentences}
                onChange={(event) => onImagePromptContextSentencesChange(Number(event.target.value))}
              />
            </label>
            <p className="form-help-text">
              Adds up to this many sentences before and after the selected range when building a consistent prompt plan
              (helps keep characters and setting consistent across the reel).
            </p>
            <label className="checkbox">
              <input
                type="checkbox"
                name="image_seed_with_previous_image"
                checked={imageSeedWithPreviousImage}
                onChange={(event) => onImageSeedWithPreviousImageChange(event.target.checked)}
              />
              Seed each frame from the previous image (img2img, experimental)
            </label>
            <p className="form-help-text">
              When enabled and supported by the image backend, each sentence image uses the previous frame as an init image.
              Default is off (often yields better scene accuracy).
            </p>
            <label className="checkbox">
              <input
                type="checkbox"
                name="image_blank_detection_enabled"
                checked={imageBlankDetectionEnabled}
                onChange={(event) => onImageBlankDetectionEnabledChange(event.target.checked)}
              />
              Detect and retry blank images (slower)
            </label>
            <p className="form-help-text">
              Re-runs generation when Draw Things returns nearly solid-color frames. Default is off.
            </p>
            <h4>Generation settings</h4>
            <p className="form-help-text">
              Tune these if you see Draw Things timeouts or want higher fidelity. Larger sizes and more steps take longer.
            </p>
            <label htmlFor={`${headingId}-image-concurrency`}>
              Image workers
              <input
                id={`${headingId}-image-concurrency`}
                name="image_concurrency"
                type="number"
                min={1}
                step={1}
                value={imageConcurrency}
                onChange={(event) => onImageConcurrencyChange(event.target.value)}
                placeholder="Use configured default"
              />
            </label>
            <label htmlFor={`${headingId}-image-timeout`}>
              API timeout (seconds)
              <input
                id={`${headingId}-image-timeout`}
                name="image_api_timeout_seconds"
                type="number"
                min={1}
                step={1}
                value={imageApiTimeoutSeconds}
                onChange={(event) => onImageApiTimeoutSecondsChange(event.target.value)}
                placeholder="Use configured default"
              />
            </label>
            <label htmlFor={`${headingId}-image-width`}>
              Width
              <input
                id={`${headingId}-image-width`}
                name="image_width"
                type="number"
                min={64}
                step={64}
                value={imageWidth}
                onChange={(event) => onImageWidthChange(event.target.value)}
                placeholder="Use configured default"
              />
            </label>
            <label htmlFor={`${headingId}-image-height`}>
              Height
              <input
                id={`${headingId}-image-height`}
                name="image_height"
                type="number"
                min={64}
                step={64}
                value={imageHeight}
                onChange={(event) => onImageHeightChange(event.target.value)}
                placeholder="Use configured default"
              />
            </label>
            <label htmlFor={`${headingId}-image-steps`}>
              Steps
              <input
                id={`${headingId}-image-steps`}
                name="image_steps"
                type="number"
                min={1}
                step={1}
                value={imageSteps}
                onChange={(event) => onImageStepsChange(event.target.value)}
                placeholder="Use configured default"
              />
            </label>
            <label htmlFor={`${headingId}-image-cfg-scale`}>
              CFG scale
              <input
                id={`${headingId}-image-cfg-scale`}
                name="image_cfg_scale"
                type="number"
                min={0}
                step={0.1}
                value={imageCfgScale}
                onChange={(event) => onImageCfgScaleChange(event.target.value)}
                placeholder="Use configured default"
              />
            </label>
            <label htmlFor={`${headingId}-image-sampler`}>
              Sampler name (optional)
              <input
                id={`${headingId}-image-sampler`}
                name="image_sampler_name"
                type="text"
                value={imageSamplerName}
                onChange={(event) => onImageSamplerNameChange(event.target.value)}
                placeholder="Use configured default"
              />
            </label>
          </>
        ) : null}
      </div>
    </section>
  );
};

export default BookNarrationImageSection;
