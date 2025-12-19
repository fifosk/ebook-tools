import type { MouseEvent, MutableRefObject } from 'react';

export type SentenceImageFrame = {
  sentenceNumber: number | null;
  url: string | null;
  isActive: boolean;
};

interface SentenceImageReelProps {
  frames: SentenceImageFrame[];
  scrollRef?: MutableRefObject<HTMLDivElement | null>;
  onFrameClick: (frame: SentenceImageFrame) => void;
  onFrameError?: (sentenceNumber: number) => void;
}

export function SentenceImageReel({
  frames,
  scrollRef,
  onFrameClick,
  onFrameError,
}: SentenceImageReelProps) {
  if (!frames.length) {
    return null;
  }

  const activeIndex = frames.findIndex((frame) => frame.isActive);

  const handleFrameClick = (frame: SentenceImageFrame) => (event: MouseEvent<HTMLButtonElement>) => {
    event.preventDefault();
    event.stopPropagation();
    onFrameClick(frame);
  };

  const handleScrollRef = (node: HTMLDivElement | null) => {
    if (!scrollRef) {
      return;
    }
    scrollRef.current = node;
  };

  return (
    <div
      ref={scrollRef ? handleScrollRef : undefined}
      className="player-panel__interactive-image-reel"
      aria-label="Sentence images"
    >
      <div className="player-panel__interactive-image-reel-strip" role="list">
        {frames.map((frame, index) => {
          const sentenceNumber = frame.sentenceNumber;
          const key = sentenceNumber ? String(sentenceNumber) : `empty-${index}`;
          const slotClassName = [
            'player-panel__interactive-image-reel-slot',
            index === activeIndex - 1 ? 'player-panel__interactive-image-reel-slot--preactive' : null,
          ]
            .filter(Boolean)
            .join(' ');
          const classNames = [
            'player-panel__interactive-image-reel-frame',
            frame.isActive ? 'player-panel__interactive-image-reel-frame--active' : null,
          ]
            .filter(Boolean)
            .join(' ');

          return (
            <div
              key={key}
              className={slotClassName}
              role="listitem"
              aria-label={sentenceNumber ? `Sentence ${sentenceNumber}` : 'No sentence'}
            >
              <button
                type="button"
                className={classNames}
                onClick={handleFrameClick(frame)}
                disabled={!sentenceNumber}
                title={sentenceNumber ? `Jump to sentence ${sentenceNumber}` : undefined}
                aria-label={sentenceNumber ? `Jump to sentence ${sentenceNumber}` : 'No image'}
                data-reel-sentence={sentenceNumber ?? undefined}
              >
                {frame.url ? (
                  <img
                    src={frame.url}
                    alt={sentenceNumber ? `Sentence ${sentenceNumber} illustration` : 'Sentence illustration'}
                    loading={frame.isActive ? 'eager' : 'lazy'}
                    decoding="async"
                    onError={() => {
                      if (!sentenceNumber) {
                        return;
                      }
                      onFrameError?.(sentenceNumber);
                    }}
                  />
                ) : (
                  <span className="player-panel__interactive-image-reel-placeholder" aria-hidden="true">
                    {sentenceNumber ? '—' : ''}
                  </span>
                )}
              </button>
            </div>
          );
        })}
      </div>
    </div>
  );
}
