import { useCallback, useEffect } from 'react';
import type {
  MutableRefObject,
  Dispatch,
  SetStateAction,
} from 'react';
import { assistantLookup } from '../../api/client';
import type { AssistantLookupResponse } from '../../api/dtos';
import type { LiveMediaChunk } from '../../hooks/useLiveMedia';
import type { TextPlayerVariantKind } from '../../text-player/TextPlayer';
import { buildMyLinguistSystemPrompt } from '../../utils/myLinguistPrompt';
import { speakText } from '../../utils/ttsPlayback';
import {
  MY_LINGUIST_DEFAULT_LLM_MODEL,
  MY_LINGUIST_DEFAULT_LOOKUP_LANGUAGE,
  MY_LINGUIST_STORAGE_KEYS,
} from './constants';
import type { LinguistBubbleNavigation, LinguistBubbleState } from './types';
import {
  loadMyLinguistStored,
  normaliseTextPlayerVariant,
  sanitizeLookupQuery,
} from './utils';

export type UseLinguistBubbleLookupArgs = {
  isEnabled: boolean;
  audioRef: MutableRefObject<HTMLAudioElement | null>;
  requestCounterRef: MutableRefObject<number>;
  bubble: LinguistBubbleState | null;
  setBubble: Dispatch<SetStateAction<LinguistBubbleState | null>>;
  anchorRectRef: MutableRefObject<DOMRect | null>;
  anchorElementRef: MutableRefObject<HTMLElement | null>;
  jobId?: string | null;
  chunk: LiveMediaChunk | null;
  globalInputLanguage: string;
  resolvedJobOriginalLanguage: string | null;
  resolvedJobTranslationLanguage: string | null;
  applyOpenLayout: () => void;
  maxQueryChars: number;
  loadingAnswer: string;
  truncationSuffix: string;
};

export type UseLinguistBubbleLookupResult = {
  openLinguistBubbleForRect: (
    query: string,
    rect: DOMRect,
    trigger: 'click' | 'selection',
    variantKind: TextPlayerVariantKind | null,
    anchorElement: HTMLElement | null,
    navigationOverride?: LinguistBubbleNavigation | null,
  ) => void;
  onSpeak: () => void;
  onSpeakSlow: () => void;
  resetBubbleState: () => void;
};

export function useLinguistBubbleLookup({
  isEnabled,
  audioRef,
  requestCounterRef,
  bubble,
  setBubble,
  anchorRectRef,
  anchorElementRef,
  jobId,
  chunk,
  globalInputLanguage,
  resolvedJobOriginalLanguage,
  resolvedJobTranslationLanguage,
  applyOpenLayout,
  maxQueryChars,
  loadingAnswer,
  truncationSuffix,
}: UseLinguistBubbleLookupArgs): UseLinguistBubbleLookupResult {
  const extractLinguistNavigation = useCallback(
    (
      anchorElement: HTMLElement | null,
      fallbackVariant: TextPlayerVariantKind | null,
    ): LinguistBubbleNavigation | null => {
      if (!anchorElement) {
        return null;
      }
      const variantKind =
        fallbackVariant ?? normaliseTextPlayerVariant(anchorElement.dataset.textPlayerVariant);
      if (!variantKind) {
        return null;
      }
      const rawTokenIndex = anchorElement.dataset.textPlayerTokenIndex;
      const rawSentenceIndex =
        anchorElement.dataset.textPlayerSentenceIndex ??
        anchorElement.closest('[data-sentence-index]')?.getAttribute('data-sentence-index') ??
        null;
      const tokenIndex = rawTokenIndex ? Number(rawTokenIndex) : Number.NaN;
      const sentenceIndex = rawSentenceIndex ? Number(rawSentenceIndex) : Number.NaN;
      if (!Number.isFinite(tokenIndex) || !Number.isFinite(sentenceIndex)) {
        return null;
      }
      return {
        sentenceIndex,
        tokenIndex,
        variantKind,
      };
    },
    [],
  );

  const openLinguistBubbleForRect = useCallback(
    (
      query: string,
      rect: DOMRect,
      trigger: 'click' | 'selection',
      variantKind: TextPlayerVariantKind | null,
      anchorElement: HTMLElement | null,
      navigationOverride: LinguistBubbleNavigation | null = null,
    ) => {
      if (!isEnabled) {
        return;
      }
      const cleanedQuery = sanitizeLookupQuery(query);
      if (!cleanedQuery) {
        return;
      }
      anchorRectRef.current = rect;
      anchorElementRef.current = anchorElement;
      const inlineAudioEl = audioRef.current;
      if (inlineAudioEl && !inlineAudioEl.paused) {
        try {
          inlineAudioEl.pause();
        } catch {
          // Ignore pause failures triggered by autoplay policies.
        }
      }
      const slicedQuery =
        cleanedQuery.length > maxQueryChars
          ? `${cleanedQuery.slice(0, maxQueryChars)}${truncationSuffix}`
          : cleanedQuery;

      const storedInputLanguage =
        loadMyLinguistStored(MY_LINGUIST_STORAGE_KEYS.inputLanguage) ?? globalInputLanguage;
      const storedLookupLanguage =
        loadMyLinguistStored(MY_LINGUIST_STORAGE_KEYS.lookupLanguage) ??
        MY_LINGUIST_DEFAULT_LOOKUP_LANGUAGE;
      const storedModel = loadMyLinguistStored(MY_LINGUIST_STORAGE_KEYS.llmModel, {
        allowEmpty: true,
      });
      const storedPrompt = loadMyLinguistStored(MY_LINGUIST_STORAGE_KEYS.systemPrompt, {
        allowEmpty: true,
      });

      const jobPreferredInputLanguage =
        variantKind === 'translation'
          ? resolvedJobTranslationLanguage
          : variantKind === 'original' || variantKind === 'translit'
            ? resolvedJobOriginalLanguage
            : null;
      const resolvedInputLanguage =
        (jobPreferredInputLanguage ?? storedInputLanguage).trim() || globalInputLanguage;
      const resolvedLookupLanguage =
        storedLookupLanguage.trim() || MY_LINGUIST_DEFAULT_LOOKUP_LANGUAGE;
      const resolvedModel =
        storedModel === null
          ? MY_LINGUIST_DEFAULT_LLM_MODEL
          : storedModel.trim()
            ? storedModel.trim()
            : null;
      const modelLabel = resolvedModel ?? 'Auto';
      const resolvedPrompt =
        storedPrompt && storedPrompt.trim()
          ? storedPrompt.trim()
          : buildMyLinguistSystemPrompt(resolvedInputLanguage, resolvedLookupLanguage);

      const requestId = (requestCounterRef.current += 1);
      const navigation =
        navigationOverride ?? extractLinguistNavigation(anchorElement, variantKind);
      setBubble({
        query: slicedQuery,
        fullQuery: cleanedQuery,
        status: 'loading',
        answer: loadingAnswer,
        modelLabel,
        ttsLanguage: resolvedInputLanguage,
        ttsStatus: 'idle',
        navigation,
      });
      applyOpenLayout();

      const page = typeof window !== 'undefined' ? window.location.pathname : null;
      void assistantLookup({
        query: slicedQuery,
        input_language: resolvedInputLanguage,
        lookup_language: resolvedLookupLanguage,
        llm_model: resolvedModel,
        system_prompt: resolvedPrompt,
        context: {
          source: 'my_linguist',
          page,
          job_id: jobId,
          selection_text: trigger === 'selection' ? slicedQuery : null,
          metadata: {
            ui: 'interactive_bubble',
            trigger,
            chunk_id: chunk?.chunkId ?? null,
          },
        },
      })
        .then((response: AssistantLookupResponse) => {
          if (requestCounterRef.current !== requestId) {
            return;
          }
          setBubble((previous) => {
            if (!previous) {
              return previous;
            }
            return {
              ...previous,
              status: 'ready',
              answer: response.answer,
              ttsStatus: 'loading',
            };
          });
          void speakText({ text: cleanedQuery, language: resolvedInputLanguage })
            .then(() => {
              if (requestCounterRef.current !== requestId) {
                return;
              }
              setBubble((previous) => {
                if (!previous) {
                  return previous;
                }
                return { ...previous, ttsStatus: 'ready' };
              });
            })
            .catch(() => {
              if (requestCounterRef.current !== requestId) {
                return;
              }
              setBubble((previous) => {
                if (!previous) {
                  return previous;
                }
                return { ...previous, ttsStatus: 'error' };
              });
            });
        })
        .catch((error: unknown) => {
          if (requestCounterRef.current !== requestId) {
            return;
          }
          const message = error instanceof Error ? error.message : 'Unable to reach MyLinguist.';
          setBubble((previous) => {
            if (!previous) {
              return previous;
            }
            return {
              ...previous,
              status: 'error',
              answer: `Error: ${message}`,
              ttsStatus: 'idle',
            };
          });
        });
    },
    [
      anchorElementRef,
      anchorRectRef,
      applyOpenLayout,
      audioRef,
      chunk?.chunkId,
      extractLinguistNavigation,
      globalInputLanguage,
      isEnabled,
      jobId,
      loadingAnswer,
      maxQueryChars,
      requestCounterRef,
      resolvedJobOriginalLanguage,
      resolvedJobTranslationLanguage,
      setBubble,
      truncationSuffix,
    ],
  );

  const onSpeak = useCallback(() => {
    if (!bubble) {
      return;
    }
    const text = bubble.fullQuery.trim();
    if (!text || bubble.ttsStatus === 'loading') {
      return;
    }
    const requestId = requestCounterRef.current;
    setBubble((previous) => {
      if (!previous) {
        return previous;
      }
      return { ...previous, ttsStatus: 'loading' };
    });
    void speakText({ text, language: bubble.ttsLanguage })
      .then(() => {
        if (requestCounterRef.current !== requestId) {
          return;
        }
        setBubble((previous) => {
          if (!previous) {
            return previous;
          }
          return { ...previous, ttsStatus: 'ready' };
        });
      })
      .catch(() => {
        if (requestCounterRef.current !== requestId) {
          return;
        }
        setBubble((previous) => {
          if (!previous) {
            return previous;
          }
          return { ...previous, ttsStatus: 'error' };
        });
      });
  }, [bubble, requestCounterRef, setBubble]);

  const onSpeakSlow = useCallback(() => {
    if (!bubble) {
      return;
    }
    const text = bubble.fullQuery.trim();
    if (!text || bubble.ttsStatus === 'loading') {
      return;
    }
    const requestId = requestCounterRef.current;
    setBubble((previous) => {
      if (!previous) {
        return previous;
      }
      return { ...previous, ttsStatus: 'loading' };
    });
    void speakText({ text, language: bubble.ttsLanguage, playbackRate: 0.5 })
      .then(() => {
        if (requestCounterRef.current !== requestId) {
          return;
        }
        setBubble((previous) => {
          if (!previous) {
            return previous;
          }
          return { ...previous, ttsStatus: 'ready' };
        });
      })
      .catch(() => {
        if (requestCounterRef.current !== requestId) {
          return;
        }
        setBubble((previous) => {
          if (!previous) {
            return previous;
          }
          return { ...previous, ttsStatus: 'error' };
        });
      });
  }, [bubble, requestCounterRef, setBubble]);

  const resetBubbleState = useCallback(() => {
    requestCounterRef.current += 1;
    anchorRectRef.current = null;
    anchorElementRef.current = null;
    setBubble(null);
  }, [anchorElementRef, anchorRectRef, requestCounterRef, setBubble]);

  useEffect(() => {
    if (!isEnabled) {
      resetBubbleState();
    }
  }, [isEnabled, resetBubbleState]);

  return {
    openLinguistBubbleForRect,
    onSpeak,
    onSpeakSlow,
    resetBubbleState,
  };
}
