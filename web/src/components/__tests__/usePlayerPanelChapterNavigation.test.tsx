import { act, renderHook } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { usePlayerPanelChapterNavigation } from '../player-panel/usePlayerPanelChapterNavigation';
import type { ChapterNavigationEntry } from '../player-panel/navigation';

const CHAPTERS: ChapterNavigationEntry[] = [
  { id: 'intro', title: 'Intro', startSentence: 1, endSentence: 10 },
  { id: 'middle', title: 'Middle', startSentence: 11, endSentence: 20 },
  { id: 'finale', title: 'Finale', startSentence: 21 },
];

describe('usePlayerPanelChapterNavigation', () => {
  it('derives the active chapter from the current sentence', () => {
    const onInteractiveSentenceJump = vi.fn();
    const { result, rerender } = renderHook(
      ({ activeSentenceNumber }) =>
        usePlayerPanelChapterNavigation({
          activeSentenceNumber,
          chapterEntries: CHAPTERS,
          onInteractiveSentenceJump,
        }),
      { initialProps: { activeSentenceNumber: 15 as number | null } },
    );

    expect(result.current.activeChapterId).toBe('middle');

    rerender({ activeSentenceNumber: 99 });
    expect(result.current.activeChapterId).toBe('finale');

    rerender({ activeSentenceNumber: null });
    expect(result.current.activeChapterId).toBeNull();
  });

  it('jumps to the selected chapter start and ignores missing chapters', () => {
    const onInteractiveSentenceJump = vi.fn();
    const { result } = renderHook(() =>
      usePlayerPanelChapterNavigation({
        activeSentenceNumber: 15,
        chapterEntries: CHAPTERS,
        onInteractiveSentenceJump,
      }),
    );

    act(() => {
      result.current.handleChapterJump('finale');
      result.current.handleChapterJump('missing');
    });

    expect(onInteractiveSentenceJump).toHaveBeenCalledTimes(1);
    expect(onInteractiveSentenceJump).toHaveBeenCalledWith(21);
  });
});
