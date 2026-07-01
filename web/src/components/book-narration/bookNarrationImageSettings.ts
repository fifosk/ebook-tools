export type ImageStyleOption = {
  id: string;
  label: string;
  description: string;
  minSteps: number;
  maxSteps: number;
  defaultSteps: number;
  secondsAtDefault: number;
};

export type ImagePromptPipelineOption = {
  id: 'prompt_plan' | 'visual_canon';
  label: string;
  description: string;
};

export type ImageGenerationEstimate = {
  stepsValue: number;
  qualityValue: number;
  widthValue: number;
  heightValue: number;
  concurrencyValue: number;
  secondsPerImage: number;
  imagesPerMinute: number;
};

export const IMAGE_STYLE_OPTIONS: ImageStyleOption[] = [
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

export const IMAGE_PROMPT_PIPELINE_OPTIONS: ImagePromptPipelineOption[] = [
  {
    id: 'prompt_plan',
    label: 'Prompt plan',
    description: 'Uses the style template and prompt plan batching to craft diffusion prompts.'
  },
  {
    id: 'visual_canon',
    label: 'Visual canon',
    description: 'Builds a visual canon + scene map for continuity and uses per-sentence deltas.'
  }
];

export function resolveImagePromptPipeline(value: string): ImagePromptPipelineOption {
  const normalized = value === 'visual_canon' ? 'visual_canon' : 'prompt_plan';
  return IMAGE_PROMPT_PIPELINE_OPTIONS.find((option) => option.id === normalized) ?? IMAGE_PROMPT_PIPELINE_OPTIONS[0];
}

export function resolveImageStyle(value: string): ImageStyleOption {
  return IMAGE_STYLE_OPTIONS.find((option) => option.id === value) ?? IMAGE_STYLE_OPTIONS[0];
}

export function clamp(value: number, min: number, max: number): number {
  return Math.min(Math.max(value, min), max);
}

export function parseNumberField(value: string): number | null {
  const trimmed = value.trim();
  if (!trimmed) {
    return null;
  }
  const parsed = Number(trimmed);
  return Number.isFinite(parsed) ? parsed : null;
}

export function stepsFromQuality(quality: number, style: ImageStyleOption): number {
  const bounded = clamp(quality, 0, 100);
  const range = style.maxSteps - style.minSteps;
  if (range <= 0) {
    return style.defaultSteps;
  }
  const steps = Math.round(style.minSteps + (bounded / 100) * range);
  return clamp(steps, style.minSteps, style.maxSteps);
}

export function qualityFromSteps(steps: number, style: ImageStyleOption): number {
  const boundedSteps = clamp(Math.round(steps), style.minSteps, style.maxSteps);
  const range = style.maxSteps - style.minSteps;
  if (range <= 0) {
    return 50;
  }
  const ratio = (boundedSteps - style.minSteps) / range;
  return Math.round(clamp(ratio * 100, 0, 100));
}

export function formatImageSeconds(seconds: number): string {
  if (!Number.isFinite(seconds)) {
    return '-';
  }
  if (seconds < 1) {
    return `${seconds.toFixed(2)}s`;
  }
  if (seconds < 10) {
    return `${seconds.toFixed(1)}s`;
  }
  return `${Math.round(seconds)}s`;
}

export function estimateImageGeneration({
  imageSteps,
  imageWidth,
  imageHeight,
  imageConcurrency,
  style
}: {
  imageSteps: string;
  imageWidth: string;
  imageHeight: string;
  imageConcurrency: string;
  style: ImageStyleOption;
}): ImageGenerationEstimate {
  const stepsValue = parseNumberField(imageSteps) ?? style.defaultSteps;
  const qualityValue = qualityFromSteps(stepsValue, style);
  const widthValue = parseNumberField(imageWidth) ?? 512;
  const heightValue = parseNumberField(imageHeight) ?? 512;
  const concurrencyValue = Math.max(1, Math.trunc(parseNumberField(imageConcurrency) ?? 1));
  const resolutionFactor = Math.max(0.25, (widthValue * heightValue) / (512 * 512));
  const secondsPerImage = (style.secondsAtDefault * resolutionFactor * stepsValue) / style.defaultSteps;
  const imagesPerMinute = concurrencyValue > 0 ? (60 * concurrencyValue) / secondsPerImage : 0;
  return {
    stepsValue,
    qualityValue,
    widthValue,
    heightValue,
    concurrencyValue,
    secondsPerImage,
    imagesPerMinute
  };
}
