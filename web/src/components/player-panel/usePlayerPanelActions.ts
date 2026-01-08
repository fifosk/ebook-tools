import { useCallback } from 'react';
import type { LiveMediaChunk, LiveMediaItem } from '../../hooks/useLiveMedia';
import { formatBookmarkTime } from '../../hooks/usePlaybackBookmarks';
import type { MediaSearchResult } from '../../api/dtos';
import type { LibraryOpenInput, LibraryOpenRequest, MediaSelectionRequest } from '../../types/player';
import type { MediaCategory } from './constants';
import {
  deriveBaseIdFromReference,
  resolveChunkBaseId,
  resolveBaseIdFromResult,
} from './helpers';

type SearchCategory = Exclude<MediaCategory, 'audio'> | 'library';

type BookmarkPayload = {
  kind: 'sentence' | 'time';
  label: string;
  position: number | null;
  sentence: number | null;
  mediaType: MediaCategory;
  mediaId: string | null;
  baseId: string | null;
};

type UsePlayerPanelActionsArgs = {
  jobId: string;
  chunks: LiveMediaChunk[];
  canJumpToSentence: boolean;
  onInteractiveSentenceJump: (sentenceNumber: number) => void;
  onOpenLibraryItem?: (item: LibraryOpenInput) => void;
  setPendingSelection: (request: MediaSelectionRequest) => void;
  getMediaItem: (category: MediaCategory, id: string | null | undefined) => LiveMediaItem | null;
  deriveBaseId: (item: LiveMediaItem | null | undefined) => string | null;
  getPosition: (mediaId: string | null | undefined) => number;
  inlineAudioSelection: string | null;
  activeSentenceNumber: number | null;
  addBookmark: (bookmark: BookmarkPayload) => void;
  removeBookmark: (id: string) => void;
};

type UsePlayerPanelActionsResult = {
  handleSearchSelection: (result: MediaSearchResult, category: SearchCategory) => void;
  handleAddBookmark: () => void;
  handleJumpBookmark: (bookmark: {
    sentence?: number | null;
    position?: number | null;
    baseId?: string | null;
    mediaType?: MediaCategory | null;
  }) => void;
  handleRemoveBookmark: (bookmark: { id: string }) => void;
};

export function usePlayerPanelActions({
  jobId,
  chunks,
  canJumpToSentence,
  onInteractiveSentenceJump,
  onOpenLibraryItem,
  setPendingSelection,
  getMediaItem,
  deriveBaseId,
  getPosition,
  inlineAudioSelection,
  activeSentenceNumber,
  addBookmark,
  removeBookmark,
}: UsePlayerPanelActionsArgs): UsePlayerPanelActionsResult {
  const handleSearchSelection = useCallback(
    (result: MediaSearchResult, category: SearchCategory) => {
      if (
        category === 'text' &&
        canJumpToSentence &&
        result.job_id === jobId &&
        typeof result.start_sentence === 'number' &&
        Number.isFinite(result.start_sentence)
      ) {
        const startSentence = Math.trunc(result.start_sentence);
        const endSentence =
          typeof result.end_sentence === 'number' && Number.isFinite(result.end_sentence)
            ? Math.max(Math.trunc(result.end_sentence), startSentence)
            : startSentence;
        const ratio =
          typeof result.offset_ratio === 'number' && Number.isFinite(result.offset_ratio)
            ? Math.min(Math.max(result.offset_ratio, 0), 1)
            : null;
        const span = Math.max(endSentence - startSentence, 0);
        const targetSentence =
          ratio !== null ? Math.max(startSentence + Math.round(span * ratio), 1) : Math.max(startSentence, 1);
        onInteractiveSentenceJump(targetSentence);
        return;
      }

      const preferredCategory: MediaCategory | null = category === 'library' ? 'text' : category;
      let baseId = resolveBaseIdFromResult(result, preferredCategory);
      if (!baseId) {
        if (typeof result.chunk_id === 'string' && result.chunk_id.trim()) {
          baseId = deriveBaseIdFromReference(result.chunk_id) ?? result.chunk_id;
        } else if (typeof result.range_fragment === 'string' && result.range_fragment.trim()) {
          baseId = result.range_fragment.trim();
        } else if (typeof result.chunk_index === 'number' && Number.isFinite(result.chunk_index)) {
          const chunk = chunks[Math.trunc(result.chunk_index)];
          baseId = chunk ? resolveChunkBaseId(chunk) ?? null : null;
        }
      }
      const offsetRatio = typeof result.offset_ratio === 'number' ? result.offset_ratio : null;
      const approximateTime =
        typeof result.approximate_time_seconds === 'number' ? result.approximate_time_seconds : null;
      const selection: MediaSelectionRequest = {
        baseId,
        preferredType: preferredCategory,
        offsetRatio,
        approximateTime,
        token: Date.now(),
      };

      if (category === 'library') {
        if (!result.job_id) {
          return;
        }
        if (result.job_id === jobId) {
          setPendingSelection(selection);
          return;
        }
        const payload: LibraryOpenRequest = {
          kind: 'library-open',
          jobId: result.job_id,
          selection,
        };
        onOpenLibraryItem?.(payload);
        return;
      }

      if (result.job_id && result.job_id !== jobId) {
        return;
      }

      setPendingSelection(selection);
    },
    [canJumpToSentence, chunks, jobId, onInteractiveSentenceJump, onOpenLibraryItem, setPendingSelection],
  );

  const handleAddBookmark = useCallback(() => {
    if (!jobId) {
      return;
    }
    const sentence = activeSentenceNumber ?? null;
    const activeAudioUrl = inlineAudioSelection;
    const activeAudioPosition = activeAudioUrl ? getPosition(activeAudioUrl) : null;
    const audioItem = activeAudioUrl ? getMediaItem('audio', activeAudioUrl) : null;
    const baseId = audioItem ? deriveBaseId(audioItem) : null;
    const labelParts: string[] = [];
    if (sentence) {
      labelParts.push(`Sentence ${sentence}`);
    }
    if (typeof activeAudioPosition === 'number' && Number.isFinite(activeAudioPosition)) {
      labelParts.push(formatBookmarkTime(activeAudioPosition));
    }
    const label = labelParts.length > 0 ? labelParts.join(' · ') : 'Bookmark';
    addBookmark({
      kind: sentence ? 'sentence' : 'time',
      label,
      position: activeAudioPosition,
      sentence,
      mediaType: activeAudioUrl ? 'audio' : 'text',
      mediaId: activeAudioUrl ?? null,
      baseId,
    });
  }, [
    activeSentenceNumber,
    addBookmark,
    deriveBaseId,
    getMediaItem,
    getPosition,
    inlineAudioSelection,
    jobId,
  ]);

  const handleJumpBookmark = useCallback(
    (bookmark: { sentence?: number | null; position?: number | null; baseId?: string | null; mediaType?: MediaCategory | null }) => {
      if (bookmark.sentence && canJumpToSentence) {
        onInteractiveSentenceJump(bookmark.sentence);
        return;
      }
      const approximateTime =
        typeof bookmark.position === 'number' && Number.isFinite(bookmark.position)
          ? bookmark.position
          : null;
      setPendingSelection({
        baseId: bookmark.baseId ?? null,
        preferredType: bookmark.mediaType ?? null,
        offsetRatio: null,
        approximateTime,
        token: Date.now(),
      });
    },
    [canJumpToSentence, onInteractiveSentenceJump, setPendingSelection],
  );

  const handleRemoveBookmark = useCallback(
    (bookmark: { id: string }) => {
      removeBookmark(bookmark.id);
    },
    [removeBookmark],
  );

  return {
    handleSearchSelection,
    handleAddBookmark,
    handleJumpBookmark,
    handleRemoveBookmark,
  };
}
