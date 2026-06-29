import type { ChapterNavigationEntry } from './navigation';

export function resolveActiveChapterId(
  activeSentenceNumber: number | null,
  chapterEntries: ChapterNavigationEntry[],
): string | null {
  if (!activeSentenceNumber || chapterEntries.length === 0) {
    return null;
  }

  const target = chapterEntries.find((chapter) => {
    const end = typeof chapter.endSentence === 'number' ? chapter.endSentence : Number.POSITIVE_INFINITY;
    return activeSentenceNumber >= chapter.startSentence && activeSentenceNumber <= end;
  });

  return target?.id ?? null;
}

export function resolveChapterStartSentence(
  chapterEntries: ChapterNavigationEntry[],
  chapterId: string,
): number | null {
  const target = chapterEntries.find((chapter) => chapter.id === chapterId);
  return target?.startSentence ?? null;
}
