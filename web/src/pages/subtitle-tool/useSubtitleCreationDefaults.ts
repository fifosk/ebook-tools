import { useEffect } from 'react';
import type { BookCreationOptionsResponse } from '../../api/createBook';
import { fetchBookCreationOptions } from '../../api/createBook';

type UseSubtitleCreationDefaultsOptions = {
  shouldSkipDefaults: boolean;
  applySubtitleDefaults: (
    defaults: BookCreationOptionsResponse['subtitle_defaults'],
    pipelineDefaults?: BookCreationOptionsResponse['pipeline_defaults']
  ) => void;
};

export function useSubtitleCreationDefaults({
  shouldSkipDefaults,
  applySubtitleDefaults
}: UseSubtitleCreationDefaultsOptions) {
  useEffect(() => {
    if (shouldSkipDefaults) {
      return undefined;
    }
    let cancelled = false;
    const loadCreationDefaults = async () => {
      try {
        const options = await fetchBookCreationOptions();
        if (!cancelled) {
          applySubtitleDefaults(options.subtitle_defaults, options.pipeline_defaults);
        }
      } catch (error) {
        if (!cancelled) {
          console.warn('Unable to load subtitle creation defaults', error);
        }
      }
    };
    void loadCreationDefaults();
    return () => {
      cancelled = true;
    };
  }, [applySubtitleDefaults, shouldSkipDefaults]);
}
