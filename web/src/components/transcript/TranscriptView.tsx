import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from 'react';
import type { Segment, WordToken } from '../../types/timing';
import type { PlayerCoreHandle } from '../../player/PlayerCore';
import { useWordHighlighting } from '../../hooks/useWordHighlighting';
import SegmentBlock from './SegmentBlock';
import './styles.css';

interface TranscriptViewProps {
  segments: Segment[];
  player?: PlayerCoreHandle | null;
  onWordClick?: (tokenId: string, token: WordToken) => void;
  className?: string;
}

const DEFAULT_ITEM_HEIGHT = 96;

function computeAverageHeight(heights: number[]): number {
  let sum = 0;
  let count = 0;
  for (const height of heights) {
    if (height > 0) {
      sum += height;
      count += 1;
    }
  }
  if (count === 0) {
    return DEFAULT_ITEM_HEIGHT;
  }
  return sum / count;
}

export function TranscriptView({
  segments,
  player,
  onWordClick,
  className,
}: TranscriptViewProps) {
  const { current, setSeeking, setFence } = useWordHighlighting();
  const containerRef = useRef<HTMLDivElement | null>(null);
  const heightsRef = useRef<number[]>([]);
  const [layoutVersion, setLayoutVersion] = useState(0);
  const [scrollTop, setScrollTop] = useState(0);
  const [viewportHeight, setViewportHeight] = useState(0);
  const rafRef = useRef<number | null>(null);

  useEffect(() => {
    if (heightsRef.current.length !== segments.length) {
      const next = new Array(segments.length);
      for (let index = 0; index < segments.length; index += 1) {
        next[index] = heightsRef.current[index] ?? 0;
      }
      heightsRef.current = next;
      setLayoutVersion((value) => value + 1);
    }
  }, [segments]);

  useEffect(() => {
    const node = containerRef.current;
    if (!node) {
      return;
    }
    const updateViewport = () => {
      setViewportHeight(node.clientHeight);
      setScrollTop(node.scrollTop);
    };
    updateViewport();
    if (typeof ResizeObserver === 'function') {
      const observer = new ResizeObserver(() => {
        updateViewport();
      });
      observer.observe(node);
      return () => observer.disconnect();
    }
    return () => undefined;
  }, [segments.length]);

  const onScroll = useCallback(() => {
    const node = containerRef.current;
    if (!node) {
      return;
    }
    if (rafRef.current !== null) {
      return;
    }
    rafRef.current = window.requestAnimationFrame(() => {
      rafRef.current = null;
      setScrollTop(node.scrollTop);
      setViewportHeight(node.clientHeight);
    });
  }, []);

  useEffect(
    () => () => {
      if (rafRef.current !== null) {
        window.cancelAnimationFrame(rafRef.current);
        rafRef.current = null;
      }
    },
    []
  );

  const registerHeight = useCallback((index: number, height: number) => {
    if (!Number.isFinite(height) || height <= 0) {
      return;
    }
    const heights = heightsRef.current;
    if (Math.abs((heights[index] ?? 0) - height) < 0.5) {
      return;
    }
    heights[index] = height;
    setLayoutVersion((value) => value + 1);
  }, []);

  const averageHeight = useMemo(
    () => computeAverageHeight(heightsRef.current),
    [layoutVersion, segments.length]
  );

  const fallbackHeight = averageHeight || DEFAULT_ITEM_HEIGHT;

  const totalHeight = useMemo(() => {
    if (segments.length === 0) {
      return 0;
    }
    return segments.reduce((sum, _, index) => {
      const measured = heightsRef.current[index];
      return sum + (measured > 0 ? measured : fallbackHeight);
    }, 0);
  }, [fallbackHeight, segments, layoutVersion]);

  const overscan = viewportHeight > 0 ? viewportHeight * 0.5 : 200;
  const targetTop = Math.max(0, scrollTop - overscan);
  const targetBottom = scrollTop + viewportHeight + overscan;

  let startIndex = 0;
  let topOffset = 0;
  while (startIndex < segments.length) {
    const height = heightsRef.current[startIndex] > 0 ? heightsRef.current[startIndex] : fallbackHeight;
    if (topOffset + height > targetTop) {
      break;
    }
    topOffset += height;
    startIndex += 1;
  }

  let endIndex = startIndex;
  let accumulated = topOffset;
  if (viewportHeight === 0 && segments.length > 0) {
    endIndex = Math.min(segments.length, startIndex + 20);
  } else {
    while (endIndex < segments.length && accumulated < targetBottom) {
      const height =
        heightsRef.current[endIndex] > 0 ? heightsRef.current[endIndex] : fallbackHeight;
      accumulated += height;
      endIndex += 1;
    }
  }

  if (endIndex <= startIndex && segments.length > 0) {
    endIndex = Math.min(segments.length, startIndex + 1);
  }

  const rendered = segments.slice(startIndex, endIndex);

  const renderedHeight = rendered.reduce((sum, _, localIndex) => {
    const height =
      heightsRef.current[startIndex + localIndex] > 0
        ? heightsRef.current[startIndex + localIndex]
        : fallbackHeight;
    return sum + height;
  }, 0);

  const activeSegmentIndex =
    current && current.segIndex >= 0 && current.segIndex < segments.length
      ? current.segIndex
      : -1;
  const activeTokenIndex = current && current.segIndex === activeSegmentIndex ? current.tokIndex : -1;

  const handleWordSeek = useCallback(
    (token: WordToken, tokenIndex: number) => {
      if (player && Number.isFinite(token.t0)) {
        setSeeking(true);
        try {
          player.seek(token.t0);
        } catch {
          setSeeking(false);
        }
      }
      if (token.segId) {
        setFence(token.segId, tokenIndex);
      }
      onWordClick?.(token.id, token);
    },
    [player, setSeeking, setFence, onWordClick]
  );

  useEffect(() => {
    if (!player) {
      return;
    }
    const unsubscribe = player.on('seeked', () => {
      setSeeking(false);
    });
    return () => {
      unsubscribe?.();
    };
  }, [player, setSeeking]);

  const containerClassName = ['transcript-view', className].filter(Boolean).join(' ');

  return (
    <div ref={containerRef} className={containerClassName} onScroll={onScroll}>
      <div className="transcript-spacer" style={{ height: `${totalHeight}px` }}>
        <div
          className="transcript-window"
          style={{
            transform: `translate3d(0, ${topOffset}px, 0)`,
          }}
        >
          {rendered.map((segment, localIndex) => {
            const index = startIndex + localIndex;
            const status: 'past' | 'current' | 'future' =
              activeSegmentIndex === -1
                ? 'future'
                : index < activeSegmentIndex
                  ? 'past'
                  : index === activeSegmentIndex
                    ? 'current'
                    : 'future';
            const activeIndexValue = status === 'current' ? activeTokenIndex : -1;
            return (
              <SegmentBlock
                key={segment.id}
                segment={segment}
                segmentIndex={index}
                status={status}
                activeTokenIndex={activeIndexValue}
                onWordClick={handleWordSeek}
                onMeasure={registerHeight}
              />
            );
          })}
        </div>
      </div>
    </div>
  );
}

export default TranscriptView;
