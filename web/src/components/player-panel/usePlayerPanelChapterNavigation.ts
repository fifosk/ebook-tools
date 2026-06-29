import { useCallback, useMemo } from 'react';
import type { ChapterNavigationEntry } from './navigation';
import {
  resolveActiveChapterId,
  resolveChapterStartSentence,
} from './utils';

type UsePlayerPanelChapterNavigationOptions = {
  activeSentenceNumber: number | null;
  chapterEntries: ChapterNavigationEntry[];
  onInteractiveSentenceJump: (sentenceNumber: number) => void;
};

type UsePlayerPanelChapterNavigationResult = {
  activeChapterId: string | null;
  handleChapterJump: (chapterId: string) => void;
};

export function usePlayerPanelChapterNavigation({
  activeSentenceNumber,
  chapterEntries,
  onInteractiveSentenceJump,
}: UsePlayerPanelChapterNavigationOptions): UsePlayerPanelChapterNavigationResult {
  const activeChapterId = useMemo(
    () => resolveActiveChapterId(activeSentenceNumber, chapterEntries),
    [activeSentenceNumber, chapterEntries],
  );

  const handleChapterJump = useCallback(
    (chapterId: string) => {
      const startSentence = resolveChapterStartSentence(chapterEntries, chapterId);
      if (startSentence === null) {
        return;
      }
      onInteractiveSentenceJump(startSentence);
    },
    [chapterEntries, onInteractiveSentenceJump],
  );

  return {
    activeChapterId,
    handleChapterJump,
  };
}
