import { useMemo } from 'react';
import type { LiveMediaChunk } from '../../hooks/useLiveMedia';
import type {
  TextPlayerSentence,
  TextPlayerVariantDisplay,
} from '../../text-player/TextPlayer';
import type { ParagraphFragment, SentenceFragment } from './types';
import { tokenizeSentenceText } from './utils';

type TimelineDisplay = {
  sentences: TextPlayerSentence[];
  activeIndex: number;
  effectiveTime: number;
};

type UseTextPlayerSentencesArgs = {
  paragraphs: ParagraphFragment[];
  timelineDisplay: TimelineDisplay | null;
  chunk: LiveMediaChunk | null;
  activeSentenceIndex: number;
  cueVisibility: {
    original: boolean;
    transliteration: boolean;
    translation: boolean;
  };
};

export function useTextPlayerSentences({
  paragraphs,
  timelineDisplay,
  chunk,
  activeSentenceIndex,
  cueVisibility,
}: UseTextPlayerSentencesArgs): {
  rawSentences: SentenceFragment[];
  textPlayerSentences: TextPlayerSentence[] | null;
  sentenceWeightSummary: { cumulative: number[]; total: number };
} {
  const rawSentences = useMemo(
    () =>
      paragraphs
        .map((paragraph) => paragraph.sentences)
        .flat()
        .sort((a, b) => a.index - b.index),
    [paragraphs],
  );

  const textPlayerSentences = useMemo(() => {
    const forceActive = (sentence: TextPlayerSentence | undefined | null): TextPlayerSentence[] | null => {
      if (!sentence) {
        return null;
      }
      return [
        {
          ...sentence,
          state: 'active',
        },
      ];
    };

    if (timelineDisplay?.sentences && timelineDisplay.sentences.length > 0) {
      const active =
        timelineDisplay.sentences.find((entry) => entry.index === activeSentenceIndex) ??
        timelineDisplay.sentences.find((entry) => entry.state === 'active') ??
        timelineDisplay.sentences[0];
      return forceActive(active);
    }

    if (chunk?.sentences && chunk.sentences.length > 0) {
      const fallbackFromChunk: TextPlayerSentence[] = chunk.sentences.map((metadata, index) => {
        const originalTokens = tokenizeSentenceText(metadata.original?.text ?? null);
        const transliterationTokens = tokenizeSentenceText(metadata.transliteration?.text ?? null);
        const translationTokens = tokenizeSentenceText(metadata.translation?.text ?? null);

        const variants: TextPlayerVariantDisplay[] = [];
        if (cueVisibility.original && originalTokens.length > 0) {
          variants.push({
            label: 'Original',
            tokens: originalTokens,
            revealedCount: originalTokens.length,
            currentIndex: originalTokens.length - 1,
            baseClass: 'original',
          });
        }
        if (cueVisibility.transliteration && transliterationTokens.length > 0) {
          variants.push({
            label: 'Transliteration',
            tokens: transliterationTokens,
            revealedCount: transliterationTokens.length,
            currentIndex: transliterationTokens.length - 1,
            baseClass: 'translit',
          });
        }
        if (cueVisibility.translation && translationTokens.length > 0) {
          variants.push({
            label: 'Translation',
            tokens: translationTokens,
            revealedCount: translationTokens.length,
            currentIndex: translationTokens.length - 1,
            baseClass: 'translation',
          });
        }

        if (variants.length === 0) {
          return null;
        }

        return {
          id: `sentence-${index}`,
          index,
          sentenceNumber: metadata.sentence_number ?? index + 1,
          state: index === activeSentenceIndex ? 'active' : 'future',
          variants,
        } as TextPlayerSentence;
      }).filter((value): value is TextPlayerSentence => value !== null);

      if (fallbackFromChunk.length === 0) {
        return null;
      }
      const active =
        fallbackFromChunk.find((sentence) => sentence.index === activeSentenceIndex) ??
        fallbackFromChunk[0];
      return forceActive(active);
    }

    if (rawSentences.length === 0) {
      return null;
    }

    const fallbackFromContent: TextPlayerSentence[] = rawSentences
      .map((sentence, position) => {
        const originalTokens = tokenizeSentenceText(sentence.text);
        const translationTokens = tokenizeSentenceText(sentence.translation);
        const transliterationTokens = tokenizeSentenceText(sentence.transliteration);

        const variants: TextPlayerVariantDisplay[] = [];
        if (cueVisibility.original && originalTokens.length > 0) {
          variants.push({
            label: 'Original',
            tokens: originalTokens,
            revealedCount: originalTokens.length,
            currentIndex: originalTokens.length - 1,
            baseClass: 'original',
          });
        }
        if (cueVisibility.transliteration && transliterationTokens.length > 0) {
          variants.push({
            label: 'Transliteration',
            tokens: transliterationTokens,
            revealedCount: transliterationTokens.length,
            currentIndex: transliterationTokens.length - 1,
            baseClass: 'translit',
          });
        }
        if (cueVisibility.translation && translationTokens.length > 0) {
          variants.push({
            label: 'Translation',
            tokens: translationTokens,
            revealedCount: translationTokens.length,
            currentIndex: translationTokens.length - 1,
            baseClass: 'translation',
          });
        }

        if (variants.length === 0) {
          return null;
        }

        return {
          id: `sentence-${sentence.index}`,
          index: sentence.index,
          sentenceNumber: sentence.index + 1,
          state: position === 0 ? 'active' : 'future',
          variants,
        } as TextPlayerSentence;
      })
      .filter((value): value is TextPlayerSentence => value !== null);

    if (fallbackFromContent.length === 0) {
      return null;
    }
    const active =
      fallbackFromContent.find((sentence) => sentence.index === activeSentenceIndex) ??
      fallbackFromContent[0];
    return forceActive(active);
  }, [activeSentenceIndex, chunk?.sentences, cueVisibility, rawSentences, timelineDisplay?.sentences]);

  const sentenceWeightSummary = useMemo(() => {
    let cumulativeTotal = 0;
    const cumulative: number[] = [];
    rawSentences.forEach((sentence) => {
      cumulativeTotal += sentence.weight;
      cumulative.push(cumulativeTotal);
    });
    return {
      cumulative,
      total: cumulativeTotal,
    };
  }, [rawSentences]);

  return { rawSentences, textPlayerSentences, sentenceWeightSummary };
}
