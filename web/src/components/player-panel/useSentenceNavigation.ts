import { useCallback, useMemo, useState } from 'react';
import type { MutableRefObject } from 'react';
import type { LiveMediaChunk, LiveMediaItem } from '../../hooks/useLiveMedia';
import type { MediaSelectionRequest } from '../../types/player';
import type { MediaCategory } from './constants';
import {
  resolveChunkBaseId,
  type SentenceLookup,
  type SentenceLookupEntry,
  type SentenceLookupRange,
} from './helpers';

type UseSentenceNavigationArgs = {
  chunks: LiveMediaChunk[];
  mediaAudio: LiveMediaItem[];
  showOriginalAudio: boolean;
  findMatchingMediaId: (baseId: string | null, type: MediaCategory, available: LiveMediaItem[]) => string | null;
  requestAutoPlay: () => void;
  inlineAudioPlayingRef: MutableRefObject<boolean>;
  onRequestSelection: (request: MediaSelectionRequest) => void;
};

type SentenceTarget = {
  chunkIndex: number;
  baseId: string | null;
  ratio: number;
};

type UseSentenceNavigationResult = {
  sentenceLookup: SentenceLookup;
  jobStartSentence: number | null;
  jobEndSentence: number | null;
  canJumpToSentence: boolean;
  sentenceJumpPlaceholder: string | undefined;
  sentenceJumpValue: string;
  sentenceJumpError: string | null;
  onSentenceJumpChange: (value: string) => void;
  onSentenceJumpSubmit: () => void;
  onInteractiveSentenceJump: (sentenceNumber: number) => void;
};

export function useSentenceNavigation({
  chunks,
  mediaAudio,
  showOriginalAudio,
  findMatchingMediaId,
  requestAutoPlay,
  inlineAudioPlayingRef,
  onRequestSelection,
}: UseSentenceNavigationArgs): UseSentenceNavigationResult {
  const [sentenceJumpValue, setSentenceJumpValue] = useState('');
  const [sentenceJumpError, setSentenceJumpError] = useState<string | null>(null);

  const sentenceLookup = useMemo<SentenceLookup>(() => {
    const exact = new Map<number, SentenceLookupEntry>();
    const ranges: SentenceLookupRange[] = [];
    let min = Number.POSITIVE_INFINITY;
    let max = Number.NEGATIVE_INFINITY;
    const boundarySet = new Set<number>();

    const registerBoundary = (value: number | null | undefined): number | null => {
      if (typeof value !== 'number' || !Number.isFinite(value)) {
        return null;
      }
      const normalized = Math.trunc(value);
      boundarySet.add(normalized);
      if (normalized < min) {
        min = normalized;
      }
      if (normalized > max) {
        max = normalized;
      }
      return normalized;
    };

    chunks.forEach((chunk, chunkIndex) => {
      const baseId = resolveChunkBaseId(chunk);
      const start = registerBoundary(chunk.startSentence ?? null);
      const end = registerBoundary(chunk.endSentence ?? null);
      if (start !== null && end !== null && end >= start) {
        ranges.push({ start, end, chunkIndex, baseId });
      }
      if (Array.isArray(chunk.sentences) && chunk.sentences.length > 0) {
        const total = chunk.sentences.length;
        chunk.sentences.forEach((sentence, localIndex) => {
          if (!sentence) {
            return;
          }
          const absolute =
            typeof sentence.sentence_number === 'number' && Number.isFinite(sentence.sentence_number)
              ? Math.trunc(sentence.sentence_number)
              : null;
          if (absolute === null) {
            return;
          }
          boundarySet.add(absolute);
          if (absolute < min) {
            min = absolute;
          }
          if (absolute > max) {
            max = absolute;
          }
          exact.set(absolute, {
            chunkIndex,
            localIndex,
            total,
            baseId,
          });
        });
      }
    });

    const hasBounds = Number.isFinite(min) && Number.isFinite(max);
    const safeMin = hasBounds ? Math.trunc(min) : null;
    const safeMax = hasBounds ? Math.trunc(max) : null;
    const suggestions: number[] = [];
    if (safeMin !== null && safeMax !== null) {
      const span = safeMax - safeMin;
      if (span <= 200) {
        for (let value = safeMin; value <= safeMax; value += 1) {
          suggestions.push(value);
        }
      } else {
        boundarySet.add(safeMin);
        boundarySet.add(safeMax);
        const step = Math.max(1, Math.round(span / 25));
        for (let value = safeMin; value <= safeMax && boundarySet.size < 400; value += step) {
          boundarySet.add(value);
        }
        Array.from(boundarySet)
          .filter((value) => value >= safeMin && value <= safeMax)
          .sort((left, right) => left - right)
          .slice(0, 400)
          .forEach((value) => suggestions.push(value));
      }
    }

    return {
      min: safeMin,
      max: safeMax,
      exact,
      ranges,
      suggestions,
    };
  }, [chunks]);

  const findSentenceTarget = useCallback(
    (sentenceNumber: number): SentenceTarget | null => {
      if (!Number.isFinite(sentenceNumber)) {
        return null;
      }
      const target = Math.trunc(sentenceNumber);
      const exactEntry = sentenceLookup.exact.get(target);
      if (exactEntry) {
        const span = Math.max(exactEntry.total - 1, 1);
        const ratio =
          exactEntry.total > 1 ? exactEntry.localIndex / span : 0;
        return {
          chunkIndex: exactEntry.chunkIndex,
          baseId: exactEntry.baseId,
          ratio: Number.isFinite(ratio) ? Math.min(Math.max(ratio, 0), 1) : 0,
        };
      }
      for (const range of sentenceLookup.ranges) {
        if (target >= range.start && target <= range.end) {
          const span = range.end - range.start;
          const ratio = span > 0 ? (target - range.start) / span : 0;
          return {
            chunkIndex: range.chunkIndex,
            baseId: range.baseId,
            ratio: Number.isFinite(ratio) ? Math.min(Math.max(ratio, 0), 1) : 0,
          };
        }
      }
      return null;
    },
    [sentenceLookup],
  );

  const canJumpToSentence = sentenceLookup.min !== null && sentenceLookup.max !== null;
  const sentenceJumpPlaceholder =
    canJumpToSentence && sentenceLookup.min !== null && sentenceLookup.max !== null
      ? sentenceLookup.min === sentenceLookup.max
        ? `${sentenceLookup.min}`
        : `${sentenceLookup.min}–${sentenceLookup.max}`
      : undefined;

  const handleSentenceJumpChange = useCallback((value: string) => {
    setSentenceJumpValue(value);
    setSentenceJumpError(null);
  }, []);

  const handleSentenceJumpSubmit = useCallback(() => {
    if (!canJumpToSentence) {
      setSentenceJumpError('Sentence navigation unavailable.');
      return;
    }
    const trimmed = sentenceJumpValue.trim();
    if (!trimmed) {
      setSentenceJumpError('Enter a sentence number.');
      return;
    }
    const parsed = Number(trimmed);
    if (!Number.isFinite(parsed)) {
      setSentenceJumpError('Enter a valid sentence number.');
      return;
    }
    const target = Math.trunc(parsed);
    if (
      sentenceLookup.min !== null &&
      sentenceLookup.max !== null &&
      (target < sentenceLookup.min || target > sentenceLookup.max)
    ) {
      setSentenceJumpError(`Enter a number between ${sentenceLookup.min} and ${sentenceLookup.max}.`);
      return;
    }
    const resolution = findSentenceTarget(target);
    if (!resolution) {
      setSentenceJumpError('Sentence not found in current assets.');
      return;
    }
    const chunk = chunks[resolution.chunkIndex];
    if (!chunk) {
      setSentenceJumpError('Sentence chunk is unavailable.');
      return;
    }
    const baseId = resolution.baseId ?? resolveChunkBaseId(chunk);
    if (!baseId) {
      setSentenceJumpError('Unable to locate chunk for this sentence.');
      return;
    }
    setSentenceJumpValue(target.toString());
    setSentenceJumpError(null);
    onRequestSelection({
      baseId,
      preferredType: 'text',
      offsetRatio: resolution.ratio ?? null,
      approximateTime: null,
      token: Date.now(),
    });
  }, [
    canJumpToSentence,
    sentenceJumpValue,
    sentenceLookup.min,
    sentenceLookup.max,
    findSentenceTarget,
    chunks,
    onRequestSelection,
  ]);

  const handleInteractiveSentenceJump = useCallback(
    (sentenceNumber: number) => {
      if (!canJumpToSentence) {
        return;
      }
      if (!Number.isFinite(sentenceNumber)) {
        return;
      }
      const target = Math.trunc(sentenceNumber);
      if (
        sentenceLookup.min !== null &&
        sentenceLookup.max !== null &&
        (target < sentenceLookup.min || target > sentenceLookup.max)
      ) {
        return;
      }

      const resolution = findSentenceTarget(target);
      if (!resolution) {
        return;
      }
      const chunk = chunks[resolution.chunkIndex];
      if (!chunk) {
        return;
      }
      const baseId = resolution.baseId ?? resolveChunkBaseId(chunk);
      if (!baseId) {
        return;
      }

      const offsetRatio =
        typeof resolution.ratio === 'number' && Number.isFinite(resolution.ratio)
          ? Math.min(Math.max(resolution.ratio, 0), 1)
          : null;

      let approximateTime: number | null = null;
      if (offsetRatio !== null && chunk.audioTracks) {
        const normaliseUrl = (value: string) => value.replace(/[?#].*$/, '');
        const audioId = findMatchingMediaId(baseId, 'audio', mediaAudio);
        const audioNeedle = audioId ? normaliseUrl(audioId) : null;
        const resolveDuration = () => {
          if (!chunk.audioTracks) {
            return null;
          }
          if (audioNeedle) {
            for (const track of Object.values(chunk.audioTracks)) {
              const url = typeof track?.url === 'string' ? normaliseUrl(track.url) : null;
              if (url && url === audioNeedle) {
                const duration = track.duration ?? null;
                return typeof duration === 'number' && Number.isFinite(duration) && duration > 0 ? duration : null;
              }
            }
          }
          const combinedDuration = chunk.audioTracks.orig_trans?.duration ?? null;
          if (showOriginalAudio && typeof combinedDuration === 'number' && Number.isFinite(combinedDuration) && combinedDuration > 0) {
            return combinedDuration;
          }
          const translationDuration =
            chunk.audioTracks.translation?.duration ?? chunk.audioTracks.trans?.duration ?? null;
          if (typeof translationDuration === 'number' && Number.isFinite(translationDuration) && translationDuration > 0) {
            return translationDuration;
          }
          for (const track of Object.values(chunk.audioTracks)) {
            const duration = track?.duration ?? null;
            if (typeof duration === 'number' && Number.isFinite(duration) && duration > 0) {
              return duration;
            }
          }
          return null;
        };
        const duration = resolveDuration();
        if (duration !== null) {
          approximateTime = offsetRatio * duration;
        }
      }

      if (inlineAudioPlayingRef.current) {
        requestAutoPlay();
      }

      onRequestSelection({
        baseId,
        preferredType: 'text',
        offsetRatio,
        approximateTime,
        token: Date.now(),
      });
    },
    [
      canJumpToSentence,
      chunks,
      findMatchingMediaId,
      findSentenceTarget,
      inlineAudioPlayingRef,
      mediaAudio,
      requestAutoPlay,
      sentenceLookup.max,
      sentenceLookup.min,
      showOriginalAudio,
      onRequestSelection,
    ],
  );

  return {
    sentenceLookup,
    jobStartSentence: sentenceLookup.min ?? null,
    jobEndSentence: sentenceLookup.max ?? null,
    canJumpToSentence,
    sentenceJumpPlaceholder,
    sentenceJumpValue,
    sentenceJumpError,
    onSentenceJumpChange: handleSentenceJumpChange,
    onSentenceJumpSubmit: handleSentenceJumpSubmit,
    onInteractiveSentenceJump: handleInteractiveSentenceJump,
  };
}
