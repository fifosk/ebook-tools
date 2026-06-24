import {
  formatProgressValue,
  formatSeconds,
  type LookupCacheBuildingProgress,
  type LookupCacheProgress,
  type ProgressCount,
} from './jobProgressUtils';

type JobProgressStageSectionProps = {
  playableProgress: ProgressCount | null;
  lookupCacheBuildingProgress: LookupCacheBuildingProgress | null;
  lookupCacheProgress: LookupCacheProgress | null;
  translationBatchProgress: ProgressCount | null;
  transliterationBatchProgress: ProgressCount | null;
  mediaBatchProgress: ProgressCount | null;
  translationProgress: ProgressCount | null;
  mediaProgress: ProgressCount | null;
  showBatchStageProgress: boolean;
  showLookupCacheBuilding: boolean;
  showLookupCacheProgress: boolean;
  showPlayableProgress: boolean;
};

export function JobProgressStageSection({
  playableProgress,
  lookupCacheBuildingProgress,
  lookupCacheProgress,
  translationBatchProgress,
  transliterationBatchProgress,
  mediaBatchProgress,
  translationProgress,
  mediaProgress,
  showBatchStageProgress,
  showLookupCacheBuilding,
  showLookupCacheProgress,
  showPlayableProgress,
}: JobProgressStageSectionProps) {
  const shouldShow =
    showPlayableProgress ||
    showBatchStageProgress ||
    Boolean(translationProgress) ||
    Boolean(mediaProgress) ||
    showLookupCacheProgress ||
    showLookupCacheBuilding;

  if (!shouldShow) {
    return null;
  }

  return (
    <div>
      <h4>Stage progress</h4>
      <div className="progress-grid">
        {showPlayableProgress && playableProgress ? (
          <div className="progress-metric">
            <strong>Playable sentences</strong>
            <span>{formatProgressValue(playableProgress)}</span>
            <p className="progress-metric__hint">Sentences fully processed and ready for playback.</p>
          </div>
        ) : null}
        {showLookupCacheBuilding && lookupCacheBuildingProgress ? (
          <div className="progress-metric">
            <strong>Dictionary cache</strong>
            <span className="progress-metric__status progress-metric__status--building">
              {lookupCacheBuildingProgress.cachedEntries !== null
                ? `${lookupCacheBuildingProgress.cachedEntries} word${lookupCacheBuildingProgress.cachedEntries === 1 ? '' : 's'}`
                : (
                    <>
                      Building&hellip;
                    </>
                  )}
            </span>
            <p className="progress-metric__hint">
              {lookupCacheBuildingProgress.batchesCompleted !== null &&
              lookupCacheBuildingProgress.batchesTotal !== null
                ? `Batch ${lookupCacheBuildingProgress.batchesCompleted} / ${lookupCacheBuildingProgress.batchesTotal}`
                : 'Processing words'}
              {lookupCacheBuildingProgress.wordsToLookup !== null
                ? ` (${lookupCacheBuildingProgress.wordsToLookup} unique words)`
                : ''}
              . Playback is available.
            </p>
          </div>
        ) : null}
        {showLookupCacheProgress && lookupCacheProgress ? (
          <div className="progress-metric">
            <strong>Dictionary cache</strong>
            <span>
              {lookupCacheProgress.wordCount} word{lookupCacheProgress.wordCount === 1 ? '' : 's'}
              {lookupCacheProgress.skippedStopwords !== null
                ? ` (${lookupCacheProgress.skippedStopwords} stopwords skipped)`
                : ''}
            </span>
            <p className="progress-metric__hint">
              Unique words cached for instant lookups.
              {lookupCacheProgress.llmCalls !== null
                ? ` ${lookupCacheProgress.llmCalls} LLM call${lookupCacheProgress.llmCalls === 1 ? '' : 's'}.`
                : ''}
              {lookupCacheProgress.buildTimeSeconds !== null
                ? ` Built in ${formatSeconds(lookupCacheProgress.buildTimeSeconds, 's')}.`
                : ''}
            </p>
          </div>
        ) : null}
        {showBatchStageProgress ? (
          <>
            {translationBatchProgress ? (
              <div className="progress-metric">
                <strong>Translation batches</strong>
                <span>{formatProgressValue(translationBatchProgress)}</span>
                <p className="progress-metric__hint">Counts completed translation batches.</p>
              </div>
            ) : null}
            {transliterationBatchProgress ? (
              <div className="progress-metric">
                <strong>Transliteration batches</strong>
                <span>{formatProgressValue(transliterationBatchProgress)}</span>
                <p className="progress-metric__hint">Counts completed transliteration batches.</p>
              </div>
            ) : null}
            {mediaBatchProgress ? (
              <div className="progress-metric">
                <strong>Media batches</strong>
                <span>{formatProgressValue(mediaBatchProgress)}</span>
                <p className="progress-metric__hint">Counts batches with finished media output.</p>
              </div>
            ) : null}
          </>
        ) : null}
        {!showBatchStageProgress && translationProgress ? (
          <div className="progress-metric">
            <strong>Translation progress</strong>
            <span>{formatProgressValue(translationProgress)}</span>
            <p className="progress-metric__hint">Counts translated sentences (LLM/googletrans).</p>
          </div>
        ) : null}
        {!showBatchStageProgress && mediaProgress ? (
          <div className="progress-metric">
            <strong>Media progress</strong>
            <span>{formatProgressValue(mediaProgress)}</span>
            <p className="progress-metric__hint">Counts sentences with generated media output.</p>
          </div>
        ) : null}
      </div>
    </div>
  );
}
