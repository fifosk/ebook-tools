import { describe, expect, it } from 'vitest';
import {
  estimateImageGeneration,
  formatImageSeconds,
  IMAGE_STYLE_OPTIONS,
  qualityFromSteps,
  resolveImagePromptPipeline,
  resolveImageStyle,
  stepsFromQuality
} from '../book-narration/bookNarrationImageSettings';

describe('bookNarrationImageSettings', () => {
  it('resolves unknown prompt pipelines and styles to supported defaults', () => {
    expect(resolveImagePromptPipeline('visual_canon').id).toBe('visual_canon');
    expect(resolveImagePromptPipeline('unexpected').id).toBe('prompt_plan');
    expect(resolveImageStyle('wireframe').id).toBe('wireframe');
    expect(resolveImageStyle('unknown-style').id).toBe(IMAGE_STYLE_OPTIONS[0].id);
  });

  it('maps quality slider values to bounded style-specific step counts', () => {
    const wireframe = resolveImageStyle('wireframe');

    expect(stepsFromQuality(-50, wireframe)).toBe(wireframe.minSteps);
    expect(stepsFromQuality(1000, wireframe)).toBe(wireframe.maxSteps);
    expect(qualityFromSteps(wireframe.minSteps, wireframe)).toBe(0);
    expect(qualityFromSteps(wireframe.maxSteps, wireframe)).toBe(100);
  });

  it('estimates image generation throughput from dimensions, steps, and workers', () => {
    const style = resolveImageStyle('comics');
    const estimate = estimateImageGeneration({
      imageSteps: '18',
      imageWidth: '1024',
      imageHeight: '512',
      imageConcurrency: '2.9',
      style
    });

    expect(estimate.concurrencyValue).toBe(2);
    expect(estimate.secondsPerImage).toBeCloseTo(style.secondsAtDefault * 2);
    expect(estimate.imagesPerMinute).toBeCloseTo(5);
  });

  it('formats compact image duration labels', () => {
    expect(formatImageSeconds(Number.NaN)).toBe('-');
    expect(formatImageSeconds(0.256)).toBe('0.26s');
    expect(formatImageSeconds(6.25)).toBe('6.3s');
    expect(formatImageSeconds(18.2)).toBe('18s');
  });
});
