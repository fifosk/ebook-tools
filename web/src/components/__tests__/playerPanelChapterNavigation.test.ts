import { describe, expect, it } from 'vitest';
import {
  resolveActiveChapterId,
  resolveChapterStartSentence,
} from '../player-panel/chapterNavigation';

describe('player-panel chapter navigation helpers', () => {
  it('resolves the active chapter for bounded and open-ended ranges', () => {
    const chapters = [
      { id: 'intro', title: 'Intro', startSentence: 1, endSentence: 10 },
      { id: 'middle', title: 'Middle', startSentence: 11, endSentence: 20 },
      { id: 'finale', title: 'Finale', startSentence: 21 },
    ];

    expect(resolveActiveChapterId(null, chapters)).toBeNull();
    expect(resolveActiveChapterId(0, chapters)).toBeNull();
    expect(resolveActiveChapterId(10, chapters)).toBe('intro');
    expect(resolveActiveChapterId(15, chapters)).toBe('middle');
    expect(resolveActiveChapterId(99, chapters)).toBe('finale');
  });

  it('resolves chapter jump targets by id', () => {
    const chapters = [
      { id: 'intro', title: 'Intro', startSentence: 1, endSentence: 10 },
      { id: 'finale', title: 'Finale', startSentence: 21 },
    ];

    expect(resolveChapterStartSentence(chapters, 'finale')).toBe(21);
    expect(resolveChapterStartSentence(chapters, 'missing')).toBeNull();
  });
});
