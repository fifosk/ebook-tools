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

export interface TextPlayerSentence {
  id: string;
  index: number;
  sentenceNumber?: number | null;
  state: 'past' | 'active' | 'future';
  variants: TextPlayerVariantDisplay[];
}

interface TextPlayerProps {
  sentences: TextPlayerSentence[];
  onSeek?: (time: number) => void;
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

function renderVariant(
  sentenceState: 'past' | 'active' | 'future',
  sentenceIndex: number,
  variant: TextPlayerVariantDisplay,
  onSeek?: (time: number) => void,
) {
  if (!variant.tokens.length) {
    return null;
  }

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
  variant.tokens.forEach((token, index) => {
    const classNames = [styles.wordBase, baseClassName];

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

  if (content.length === 0) {
    return null;
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

  return (
    <div className={styles.lineRow} key={`${variant.baseClass}-row`}>
      <span className={styles.lineLabel}>{variant.label}</span>
      <div className={contentClassName}>{content}</div>
    </div>
  );
}

const TextPlayer: React.FC<TextPlayerProps> = ({ sentences, onSeek }) => {
  if (!sentences.length) {
    return (
      <div className={styles.frame}>
        <div className={styles.lineRow}>
          <span className={styles.lineLabel}>Waiting for transcript…</span>
        </div>
      </div>
    );
  }

  return (
    <div className={styles.frame}>
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
              renderVariant(sentence.state, sentence.index, variant, onSeek)
            )}
          </div>
        );
      })}
    </div>
  );
};

export default TextPlayer;
