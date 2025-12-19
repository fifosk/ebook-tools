import type { CSSProperties, Ref } from 'react';
import type { LinguistBubbleFloatingPlacement, LinguistBubbleState } from './types';
import { containsNonLatinLetters, renderWithNonLatinBoost } from './utils';

type MyLinguistBubbleVariant = 'docked' | 'floating';

interface MyLinguistBubbleProps {
  bubble: LinguistBubbleState;
  isPinned: boolean;
  variant: MyLinguistBubbleVariant;
  bubbleRef?: Ref<HTMLDivElement>;
  floatingPlacement?: LinguistBubbleFloatingPlacement;
  floatingPosition?: { top: number; left: number } | null;
  canNavigatePrev: boolean;
  canNavigateNext: boolean;
  onTogglePinned: () => void;
  onNavigatePrev: () => void;
  onNavigateNext: () => void;
  onSpeak: () => void;
  onSpeakSlow: () => void;
  onClose: () => void;
}

export function MyLinguistBubble({
  bubble,
  isPinned,
  variant,
  bubbleRef,
  floatingPlacement,
  floatingPosition,
  canNavigatePrev,
  canNavigateNext,
  onTogglePinned,
  onNavigatePrev,
  onNavigateNext,
  onSpeak,
  onSpeakSlow,
  onClose,
}: MyLinguistBubbleProps) {
  const className = [
    'player-panel__my-linguist-bubble',
    variant === 'docked' ? 'player-panel__my-linguist-bubble--docked' : 'player-panel__my-linguist-bubble--floating',
    bubble.status === 'loading' ? 'player-panel__my-linguist-bubble--loading' : null,
    bubble.status === 'error' ? 'player-panel__my-linguist-bubble--error' : null,
  ]
    .filter(Boolean)
    .join(' ');

  const style =
    variant === 'floating' && floatingPosition
      ? ({
          top: `${floatingPosition.top}px`,
          left: `${floatingPosition.left}px`,
          bottom: 'auto',
        } as CSSProperties)
      : undefined;

  return (
    <div
      ref={bubbleRef}
      className={className}
      data-placement={variant === 'floating' ? floatingPlacement : undefined}
      style={style}
      role="dialog"
      aria-label="MyLinguist lookup"
    >
      <div className="player-panel__my-linguist-bubble-header">
        <div className="player-panel__my-linguist-bubble-header-left">
          <span className="player-panel__my-linguist-bubble-title">MyLinguist</span>
          <span className="player-panel__my-linguist-bubble-meta">Model: {bubble.modelLabel}</span>
        </div>
        <div className="player-panel__my-linguist-bubble-actions">
          <button
            type="button"
            className="player-panel__my-linguist-bubble-pin"
            onClick={onTogglePinned}
            aria-label={isPinned ? 'Unpin MyLinguist bubble' : 'Pin MyLinguist bubble'}
            aria-pressed={isPinned}
            title={isPinned ? 'Unpin bubble' : 'Pin bubble'}
          >
            <svg viewBox="0 0 24 24" role="img" focusable="false" aria-hidden="true">
              {isPinned ? (
                <>
                  <path d="M9 3h6l1 6 2 2v2H6v-2l2-2 1-6Z" />
                  <path d="M12 13v8" />
                </>
              ) : (
                <>
                  <path d="M9 3h6l1 6 2 2v2H6v-2l2-2 1-6Z" />
                  <path d="M12 13v8" />
                  <path d="M4 4l16 16" />
                </>
              )}
            </svg>
          </button>
          <button
            type="button"
            className="player-panel__my-linguist-bubble-nav"
            onClick={onNavigatePrev}
            aria-label="Previous word"
            title="Previous word (Alt+←)"
            disabled={!canNavigatePrev}
          >
            ←
          </button>
          <button
            type="button"
            className="player-panel__my-linguist-bubble-nav"
            onClick={onNavigateNext}
            aria-label="Next word"
            title="Next word (Alt+→)"
            disabled={!canNavigateNext}
          >
            →
          </button>
          <button
            type="button"
            className="player-panel__my-linguist-bubble-speak"
            onClick={onSpeak}
            aria-label="Speak selection aloud"
            title="Speak selection aloud"
            disabled={bubble.ttsStatus === 'loading'}
          >
            {bubble.ttsStatus === 'loading' ? '…' : '🔊'}
          </button>
          <button
            type="button"
            className="player-panel__my-linguist-bubble-speak"
            onClick={onSpeakSlow}
            aria-label="Speak selection slowly"
            title="Speak slowly (0.5×)"
            disabled={bubble.ttsStatus === 'loading'}
          >
            {bubble.ttsStatus === 'loading' ? '…' : '🐢'}
          </button>
          <button
            type="button"
            className="player-panel__my-linguist-bubble-close"
            onClick={onClose}
            aria-label="Close MyLinguist lookup"
          >
            ✕
          </button>
        </div>
      </div>
      <div
        className={[
          'player-panel__my-linguist-bubble-query',
          containsNonLatinLetters(bubble.fullQuery)
            ? 'player-panel__my-linguist-bubble-query--non-latin'
            : null,
        ]
          .filter(Boolean)
          .join(' ')}
      >
        {bubble.query}
      </div>
      <div className="player-panel__my-linguist-bubble-body">
        {renderWithNonLatinBoost(
          bubble.answer,
          'player-panel__my-linguist-bubble-non-latin',
        )}
      </div>
    </div>
  );
}
