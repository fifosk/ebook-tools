import {
  memo,
  useCallback,
  useLayoutEffect,
  useMemo,
  useRef,
} from 'react';
import type { Segment, WordToken } from '../../types/timing';
import Word from './Word';

type SegmentStatus = 'past' | 'current' | 'future';

export interface SegmentBlockProps {
  segment: Segment;
  segmentIndex: number;
  status: SegmentStatus;
  activeTokenIndex: number;
  onWordClick?: (token: WordToken, tokenIndex: number) => void;
  onMeasure: (index: number, height: number) => void;
}

type LaneBuckets = Record<'orig' | 'tran', Array<{ token: WordToken; index: number }>>;

function buildBuckets(segment: Segment): LaneBuckets {
  const buckets: LaneBuckets = {
    orig: [],
    tran: [],
  };
  segment.tokens.forEach((token, index) => {
    const lane = token.lane === 'orig' ? 'orig' : 'tran';
    buckets[lane].push({ token, index });
  });
  return buckets;
}

function describeTokenStatus(
  segmentStatus: SegmentStatus,
  activeTokenIndex: number,
  tokenIndex: number
): 'prev' | 'now' | 'next' {
  if (segmentStatus === 'past') {
    return 'prev';
  }
  if (segmentStatus === 'future') {
    return 'next';
  }
  if (tokenIndex < activeTokenIndex) {
    return 'prev';
  }
  if (tokenIndex === activeTokenIndex) {
    return 'now';
  }
  return 'next';
}

function SegmentBlockComponent({
  segment,
  segmentIndex,
  status,
  activeTokenIndex,
  onWordClick,
  onMeasure,
}: SegmentBlockProps) {
  const blockRef = useRef<HTMLDivElement | null>(null);

  const buckets = useMemo(() => buildBuckets(segment), [segment]);

  const handleWordClick = useCallback(
    (token: WordToken, tokenIndex: number) => {
      onWordClick?.(token, tokenIndex);
    },
    [onWordClick]
  );

  useLayoutEffect(() => {
    const element = blockRef.current;
    if (!element) {
      return;
    }

    const report = () => {
      const rect = element.getBoundingClientRect();
      const height = rect.height;
      if (!Number.isNaN(height) && Number.isFinite(height)) {
        onMeasure(segmentIndex, height);
      }
    };

    report();

    if (typeof ResizeObserver === 'function') {
      const observer = new ResizeObserver(() => {
        report();
      });
      observer.observe(element);
      return () => {
        observer.disconnect();
      };
    }

    return () => undefined;
  }, [onMeasure, segmentIndex, buckets]);

  const blockClassName = [
    'transcript-segment',
    status === 'past' ? 'segment-past' : null,
    status === 'current' ? 'segment-current' : null,
    status === 'future' ? 'segment-future' : null,
  ]
    .filter(Boolean)
    .join(' ');

  return (
    <div ref={blockRef} className={blockClassName} data-segment-id={segment.id}>
      <div className="segment-header">
        <span className="segment-label">Segment {segment.id}</span>
      </div>
      <div className="segment-body">
        <div className="segment-lane lane-orig">
          {buckets.orig.map(({ token, index }) => (
            <Word
              key={token.id}
              token={token}
              status={describeTokenStatus(status, activeTokenIndex, index)}
              onClick={() => handleWordClick(token, index)}
            />
          ))}
        </div>
        <div className="segment-lane lane-tran">
          {buckets.tran.map(({ token, index }) => (
            <Word
              key={token.id}
              token={token}
              status={describeTokenStatus(status, activeTokenIndex, index)}
              onClick={() => handleWordClick(token, index)}
            />
          ))}
        </div>
      </div>
    </div>
  );
}

function propsAreEqual(prev: SegmentBlockProps, next: SegmentBlockProps): boolean {
  return (
    prev.segment === next.segment &&
    prev.segmentIndex === next.segmentIndex &&
    prev.status === next.status &&
    prev.activeTokenIndex === next.activeTokenIndex &&
    prev.onWordClick === next.onWordClick
  );
}

export const SegmentBlock = memo(SegmentBlockComponent, propsAreEqual);

export default SegmentBlock;
