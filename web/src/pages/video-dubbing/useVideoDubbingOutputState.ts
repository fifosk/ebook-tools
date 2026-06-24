import { useCallback, useEffect, useState } from 'react';
import { fetchBookCreationOptions } from '../../api/createBook';
import type { JobParameterSnapshot } from '../../api/dtos';
import {
  DEFAULT_FLUSH_SENTENCES,
  DEFAULT_ORIGINAL_MIX_PERCENT,
  DEFAULT_PRESERVE_ASPECT_RATIO,
  DEFAULT_SPLIT_BATCHES,
  DEFAULT_STITCH_BATCHES,
  DEFAULT_TARGET_HEIGHT,
  DEFAULT_TRANSLATION_BATCH_SIZE
} from './videoDubbingConfig';
import { resolveVideoDubPrefill } from './videoDubbingUtils';

type VideoDubbingOutputStateOptions = {
  prefillParameters?: JobParameterSnapshot | null;
};

export function useVideoDubbingOutputState({
  prefillParameters = null
}: VideoDubbingOutputStateOptions = {}) {
  const [startOffset, setStartOffset] = useState('');
  const [endOffset, setEndOffset] = useState('');
  const [originalMixPercent, setOriginalMixPercent] = useState(DEFAULT_ORIGINAL_MIX_PERCENT);
  const [flushSentences, setFlushSentences] = useState(DEFAULT_FLUSH_SENTENCES);
  const [translationBatchSize, setTranslationBatchSize] = useState(DEFAULT_TRANSLATION_BATCH_SIZE);
  const [targetHeight, setTargetHeight] = useState(DEFAULT_TARGET_HEIGHT);
  const [preserveAspectRatio, setPreserveAspectRatio] = useState(DEFAULT_PRESERVE_ASPECT_RATIO);
  const [splitBatches, setSplitBatches] = useState(DEFAULT_SPLIT_BATCHES);
  const [stitchBatches, setStitchBatches] = useState(DEFAULT_STITCH_BATCHES);
  const [includeTransliteration, setIncludeTransliteration] = useState(true);
  const [enableLookupCache, setEnableLookupCache] = useState(true);

  const applyYoutubeDubDefaults = useCallback(
    (defaults: Awaited<ReturnType<typeof fetchBookCreationOptions>>['youtube_dub_defaults']) => {
      if (!defaults) {
        return;
      }
      setOriginalMixPercent((current) =>
        current === DEFAULT_ORIGINAL_MIX_PERCENT ? defaults.original_mix_percent : current
      );
      setFlushSentences((current) =>
        current === DEFAULT_FLUSH_SENTENCES ? defaults.flush_sentences : current
      );
      setTranslationBatchSize((current) =>
        current === DEFAULT_TRANSLATION_BATCH_SIZE ? defaults.translation_batch_size : current
      );
      setTargetHeight((current) =>
        current === DEFAULT_TARGET_HEIGHT ? defaults.target_height : current
      );
      setPreserveAspectRatio((current) =>
        current === DEFAULT_PRESERVE_ASPECT_RATIO ? defaults.preserve_aspect_ratio : current
      );
      setSplitBatches((current) =>
        current === DEFAULT_SPLIT_BATCHES ? defaults.split_batches : current
      );
      setStitchBatches((current) =>
        current === DEFAULT_STITCH_BATCHES ? defaults.stitch_batches : current
      );
    },
    []
  );

  useEffect(() => {
    if (prefillParameters) {
      return undefined;
    }
    let cancelled = false;
    const loadCreationDefaults = async () => {
      try {
        const options = await fetchBookCreationOptions();
        if (!cancelled) {
          applyYoutubeDubDefaults(options.youtube_dub_defaults);
        }
      } catch (error) {
        if (!cancelled) {
          console.warn('Unable to load YouTube dubbing creation defaults', error);
        }
      }
    };
    void loadCreationDefaults();
    return () => {
      cancelled = true;
    };
  }, [applyYoutubeDubDefaults, prefillParameters]);

  useEffect(() => {
    const prefill = resolveVideoDubPrefill(prefillParameters);
    if (!prefill) {
      return;
    }
    if (prefill.startOffset !== undefined) {
      setStartOffset(prefill.startOffset);
    }
    if (prefill.endOffset !== undefined) {
      setEndOffset(prefill.endOffset);
    }
    setOriginalMixPercent(prefill.originalMixPercent);
    if (prefill.flushSentences !== undefined) {
      setFlushSentences(prefill.flushSentences);
    }
    if (prefill.translationBatchSize !== undefined) {
      setTranslationBatchSize(prefill.translationBatchSize);
    }
    setTargetHeight(prefill.targetHeight);
    setPreserveAspectRatio(prefill.preserveAspectRatio);
    setSplitBatches(prefill.splitBatches);
    setIncludeTransliteration(prefill.includeTransliteration);
  }, [prefillParameters]);

  return {
    startOffset,
    setStartOffset,
    endOffset,
    setEndOffset,
    originalMixPercent,
    setOriginalMixPercent,
    flushSentences,
    setFlushSentences,
    translationBatchSize,
    setTranslationBatchSize,
    targetHeight,
    setTargetHeight,
    preserveAspectRatio,
    setPreserveAspectRatio,
    splitBatches,
    setSplitBatches,
    stitchBatches,
    setStitchBatches,
    includeTransliteration,
    setIncludeTransliteration,
    enableLookupCache,
    setEnableLookupCache
  };
}
