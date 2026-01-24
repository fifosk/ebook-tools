import { useId, type ChangeEvent, type KeyboardEvent as ReactKeyboardEvent } from 'react';
import type { ReactNode } from 'react';
import type { ChapterNavigationEntry, SentenceJumpProps, ChapterJumpProps } from './types';

interface SecondaryNavigationProps extends SentenceJumpProps, ChapterJumpProps {
  searchPanel?: ReactNode;
  searchInSecondary?: boolean;
}

/**
 * Secondary navigation row with chapter jump, search, and sentence jump controls.
 */
export function SecondaryNavigation({
  searchPanel,
  searchInSecondary = false,
  showSentenceJump = false,
  sentenceJumpValue = '',
  sentenceJumpMin = null,
  sentenceJumpMax = null,
  sentenceJumpError = null,
  sentenceJumpDisabled = false,
  sentenceJumpInputId,
  sentenceJumpListId,
  sentenceJumpPlaceholder,
  onSentenceJumpChange,
  onSentenceJumpSubmit,
  showChapterJump = false,
  chapters = [],
  activeChapterId = null,
  onChapterJump,
  jobStartSentence = null,
  totalSentencesInBook = null,
}: SecondaryNavigationProps) {
  const jumpInputFallbackId = useId();
  const chapterSelectId = useId();
  const jumpInputId = sentenceJumpInputId ?? jumpInputFallbackId;
  const jumpRangeId = `${jumpInputId}-range`;
  const jumpErrorId = `${jumpInputId}-error`;

  const describedBy =
    sentenceJumpError && showSentenceJump
      ? jumpErrorId
      : showSentenceJump && sentenceJumpMin !== null && sentenceJumpMax !== null
        ? jumpRangeId
        : undefined;

  const jobRangeStart = typeof jobStartSentence === 'number' ? jobStartSentence : null;
  const jobRangeEnd = typeof totalSentencesInBook === 'number' ? totalSentencesInBook : null;

  const isChapterInJobRange = (chapter: ChapterNavigationEntry) => {
    if (jobRangeStart === null && jobRangeEnd === null) {
      return true;
    }
    const start = chapter.startSentence;
    const end = typeof chapter.endSentence === 'number' ? chapter.endSentence : chapter.startSentence;
    if (jobRangeStart !== null && end < jobRangeStart) {
      return false;
    }
    if (jobRangeEnd !== null && start > jobRangeEnd) {
      return false;
    }
    return true;
  };

  const resolvedChapters = Array.isArray(chapters) ? chapters : [];
  const scopedChapters = resolvedChapters.filter(isChapterInJobRange);
  const shouldShowChapterJump = showChapterJump && scopedChapters.length > 0;
  const resolvedActiveChapterId =
    activeChapterId && scopedChapters.some((chapter) => chapter.id === activeChapterId)
      ? activeChapterId
      : null;

  const handleSentenceInputChange = (event: ChangeEvent<HTMLInputElement>) => {
    onSentenceJumpChange?.(event.target.value);
  };

  const handleSentenceInputKeyDown = (event: ReactKeyboardEvent<HTMLInputElement>) => {
    if (event.key === 'Enter') {
      event.preventDefault();
      onSentenceJumpSubmit?.();
    }
  };

  const handleChapterSelect = (event: ChangeEvent<HTMLSelectElement>) => {
    const value = event.target.value;
    if (!value) {
      return;
    }
    onChapterJump?.(value);
  };

  if (!searchInSecondary && !showSentenceJump && !shouldShowChapterJump) {
    return null;
  }

  return (
    <div className="player-panel__navigation-secondary">
      <div className="player-panel__navigation-secondary-group">
        {shouldShowChapterJump ? (
          <div className="player-panel__chapter-jump" data-testid="player-panel-chapter-jump">
            <span className="player-panel__chapter-jump-label" aria-hidden="true">
              Chapter
            </span>
            <select
              id={chapterSelectId}
              className="player-panel__chapter-jump-select"
              value={resolvedActiveChapterId ?? ''}
              onChange={handleChapterSelect}
              aria-label="Jump to chapter"
              disabled={!onChapterJump}
              title="Jump to chapter"
            >
              <option value="" disabled>
                Select
              </option>
              {scopedChapters.map((chapter, index) => {
                const label = chapter.title?.trim() || `Chapter ${index + 1}`;
                const range =
                  typeof chapter.endSentence === 'number'
                    ? `${chapter.startSentence}-${chapter.endSentence}`
                    : `${chapter.startSentence}+`;
                return (
                  <option
                    key={chapter.id}
                    value={chapter.id}
                    title={`Sentences ${range}`}
                  >
                    {label}
                  </option>
                );
              })}
            </select>
          </div>
        ) : null}

        {searchInSecondary ? (
          <div className="player-panel__navigation-search">{searchPanel}</div>
        ) : null}

        {showSentenceJump ? (
          <div className="player-panel__sentence-jump" data-testid="player-panel-sentence-jump">
            {sentenceJumpError ? (
              <span id={jumpErrorId} className="visually-hidden">
                {sentenceJumpError}
              </span>
            ) : sentenceJumpMin !== null && sentenceJumpMax !== null ? (
              <span id={jumpRangeId} className="visually-hidden">
                Range {sentenceJumpMin}–{sentenceJumpMax}
              </span>
            ) : null}
            <span className="player-panel__sentence-jump-label" aria-hidden="true">
              Jump
            </span>
            <input
              id={jumpInputId}
              className="player-panel__sentence-jump-input"
              type="number"
              inputMode="numeric"
              min={sentenceJumpMin ?? undefined}
              max={sentenceJumpMax ?? undefined}
              step={1}
              list={sentenceJumpListId}
              value={sentenceJumpValue}
              onChange={handleSentenceInputChange}
              onKeyDown={handleSentenceInputKeyDown}
              placeholder="…"
              aria-label="Jump to sentence"
              aria-describedby={describedBy}
              aria-invalid={sentenceJumpError ? 'true' : undefined}
              disabled={sentenceJumpDisabled}
              title={
                sentenceJumpError ??
                (sentenceJumpPlaceholder ? `Jump (range ${sentenceJumpPlaceholder})` : 'Jump to sentence')
              }
            />
            <button
              type="button"
              className="player-panel__sentence-jump-button"
              onClick={onSentenceJumpSubmit}
              disabled={sentenceJumpDisabled || !onSentenceJumpSubmit}
              title="Jump to sentence"
            >
              Go
            </button>
          </div>
        ) : null}
      </div>
    </div>
  );
}

export default SecondaryNavigation;
