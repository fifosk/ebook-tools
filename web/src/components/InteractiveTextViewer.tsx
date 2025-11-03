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

type InlineAudioControls = {
  pause: () => void;
};

interface InteractiveTextViewerProps {
  content: string;
  rawContent?: string | null;
  chunk: LiveMediaChunk | null;
  audioItems: LiveMediaItem[];
  activeAudioUrl: string | null;
  noAudioAvailable: boolean;
  onScroll?: (event: UIEvent<HTMLDivElement>) => void;
  onAudioProgress?: (audioUrl: string, position: number) => void;
  getStoredAudioPosition?: (audioUrl: string) => number;
  onRegisterInlineAudioControls?: (controls: InlineAudioControls | null) => void;
  onSelectAudio?: (audioUrl: string) => void;
  onRequestAdvanceChunk?: () => void;
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
    activeAudioUrl,
    noAudioAvailable,
    onScroll,
    onAudioProgress,
    getStoredAudioPosition,
    onRegisterInlineAudioControls,
    onSelectAudio,
    onRequestAdvanceChunk,
  },
  forwardedRef,
) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  useImperativeHandle<HTMLDivElement | null, HTMLDivElement | null>(forwardedRef, () => containerRef.current);
  const [chunkTime, setChunkTime] = useState(0);
  const hasTimeline = Boolean(chunk?.sentences && chunk.sentences.length > 0);
  const [audioDuration, setAudioDuration] = useState<number | null>(null);
  const [activeSentenceIndex, setActiveSentenceIndex] = useState(0);
  const [activeSentenceProgress, setActiveSentenceProgress] = useState(0);

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

      const durationScale =
        eventDurationTotal > 0 && declaredDuration > 0 ? declaredDuration / eventDurationTotal : 1;

      let prevOriginal = 0;
      let prevTranslation = 0;
      let prevTranslit = 0;
      let elapsed = 0;

      events.forEach((event) => {
        const baseDuration = typeof event.duration === 'number' && event.duration > 0 ? event.duration : 0;
        const adjustedDuration = baseDuration * durationScale;
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

        distributeRevealTimes(
          prevOriginal,
          nextOriginal,
          eventStart,
          adjustedDuration,
          originalReveal,
        );
        distributeRevealTimes(
          prevTranslation,
          nextTranslation,
          eventStart,
          adjustedDuration,
          translationReveal,
        );
        distributeRevealTimes(
          prevTranslit,
          nextTranslit,
          eventStart,
          adjustedDuration,
          transliterationReveal,
        );

        prevOriginal = nextOriginal;
        prevTranslation = nextTranslation;
        prevTranslit = nextTranslit;
        elapsed += adjustedDuration;
      });

      let sentenceDuration = declaredDuration;
      if (!(sentenceDuration > 0)) {
        sentenceDuration = elapsed;
      } else if (elapsed > sentenceDuration) {
        sentenceDuration = elapsed;
      }

      const endTime = offset + sentenceDuration;

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

        const tokens = variantRuntime.tokens;
        const revealTimes = variantRuntime.revealTimes;
        const safeEffectiveTime = Math.max(effectiveTime, 0);
        const revealCutoff = Math.min(safeEffectiveTime, endTime);
        const progressCount = revealTimes.filter((time) => time <= revealCutoff + 1e-3).length;

        let revealedCount: number;
        if (state === 'past') {
          revealedCount = tokens.length;
        } else if (state === 'future') {
          revealedCount = progressCount;
        } else {
          revealedCount = progressCount;
        }

        revealedCount = Math.max(0, Math.min(revealedCount, tokens.length));
        if (state === 'active' && revealedCount === 0 && revealTimes.length > 0) {
          if (safeEffectiveTime >= startTime - 1e-3) {
            revealedCount = 1;
          }
        }

        let currentIndex: number | null = revealedCount > 0 ? revealedCount - 1 : null;
        if (state === 'past' && tokens.length > 0) {
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
      effectiveTime,
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
    const forceActive = (sentence: TextPlayerSentence | undefined | null): TextPlayerSentence[] | null => {
      if (!sentence) {
        return null;
      }
      return [
        {
          ...sentence,
          state: 'active',
        },
      ];
    };

    if (timelineDisplay?.sentences && timelineDisplay.sentences.length > 0) {
      const active =
        timelineDisplay.sentences.find((entry) => entry.index === activeSentenceIndex) ??
        timelineDisplay.sentences.find((entry) => entry.state === 'active') ??
        timelineDisplay.sentences[0];
      return forceActive(active);
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
        const active =
          filtered.find((sentence) => sentence.index === activeSentenceIndex) ?? filtered[0];
        return forceActive(active);
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

    if (fallbackFromContent.length === 0) {
      return null;
    }
    const active =
      fallbackFromContent.find((sentence) => sentence.index === activeSentenceIndex) ??
      fallbackFromContent[0];
    return forceActive(active);
  }, [timelineDisplay, chunk?.sentences, rawSentences, activeSentenceIndex]);
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

  const audioPlaylist = useMemo(() => {
    const seen = new Set<string>();
    const items: Array<{ id: string; label: string }> = [];
    audioItems.forEach((item) => {
      const url = item.url ?? '';
      if (!url || seen.has(url)) {
        return;
      }
      seen.add(url);
      const label =
        typeof item.name === 'string' && item.name.trim().length > 0
          ? item.name
          : `Track ${items.length + 1}`;
      items.push({ id: url, label });
    });
    return items;
  }, [audioItems]);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  useEffect(() => {
    if (!onRegisterInlineAudioControls) {
      return;
    }
    if (!activeAudioUrl) {
      onRegisterInlineAudioControls(null);
      return () => {
        onRegisterInlineAudioControls(null);
      };
    }
    const handler = () => {
      const element = audioRef.current;
      if (!element) {
        return;
      }
      try {
        element.pause();
      } catch (error) {
        // Ignore pause failures triggered by browsers blocking programmatic control.
      }
    };
    onRegisterInlineAudioControls({ pause: handler });
    return () => {
      onRegisterInlineAudioControls(null);
    };
  }, [onRegisterInlineAudioControls, activeAudioUrl]);
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
  }, [content, totalSentences]);

  useEffect(() => {
    if (!timelineDisplay) {
      return;
    }
    const { activeIndex: candidateIndex, effectiveTime } = timelineDisplay;
    if (candidateIndex === activeSentenceIndex) {
      return;
    }
    if (!timelineSentences || timelineSentences.length === 0) {
      setActiveSentenceIndex(candidateIndex);
      return;
    }
    const epsilon = 0.05;
    const clampedIndex = Math.max(0, Math.min(candidateIndex, timelineSentences.length - 1));
    const candidateRuntime = timelineSentences[clampedIndex];
    if (!candidateRuntime) {
      setActiveSentenceIndex(clampedIndex);
      return;
    }
    if (clampedIndex > activeSentenceIndex) {
      if (effectiveTime < candidateRuntime.startTime + epsilon) {
        return;
      }
    } else if (clampedIndex < activeSentenceIndex) {
      if (effectiveTime > candidateRuntime.endTime - epsilon) {
        return;
      }
    }
    setActiveSentenceIndex(clampedIndex);
  }, [timelineDisplay, activeSentenceIndex, timelineSentences]);

  useEffect(() => {
    if (!activeAudioUrl) {
      pendingInitialSeek.current = null;
      lastReportedPosition.current = 0;
      setActiveSentenceIndex(0);
      setActiveSentenceProgress(0);
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

  const handlePlaylistSelect = useCallback(
    (audioId: string) => {
      if (!audioId) {
        return;
      }
      if (audioId === activeAudioUrl) {
        const element = audioRef.current;
        if (!element) {
          return;
        }
        try {
          element.currentTime = 0;
        } catch (error) {
          // Ignore failures in restricted environments.
        }
        const duration =
          Number.isFinite(element.duration) && element.duration > 0 ? element.duration : audioDuration ?? 0;
        setChunkTime(0);
        if (hasTimeline) {
          setActiveSentenceIndex(0);
          setActiveSentenceProgress(0);
        } else if (duration > 0) {
          updateSentenceForTime(0, duration);
        } else {
          setActiveSentenceIndex(0);
          setActiveSentenceProgress(0);
        }
        emitAudioProgress(0);
        try {
          const attempt = element.play?.();
          if (attempt && typeof attempt.catch === 'function') {
            attempt.catch(() => undefined);
          }
        } catch (error) {
          // Ignore playback errors in restricted environments.
        }
        return;
      }
      onSelectAudio?.(audioId);
    },
    [
      activeAudioUrl,
      audioDuration,
      emitAudioProgress,
      hasTimeline,
      onSelectAudio,
      updateSentenceForTime,
    ],
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
      const maybePlay = element.play?.();
      if (maybePlay && typeof maybePlay.catch === 'function') {
        maybePlay.catch(() => undefined);
      }
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

  const handleAudioEnded = useCallback(() => {
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
    onRequestAdvanceChunk?.();
  }, [audioDuration, emitAudioProgress, hasTimeline, onRequestAdvanceChunk, timelineDisplay, totalSentences]);

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
      {resolvedAudioUrl ? (
        <div className="player-panel__interactive-audio">
          <span className="player-panel__interactive-label">Synchronized audio</span>
          <div className="player-panel__interactive-audio-controls">
            <audio
              ref={audioRef}
              src={resolvedAudioUrl ?? undefined}
              controls
              preload="metadata"
              autoPlay
              onLoadedMetadata={handleLoadedMetadata}
              onTimeUpdate={handleTimeUpdate}
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
        ) : chunk ? (
          <div className="player-panel__document-status" role="status">
            Loading interactive chunk…
          </div>
        ) : (
          <div className="player-panel__document-status" role="status">
            Text preview will appear once generated.
          </div>
        )}
      </div>
      {audioPlaylist.length > 0 ? (
        <div className="player-panel__interactive-playlist">
          <span className="player-panel__interactive-label">Audio tracks</span>
          <div className="audio-player__playlist" role="group" aria-label="Audio tracks">
            {audioPlaylist.map((item) => (
              <button
                key={item.id}
                type="button"
                className="audio-player__track"
                aria-pressed={item.id === activeAudioUrl}
                onClick={() => handlePlaylistSelect(item.id)}
              >
                {item.label}
              </button>
            ))}
          </div>
        </div>
      ) : null}
    </div>
  );
});

export default InteractiveTextViewer;
