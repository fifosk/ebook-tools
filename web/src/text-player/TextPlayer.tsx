import React from 'react';
import styles from './TextPlayer.module.css';

export type TextPlayerVariantKind = 'original' | 'translit' | 'translation';

export interface TextPlayerVariantDisplay {
  label: string;
  tokens: string[];
  revealedCount: number;
  currentIndex: number | null;
  baseClass: TextPlayerVariantKind;
  seekTimes?: number[];
}

export type TextPlayerTokenSelection = {
  sentenceIndex: number;
  tokenIndex: number;
  variantKind: TextPlayerVariantKind;
};

export type TextPlayerTokenRange = {
  sentenceIndex: number;
  variantKind: TextPlayerVariantKind;
  startIndex: number;
  endIndex: number;
};

export interface TextPlayerSentence {
  id: string;
  index: number;
  sentenceNumber?: number | null;
  state: 'past' | 'active' | 'future';
  variants: TextPlayerVariantDisplay[];
}

type VariantVisibility = Partial<Record<TextPlayerVariantKind, boolean>>;

interface TextPlayerProps {
  sentences: TextPlayerSentence[];
  onSeek?: (time: number) => void;
  selection?: TextPlayerTokenSelection | null;
  selectionRange?: TextPlayerTokenRange | null;
  shadowSelection?: TextPlayerTokenSelection | null;
  variantVisibility?: VariantVisibility;
  onToggleVariant?: (variant: TextPlayerVariantKind) => void;
  belowTracks?: React.ReactNode;
  footer?: React.ReactNode;
}

function variantBaseClass(kind: TextPlayerVariantKind): string {
  switch (kind) {
    case 'translit':
      return styles.wordTranslit;
    case 'translation':
      return styles.wordTranslation;
    default:
      return styles.wordOriginal;
  }
}

function variantPastClass(kind: TextPlayerVariantKind): string {
  switch (kind) {
    case 'translit':
      return styles.wordTranslitPast;
    case 'translation':
      return styles.wordTranslationPast;
    default:
      return styles.wordOriginalPast;
  }
}

function variantCurrentClass(kind: TextPlayerVariantKind): string {
  switch (kind) {
    case 'translit':
      return styles.wordTranslitCurrent;
    case 'translation':
      return styles.wordTranslationCurrent;
    default:
      return styles.wordOriginalCurrent;
  }
}

function variantFutureClass(kind: TextPlayerVariantKind): string {
  switch (kind) {
    case 'translit':
      return styles.wordTranslitFuture;
    case 'translation':
      return styles.wordTranslationFuture;
    default:
      return styles.wordOriginalFuture;
  }
}

function resolveVariantVisibility(
  kind: TextPlayerVariantKind,
  visibility?: VariantVisibility,
): boolean {
  if (!visibility) {
    return true;
  }
  return visibility[kind] ?? true;
}

function renderVariant(
  sentenceState: 'past' | 'active' | 'future',
  sentenceIndex: number,
  variant: TextPlayerVariantDisplay,
  onSeek?: (time: number) => void,
  selection?: TextPlayerTokenSelection | null,
  selectionRange?: TextPlayerTokenRange | null,
  shadowSelection?: TextPlayerTokenSelection | null,
  variantVisibility?: VariantVisibility,
  onToggleVariant?: (variant: TextPlayerVariantKind) => void,
) {
  if (!variant.tokens.length) {
    return null;
  }

  const isVisible = resolveVariantVisibility(variant.baseClass, variantVisibility);
  const baseClassName = variantBaseClass(variant.baseClass);
  const pastClassName = variantPastClass(variant.baseClass);
  const currentClassName = variantCurrentClass(variant.baseClass);
  const futureClassName = variantFutureClass(variant.baseClass);
  const totalTokens = variant.tokens.length;
  const revealedCount = Math.max(0, Math.min(variant.revealedCount, totalTokens));

  const handleSeek = (tokenIndex: number) => {
    if (!onSeek || !variant.seekTimes) {
      return;
    }
    const target = variant.seekTimes[tokenIndex];
    if (typeof target !== 'number' || Number.isNaN(target)) {
      return;
    }
    onSeek(Math.max(target, 0));
  };

  const content: React.ReactNode[] = [];
  if (isVisible) {
    variant.tokens.forEach((token, index) => {
      const classNames = [styles.wordBase, baseClassName];
      const isSelected =
        selection?.sentenceIndex === sentenceIndex &&
        selection.variantKind === variant.baseClass &&
        selection.tokenIndex === index;
      const isRangeSelected =
        selectionRange?.sentenceIndex === sentenceIndex &&
        selectionRange.variantKind === variant.baseClass &&
        index >= selectionRange.startIndex &&
        index <= selectionRange.endIndex;
      const isShadow =
        shadowSelection?.sentenceIndex === sentenceIndex &&
        shadowSelection.variantKind === variant.baseClass &&
        shadowSelection.tokenIndex === index;

      if (sentenceState === 'future') {
        classNames.push(futureClassName);
      } else if (sentenceState === 'past') {
        classNames.push(pastClassName);
      } else if (revealedCount === 0) {
        classNames.push(futureClassName);
      } else if (index < revealedCount - 1) {
        classNames.push(pastClassName);
      } else if (index === revealedCount - 1) {
        classNames.push(currentClassName);
      } else {
        classNames.push(futureClassName);
      }

      if (isSelected || isRangeSelected) {
        classNames.push(styles.wordSelected);
      }
      if (isShadow) {
        classNames.push(styles.wordShadow);
      }

      const tokenKey = `${variant.baseClass}-${sentenceIndex}-${index}`;
      content.push(
        <span
          key={tokenKey}
          className={classNames.join(' ')}
          role={onSeek ? 'button' : undefined}
          tabIndex={onSeek ? 0 : undefined}
          onClick={() => handleSeek(index)}
          onKeyDown={(event) => {
            if (!onSeek) {
              return;
            }
            if (event.key === 'Enter' || event.key === ' ') {
              event.preventDefault();
              handleSeek(index);
            }
          }}
          data-text-player-token="true"
          data-text-player-variant={variant.baseClass}
          data-text-player-token-index={index}
          data-text-player-sentence-index={sentenceIndex}
        >
          {token}
        </span>
      );
      if (index < variant.tokens.length - 1) {
        content.push(
          <span
            key={`${tokenKey}-space`}
            className={styles.wordSpacer}
          >
            {' '}
          </span>
        );
      }
    });
  }

  const contentClassName = (() => {
    switch (variant.baseClass) {
      case 'translit':
        return `${styles.lineContent} ${styles.lineContentTranslit}`;
      case 'translation':
        return `${styles.lineContent} ${styles.lineContentTranslation}`;
      default:
        return `${styles.lineContent} ${styles.lineContentOriginal}`;
    }
  })();

  const labelNode = onToggleVariant ? (
    <button
      type="button"
      className={`${styles.lineLabel} ${styles.lineLabelButton}`}
      aria-pressed={isVisible}
      onClick={() => onToggleVariant(variant.baseClass)}
      title={`${isVisible ? 'Hide' : 'Show'} ${variant.label} track`}
    >
      <span className={styles.lineLabelText}>{variant.label}</span>
      <span className={styles.lineLabelCaret} aria-hidden="true" />
    </button>
  ) : (
    <span className={styles.lineLabel}>{variant.label}</span>
  );

  const contentNode = isVisible ? (
    <div className={contentClassName}>{content}</div>
  ) : (
    <div className={`${styles.lineContent} ${styles.lineContentPlaceholder}`} aria-hidden="true" />
  );

  return (
    <div className={styles.lineRow} key={`${variant.baseClass}-row`} data-text-player-variant={variant.baseClass}>
      {labelNode}
      {contentNode}
    </div>
  );
}

const TextPlayer: React.FC<TextPlayerProps> = ({
  sentences,
  onSeek,
  selection = null,
  selectionRange = null,
  shadowSelection = null,
  variantVisibility,
  onToggleVariant,
  belowTracks,
  footer,
}) => {
  if (!sentences.length) {
    return (
      <div className={styles.frame} data-text-player-frame="true">
        <div className={styles.lineRow}>
          <span className={styles.lineLabel}>Waiting for transcript…</span>
        </div>
        {belowTracks ? <div className={styles.belowTracks}>{belowTracks}</div> : null}
        {footer ? <div className={styles.footer}>{footer}</div> : null}
      </div>
    );
  }

  return (
    <div className={styles.frame} data-text-player-frame="true">
      {sentences.map((sentence) => {
        const classNames = [styles.sentence];
        if (sentence.state === 'active') {
          classNames.push(styles.sentenceActive);
        } else if (sentence.state === 'past') {
          classNames.push(styles.sentencePast);
        } else {
          classNames.push(styles.sentenceFuture);
        }

        return (
          <div
            className={classNames.join(' ')}
            key={sentence.id}
            data-sentence-index={sentence.index}
          >
            {sentence.variants.map((variant) =>
              renderVariant(
                sentence.state,
                sentence.index,
                variant,
                onSeek,
                selection,
                selectionRange,
                shadowSelection,
                variantVisibility,
                onToggleVariant,
              )
            )}
          </div>
        );
      })}
      {belowTracks ? <div className={styles.belowTracks}>{belowTracks}</div> : null}
      {footer ? <div className={styles.footer}>{footer}</div> : null}
    </div>
  );
};

export default TextPlayer;
