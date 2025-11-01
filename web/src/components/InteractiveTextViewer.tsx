import {
  forwardRef,
  useCallback,
  useEffect,
  useImperativeHandle,
  useMemo,
  useRef,
  useState,
} from 'react';
import type { CSSProperties, UIEvent } from 'react';
import { appendAccessToken } from '../api/client';
import type { LiveMediaChunk, LiveMediaItem } from '../hooks/useLiveMedia';

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

interface InteractiveTextViewerProps {
  content: string;
  rawContent?: string | null;
  chunk: LiveMediaChunk | null;
  audioItems: LiveMediaItem[];
  onScroll?: (event: UIEvent<HTMLElement>) => void;
  onAudioProgress?: (audioUrl: string, position: number) => void;
  getStoredAudioPosition?: (audioUrl: string) => number;
}

const hasIntlSegmenter =
  typeof Intl !== 'undefined' && typeof (Intl as { Segmenter?: unknown }).Segmenter === 'function';

function segmentParagraph(paragraph: string): string[] {
  if (!paragraph) {
    return [];
  }

  const trimmed = paragraph.trim();
  if (!trimmed) {
    return [];
  }

  if (hasIntlSegmenter) {
    try {
      const segmenter = new Intl.Segmenter(undefined, { granularity: 'sentence' });
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

const InteractiveTextViewer = forwardRef<HTMLElement, InteractiveTextViewerProps>(function InteractiveTextViewer(
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
  const containerRef = useRef<HTMLElement | null>(null);
  useImperativeHandle(forwardedRef, () => containerRef.current as HTMLElement | null);

  const paragraphs = useMemo(() => buildParagraphs(content), [content]);
  const flattenedSentences = useMemo(
    () =>
      paragraphs
        .map((paragraph) => paragraph.sentences)
        .flat()
        .sort((a, b) => a.index - b.index),
    [paragraphs],
  );
  const sentenceWeightSummary = useMemo(() => {
    let cumulativeTotal = 0;
    const cumulative: number[] = [];
    flattenedSentences.forEach((sentence) => {
      cumulativeTotal += sentence.weight;
      cumulative.push(cumulativeTotal);
    });
    return {
      cumulative,
      total: cumulativeTotal,
    };
  }, [flattenedSentences]);
  const totalSentences = useMemo(
    () => paragraphs.reduce((count, paragraph) => count + paragraph.sentences.length, 0),
    [paragraphs],
  );

  const sentenceRefs = useRef<HTMLSpanElement[]>([]);
  sentenceRefs.current = sentenceRefs.current.slice(0, totalSentences);
  const registerSentenceRef = useCallback(
    (index: number) => (element: HTMLSpanElement | null) => {
      sentenceRefs.current[index] = element ?? undefined;
    },
    [],
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
    setActiveSentenceIndex(0);
    setActiveSentenceProgress(0);
    const container = containerRef.current;
    if (container) {
      container.scrollTop = 0;
    }
  }, [content, totalSentences]);

  useEffect(() => {
    if (!activeAudioUrl) {
      pendingInitialSeek.current = null;
      lastReportedPosition.current = 0;
      setActiveSentenceIndex(0);
      setActiveSentenceProgress(0);
      setIsAudioPlaying(false);
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
  }, [activeAudioUrl, getStoredAudioPosition]);

  const handleScroll = useCallback(
    (event: UIEvent<HTMLElement>) => {
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
      if (totalWeight <= 0 || duration <= 0 || flattenedSentences.length === 0) {
        setActiveSentenceIndex(0);
        setActiveSentenceProgress(0);
        return;
      }

      const progress = Math.max(0, Math.min(time / duration, 0.9999));
      const targetUnits = progress * totalWeight;
      const cumulative = sentenceWeightSummary.cumulative;

      let sentencePosition = cumulative.findIndex((value) => targetUnits < value);
      if (sentencePosition === -1) {
        sentencePosition = flattenedSentences.length - 1;
      }

      const sentence = flattenedSentences[sentencePosition];
      const sentenceStartUnits = sentencePosition === 0 ? 0 : cumulative[sentencePosition - 1];
      const sentenceWeight = Math.max(sentence.weight, 1);
      const intraUnits = targetUnits - sentenceStartUnits;
      const intra = Math.max(0, Math.min(intraUnits / sentenceWeight, 1));

      setActiveSentenceIndex(sentence.index);
      setActiveSentenceProgress(intra);
    },
    [flattenedSentences, sentenceWeightSummary],
  );

  const handleLoadedMetadata = useCallback(() => {
    const element = audioRef.current;
    if (!element) {
      return;
    }
    const duration = element.duration;
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
    updateSentenceForTime(currentTime, duration);
    emitAudioProgress(currentTime);
  }, [emitAudioProgress, updateSentenceForTime]);

  const handleAudioPlay = useCallback(() => {
    setIsAudioPlaying(true);
  }, []);

  const handleAudioPause = useCallback(() => {
    setIsAudioPlaying(false);
  }, []);

  const handleAudioEnded = useCallback(() => {
    setIsAudioPlaying(false);
    if (totalSentences > 0) {
      setActiveSentenceIndex(totalSentences - 1);
      setActiveSentenceProgress(1);
    }
    emitAudioProgress(0);
  }, [emitAudioProgress, totalSentences]);

  const handleSentenceClick = useCallback(
    (index: number) => {
      if (index < 0 || index >= totalSentences) {
        return;
      }
      const element = audioRef.current;
      if (!element || !Number.isFinite(element.duration) || element.duration <= 0) {
        setActiveSentenceIndex(index);
        setActiveSentenceProgress(0);
        return;
      }
      const segmentDuration = element.duration / totalSentences;
      const target = Math.min(index * segmentDuration, element.duration - 0.1);
      try {
        element.currentTime = target;
        const result = element.play();
        if (result && typeof result.then === 'function') {
          result.catch(() => {
            // Ignore playback errors triggered by autoplay restrictions.
          });
        }
      } catch (error) {
        // Swallow assignment errors in non-browser environments.
      }
      emitAudioProgress(target);
      updateSentenceForTime(target, element.duration);
    },
    [emitAudioProgress, totalSentences, updateSentenceForTime],
  );

  const handleAudioSeeked = useCallback(() => {
    const element = audioRef.current;
    if (!element || !Number.isFinite(element.duration) || element.duration <= 0) {
      return;
    }
    updateSentenceForTime(element.currentTime, element.duration);
    emitAudioProgress(element.currentTime);
  }, [emitAudioProgress, updateSentenceForTime]);

  const previousActiveIndexRef = useRef<number | null>(null);

  useEffect(() => {
    if (previousActiveIndexRef.current === activeSentenceIndex) {
      return;
    }
    previousActiveIndexRef.current = activeSentenceIndex;
    const container = containerRef.current;
    const sentenceNode = sentenceRefs.current[activeSentenceIndex];
    if (!container || !sentenceNode) {
      return;
    }
    const target =
      sentenceNode.offsetTop -
      Math.max((container.clientHeight - sentenceNode.offsetHeight) / 2, 0);
    container.scrollTo({ top: Math.max(target, 0), behavior: 'smooth' });
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
    setActiveSentenceIndex(0);
    setActiveSentenceProgress(0);
    if (activeAudioUrl && onAudioProgress) {
      onAudioProgress(activeAudioUrl, 0);
      lastReportedPosition.current = 0;
    }
  }, [activeAudioUrl, onAudioProgress]);

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
      <article
        ref={containerRef}
        className="player-panel__document-body player-panel__interactive-body"
        data-testid="player-panel-document"
        onScroll={handleScroll}
      >
        {paragraphs.map((paragraph) => {
          const visibleSentences = paragraph.sentences.filter(
            (sentence) => Math.abs(sentence.index - activeSentenceIndex) <= 1,
          );
          if (visibleSentences.length === 0) {
            return null;
          }
          return (
            <div key={paragraph.id} className="player-panel__interactive-paragraph">
              {visibleSentences.map((sentence) => {
                const isActive = sentence.index === activeSentenceIndex;
                const isBefore = sentence.index === activeSentenceIndex - 1;
                const isAfter = sentence.index === activeSentenceIndex + 1;
                const sentenceClassName = [
                  'player-panel__interactive-sentence-group',
                  isActive ? 'player-panel__interactive-sentence-group--active' : '',
                  isBefore ? 'player-panel__interactive-sentence-group--previous' : '',
                  isAfter ? 'player-panel__interactive-sentence-group--upcoming' : '',
                ]
                  .filter(Boolean)
                  .join(' ');
                const activeWordIndex = isActive && sentence.wordCount > 0
                  ? Math.min(
                      sentence.wordCount - 1,
                      Math.floor(activeSentenceProgress * sentence.wordCount),
                    )
                  : -1;
                const activeWordProgress = isActive && sentence.wordCount > 0
                  ? Math.max(0, Math.min(activeSentenceProgress * sentence.wordCount - activeWordIndex, 1))
                  : 0;
                let wordPointer = 0;

                return (
                  <div
                    key={`${paragraph.id}-sentence-${sentence.index}`}
                    ref={registerSentenceRef(sentence.index)}
                    className={sentenceClassName}
                    role="presentation"
                    tabIndex={-1}
                    onClick={() => handleSentenceClick(sentence.index)}
                  >
                    <div className="player-panel__interactive-original">
                      {sentence.parts.map((part, partIndex) => {
                        if (!part.isWord) {
                          return <span key={`part-${partIndex}`}>{part.content}</span>;
                        }
                        const currentWordIndex = wordPointer;
                        wordPointer += 1;
                        let wordClassName = 'player-panel__interactive-word';
                        if (isActive) {
                          if (currentWordIndex < activeWordIndex) {
                            wordClassName += ' player-panel__interactive-word--spoken';
                          } else if (currentWordIndex === activeWordIndex) {
                            wordClassName += ' player-panel__interactive-word--current';
                          }
                        }

                        return (
                          <span
                            key={`part-${partIndex}`}
                            className={wordClassName}
                            style={
                              isActive && currentWordIndex === activeWordIndex
                                ? ({
                                    '--word-progress': `${Math.round(activeWordProgress * 100)}%`,
                                  } as CSSProperties)
                                : undefined
                            }
                          >
                            {part.content}
                          </span>
                        );
                      })}
                    </div>
                    {sentence.translation ? (
                      <div className="player-panel__interactive-translation">{sentence.translation}</div>
                    ) : null}
                    {sentence.transliteration ? (
                      <div className="player-panel__interactive-transliteration">{sentence.transliteration}</div>
                    ) : null}
                  </div>
                );
              })}
            </div>
          );
        })}
      </article>
    </div>
  );
});

export default InteractiveTextViewer;
