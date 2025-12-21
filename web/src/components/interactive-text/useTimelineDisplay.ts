import { useMemo } from 'react';
import type { MutableRefObject } from 'react';
import type { LiveMediaChunk } from '../../hooks/useLiveMedia';
import type {
  TextPlayerSentence,
  TextPlayerVariantDisplay,
  TextPlayerVariantKind,
} from '../../text-player/TextPlayer';
import type { TimelineSentenceRuntime, TimelineVariantRuntime } from './types';
import { buildUniformRevealTimes, normaliseTokens } from './utils';

type TimelineDisplay = {
  sentences: TextPlayerSentence[];
  activeIndex: number;
  effectiveTime: number;
};

type RevealMemoryRef = MutableRefObject<{
  sentenceIdx: number | null;
  counts: Record<TextPlayerVariantKind, number>;
}>;

type UseTimelineDisplayArgs = {
  chunk: LiveMediaChunk | null;
  hasTimeline: boolean;
  useCombinedPhases: boolean;
  activeTimingTrack: 'mix' | 'translation' | 'original';
  audioDuration: number | null;
  chunkTime: number;
  activeSentenceIndex: number;
  isVariantVisible: (variant: TextPlayerVariantKind) => boolean;
  revealMemoryRef: RevealMemoryRef;
};

export function useTimelineDisplay({
  chunk,
  hasTimeline,
  useCombinedPhases,
  activeTimingTrack,
  audioDuration,
  chunkTime,
  activeSentenceIndex,
  isVariantVisible,
  revealMemoryRef,
}: UseTimelineDisplayArgs): {
  timelineSentences: TimelineSentenceRuntime[] | null;
  timelineDisplay: TimelineDisplay | null;
} {
  const timelineSentences = useMemo(() => {
    if (!hasTimeline || !chunk?.sentences?.length) {
      return null;
    }

    let offset = 0;
    const result: TimelineSentenceRuntime[] = [];

    chunk.sentences.forEach((metadata, index) => {
      const originalTokens = normaliseTokens(metadata.original ?? undefined);
      const translationTokens = normaliseTokens(metadata.translation ?? undefined);
      const transliterationTokens = normaliseTokens(metadata.transliteration ?? undefined);

      const events = Array.isArray(metadata.timeline) ? metadata.timeline : [];

      const originalReveal: number[] = [];
      const isOriginalTrack = activeTimingTrack === 'original';

      const phaseDurations = useCombinedPhases ? metadata.phase_durations ?? null : null;
      const originalPhaseDuration = (() => {
        if (phaseDurations && typeof phaseDurations.original === 'number') {
          return Math.max(phaseDurations.original, 0);
        }
        if (originalTokens.length > 0) {
          return originalTokens.length * 0.35;
        }
        return 0;
      })();
      const gapBeforeTranslation =
        phaseDurations && typeof phaseDurations.gap === 'number'
          ? Math.max(phaseDurations.gap, 0)
          : 0;
      const tailPhaseDuration =
        phaseDurations && typeof phaseDurations.tail === 'number'
          ? Math.max(phaseDurations.tail, 0)
          : 0;
      const translationPhaseDurationOverride =
        phaseDurations && typeof phaseDurations.translation === 'number'
          ? Math.max(phaseDurations.translation, 0)
          : null;
      const highlightOriginal =
        (useCombinedPhases || isOriginalTrack) &&
        originalTokens.length > 0 &&
        originalPhaseDuration > 0;

      const eventDurationTotal = events.reduce((total, event) => {
        const duration = typeof event.duration === 'number' && event.duration > 0 ? event.duration : 0;
        return total + duration;
      }, 0);

      const declaredDuration = (() => {
        if (typeof metadata.total_duration === 'number' && metadata.total_duration > 0) {
          return metadata.total_duration;
        }
        if (eventDurationTotal > 0) {
          return eventDurationTotal;
        }
        const fallbackTokens = Math.max(
          originalTokens.length,
          translationTokens.length,
          transliterationTokens.length,
        );
        if (fallbackTokens > 0) {
          return fallbackTokens * 0.35;
        }
        return 0.5;
      })();

      const sentenceStart = offset;

      const translationPhaseDuration = (() => {
        if (isOriginalTrack) {
          return 0;
        }
        if (translationPhaseDurationOverride !== null && translationPhaseDurationOverride > 0) {
          return translationPhaseDurationOverride;
        }
        if (declaredDuration > 0) {
          return declaredDuration;
        }
        if (translationTokens.length > 0 || transliterationTokens.length > 0) {
          return Math.max(translationTokens.length, transliterationTokens.length) * 0.35;
        }
        return 0.5;
      })();

      const translationTrackStart = sentenceStart + (useCombinedPhases ? originalPhaseDuration + gapBeforeTranslation : 0);

      const translationDurationsRaw: number[] = [];
      let prevTranslationCount = 0;

      if (!isOriginalTrack) {
        events.forEach((event) => {
          const baseDuration = typeof event.duration === 'number' && event.duration > 0 ? event.duration : 0;
          if (!(baseDuration > 0)) {
            return;
          }
          const targetTranslationIndex =
            typeof event.translation_index === 'number' ? Math.max(0, event.translation_index) : prevTranslationCount;
          const nextTranslationCount = Math.min(
            translationTokens.length,
            Math.max(prevTranslationCount, targetTranslationIndex),
          );
          const delta = nextTranslationCount - prevTranslationCount;
          if (delta <= 0) {
            return;
          }
          const perToken = baseDuration / delta;
          for (let idx = 0; idx < delta; idx += 1) {
            translationDurationsRaw.push(perToken);
          }
          prevTranslationCount = nextTranslationCount;
        });
      }

      const totalTranslationDurationRaw = translationDurationsRaw.reduce((sum, value) => sum + value, 0);
      const translationSpeechDuration =
        totalTranslationDurationRaw > 0 ? totalTranslationDurationRaw : translationPhaseDuration;
      const translationTotalDuration = translationSpeechDuration + tailPhaseDuration;
      const translationPhaseEndAbsolute = translationTrackStart + translationTotalDuration;

      let translationRevealTimes: number[] = [];
      if (!isOriginalTrack && translationDurationsRaw.length > 0) {
        let cumulativeTranslation = 0;
        translationDurationsRaw.forEach((rawDuration) => {
          translationRevealTimes.push(translationTrackStart + cumulativeTranslation);
          cumulativeTranslation += rawDuration;
        });
      }

      if (
        !isOriginalTrack &&
        translationRevealTimes.length !== translationTokens.length &&
        translationTokens.length > 0
      ) {
        translationRevealTimes = buildUniformRevealTimes(
          translationTokens.length,
          translationTrackStart,
          translationSpeechDuration,
        );
      }

      const transliterationRevealTimes =
        !isOriginalTrack && transliterationTokens.length > 0
          ? transliterationTokens.map((_, idx) => {
              if (translationRevealTimes.length === 0) {
                return translationTrackStart;
              }
              if (translationRevealTimes.length === 1) {
                return translationRevealTimes[0];
              }
              const ratio = transliterationTokens.length > 1 ? idx / (transliterationTokens.length - 1) : 0;
              const mappedIndex = Math.min(
                translationRevealTimes.length - 1,
                Math.round(ratio * (translationRevealTimes.length - 1)),
              );
              return translationRevealTimes[mappedIndex];
            })
          : [];

      if (!isOriginalTrack && translationRevealTimes.length > 0) {
        translationRevealTimes[0] = translationTrackStart;
        translationRevealTimes[translationRevealTimes.length - 1] = translationPhaseEndAbsolute;
      }
      if (!isOriginalTrack && transliterationRevealTimes.length > 0) {
        transliterationRevealTimes[0] = translationTrackStart;
        transliterationRevealTimes[transliterationRevealTimes.length - 1] = translationPhaseEndAbsolute;
      }

      if (highlightOriginal) {
        const reveals = buildUniformRevealTimes(originalTokens.length, sentenceStart, originalPhaseDuration);
        originalReveal.splice(0, originalReveal.length, ...reveals);
      }

      const sentenceDuration = useCombinedPhases
        ? originalPhaseDuration + gapBeforeTranslation + translationTotalDuration
        : isOriginalTrack
          ? originalPhaseDuration
          : translationTotalDuration;
      const endTime = sentenceStart + sentenceDuration;

      result.push({
        index,
        sentenceNumber: metadata.sentence_number ?? null,
        startTime: sentenceStart,
        endTime,
        variants: {
          original: {
            tokens: originalTokens,
            revealTimes: originalReveal,
          },
          translation: translationTokens.length
            ? {
                tokens: translationTokens,
                revealTimes: translationRevealTimes,
              }
            : undefined,
          transliteration: transliterationTokens.length
            ? {
                tokens: transliterationTokens,
                revealTimes: transliterationRevealTimes,
              }
            : undefined,
        },
      });

      offset = endTime;
    });

    if (!useCombinedPhases && audioDuration && audioDuration > 0 && result.length > 0) {
      const totalTimelineDuration = result[result.length - 1].endTime;
      if (totalTimelineDuration > 0) {
        const scale = audioDuration / totalTimelineDuration;
        const scaled = result.map((sentence) => {
          const originalVariant = {
            ...sentence.variants.original,
            revealTimes: sentence.variants.original.revealTimes.map((time) => time * scale),
          };

          const translationVariant = sentence.variants.translation
            ? {
                ...sentence.variants.translation,
                revealTimes: sentence.variants.translation.revealTimes.map((time) => time * scale),
              }
            : undefined;

          const transliterationVariant = sentence.variants.transliteration
            ? {
                ...sentence.variants.transliteration,
                revealTimes: sentence.variants.transliteration.revealTimes.map((time) => time * scale),
              }
            : undefined;

          return {
            ...sentence,
            startTime: sentence.startTime * scale,
            endTime: sentence.endTime * scale,
            variants: {
              original: originalVariant,
              translation: translationVariant,
              transliteration: transliterationVariant,
            },
          };
        });
        return scaled;
      }
    }

    return result;
  }, [activeTimingTrack, audioDuration, chunk?.sentences, hasTimeline, useCombinedPhases]);

  const timelineDisplay = useMemo(() => {
    if (!timelineSentences) {
      return null;
    }

    const displaySentences: TextPlayerSentence[] = [];
    let activeIndex: number | null = null;

    const timelineTotalDuration =
      timelineSentences.length > 0 ? timelineSentences[timelineSentences.length - 1].endTime : null;
    const effectiveTime = (() => {
      if (!timelineTotalDuration || !audioDuration || audioDuration <= 0 || timelineTotalDuration <= 0) {
        return Math.max(chunkTime, 0);
      }
      const ratio = timelineTotalDuration / audioDuration;
      if (ratio > 0.98 && ratio < 1.02) {
        return Math.min(chunkTime, timelineTotalDuration);
      }
      const scaled = (chunkTime / audioDuration) * timelineTotalDuration;
      if (!Number.isFinite(scaled) || scaled < 0) {
        return 0;
      }
      return Math.min(scaled, timelineTotalDuration);
    })();

    timelineSentences.forEach((runtime) => {
      const { startTime, endTime } = runtime;
      let timeState: 'past' | 'active' | 'future';
      if (effectiveTime < startTime - 1e-3) {
        timeState = 'future';
      } else if (effectiveTime > endTime + 1e-3) {
        timeState = 'past';
      } else {
        timeState = 'active';
        if (activeIndex === null) {
          activeIndex = runtime.index;
        }
      }

      const stabilisedState: 'past' | 'active' | 'future' = (() => {
        if (runtime.index === activeSentenceIndex) {
          return 'active';
        }
        if (runtime.index < activeSentenceIndex) {
          return 'past';
        }
        if (runtime.index > activeSentenceIndex) {
          return 'future';
        }
        return timeState;
      })();

      const variants: TextPlayerVariantDisplay[] = [];

      const buildVariant = (
        label: string,
        baseClass: TextPlayerVariantKind,
        variantRuntime?: TimelineVariantRuntime,
      ) => {
        if (!isVariantVisible(baseClass)) {
          return;
        }
        if (!variantRuntime || variantRuntime.tokens.length === 0) {
          return;
        }

        const tokens = variantRuntime.tokens;
        const revealTimes = variantRuntime.revealTimes;
        const safeEffectiveTime = Math.min(Math.max(effectiveTime, startTime - 1e-3), endTime + 1e-3);
        const revealCutoff = Math.min(safeEffectiveTime, endTime);
        const progressCount = revealTimes.filter((time) => time <= revealCutoff + 1e-3).length;

        let revealedCount: number;
        if (stabilisedState === 'past') {
          revealedCount = tokens.length;
        } else if (stabilisedState === 'future') {
          revealedCount = progressCount;
        } else {
          revealedCount = progressCount;
        }

        revealedCount = Math.max(0, Math.min(revealedCount, tokens.length));
        if (safeEffectiveTime >= endTime - 1e-3) {
          revealedCount = tokens.length;
        }
        if (revealMemoryRef.current.sentenceIdx !== runtime.index) {
          revealMemoryRef.current = {
            sentenceIdx: runtime.index,
            counts: { original: 0, translit: 0, translation: 0 },
          };
        }
        const previousCount = revealMemoryRef.current.counts[baseClass] ?? 0;
        const stableCount = Math.max(previousCount, revealedCount);
        revealMemoryRef.current.counts[baseClass] = stableCount;
        revealedCount = stableCount;
        const zeroToOneEligible =
          revealTimes.length > 0 &&
          stabilisedState === 'active' &&
          safeEffectiveTime >= startTime - 1e-3 &&
          revealedCount === 0;
        if (zeroToOneEligible) {
          revealedCount = 1;
          revealMemoryRef.current.counts[baseClass] = 1;
        }

        let currentIndex: number | null = revealedCount > 0 ? revealedCount - 1 : null;
        if (tokens.length > 0 && (stabilisedState === 'past' || safeEffectiveTime >= endTime - 1e-3)) {
          currentIndex = tokens.length - 1;
        }

        variants.push({
          label,
          tokens,
          revealedCount,
          currentIndex,
          baseClass,
          seekTimes: variantRuntime.revealTimes,
        });
      };

      buildVariant('Original', 'original', runtime.variants.original);
      buildVariant('Transliteration', 'translit', runtime.variants.transliteration);
      buildVariant('Translation', 'translation', runtime.variants.translation);

      if (variants.length === 0) {
        return;
      }

      displaySentences.push({
        id: `sentence-${runtime.index}`,
        index: runtime.index,
        sentenceNumber: runtime.sentenceNumber ?? runtime.index + 1,
        state: stabilisedState,
        variants,
      });
    });

    if (activeIndex === null && displaySentences.length > 0) {
      for (let i = displaySentences.length - 1; i >= 0; i -= 1) {
        if (displaySentences[i].state === 'past') {
          activeIndex = displaySentences[i].index;
          break;
        }
      }
      if (activeIndex === null) {
        activeIndex = 0;
      }
    }

    return {
      sentences: displaySentences,
      activeIndex: activeIndex ?? 0,
      effectiveTime,
    };
  }, [timelineSentences, chunkTime, audioDuration, activeSentenceIndex, isVariantVisible]);

  return { timelineSentences, timelineDisplay };
}
