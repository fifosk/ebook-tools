/**
 * Hook for handling keyboard navigation in the text player.
 */

import { useCallback, useEffect, useMemo, useState } from 'react';
import type { KeyboardEvent as ReactKeyboardEvent } from 'react';
import type {
  TextPlayerSentence,
  TextPlayerTokenRange,
  TextPlayerTokenSelection,
  TextPlayerVariantKind,
} from '../../text-player/TextPlayer';

type TextPlayerMultiSelection = {
  sentenceIndex: number;
  variantKind: TextPlayerVariantKind;
  anchorIndex: number;
  focusIndex: number;
};

interface LinguistBubbleNavigation {
  sentenceIndex: number;
  variantKind: TextPlayerVariantKind;
  tokenIndex: number;
}

interface LinguistBubble {
  navigation?: LinguistBubbleNavigation | null;
}

export interface UseTextPlayerKeyboardOptions {
  containerRef: React.RefObject<HTMLDivElement | null>;
  activeTextSentence: TextPlayerSentence | null;
  isInlineAudioPlaying: boolean;
  linguistBubble: LinguistBubble | null;
  isVariantVisible: (kind: TextPlayerVariantKind) => boolean;
  openLinguistTokenLookup: (
    tokenText: string,
    variantKind: TextPlayerVariantKind,
    anchorElement: HTMLElement | null,
    navigation: { sentenceIndex: number; tokenIndex: number; variantKind: TextPlayerVariantKind },
  ) => void;
}

export interface TextPlayerKeyboardState {
  /** Manual token selection (set by keyboard navigation) */
  manualSelection: TextPlayerTokenSelection | null;
  /** Set manual selection */
  setManualSelection: React.Dispatch<React.SetStateAction<TextPlayerTokenSelection | null>>;
  /** Multi-token selection range (set by Shift+Arrow) */
  multiSelection: TextPlayerMultiSelection | null;
  /** Set multi selection */
  setMultiSelection: React.Dispatch<React.SetStateAction<TextPlayerMultiSelection | null>>;
  /** Computed selection for text player */
  textPlayerSelection: TextPlayerTokenSelection | null;
  /** Shadow selection for paired variants (translation/translit) */
  textPlayerShadowSelection: TextPlayerTokenSelection | null;
  /** Selection range for highlighting */
  textPlayerSelectionRange: TextPlayerTokenRange | null;
  /** Keyboard event handler */
  handleTextPlayerKeyDown: (event: ReactKeyboardEvent<HTMLDivElement>) => void;
}

export function useTextPlayerKeyboard({
  containerRef,
  activeTextSentence,
  isInlineAudioPlaying,
  linguistBubble,
  isVariantVisible,
  openLinguistTokenLookup,
}: UseTextPlayerKeyboardOptions): TextPlayerKeyboardState {
  const [manualSelection, setManualSelection] = useState<TextPlayerTokenSelection | null>(null);
  const [multiSelection, setMultiSelection] = useState<TextPlayerMultiSelection | null>(null);

  // Clear selection when sentence changes
  useEffect(() => {
    setManualSelection(null);
    setMultiSelection(null);
  }, [activeTextSentence?.id]);

  // Clear selection when audio starts playing
  useEffect(() => {
    if (isInlineAudioPlaying) {
      setManualSelection(null);
      setMultiSelection(null);
    }
  }, [isInlineAudioPlaying]);

  // Sync manual selection with linguist bubble navigation
  useEffect(() => {
    if (isInlineAudioPlaying || !activeTextSentence) {
      return;
    }
    const navigation = linguistBubble?.navigation ?? null;
    if (!navigation || navigation.sentenceIndex !== activeTextSentence.index) {
      return;
    }
    if (!isVariantVisible(navigation.variantKind)) {
      return;
    }
    const variant = activeTextSentence.variants.find((entry) => entry.baseClass === navigation.variantKind);
    if (!variant || variant.tokens.length === 0) {
      return;
    }
    const clampedIndex = Math.max(0, Math.min(navigation.tokenIndex, variant.tokens.length - 1));
    setManualSelection({
      sentenceIndex: activeTextSentence.index,
      variantKind: navigation.variantKind,
      tokenIndex: clampedIndex,
    });
    setMultiSelection(null);
  }, [activeTextSentence, isInlineAudioPlaying, isVariantVisible, linguistBubble?.navigation]);

  // Compute selection and shadow selection
  const { selection: textPlayerSelection, shadowSelection: textPlayerShadowSelection } = useMemo(() => {
    if (!activeTextSentence) {
      return { selection: null, shadowSelection: null };
    }

    const variantForKind = (kind: TextPlayerVariantKind) => {
      if (!isVariantVisible(kind)) {
        return null;
      }
      return activeTextSentence.variants.find((variant) => variant.baseClass === kind) ?? null;
    };

    const resolveSelection = (
      variant: (typeof activeTextSentence.variants)[number] | null,
    ): TextPlayerTokenSelection | null => {
      if (!variant || variant.tokens.length === 0) {
        return null;
      }
      const rawIndex =
        typeof variant.currentIndex === 'number' && Number.isFinite(variant.currentIndex)
          ? Math.trunc(variant.currentIndex)
          : 0;
      const clampedIndex = Math.max(0, Math.min(rawIndex, variant.tokens.length - 1));
      return {
        sentenceIndex: activeTextSentence.index,
        variantKind: variant.baseClass,
        tokenIndex: clampedIndex,
      };
    };

    const normalizeSelection = (selection: TextPlayerTokenSelection | null): TextPlayerTokenSelection | null => {
      if (!selection || selection.sentenceIndex !== activeTextSentence.index) {
        return null;
      }
      const variant = variantForKind(selection.variantKind);
      if (!variant || variant.tokens.length === 0) {
        return null;
      }
      const clampedIndex = Math.max(0, Math.min(selection.tokenIndex, variant.tokens.length - 1));
      return {
        sentenceIndex: activeTextSentence.index,
        variantKind: variant.baseClass,
        tokenIndex: clampedIndex,
      };
    };

    const defaultSelection =
      resolveSelection(variantForKind('translation')) ??
      resolveSelection(variantForKind('translit')) ??
      resolveSelection(variantForKind('original'));

    const navigation = linguistBubble?.navigation ?? null;
    const bubbleSelection = navigation
      ? normalizeSelection({
          sentenceIndex: navigation.sentenceIndex,
          variantKind: navigation.variantKind,
          tokenIndex: navigation.tokenIndex,
        })
      : null;
    const safeManualSelection = normalizeSelection(manualSelection);

    const selection = isInlineAudioPlaying
      ? defaultSelection
      : safeManualSelection ?? bubbleSelection ?? defaultSelection;

    const translationVariant = variantForKind('translation');
    const translitVariant = variantForKind('translit');
    let shadowSelection: TextPlayerTokenSelection | null = null;
    if (
      selection &&
      translationVariant &&
      translitVariant &&
      translationVariant.tokens.length === translitVariant.tokens.length
    ) {
      const shadowIndex = selection.tokenIndex;
      if (shadowIndex >= 0 && shadowIndex < translationVariant.tokens.length) {
        if (selection.variantKind === 'translation') {
          shadowSelection = {
            sentenceIndex: activeTextSentence.index,
            variantKind: 'translit',
            tokenIndex: shadowIndex,
          };
        } else if (selection.variantKind === 'translit') {
          shadowSelection = {
            sentenceIndex: activeTextSentence.index,
            variantKind: 'translation',
            tokenIndex: shadowIndex,
          };
        }
      }
    }

    return { selection, shadowSelection };
  }, [activeTextSentence, isInlineAudioPlaying, isVariantVisible, linguistBubble?.navigation, manualSelection]);

  // Compute selection range for multi-selection highlight
  const textPlayerSelectionRange = useMemo<TextPlayerTokenRange | null>(() => {
    if (!activeTextSentence || isInlineAudioPlaying || !multiSelection) {
      return null;
    }
    if (multiSelection.sentenceIndex !== activeTextSentence.index) {
      return null;
    }
    if (!isVariantVisible(multiSelection.variantKind)) {
      return null;
    }
    const variant = activeTextSentence.variants.find(
      (entry) => entry.baseClass === multiSelection.variantKind,
    );
    if (!variant || variant.tokens.length === 0) {
      return null;
    }
    const maxIndex = variant.tokens.length - 1;
    const anchorIndex = Math.max(0, Math.min(multiSelection.anchorIndex, maxIndex));
    const focusIndex = Math.max(0, Math.min(multiSelection.focusIndex, maxIndex));
    return {
      sentenceIndex: activeTextSentence.index,
      variantKind: variant.baseClass,
      startIndex: Math.min(anchorIndex, focusIndex),
      endIndex: Math.max(anchorIndex, focusIndex),
    };
  }, [activeTextSentence, isInlineAudioPlaying, isVariantVisible, multiSelection]);

  const handleTextPlayerKeyDown = useCallback(
    (event: ReactKeyboardEvent<HTMLDivElement>) => {
      if (isInlineAudioPlaying || !activeTextSentence) {
        return;
      }
      const key = event.key;
      const isArrow =
        key === 'ArrowLeft' || key === 'ArrowRight' || key === 'ArrowUp' || key === 'ArrowDown';
      const isShift = event.shiftKey;
      const isHorizontal = key === 'ArrowLeft' || key === 'ArrowRight';
      if (key !== 'Enter' && !isArrow) {
        return;
      }
      const variants = activeTextSentence.variants.filter(
        (variant) => variant.tokens.length > 0 && isVariantVisible(variant.baseClass),
      );
      if (variants.length === 0) {
        return;
      }
      const fallbackSelection: TextPlayerTokenSelection = {
        sentenceIndex: activeTextSentence.index,
        variantKind: variants[0].baseClass,
        tokenIndex: 0,
      };
      const current = textPlayerSelection ?? fallbackSelection;
      const currentVariant =
        variants.find((variant) => variant.baseClass === current.variantKind) ?? variants[0];
      const tokenCount = currentVariant.tokens.length;
      if (tokenCount === 0) {
        return;
      }
      const clampIndex = (value: number) => Math.max(0, Math.min(value, tokenCount - 1));
      const activeMultiSelection =
        multiSelection &&
        multiSelection.sentenceIndex === activeTextSentence.index &&
        multiSelection.variantKind === currentVariant.baseClass
          ? multiSelection
          : null;

      if (key === 'Enter') {
        const anchorIndex = activeMultiSelection
          ? clampIndex(activeMultiSelection.anchorIndex)
          : clampIndex(current.tokenIndex);
        const focusIndex = activeMultiSelection
          ? clampIndex(activeMultiSelection.focusIndex)
          : clampIndex(current.tokenIndex);
        const rangeStart = Math.min(anchorIndex, focusIndex);
        const rangeEnd = Math.max(anchorIndex, focusIndex);
        const selectedTokens = activeMultiSelection
          ? currentVariant.tokens.slice(rangeStart, rangeEnd + 1)
          : [currentVariant.tokens[focusIndex]];
        const tokenText = selectedTokens.join(' ').trim();
        if (!tokenText) {
          return;
        }
        const selector = [
          `[data-sentence-index="${current.sentenceIndex}"]`,
          `[data-text-player-token="true"][data-text-player-variant="${currentVariant.baseClass}"][data-text-player-token-index="${focusIndex}"]`,
        ].join(' ');
        const candidate = containerRef.current?.querySelector(selector);
        const anchorElement = candidate instanceof HTMLElement ? candidate : null;
        openLinguistTokenLookup(tokenText, currentVariant.baseClass, anchorElement, {
          sentenceIndex: activeTextSentence.index,
          tokenIndex: focusIndex,
          variantKind: currentVariant.baseClass,
        });
        event.preventDefault();
        event.stopPropagation();
        return;
      }

      if (!isShift || !isHorizontal) {
        setMultiSelection(null);
      }

      let nextSelection: TextPlayerTokenSelection | null = null;
      if (isHorizontal) {
        const delta = key === 'ArrowRight' ? 1 : -1;
        const baseFocusIndex = activeMultiSelection
          ? clampIndex(activeMultiSelection.focusIndex)
          : clampIndex(current.tokenIndex);
        const anchorIndex = activeMultiSelection
          ? clampIndex(activeMultiSelection.anchorIndex)
          : clampIndex(current.tokenIndex);
        let nextIndex = baseFocusIndex + delta;
        if (isShift) {
          if (nextIndex < 0) {
            nextIndex = 0;
          } else if (nextIndex >= tokenCount) {
            nextIndex = tokenCount - 1;
          }
        } else {
          if (nextIndex < 0) {
            nextIndex = tokenCount - 1;
          } else if (nextIndex >= tokenCount) {
            nextIndex = 0;
          }
        }
        nextSelection = {
          sentenceIndex: activeTextSentence.index,
          variantKind: currentVariant.baseClass,
          tokenIndex: nextIndex,
        };
        if (isShift) {
          setMultiSelection({
            sentenceIndex: activeTextSentence.index,
            variantKind: currentVariant.baseClass,
            anchorIndex,
            focusIndex: nextIndex,
          });
        }
      } else {
        const order = variants.map((variant) => variant.baseClass);
        const currentPos = order.indexOf(currentVariant.baseClass);
        const nextPos = key === 'ArrowUp' ? currentPos - 1 : currentPos + 1;
        if (nextPos < 0 || nextPos >= order.length) {
          return;
        }
        const nextVariant = variants[nextPos];
        const clampedIndex = Math.max(0, Math.min(current.tokenIndex, nextVariant.tokens.length - 1));
        nextSelection = {
          sentenceIndex: activeTextSentence.index,
          variantKind: nextVariant.baseClass,
          tokenIndex: clampedIndex,
        };
      }

      setManualSelection(nextSelection);
      event.preventDefault();
      event.stopPropagation();
    },
    [
      activeTextSentence,
      containerRef,
      isInlineAudioPlaying,
      isVariantVisible,
      multiSelection,
      openLinguistTokenLookup,
      textPlayerSelection,
    ],
  );

  return {
    manualSelection,
    setManualSelection,
    multiSelection,
    setMultiSelection,
    textPlayerSelection,
    textPlayerShadowSelection,
    textPlayerSelectionRange,
    handleTextPlayerKeyDown,
  };
}
