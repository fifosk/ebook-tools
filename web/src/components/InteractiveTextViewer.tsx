import {
  forwardRef,
  useCallback,
  useEffect,
  useImperativeHandle,
  useMemo,
  useRef,
  useState,
} from 'react';
import type { UIEvent } from 'react';
import { appendAccessToken } from '../api/client';
import type { LiveMediaChunk, LiveMediaItem } from '../hooks/useLiveMedia';
import TextPlayer, {
  type TextPlayerSentence,
  type TextPlayerVariantDisplay,
  type TextPlayerVariantKind,
} from '../text-player/TextPlayer';

type SentenceFragment = {
  index: number;
  text: string;
  wordCount: number;
  parts: Array<{ content: string; isWord: boolean }>;
  translation: string | null;
  transliteration: string | null;
  weight: number;
};

type ParagraphFragment = {
  id: string;
  sentences: SentenceFragment[];
};

type TimelineVariantRuntime = {
  tokens: string[];
  revealTimes: number[];
};

type TimelineSentenceRuntime = {
  index: number;
  sentenceNumber?: number | null;
  startTime: number;
  endTime: number;
  variants: {
    original: TimelineVariantRuntime;
    translation?: TimelineVariantRuntime;
    transliteration?: TimelineVariantRuntime;
  };
};

function normaliseTokens(variant?: { tokens?: string[]; text?: string | null }): string[] {
  if (!variant) {
    return [];
  }
  if (Array.isArray(variant.tokens) && variant.tokens.length > 0) {
    return variant.tokens.filter((token) => typeof token === 'string' && token.length > 0);
  }
  if (variant.text && typeof variant.text === 'string') {
    const trimmed = variant.text.trim();
    if (!trimmed) {
      return [];
    }
    return trimmed.split(/\s+/);
  }
  return [];
}

function distributeRevealTimes(
  previousCount: number,
  nextCount: number,
  startTime: number,
  duration: number,
  collector: number[],
) {
  const clampedPrev = Math.max(previousCount, 0);
  const clampedNext = Math.max(nextCount, 0);
  const delta = clampedNext - clampedPrev;
  if (delta <= 0) {
    return;
  }
  const safeDuration = duration > 0 ? duration : 0;
  const step = delta > 0 ? safeDuration / delta : 0;
  for (let i = 1; i <= delta; i += 1) {
    collector.push(startTime + step * i);
  }
}

function fillRemainTimes(target: number[], totalTokens: number, fallbackTime: number) {
  const safeFallback = fallbackTime > 0 ? fallbackTime : 0;
  while (target.length < totalTokens) {
    target.push(safeFallback);
  }
  if (target.length > totalTokens) {
    target.length = totalTokens;
  }
}

interface InteractiveTextViewerProps {
  content: string;
  rawContent?: string | null;
  chunk: LiveMediaChunk | null;
  audioItems: LiveMediaItem[];
  onScroll?: (event: UIEvent<HTMLDivElement>) => void;
  onAudioProgress?: (audioUrl: string, position: number) => void;
  getStoredAudioPosition?: (audioUrl: string) => number;
}

type SegmenterInstance = {
  segment: (input: string) => Iterable<{ segment: string }>;
};

type SegmenterConstructor = new (
  locales?: Intl.LocalesArgument,
  options?: { granularity?: 'grapheme' | 'word' | 'sentence' },
) => SegmenterInstance;

const segmenterCtor =
  typeof Intl !== 'undefined'
    ? (Intl as typeof Intl & { Segmenter?: SegmenterConstructor }).Segmenter ?? null
    : null;
const hasIntlSegmenter = typeof segmenterCtor === 'function';

function segmentParagraph(paragraph: string): string[] {
  if (!paragraph) {
    return [];
  }

  const trimmed = paragraph.trim();
  if (!trimmed) {
    return [];
  }

  if (hasIntlSegmenter && segmenterCtor) {
    try {
      const segmenter = new segmenterCtor(undefined, { granularity: 'sentence' });
      const segments: string[] = [];
      for (const entry of segmenter.segment(trimmed)) {
        const segment = entry.segment.trim();
        if (segment) {
          segments.push(segment);
        }
      }
      if (segments.length > 0) {
        return segments;
      }
    } catch (error) {
      // Ignore segmenter failures and fall back to regex splitting.
    }
  }

  const fallbackMatches = trimmed.match(/[^.!?。！？]+[.!?。！？]?/g);
  if (!fallbackMatches || fallbackMatches.length === 0) {
    return [trimmed];
  }

  return fallbackMatches.map((segment) => segment.trim()).filter(Boolean);
}

function buildSentenceParts(value: string): Array<{ content: string; isWord: boolean }> {
  if (!value) {
    return [];
  }
  const segments = value.match(/(\S+|\s+)/g) ?? [value];
  return segments.map((segment) => ({
    content: segment,
    isWord: /\S/.test(segment) && !/^\s+$/.test(segment),
  }));
}

function parseSentenceVariants(raw: string): {
  primary: string;
  translation: string | null;
  transliteration: string | null;
} {
  const trimmed = raw.trim();
  if (!trimmed) {
    return { primary: '', translation: null, transliteration: null };
  }
  const segments = trimmed
    .split('||')
    .map((segment) => segment.trim())
    .filter((segment, index) => segment.length > 0 || index === 0);
  const primary = segments[0] ?? trimmed;
  const translation = segments[1] ?? null;
  const transliteration = segments[2] ?? null;
  return {
    primary,
    translation,
    transliteration,
  };
}

function buildParagraphs(content: string): ParagraphFragment[] {
  const trimmed = content?.trim();
  if (!trimmed) {
    return [];
  }

  const rawParagraphs = trimmed.split(/\n{2,}/).map((paragraph) => paragraph.replace(/\s*\n\s*/g, ' ').trim());
  const paragraphs: ParagraphFragment[] = [];
  let nextIndex = 0;

  rawParagraphs.forEach((raw, paragraphIndex) => {
    if (!raw) {
      return;
    }

    const segments = segmentParagraph(raw);
    if (segments.length === 0) {
      const variants = parseSentenceVariants(raw);
      const parts = buildSentenceParts(variants.primary);
      const wordCount = parts.filter((part) => part.isWord).length;
      const weight = Math.max(wordCount, variants.primary.length, 1);
      paragraphs.push({
        id: `paragraph-${paragraphIndex}`,
        sentences: [
          {
            index: nextIndex,
            text: variants.primary,
            translation: variants.translation,
            transliteration: variants.transliteration,
            parts,
            wordCount,
            weight,
          },
        ],
      });
      nextIndex += 1;
      return;
    }

    const sentences: SentenceFragment[] = segments.map((segment) => {
      const variants = parseSentenceVariants(segment);
      const parts = buildSentenceParts(variants.primary);
      const wordCount = parts.filter((part) => part.isWord).length;
      const weight = Math.max(wordCount, variants.primary.length, 1);
      const fragment: SentenceFragment = {
        index: nextIndex,
        text: variants.primary,
        translation: variants.translation,
        transliteration: variants.transliteration,
        parts,
        wordCount,
        weight,
      };
      nextIndex += 1;
      return fragment;
    });

    paragraphs.push({
      id: `paragraph-${paragraphIndex}`,
      sentences,
    });
  });

  if (paragraphs.length === 0) {
    const variants = parseSentenceVariants(trimmed);
    const fallbackParts = buildSentenceParts(variants.primary);
    const fallbackWordCount = fallbackParts.filter((part) => part.isWord).length;
    const fallbackWeight = Math.max(fallbackWordCount, variants.primary.length, 1);
    return [
      {
        id: 'paragraph-0',
        sentences: [
          {
            index: 0,
            text: variants.primary,
            translation: variants.translation,
            transliteration: variants.transliteration,
            parts: fallbackParts,
            wordCount: fallbackWordCount,
            weight: fallbackWeight,
          },
        ],
      },
    ];
  }

  return paragraphs;
}

const InteractiveTextViewer = forwardRef<HTMLDivElement | null, InteractiveTextViewerProps>(function InteractiveTextViewer(
  {
    content,
    chunk,
    audioItems,
    onScroll,
    onAudioProgress,
    getStoredAudioPosition,
  },
  forwardedRef,
) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  useImperativeHandle<HTMLDivElement | null, HTMLDivElement | null>(forwardedRef, () => containerRef.current);
  const [chunkTime, setChunkTime] = useState(0);
  const hasTimeline = Boolean(chunk?.sentences && chunk.sentences.length > 0);
  const [audioDuration, setAudioDuration] = useState<number | null>(null);

  const paragraphs = useMemo(() => buildParagraphs(content), [content]);
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
      const translationReveal: number[] = [];
      const transliterationReveal: number[] = [];

      let prevOriginal = 0;
      let prevTranslation = 0;
      let prevTranslit = 0;
      let elapsed = 0;

      events.forEach((event) => {
        const duration = typeof event.duration === 'number' && event.duration > 0 ? event.duration : 0;
        const eventStart = offset + elapsed;
        const nextOriginal = Math.min(
          typeof event.original_index === 'number' ? Math.max(event.original_index, 0) : prevOriginal,
          originalTokens.length,
        );
        const nextTranslation = Math.min(
          typeof event.translation_index === 'number' ? Math.max(event.translation_index, 0) : prevTranslation,
          translationTokens.length,
        );
        const nextTranslit = Math.min(
          typeof event.transliteration_index === 'number'
            ? Math.max(event.transliteration_index, 0)
            : prevTranslit,
          transliterationTokens.length,
        );

        distributeRevealTimes(prevOriginal, nextOriginal, eventStart, duration, originalReveal);
        distributeRevealTimes(prevTranslation, nextTranslation, eventStart, duration, translationReveal);
        distributeRevealTimes(prevTranslit, nextTranslit, eventStart, duration, transliterationReveal);

        prevOriginal = nextOriginal;
        prevTranslation = nextTranslation;
        prevTranslit = nextTranslit;
        elapsed += duration;
      });

      const totalDuration = (() => {
        if (typeof metadata.total_duration === 'number' && metadata.total_duration > 0) {
          return metadata.total_duration;
        }
        if (elapsed > 0) {
          return elapsed;
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

      const endTime = offset + totalDuration;

      fillRemainTimes(originalReveal, originalTokens.length, endTime);
      fillRemainTimes(translationReveal, translationTokens.length, endTime);
      fillRemainTimes(transliterationReveal, transliterationTokens.length, endTime);

      result.push({
        index,
        sentenceNumber: metadata.sentence_number ?? null,
        startTime: offset,
        endTime,
        variants: {
          original: {
            tokens: originalTokens,
            revealTimes: originalReveal,
          },
          translation: translationTokens.length
            ? {
                tokens: translationTokens,
                revealTimes: translationReveal,
              }
            : undefined,
          transliteration: transliterationTokens.length
            ? {
                tokens: transliterationTokens,
                revealTimes: transliterationReveal,
              }
            : undefined,
        },
      });

      offset = endTime;
    });

    return result;
  }, [chunk?.sentences, hasTimeline]);
  const timelineDisplay = useMemo(() => {
    if (!timelineSentences) {
      return null;
    }

    const displaySentences: TextPlayerSentence[] = [];
    let activeIndex: number | null = null;

    const timelineTotalDuration = timelineSentences.length > 0 ? timelineSentences[timelineSentences.length - 1].endTime : null;
    const effectiveTime = (() => {
      if (!timelineTotalDuration || !audioDuration || audioDuration <= 0 || timelineTotalDuration <= 0) {
        return Math.max(chunkTime, 0);
      }
      const scaled = (chunkTime / audioDuration) * timelineTotalDuration;
      if (!Number.isFinite(scaled) || scaled < 0) {
        return 0;
      }
      return Math.min(scaled, timelineTotalDuration);
    })();

    timelineSentences.forEach((runtime) => {
      const { startTime, endTime } = runtime;
      let state: 'past' | 'active' | 'future';
      if (effectiveTime < startTime - 1e-3) {
        state = 'future';
      } else if (effectiveTime > endTime + 1e-3) {
        state = 'past';
      } else {
        state = 'active';
        if (activeIndex === null) {
          activeIndex = runtime.index;
        }
      }

      const variants: TextPlayerVariantDisplay[] = [];

      const buildVariant = (
        label: string,
        baseClass: TextPlayerVariantKind,
        variantRuntime?: TimelineVariantRuntime,
      ) => {
        if (!variantRuntime || variantRuntime.tokens.length === 0) {
          return;
        }

        let revealedCount = 0;
        let currentIndex: number | null = null;

        if (state !== 'future') {
          revealedCount = variantRuntime.tokens.length;
          currentIndex = variantRuntime.tokens.length - 1;
        }

        revealedCount = Math.max(revealedCount, 0);
        revealedCount = Math.min(revealedCount, variantRuntime.tokens.length);
        if (state === 'future') {
          revealedCount = variantRuntime.revealTimes.filter((time) => time <= effectiveTime + 1e-3).length;
          revealedCount = Math.max(revealedCount, 1);
          revealedCount = Math.min(revealedCount, variantRuntime.tokens.length);
          currentIndex = revealedCount - 1;
        }

        variants.push({
          label,
          tokens: variantRuntime.tokens,
          revealedCount,
          currentIndex,
          baseClass,
          seekTimes: variantRuntime.revealTimes,
        });
      };

      buildVariant('Original', 'original', runtime.variants.original);
      buildVariant('Transliteration', 'translit', runtime.variants.transliteration);
      buildVariant('Translation', 'translation', runtime.variants.translation);

      displaySentences.push({
        id: `sentence-${runtime.index}`,
        index: runtime.index,
        sentenceNumber: runtime.sentenceNumber ?? runtime.index + 1,
        state,
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
    };
  }, [timelineSentences, chunkTime, audioDuration]);
  
  const rawSentences = useMemo(
    () =>
      paragraphs
        .map((paragraph) => paragraph.sentences)
        .flat()
        .sort((a, b) => a.index - b.index),
    [paragraphs],
  );

  const textPlayerSentences = useMemo(() => {
    if (timelineDisplay?.sentences && timelineDisplay.sentences.length > 0) {
      return timelineDisplay.sentences;
    }

    const buildTokens = (value: string | null | undefined): string[] => {
      if (!value) {
        return [];
      }
      return value
        .split(/\s+/)
        .map((token) => token.trim())
        .filter((token) => token.length > 0);
    };

    if (chunk?.sentences && chunk.sentences.length > 0) {
      const fallbackFromChunk: TextPlayerSentence[] = chunk.sentences.map((metadata, index) => {
        const originalTokens = buildTokens(metadata.original?.text ?? null);
        const transliterationTokens = buildTokens(metadata.transliteration?.text ?? null);
        const translationTokens = buildTokens(metadata.translation?.text ?? null);

        const variants: TextPlayerVariantDisplay[] = [];
        if (originalTokens.length > 0) {
          variants.push({
            label: 'Original',
            tokens: originalTokens,
            revealedCount: originalTokens.length,
            currentIndex: originalTokens.length - 1,
            baseClass: 'original',
          });
        }
        if (transliterationTokens.length > 0) {
          variants.push({
            label: 'Transliteration',
            tokens: transliterationTokens,
            revealedCount: transliterationTokens.length,
            currentIndex: transliterationTokens.length - 1,
            baseClass: 'translit',
          });
        }
        if (translationTokens.length > 0) {
          variants.push({
            label: 'Translation',
            tokens: translationTokens,
            revealedCount: translationTokens.length,
            currentIndex: translationTokens.length - 1,
            baseClass: 'translation',
          });
        }

        return {
          id: `chunk-sentence-${index}`,
          index: index,
          sentenceNumber: metadata.sentence_number ?? index + 1,
          state: index === 0 ? 'active' : 'future',
          variants,
        };
      });

      const filtered = fallbackFromChunk.filter((sentence) => sentence.variants.length > 0);
      if (filtered.length > 0) {
        return filtered;
      }
    }

    if (rawSentences.length === 0) {
      return null;
    }

    const fallbackFromContent: TextPlayerSentence[] = rawSentences
      .map((sentence, position) => {
        const originalTokens = buildTokens(sentence.text);
        const translationTokens = buildTokens(sentence.translation);
        const transliterationTokens = buildTokens(sentence.transliteration);

        const variants: TextPlayerVariantDisplay[] = [];
        if (originalTokens.length > 0) {
          variants.push({
            label: 'Original',
            tokens: originalTokens,
            revealedCount: originalTokens.length,
            currentIndex: originalTokens.length - 1,
            baseClass: 'original',
          });
        }
        if (transliterationTokens.length > 0) {
          variants.push({
            label: 'Transliteration',
            tokens: transliterationTokens,
            revealedCount: transliterationTokens.length,
            currentIndex: transliterationTokens.length - 1,
            baseClass: 'translit',
          });
        }
        if (translationTokens.length > 0) {
          variants.push({
            label: 'Translation',
            tokens: translationTokens,
            revealedCount: translationTokens.length,
            currentIndex: translationTokens.length - 1,
            baseClass: 'translation',
          });
        }

        if (variants.length === 0) {
          return null;
        }

        return {
          id: `sentence-${sentence.index}`,
          index: sentence.index,
          sentenceNumber: sentence.index + 1,
          state: position === 0 ? 'active' : 'future',
          variants,
        } as TextPlayerSentence;
      })
      .filter((value): value is TextPlayerSentence => value !== null);

    return fallbackFromContent.length > 0 ? fallbackFromContent : null;
  }, [timelineDisplay, chunk?.sentences, rawSentences]);
  const sentenceWeightSummary = useMemo(() => {
    let cumulativeTotal = 0;
    const cumulative: number[] = [];
    rawSentences.forEach((sentence) => {
      cumulativeTotal += sentence.weight;
      cumulative.push(cumulativeTotal);
    });
    return {
      cumulative,
      total: cumulativeTotal,
    };
  }, [rawSentences]);
  const totalSentences = useMemo(
    () => paragraphs.reduce((count, paragraph) => count + paragraph.sentences.length, 0),
    [paragraphs],
  );

  const audioOptions = useMemo(() => {
    const seen = new Set<string>();
    const options: { url: string; label: string }[] = [];
    audioItems.forEach((item, index) => {
      const url = item.url ?? '';
      if (!url || seen.has(url)) {
        return;
      }
      seen.add(url);
      options.push({
        url,
        label: item.name ?? `Audio ${index + 1}`,
      });
    });
    return options;
  }, [audioItems]);

  const [activeAudioUrl, setActiveAudioUrl] = useState<string | null>(() => audioOptions[0]?.url ?? null);

  useEffect(() => {
    if (audioOptions.length === 0) {
      setActiveAudioUrl(null);
      return;
    }
    setActiveAudioUrl((current) => {
      if (current && audioOptions.some((option) => option.url === current)) {
        return current;
      }
      return audioOptions[0]?.url ?? null;
    });
  }, [audioOptions]);

  const audioRef = useRef<HTMLAudioElement | null>(null);
  const [isAudioPlaying, setIsAudioPlaying] = useState(false);
  const [activeSentenceIndex, setActiveSentenceIndex] = useState(0);
  const [activeSentenceProgress, setActiveSentenceProgress] = useState(0);
  const pendingInitialSeek = useRef<number | null>(null);
  const lastReportedPosition = useRef(0);

  useEffect(() => {
    if (!hasTimeline) {
      return;
    }
    setChunkTime(0);
    setActiveSentenceIndex(0);
  }, [hasTimeline, chunk?.chunkId, chunk?.rangeFragment, chunk?.startSentence, chunk?.endSentence]);

  useEffect(() => {
    setActiveSentenceIndex(0);
    setActiveSentenceProgress(0);
    const container = containerRef.current;
    if (container) {
      container.scrollTop = 0;
    }
  }, [content, totalSentences]);

  useEffect(() => {
    if (!timelineDisplay) {
      return;
    }
    setActiveSentenceIndex(timelineDisplay.activeIndex);
  }, [timelineDisplay]);

  useEffect(() => {
    if (!activeAudioUrl) {
      pendingInitialSeek.current = null;
      lastReportedPosition.current = 0;
      setActiveSentenceIndex(0);
      setActiveSentenceProgress(0);
      setIsAudioPlaying(false);
      setAudioDuration(null);
      return;
    }
    const stored = getStoredAudioPosition?.(activeAudioUrl);
    if (typeof stored === 'number' && stored > 0) {
      pendingInitialSeek.current = stored;
    } else {
      pendingInitialSeek.current = null;
    }
    lastReportedPosition.current = typeof stored === 'number' ? stored : 0;
    setActiveSentenceIndex(0);
    setActiveSentenceProgress(0);
    setAudioDuration(null);
  }, [activeAudioUrl, getStoredAudioPosition]);

  const handleScroll = useCallback(
    (event: UIEvent<HTMLDivElement>) => {
      onScroll?.(event);
    },
    [onScroll],
  );

  const resolvedAudioUrl = useMemo(
    () => (activeAudioUrl ? appendAccessToken(activeAudioUrl) : null),
    [activeAudioUrl],
  );

  useEffect(() => {
    if (!resolvedAudioUrl) {
      return;
    }
    const element = audioRef.current;
    if (!element) {
      return;
    }
    const attempt = element.play();
    if (attempt && typeof attempt.catch === 'function') {
      attempt.catch(() => {
        /* Ignore autoplay restrictions */
      });
    }
  }, [resolvedAudioUrl]);

  const emitAudioProgress = useCallback(
    (position: number) => {
      if (!activeAudioUrl || !onAudioProgress) {
        return;
      }
      if (Math.abs(position - lastReportedPosition.current) < 0.25) {
        return;
      }
      lastReportedPosition.current = position;
      onAudioProgress(activeAudioUrl, position);
    },
    [activeAudioUrl, onAudioProgress],
  );

  const updateSentenceForTime = useCallback(
    (time: number, duration: number) => {
      const totalWeight = sentenceWeightSummary.total;
      if (totalWeight <= 0 || duration <= 0 || rawSentences.length === 0) {
        setActiveSentenceIndex(0);
        setActiveSentenceProgress(0);
        return;
      }

      const progress = Math.max(0, Math.min(time / duration, 0.9999));
      const targetUnits = progress * totalWeight;
      const cumulative = sentenceWeightSummary.cumulative;

      let sentencePosition = cumulative.findIndex((value) => targetUnits < value);
      if (sentencePosition === -1) {
        sentencePosition = rawSentences.length - 1;
      }

      const sentence = rawSentences[sentencePosition];
      const sentenceStartUnits = sentencePosition === 0 ? 0 : cumulative[sentencePosition - 1];
      const sentenceWeight = Math.max(sentence.weight, 1);
      const intraUnits = targetUnits - sentenceStartUnits;
      const intra = Math.max(0, Math.min(intraUnits / sentenceWeight, 1));

      setActiveSentenceIndex(sentence.index);
      setActiveSentenceProgress(intra);
    },
    [rawSentences, sentenceWeightSummary],
  );

  const sentenceTimings = useMemo(() => {
    if (!audioDuration || audioDuration <= 0) {
      return null;
    }
    const totalUnits = sentenceWeightSummary.total;
    if (totalUnits <= 0) {
      return null;
    }
    const cumulative = sentenceWeightSummary.cumulative;
    const timings = new Map<number, { start: number; end: number }>();
    rawSentences.forEach((sentence, index) => {
      const startUnits = index === 0 ? 0 : cumulative[index - 1];
      const endUnits = cumulative[index];
      const start = (startUnits / totalUnits) * audioDuration;
      const end = (endUnits / totalUnits) * audioDuration;
      timings.set(sentence.index, {
        start: Number.isFinite(start) ? Math.max(0, start) : 0,
        end: Number.isFinite(end) ? Math.max(0, end) : 0,
      });
    });
    return timings;
  }, [audioDuration, rawSentences, sentenceWeightSummary]);

  const seekWithinSentence = useCallback(
    (sentenceIndex: number, fraction: number) => {
      if (sentenceIndex < 0 || sentenceIndex >= totalSentences) {
        return;
      }
      const element = audioRef.current;
      const clampedFraction = Math.max(0, Math.min(fraction, 1));
      if (!element || !Number.isFinite(element.duration) || element.duration <= 0) {
        setActiveSentenceIndex(sentenceIndex);
        setActiveSentenceProgress(clampedFraction);
        return;
      }
      const duration = element.duration;
      const timing = sentenceTimings?.get(sentenceIndex);
      let targetTime: number;
      if (timing) {
        const span = Math.max(timing.end - timing.start, 0);
        targetTime = Math.min(timing.start + span * clampedFraction, duration - 0.05);
      } else {
        const approximate = duration * (sentenceIndex / Math.max(totalSentences, 1));
        targetTime = Math.min(Math.max(approximate, 0), duration - 0.05);
      }
      try {
        element.currentTime = targetTime;
      } catch (error) {
        // Ignore assignment failures in restricted environments.
      }
      const playResult = element.play?.();
      if (playResult && typeof playResult.catch === 'function') {
        playResult.catch(() => undefined);
      }
      emitAudioProgress(targetTime);
      updateSentenceForTime(targetTime, duration);
    },
    [emitAudioProgress, sentenceTimings, totalSentences, updateSentenceForTime],
  );

  const handleLoadedMetadata = useCallback(() => {
    const element = audioRef.current;
    if (!element) {
      return;
    }
    const duration = element.duration;
    if (Number.isFinite(duration) && duration > 0) {
      setAudioDuration(duration);
    } else {
      setAudioDuration(null);
    }
    setChunkTime(element.currentTime ?? 0);
    const seek = pendingInitialSeek.current;
    if (typeof seek === 'number' && seek > 0 && Number.isFinite(duration) && duration > 0) {
      const clamped = Math.min(seek, duration - 0.1);
      element.currentTime = clamped;
      updateSentenceForTime(clamped, duration);
      emitAudioProgress(clamped);
      pendingInitialSeek.current = null;
      return;
    }
    pendingInitialSeek.current = null;
  }, [emitAudioProgress, updateSentenceForTime]);

  const handleTimeUpdate = useCallback(() => {
    const element = audioRef.current;
    if (!element) {
      return;
    }
    const { currentTime, duration } = element;
    if (!Number.isFinite(currentTime) || !Number.isFinite(duration) || duration <= 0) {
      return;
    }
    setAudioDuration((existing) => (existing && Math.abs(existing - duration) < 0.01 ? existing : duration));
    setChunkTime(currentTime);
    if (!hasTimeline) {
      updateSentenceForTime(currentTime, duration);
    }
    emitAudioProgress(currentTime);
  }, [emitAudioProgress, hasTimeline, updateSentenceForTime]);

  const handleAudioPlay = useCallback(() => {
    setIsAudioPlaying(true);
  }, []);

  const handleAudioPause = useCallback(() => {
    setIsAudioPlaying(false);
  }, []);

  const handleAudioEnded = useCallback(() => {
    setIsAudioPlaying(false);
    if (hasTimeline && timelineDisplay) {
      setChunkTime((prev) => (audioDuration ? audioDuration : prev));
      setActiveSentenceIndex(timelineDisplay.activeIndex);
    } else {
      if (totalSentences > 0) {
        setActiveSentenceIndex(totalSentences - 1);
        setActiveSentenceProgress(1);
      }
    }
    emitAudioProgress(0);
  }, [audioDuration, emitAudioProgress, hasTimeline, timelineDisplay, totalSentences]);

  const handleAudioSeeked = useCallback(() => {
    const element = audioRef.current;
    if (!element || !Number.isFinite(element.duration) || element.duration <= 0) {
      return;
    }
    setChunkTime(element.currentTime ?? 0);
    if (!hasTimeline) {
      updateSentenceForTime(element.currentTime, element.duration);
    }
    emitAudioProgress(element.currentTime);
  }, [emitAudioProgress, hasTimeline, updateSentenceForTime]);

  const previousActiveIndexRef = useRef<number | null>(null);

  useEffect(() => {
    if (previousActiveIndexRef.current === activeSentenceIndex) {
      return;
    }
    previousActiveIndexRef.current = activeSentenceIndex;
    const container = containerRef.current;
    if (!container || !timelineDisplay) {
      return;
    }
    const sentence = timelineDisplay.sentences.find((entry) => entry.index === activeSentenceIndex);
    if (!sentence) {
      return;
    }
    const approxOffset = sentence.index * 160;
    container.scrollTo({ top: Math.max(approxOffset - container.clientHeight * 0.3, 0), behavior: 'smooth' });
  }, [activeSentenceIndex]);

  const noAudioAvailable = Boolean(chunk) && audioOptions.length === 0;
  const chunkLabel = useMemo(() => {
    if (!chunk) {
      return 'Current chunk';
    }
    if (chunk.rangeFragment) {
      return chunk.rangeFragment ?? 'Chunk';
    }
    const start = chunk.startSentence;
    const end = chunk.endSentence;
    if (typeof start === 'number' && typeof end === 'number') {
      return `Sentences ${start}–${end}`;
    }
    if (typeof start === 'number') {
      return `Sentence ${start}`;
    }
    return 'Current chunk';
  }, [chunk]);

  const hasAudio = Boolean(resolvedAudioUrl);

  const handleChunkPlayPause = useCallback(() => {
    const element = audioRef.current;
    if (!element) {
      return;
    }
    if (element.paused) {
      element.play().catch(() => {
        /* Ignore autoplay restrictions */
      });
    } else {
      element.pause();
    }
  }, []);

  const handleChunkRestart = useCallback(() => {
    const element = audioRef.current;
    if (!element) {
      return;
    }
    try {
      element.currentTime = 0;
    } catch (error) {
      // Ignore seek failures in unsupported environments
    }
    setChunkTime(0);
    setActiveSentenceIndex(0);
    setActiveSentenceProgress(0);
    if (activeAudioUrl && onAudioProgress) {
      onAudioProgress(activeAudioUrl, 0);
      lastReportedPosition.current = 0;
    }
  }, [activeAudioUrl, onAudioProgress]);

  const handleTokenSeek = useCallback(
    (time: number) => {
      const element = audioRef.current;
      if (!element || !Number.isFinite(time)) {
        return;
      }
      try {
        const target = Math.max(0, Math.min(time, Number.isFinite(element.duration) ? element.duration : time));
        element.currentTime = target;
        const maybePlay = element.play?.();
        if (maybePlay && typeof maybePlay.catch === 'function') {
          maybePlay.catch(() => undefined);
        }
      } catch (error) {
        // Ignore seek failures in restricted environments.
      }
    },
    [],
  );

  return (
    <div className="player-panel__interactive">
      <div className="player-panel__interactive-toolbar">
        <div className="player-panel__interactive-chunk">
          <span className="player-panel__interactive-chunk-label">Chunk</span>
          <span className="player-panel__interactive-chunk-value">{chunkLabel}</span>
        </div>
        <div className="player-panel__interactive-controls">
          <button
            type="button"
            className="player-panel__interactive-button"
            onClick={handleChunkPlayPause}
            disabled={!hasAudio}
          >
            {isAudioPlaying ? 'Pause chunk' : 'Play chunk'}
          </button>
          <button
            type="button"
            className="player-panel__interactive-button player-panel__interactive-button--secondary"
            onClick={handleChunkRestart}
            disabled={!hasAudio}
          >
            Restart
          </button>
        </div>
      </div>
      {audioOptions.length > 0 ? (
      <div className="player-panel__interactive-audio">
        <label className="player-panel__interactive-label" htmlFor="player-panel-inline-audio">
          Synchronized audio
        </label>
          <div className="player-panel__interactive-audio-controls">
            {audioOptions.length > 1 ? (
              <select
                id="player-panel-inline-audio"
                value={activeAudioUrl ?? ''}
                onChange={(event) => setActiveAudioUrl(event.target.value || null)}
              >
                {audioOptions.map((option) => (
                  <option key={option.url} value={option.url}>
                    {option.label}
                  </option>
                ))}
              </select>
            ) : null}
            <audio
              ref={audioRef}
              src={resolvedAudioUrl ?? undefined}
              controls
              preload="metadata"
              autoPlay
              onLoadedMetadata={handleLoadedMetadata}
              onTimeUpdate={handleTimeUpdate}
              onPlay={handleAudioPlay}
              onPause={handleAudioPause}
              onEnded={handleAudioEnded}
              onSeeked={handleAudioSeeked}
            />
          </div>
        </div>
      ) : noAudioAvailable ? (
        <div className="player-panel__interactive-no-audio" role="status">
          Matching audio has not been generated for this selection yet.
        </div>
      ) : null}
      <div
        ref={containerRef}
        className="player-panel__document-body player-panel__interactive-body"
        data-testid="player-panel-document"
        onScroll={handleScroll}
      >
        {textPlayerSentences && textPlayerSentences.length > 0 ? (
          <TextPlayer sentences={textPlayerSentences} onSeek={handleTokenSeek} />
        ) : paragraphs.length > 0 ? (
          <pre className="player-panel__document-text">{content}</pre>
        ) : (
          <div className="player-panel__document-status" role="status">
            Text preview will appear once generated.
          </div>
        )}
      </div>
    </div>
  );
});

export default InteractiveTextViewer;
