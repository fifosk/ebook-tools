import { useMemo } from 'react';
import type { LiveMediaChunk } from '../../hooks/useLiveMedia';

type SlideIndicator = {
  label: string;
};

type UseSlideIndicatorArgs = {
  chunk: LiveMediaChunk | null;
  activeSentenceIndex: number;
  jobStartSentence?: number | null;
  jobEndSentence?: number | null;
  bookTotalSentences?: number | null;
  totalSentencesInBook?: number | null;
};

export function useSlideIndicator({
  chunk,
  activeSentenceIndex,
  jobStartSentence = null,
  jobEndSentence = null,
  bookTotalSentences = null,
  totalSentencesInBook = null,
}: UseSlideIndicatorArgs): SlideIndicator | null {
  return useMemo(() => {
    if (!chunk) {
      return null;
    }
    const start =
      typeof chunk.startSentence === 'number' && Number.isFinite(chunk.startSentence)
        ? Math.max(Math.trunc(chunk.startSentence), 1)
        : null;

    const currentFromMetadata = (() => {
      if (!Array.isArray(chunk.sentences) || chunk.sentences.length === 0) {
        return null;
      }
      const activeMeta = chunk.sentences[Math.max(0, Math.min(activeSentenceIndex, chunk.sentences.length - 1))];
      const candidate = activeMeta?.sentence_number;
      return typeof candidate === 'number' && Number.isFinite(candidate) ? Math.trunc(candidate) : null;
    })();

    const current =
      start !== null
        ? start + Math.max(activeSentenceIndex, 0)
        : currentFromMetadata;

    const sentenceCountFromChunk =
      typeof chunk.sentenceCount === 'number' && Number.isFinite(chunk.sentenceCount)
        ? Math.max(Math.trunc(chunk.sentenceCount), 0)
        : Array.isArray(chunk.sentences)
          ? chunk.sentences.length
          : null;

    const jobEndFromCount =
      start !== null && sentenceCountFromChunk !== null && sentenceCountFromChunk > 0
        ? start + sentenceCountFromChunk - 1
        : null;

    const jobEndFromMetadata = (() => {
      if (!Array.isArray(chunk.sentences) || chunk.sentences.length === 0) {
        return null;
      }
      const last = chunk.sentences[chunk.sentences.length - 1]?.sentence_number;
      return typeof last === 'number' && Number.isFinite(last) ? Math.trunc(last) : null;
    })();

    const explicitJobEnd =
      typeof jobEndSentence === 'number' && Number.isFinite(jobEndSentence)
        ? Math.max(Math.trunc(jobEndSentence), 1)
        : null;
    const jobEndFromChunk =
      typeof chunk.endSentence === 'number' && Number.isFinite(chunk.endSentence)
        ? Math.max(Math.trunc(chunk.endSentence), start ?? 1)
        : null;
    const jobEnd = explicitJobEnd ?? jobEndFromChunk ?? jobEndFromCount ?? jobEndFromMetadata;

    const resolvedJobStart =
      typeof jobStartSentence === 'number' && Number.isFinite(jobStartSentence)
        ? Math.max(Math.trunc(jobStartSentence), 1)
        : start ?? 1;

    const resolvedBookTotal =
      typeof bookTotalSentences === 'number' && Number.isFinite(bookTotalSentences)
        ? Math.max(Math.trunc(bookTotalSentences), 1)
        : typeof totalSentencesInBook === 'number' && Number.isFinite(totalSentencesInBook)
          ? Math.max(Math.trunc(totalSentencesInBook), 1)
          : null;

    if (current === null) {
      return null;
    }

    const displayCurrent = jobEnd !== null ? Math.min(current, jobEnd) : current;
    const base = jobEnd !== null ? `Playing sentence ${displayCurrent} of ${jobEnd}` : `Playing sentence ${displayCurrent}`;

    const jobPercent = (() => {
      if (jobEnd === null) {
        return null;
      }
      const span = Math.max(jobEnd - resolvedJobStart, 0);
      const ratio = span > 0 ? (displayCurrent - resolvedJobStart) / span : 1;
      if (!Number.isFinite(ratio)) {
        return null;
      }
      return Math.min(Math.max(Math.round(ratio * 100), 0), 100);
    })();

    const bookPercent = (() => {
      if (resolvedBookTotal === null) {
        return null;
      }
      const ratio = resolvedBookTotal > 0 ? displayCurrent / resolvedBookTotal : null;
      if (ratio === null || !Number.isFinite(ratio)) {
        return null;
      }
      return Math.min(Math.max(Math.round(ratio * 100), 0), 100);
    })();

    const suffixParts: string[] = [];
    if (jobPercent !== null) {
      suffixParts.push(`Job ${jobPercent}%`);
    }
    if (bookPercent !== null) {
      suffixParts.push(`Book ${bookPercent}%`);
    }
    const label = suffixParts.length > 0 ? `${base} · ${suffixParts.join(' · ')}` : base;

    return { label };
  }, [activeSentenceIndex, bookTotalSentences, chunk, jobEndSentence, jobStartSentence, totalSentencesInBook]);
}
