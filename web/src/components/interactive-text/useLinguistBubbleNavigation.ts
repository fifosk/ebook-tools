import { useCallback, useEffect, useMemo, useRef } from 'react';
import type { MutableRefObject } from 'react';
import type { LiveMediaChunk } from '../../hooks/useLiveMedia';
import type { TextPlayerVariantKind } from '../../text-player/TextPlayer';
import type {
  LinguistBubbleNavigation,
  LinguistBubbleState,
  SentenceFragment,
  TimelineDisplay,
} from './types';
import { tokenizeSentenceText } from './utils';

export type UseLinguistBubbleNavigationArgs = {
  containerRef: MutableRefObject<HTMLDivElement | null>;
  anchorRectRef: MutableRefObject<DOMRect | null>;
  anchorElementRef: MutableRefObject<HTMLElement | null>;
  bubble: LinguistBubbleState | null;
  bubblePinned: boolean;
  bubbleDocked: boolean;
  activeSentenceIndex: number;
  setActiveSentenceIndex: (value: number) => void;
  timelineDisplay: TimelineDisplay | null;
  rawSentences: SentenceFragment[];
  chunk: LiveMediaChunk | null;
  onRequestAdvanceChunk?: () => void;
  seekInlineAudioToTime: (time: number) => void;
  openLinguistBubbleForRect: (
    query: string,
    rect: DOMRect,
    trigger: 'click' | 'selection',
    variantKind: TextPlayerVariantKind | null,
    anchorElement: HTMLElement | null,
    navigationOverride?: LinguistBubbleNavigation | null,
  ) => void;
  requestPositionUpdate: () => void;
};

export type UseLinguistBubbleNavigationResult = {
  canNavigatePrev: boolean;
  canNavigateNext: boolean;
  onNavigateWord: (delta: -1 | 1) => void;
  resetNavigation: () => void;
};

export function useLinguistBubbleNavigation({
  containerRef,
  anchorRectRef,
  anchorElementRef,
  bubble,
  bubblePinned,
  bubbleDocked,
  activeSentenceIndex,
  setActiveSentenceIndex,
  timelineDisplay,
  rawSentences,
  chunk,
  onRequestAdvanceChunk,
  seekInlineAudioToTime,
  openLinguistBubbleForRect,
  requestPositionUpdate,
}: UseLinguistBubbleNavigationArgs): UseLinguistBubbleNavigationResult {
  const navigationPendingRef = useRef<LinguistBubbleNavigation | null>(null);
  const chunkAdvancePendingRef = useRef<{ variantKind: TextPlayerVariantKind } | null>(null);

  const linguistSentenceOrder = useMemo(() => {
    if (timelineDisplay?.sentences && timelineDisplay.sentences.length > 0) {
      return timelineDisplay.sentences.map((sentence) => sentence.index);
    }
    if (chunk?.sentences && chunk.sentences.length > 0) {
      return chunk.sentences.map((_sentence, index) => index);
    }
    return rawSentences.map((sentence) => sentence.index);
  }, [chunk?.sentences, rawSentences, timelineDisplay?.sentences]);

  const linguistSentencePositionByIndex = useMemo(() => {
    const map = new Map<number, number>();
    linguistSentenceOrder.forEach((sentenceIndex, position) => {
      map.set(sentenceIndex, position);
    });
    return map;
  }, [linguistSentenceOrder]);

  const tokensForSentence = useCallback(
    (sentenceIndex: number, variantKind: TextPlayerVariantKind): string[] => {
      if (timelineDisplay?.sentences && timelineDisplay.sentences.length > 0) {
        const sentence = timelineDisplay.sentences.find(
          (entry) => entry.index === sentenceIndex,
        );
        const variant =
          sentence?.variants?.find((candidate) => candidate.baseClass === variantKind) ??
          null;
        return variant?.tokens ?? [];
      }

      if (chunk?.sentences && chunk.sentences.length > 0) {
        const sentence = chunk.sentences[sentenceIndex];
        if (!sentence) {
          return [];
        }
        if (variantKind === 'translation') {
          return tokenizeSentenceText(sentence.translation?.text ?? null);
        }
        if (variantKind === 'translit') {
          return tokenizeSentenceText(sentence.transliteration?.text ?? null);
        }
        return tokenizeSentenceText(sentence.original?.text ?? null);
      }

      const position = linguistSentencePositionByIndex.get(sentenceIndex);
      if (position === undefined) {
        return [];
      }
      const sentence = rawSentences[position];
      if (variantKind === 'translation') {
        return tokenizeSentenceText(sentence.translation);
      }
      if (variantKind === 'translit') {
        return tokenizeSentenceText(sentence.transliteration);
      }
      return tokenizeSentenceText(sentence.text);
    },
    [chunk?.sentences, linguistSentencePositionByIndex, rawSentences, timelineDisplay?.sentences],
  );

  const seekTimeForNavigation = useCallback(
    (navigation: LinguistBubbleNavigation): number | null => {
      if (!timelineDisplay?.sentences || timelineDisplay.sentences.length === 0) {
        return null;
      }
      const sentence = timelineDisplay.sentences.find(
        (entry) => entry.index === navigation.sentenceIndex,
      );
      const variant =
        sentence?.variants?.find((candidate) => candidate.baseClass === navigation.variantKind) ??
        null;
      const times = variant?.seekTimes ?? null;
      if (!times || navigation.tokenIndex < 0 || navigation.tokenIndex >= times.length) {
        return null;
      }
      const time = times[navigation.tokenIndex];
      return typeof time === 'number' && Number.isFinite(time) ? time : null;
    },
    [timelineDisplay?.sentences],
  );

  const resolveRelativeLinguistNavigation = useCallback(
    (current: LinguistBubbleNavigation, delta: -1 | 1): LinguistBubbleNavigation | null => {
      const startPosition = linguistSentencePositionByIndex.get(current.sentenceIndex);
      if (startPosition === undefined) {
        return null;
      }
      const variantKind = current.variantKind;
      const currentTokens = tokensForSentence(current.sentenceIndex, variantKind);
      if (currentTokens.length === 0) {
        return null;
      }

      let sentencePosition = startPosition;
      let tokenIndex = current.tokenIndex + delta;

      if (tokenIndex < 0) {
        sentencePosition -= 1;
        while (sentencePosition >= 0) {
          const nextSentenceIndex = linguistSentenceOrder[sentencePosition];
          const tokens = tokensForSentence(nextSentenceIndex, variantKind);
          if (tokens.length > 0) {
            tokenIndex = tokens.length - 1;
            return { sentenceIndex: nextSentenceIndex, tokenIndex, variantKind };
          }
          sentencePosition -= 1;
        }
        return null;
      }

      if (tokenIndex >= currentTokens.length) {
        sentencePosition += 1;
        while (sentencePosition < linguistSentenceOrder.length) {
          const nextSentenceIndex = linguistSentenceOrder[sentencePosition];
          const tokens = tokensForSentence(nextSentenceIndex, variantKind);
          if (tokens.length > 0) {
            tokenIndex = 0;
            return { sentenceIndex: nextSentenceIndex, tokenIndex, variantKind };
          }
          sentencePosition += 1;
        }
        return null;
      }

      return {
        sentenceIndex: current.sentenceIndex,
        tokenIndex,
        variantKind,
      };
    },
    [linguistSentenceOrder, linguistSentencePositionByIndex, tokensForSentence],
  );

  const findTextPlayerTokenElement = useCallback(
    (navigation: LinguistBubbleNavigation): HTMLElement | null => {
      const container = containerRef.current;
      if (!container) {
        return null;
      }
      const selector = [
        `[data-sentence-index="${navigation.sentenceIndex}"]`,
        `[data-text-player-token="true"][data-text-player-variant="${navigation.variantKind}"][data-text-player-token-index="${navigation.tokenIndex}"]`,
      ].join(' ');
      const match = container.querySelector(selector);
      return match instanceof HTMLElement ? match : null;
    },
    [containerRef],
  );

  const onNavigateWord = useCallback(
    (delta: -1 | 1) => {
      const current = bubble?.navigation ?? null;
      if (!bubble || !current) {
        return;
      }
      const target = resolveRelativeLinguistNavigation(current, delta);
      if (!target) {
        if (delta === 1 && onRequestAdvanceChunk) {
          chunkAdvancePendingRef.current = { variantKind: current.variantKind };
          onRequestAdvanceChunk();
        }
        return;
      }

      const targetTokens = tokensForSentence(target.sentenceIndex, target.variantKind);
      const rawWord = targetTokens[target.tokenIndex] ?? '';
      if (!rawWord.trim()) {
        return;
      }

      const seekTime = seekTimeForNavigation(target);

      const tokenEl = findTextPlayerTokenElement(target);
      if (tokenEl) {
        openLinguistBubbleForRect(
          rawWord,
          tokenEl.getBoundingClientRect(),
          'click',
          target.variantKind,
          tokenEl,
        );
        if (seekTime !== null) {
          seekInlineAudioToTime(seekTime);
        }
        return;
      }

      const container = containerRef.current;
      const fallbackRect =
        anchorRectRef.current ?? container?.getBoundingClientRect();
      if (!fallbackRect) {
        return;
      }

      openLinguistBubbleForRect(
        rawWord,
        fallbackRect,
        'click',
        target.variantKind,
        null,
        target,
      );
      if (seekTime !== null) {
        seekInlineAudioToTime(seekTime);
      }
      if (target.sentenceIndex !== activeSentenceIndex) {
        navigationPendingRef.current = target;
        setActiveSentenceIndex(target.sentenceIndex);
      }
    },
    [
      activeSentenceIndex,
      anchorRectRef,
      bubble,
      containerRef,
      findTextPlayerTokenElement,
      onRequestAdvanceChunk,
      openLinguistBubbleForRect,
      resolveRelativeLinguistNavigation,
      seekInlineAudioToTime,
      seekTimeForNavigation,
      setActiveSentenceIndex,
      tokensForSentence,
    ],
  );

  const canNavigatePrev = useMemo(() => {
    const current = bubble?.navigation ?? null;
    if (!current) {
      return false;
    }
    return resolveRelativeLinguistNavigation(current, -1) !== null;
  }, [bubble?.navigation, resolveRelativeLinguistNavigation]);

  const canNavigateNext = useMemo(() => {
    const current = bubble?.navigation ?? null;
    if (!current) {
      return false;
    }
    return resolveRelativeLinguistNavigation(current, 1) !== null;
  }, [bubble?.navigation, resolveRelativeLinguistNavigation]);

  useEffect(() => {
    const pending = navigationPendingRef.current;
    if (!pending || !bubble || bubblePinned || bubbleDocked) {
      return;
    }
    const tokenEl = findTextPlayerTokenElement(pending);
    if (!tokenEl) {
      return;
    }
    navigationPendingRef.current = null;
    anchorElementRef.current = tokenEl;
    anchorRectRef.current = tokenEl.getBoundingClientRect();
    requestPositionUpdate();
  }, [
    anchorElementRef,
    anchorRectRef,
    bubble,
    bubblePinned,
    bubbleDocked,
    findTextPlayerTokenElement,
    requestPositionUpdate,
  ]);

  useEffect(() => {
    const pendingAdvance = chunkAdvancePendingRef.current;
    if (!pendingAdvance || !bubble) {
      return;
    }

    const variantKind = pendingAdvance.variantKind;
    let sentenceIndex: number | null = null;
    for (const candidate of linguistSentenceOrder) {
      const tokens = tokensForSentence(candidate, variantKind);
      if (tokens.length > 0) {
        sentenceIndex = candidate;
        break;
      }
    }

    chunkAdvancePendingRef.current = null;
    if (sentenceIndex === null) {
      return;
    }

    const tokens = tokensForSentence(sentenceIndex, variantKind);
    const rawWord = tokens[0] ?? '';
    if (!rawWord.trim()) {
      return;
    }

    const navigation: LinguistBubbleNavigation = {
      sentenceIndex,
      tokenIndex: 0,
      variantKind,
    };

    const seekTime = seekTimeForNavigation(navigation);
    if (seekTime !== null) {
      seekInlineAudioToTime(seekTime);
    }

    const container = containerRef.current;
    const fallbackRect =
      container?.getBoundingClientRect() ?? anchorRectRef.current;
    if (!fallbackRect) {
      return;
    }

    openLinguistBubbleForRect(
      rawWord,
      fallbackRect,
      'click',
      variantKind,
      null,
      navigation,
    );
    if (sentenceIndex !== activeSentenceIndex) {
      setActiveSentenceIndex(sentenceIndex);
      if (!bubblePinned && !bubbleDocked) {
        navigationPendingRef.current = navigation;
      }
    }
  }, [
    activeSentenceIndex,
    anchorRectRef,
    bubble,
    bubbleDocked,
    bubblePinned,
    containerRef,
    linguistSentenceOrder,
    openLinguistBubbleForRect,
    seekInlineAudioToTime,
    seekTimeForNavigation,
    setActiveSentenceIndex,
    tokensForSentence,
  ]);

  useEffect(() => {
    if (!bubble) {
      return;
    }
    const isTypingTarget = (target: EventTarget | null): target is HTMLElement => {
      if (!target || !(target instanceof HTMLElement)) {
        return false;
      }
      if (target.isContentEditable) {
        return true;
      }
      const tag = target.tagName;
      return tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT';
    };
    const handleShortcut = (event: KeyboardEvent) => {
      if (
        event.defaultPrevented ||
        event.metaKey ||
        event.ctrlKey ||
        !event.altKey ||
        isTypingTarget(event.target)
      ) {
        return;
      }
      if (event.key === 'ArrowLeft') {
        event.preventDefault();
        onNavigateWord(-1);
        return;
      }
      if (event.key === 'ArrowRight') {
        event.preventDefault();
        onNavigateWord(1);
      }
    };
    window.addEventListener('keydown', handleShortcut);
    return () => {
      window.removeEventListener('keydown', handleShortcut);
    };
  }, [bubble, onNavigateWord]);

  const resetNavigation = useCallback(() => {
    navigationPendingRef.current = null;
    chunkAdvancePendingRef.current = null;
  }, []);

  return {
    canNavigatePrev,
    canNavigateNext,
    onNavigateWord,
    resetNavigation,
  };
}
