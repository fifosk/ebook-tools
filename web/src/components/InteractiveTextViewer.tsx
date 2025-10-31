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

type SentenceFragment = {
  index: number;
  text: string;
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
      paragraphs.push({
        id: `paragraph-${paragraphIndex}`,
        sentences: [{ index: nextIndex, text: raw }],
      });
      nextIndex += 1;
      return;
    }

    const sentences: SentenceFragment[] = segments.map((segment) => {
      const fragment: SentenceFragment = {
        index: nextIndex,
        text: segment,
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
    return [
      {
        id: 'paragraph-0',
        sentences: [{ index: 0, text: trimmed }],
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
  const pendingInitialSeek = useRef<number | null>(null);
  const lastReportedPosition = useRef(0);

  useEffect(() => {
    setActiveSentenceIndex(0);
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
    setActiveSentenceIndex((current) => (current > 0 ? 0 : current));
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
      if (totalSentences === 0 || duration <= 0) {
        return;
      }
      const progress = Math.max(0, Math.min(time / duration, 0.9999));
      const nextIndex = Math.min(Math.floor(progress * totalSentences), totalSentences - 1);
      setActiveSentenceIndex((current) => (current === nextIndex ? current : nextIndex));
    },
    [totalSentences],
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

  useEffect(() => {
    if (!isAudioPlaying) {
      return;
    }
    const container = containerRef.current;
    const sentenceNode = sentenceRefs.current[activeSentenceIndex];
    if (!container || !sentenceNode) {
      return;
    }
    const nodeOffsetTop = sentenceNode.offsetTop;
    const nodeOffsetBottom = nodeOffsetTop + sentenceNode.offsetHeight;
    const viewTop = container.scrollTop;
    const viewBottom = viewTop + container.clientHeight;
    const margin = Math.max(32, container.clientHeight * 0.15);

    if (nodeOffsetTop < viewTop + margin) {
      container.scrollTo({ top: Math.max(nodeOffsetTop - margin, 0), behavior: 'smooth' });
      return;
    }
    if (nodeOffsetBottom > viewBottom - margin) {
      const target = Math.min(nodeOffsetBottom + margin - container.clientHeight, container.scrollHeight);
      container.scrollTo({ top: Math.max(target, 0), behavior: 'smooth' });
    }
  }, [activeSentenceIndex, isAudioPlaying]);

  const noAudioAvailable = Boolean(chunk) && audioOptions.length === 0;

  return (
    <div className="player-panel__interactive">
      {audioOptions.length > 0 ? (
        <div className="player-panel__interactive-audio">
          <label htmlFor="player-panel-inline-audio">Synchronized audio</label>
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
        {paragraphs.map((paragraph) => (
          <p key={paragraph.id} className="player-panel__interactive-paragraph">
            {paragraph.sentences.map((sentence, sentenceIndex) => {
              const isActive = sentence.index === activeSentenceIndex;
              return (
                <span
                  key={`${paragraph.id}-sentence-${sentenceIndex}`}
                  ref={registerSentenceRef(sentence.index)}
                  className={
                    isActive
                      ? 'player-panel__interactive-sentence player-panel__interactive-sentence--active'
                      : 'player-panel__interactive-sentence'
                  }
                  role="presentation"
                  tabIndex={-1}
                  onClick={() => handleSentenceClick(sentence.index)}
                >
                  {sentence.text}
                  {' '}
                </span>
              );
            })}
          </p>
        ))}
      </article>
    </div>
  );
});

export default InteractiveTextViewer;
