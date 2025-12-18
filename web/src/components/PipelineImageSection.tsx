type PipelineImageSectionProps = {
  headingId: string;
  title: string;
  description: string;
  addImages: boolean;
  imagePromptContextSentences: number;
  imageSeedWithPreviousImage: boolean;
  imageConcurrency: string;
  imageWidth: string;
  imageHeight: string;
  imageSteps: string;
  imageCfgScale: string;
  imageSamplerName: string;
  imageApiTimeoutSeconds: string;
  onAddImagesChange: (value: boolean) => void;
  onImagePromptContextSentencesChange: (value: number) => void;
  onImageSeedWithPreviousImageChange: (value: boolean) => void;
  onImageConcurrencyChange: (value: string) => void;
  onImageWidthChange: (value: string) => void;
  onImageHeightChange: (value: string) => void;
  onImageStepsChange: (value: string) => void;
  onImageCfgScaleChange: (value: string) => void;
  onImageSamplerNameChange: (value: string) => void;
  onImageApiTimeoutSecondsChange: (value: string) => void;
};

const PipelineImageSection = ({
  headingId,
  title,
  description,
  addImages,
  imagePromptContextSentences,
  imageSeedWithPreviousImage,
  imageConcurrency,
  imageWidth,
  imageHeight,
  imageSteps,
  imageCfgScale,
  imageSamplerName,
  imageApiTimeoutSeconds,
  onAddImagesChange,
  onImagePromptContextSentencesChange,
  onImageSeedWithPreviousImageChange,
  onImageConcurrencyChange,
  onImageWidthChange,
  onImageHeightChange,
  onImageStepsChange,
  onImageCfgScaleChange,
  onImageSamplerNameChange,
  onImageApiTimeoutSecondsChange
}: PipelineImageSectionProps) => {
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

export default PipelineImageSection;

