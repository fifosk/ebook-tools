import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { fetchBookContentIndex } from '../../api/client';
import { extractContentIndexTotalSentences, normaliseContentIndexChapters } from '../../utils/contentIndex';
import { formatDurationLabel } from '../../utils/timeFormatters';
import { parseEndSentenceInput } from './bookNarrationFormUtils';
import { ESTIMATED_AUDIO_SECONDS_PER_SENTENCE } from './bookNarrationFormDefaults';
import type { BookNarrationChapterOption } from './BookNarrationLanguageSection';

type ChapterSelection = {
  startIndex: number;
  endIndex: number;
  startSentence: number;
  endSentence: number;
  count: number;
};

type UseBookNarrationChaptersOptions = {
  inputFile: string;
  startSentence: number;
  endSentence: string;
  isGeneratedSource: boolean;
  implicitEndOffsetThreshold: number | null;
  normalizedInputPath: string | null;
};

export function useBookNarrationChapters({
  inputFile,
  startSentence,
  endSentence,
  isGeneratedSource,
  implicitEndOffsetThreshold,
  normalizedInputPath,
}: UseBookNarrationChaptersOptions) {
  const [chapterOptions, setChapterOptions] = useState<BookNarrationChapterOption[]>([]);
  const [contentIndexTotalSentences, setContentIndexTotalSentences] = useState<number | null>(null);
  const [chaptersLoading, setChaptersLoading] = useState<boolean>(false);
  const [chaptersError, setChaptersError] = useState<string | null>(null);
  const [chapterSelectionMode, setChapterSelectionMode] = useState<'range' | 'chapters'>('range');
  const [chapterRangeSelection, setChapterRangeSelection] = useState<{ startIndex: number; endIndex: number } | null>(
    null,
  );
  const chapterLookupIdRef = useRef<number>(0);

  const chapterIndexLookup = useMemo(() => {
    const map = new Map<string, number>();
    chapterOptions.forEach((chapter, index) => {
      map.set(chapter.id, index);
    });
    return map;
  }, [chapterOptions]);

  const selectedChapterIds = useMemo(() => {
    if (!chapterRangeSelection) {
      return [];
    }
    const { startIndex, endIndex } = chapterRangeSelection;
    if (startIndex < 0 || endIndex < startIndex || startIndex >= chapterOptions.length) {
      return [];
    }
    return chapterOptions.slice(startIndex, endIndex + 1).map((chapter) => chapter.id);
  }, [chapterOptions, chapterRangeSelection]);

  const chapterSelection = useMemo<ChapterSelection | null>(() => {
    if (!chapterRangeSelection) {
      return null;
    }
    const { startIndex, endIndex } = chapterRangeSelection;
    const startChapter = chapterOptions[startIndex];
    const endChapter = chapterOptions[endIndex];
    if (!startChapter || !endChapter) {
      return null;
    }
    const startSentenceValue = startChapter.startSentence;
    const endSentenceValue =
      typeof endChapter.endSentence === 'number' ? endChapter.endSentence : endChapter.startSentence;
    return {
      startIndex,
      endIndex,
      startSentence: startSentenceValue,
      endSentence: endSentenceValue,
      count: Math.max(1, endIndex - startIndex + 1),
    };
  }, [chapterOptions, chapterRangeSelection]);

  const chapterSelectionSummary = useMemo(() => {
    if (chapterSelectionMode !== 'chapters') {
      return '';
    }
    if (chaptersLoading || chaptersError || chapterOptions.length === 0) {
      return '';
    }
    if (!chapterSelection) {
      return 'Select consecutive chapters to set the processing window.';
    }
    const startLabel = chapterOptions[chapterSelection.startIndex]?.title ?? 'Chapter';
    const endLabel = chapterOptions[chapterSelection.endIndex]?.title ?? 'Chapter';
    const chapterLabel =
      chapterSelection.count === 1 ? startLabel : `${startLabel} – ${endLabel}`;
    return `${chapterLabel} • sentences ${chapterSelection.startSentence}-${chapterSelection.endSentence}`;
  }, [
    chapterOptions,
    chapterSelection,
    chapterSelectionMode,
    chaptersError,
    chaptersLoading,
  ]);

  const totalSentencesFromIndex = useMemo(() => {
    if (contentIndexTotalSentences && contentIndexTotalSentences > 0) {
      return contentIndexTotalSentences;
    }
    if (chapterOptions.length === 0) {
      return null;
    }
    let maxSentence = 0;
    chapterOptions.forEach((chapter) => {
      const end = typeof chapter.endSentence === 'number' ? chapter.endSentence : chapter.startSentence;
      if (end > maxSentence) {
        maxSentence = end;
      }
    });
    return maxSentence > 0 ? maxSentence : null;
  }, [chapterOptions, contentIndexTotalSentences]);

  const estimatedSentenceRange = useMemo(() => {
    if (chapterSelectionMode === 'chapters') {
      if (!chapterSelection) {
        return null;
      }
      return {
        start: chapterSelection.startSentence,
        end: chapterSelection.endSentence,
      };
    }
    const start = Math.max(1, Math.trunc(Number(startSentence)));
    if (!Number.isFinite(start)) {
      return null;
    }
    let end: number | null = null;
    try {
      end = parseEndSentenceInput(endSentence, start, implicitEndOffsetThreshold);
    } catch {
      end = null;
    }
    if (end === null) {
      end = totalSentencesFromIndex;
    }
    if (end === null || !Number.isFinite(end)) {
      return null;
    }
    if (end < start) {
      return null;
    }
    return { start, end };
  }, [
    chapterSelection,
    chapterSelectionMode,
    endSentence,
    implicitEndOffsetThreshold,
    startSentence,
    totalSentencesFromIndex,
  ]);

  const estimatedSentenceCount = useMemo(() => {
    if (!estimatedSentenceRange) {
      return null;
    }
    const count = Math.max(0, estimatedSentenceRange.end - estimatedSentenceRange.start + 1);
    return count > 0 ? count : null;
  }, [estimatedSentenceRange]);

  const estimatedAudioDurationLabel = useMemo(() => {
    if (!estimatedSentenceCount) {
      return null;
    }
    const estimatedSeconds = estimatedSentenceCount * ESTIMATED_AUDIO_SECONDS_PER_SENTENCE;
    if (!Number.isFinite(estimatedSeconds) || estimatedSeconds <= 0) {
      return null;
    }
    const sentenceLabel = estimatedSentenceCount === 1 ? 'sentence' : 'sentences';
    return `Estimated audio duration: ~${formatDurationLabel(estimatedSeconds)} (${estimatedSentenceCount} ${sentenceLabel}, ${ESTIMATED_AUDIO_SECONDS_PER_SENTENCE.toFixed(
      1,
    )}s/sentence)`;
  }, [estimatedSentenceCount]);

  const chaptersDisabled = isGeneratedSource || !inputFile.trim();

  useEffect(() => {
    setChapterRangeSelection(null);
  }, [normalizedInputPath]);

  useEffect(() => {
    const trimmedInput = inputFile.trim();
    if (isGeneratedSource || !trimmedInput) {
      chapterLookupIdRef.current += 1;
      setChapterOptions([]);
      setContentIndexTotalSentences(null);
      setChaptersLoading(false);
      setChaptersError(null);
      return;
    }
    const requestId = chapterLookupIdRef.current + 1;
    chapterLookupIdRef.current = requestId;
    setChaptersLoading(true);
    setChaptersError(null);
    void (async () => {
      try {
        const payload = await fetchBookContentIndex(trimmedInput);
        if (chapterLookupIdRef.current !== requestId) {
          return;
        }
        const chapters = normaliseContentIndexChapters(payload.content_index);
        const totalSentences = extractContentIndexTotalSentences(payload.content_index);
        setChapterOptions(chapters);
        setContentIndexTotalSentences(totalSentences);
      } catch (error) {
        if (chapterLookupIdRef.current !== requestId) {
          return;
        }
        const message = error instanceof Error ? error.message : 'Unable to load chapter data.';
        setChaptersError(message);
        setChapterOptions([]);
        setContentIndexTotalSentences(null);
      } finally {
        if (chapterLookupIdRef.current === requestId) {
          setChaptersLoading(false);
        }
      }
    })();
  }, [inputFile, isGeneratedSource]);

  useEffect(() => {
    if (chaptersDisabled && chapterSelectionMode === 'chapters') {
      setChapterSelectionMode('range');
    }
  }, [chaptersDisabled, chapterSelectionMode]);

  const handleChapterModeChange = useCallback((mode: 'range' | 'chapters') => {
    setChapterSelectionMode(mode);
  }, []);

  const handleChapterToggle = useCallback(
    (chapterId: string) => {
      const index = chapterIndexLookup.get(chapterId);
      if (index === undefined) {
        return;
      }
      setChapterRangeSelection((previous) => {
        if (!previous) {
          return { startIndex: index, endIndex: index };
        }
        const { startIndex, endIndex } = previous;
        if (index < startIndex) {
          return { startIndex: index, endIndex };
        }
        if (index > endIndex) {
          return { startIndex, endIndex: index };
        }
        if (startIndex === endIndex && index === startIndex) {
          return null;
        }
        if (index === startIndex) {
          return { startIndex: startIndex + 1, endIndex };
        }
        if (index === endIndex) {
          return { startIndex, endIndex: endIndex - 1 };
        }
        return { startIndex: index, endIndex: index };
      });
    },
    [chapterIndexLookup],
  );

  const handleChapterClear = useCallback(() => {
    setChapterRangeSelection(null);
  }, []);

  const displayStartSentence =
    chapterSelectionMode === 'chapters' && chapterSelection
      ? chapterSelection.startSentence
      : startSentence;
  const displayEndSentence =
    chapterSelectionMode === 'chapters' && chapterSelection
      ? String(chapterSelection.endSentence)
      : endSentence;

  return {
    chapterSelectionMode,
    chapterOptions,
    selectedChapterIds,
    chapterSelection,
    chapterSelectionSummary,
    chaptersLoading,
    chaptersError,
    chaptersDisabled,
    estimatedAudioDurationLabel,
    handleChapterModeChange,
    handleChapterToggle,
    handleChapterClear,
    displayStartSentence,
    displayEndSentence,
  };
}
