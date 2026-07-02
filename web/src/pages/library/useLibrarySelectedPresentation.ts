import { useMemo } from 'react';
import type { LibraryItem } from '../../api/dtos';
import { extractJobType, getJobTypeGlyph, isTvSeriesMetadata, type JobTypeGlyph } from '../../utils/jobGlyphs';
import { extractLibraryBookMetadata, resolveLibraryCoverUrl } from '../../utils/libraryMetadata';
import {
  extractTvMediaMetadata,
  extractYoutubeVideoMetadata,
  resolveAuthor,
  resolveGenre,
  resolveItemType,
  resolveTitle,
  resolveTvImage,
  resolveYoutubeThumbnail,
  type LibraryItemType,
} from './libraryPageMetadata';

export type LibrarySelectedPresentation = {
  itemType: LibraryItemType;
  title: string;
  author: string;
  genre: string;
  jobType: string | null;
  jobGlyph: JobTypeGlyph;
  bookMetadata: Record<string, unknown> | null;
  tvMetadata: Record<string, unknown> | null;
  youtubeMetadata: Record<string, unknown> | null;
  coverUrl: string | null;
  displayedCoverUrl: string | null;
  tvPoster: { src: string; link: string } | null;
  tvStill: { src: string; link: string } | null;
  youtubeThumbnail: { src: string; link: string } | null;
};

export type UseLibrarySelectedPresentationInput = {
  selectedItem: LibraryItem | null;
  isEditing: boolean;
  previewCoverUrl: string | null;
};

export function useLibrarySelectedPresentation({
  selectedItem,
  isEditing,
  previewCoverUrl,
}: UseLibrarySelectedPresentationInput): LibrarySelectedPresentation {
  return useMemo(() => {
    const itemType = resolveItemType(selectedItem);
    const title = resolveTitle(selectedItem);
    const author = resolveAuthor(selectedItem);
    const genre = resolveGenre(selectedItem);
    const jobType = extractJobType(selectedItem?.metadata) ?? null;
    const tvMetadata = extractTvMediaMetadata(selectedItem);
    const youtubeMetadata = extractYoutubeVideoMetadata(tvMetadata);
    const jobGlyph = getJobTypeGlyph(jobType, { isTvSeries: isTvSeriesMetadata(tvMetadata) });
    const bookMetadata = extractLibraryBookMetadata(selectedItem);
    const coverUrl = selectedItem ? resolveLibraryCoverUrl(selectedItem, bookMetadata) : null;
    const tvPoster = selectedItem ? resolveTvImage(selectedItem.jobId, tvMetadata, 'show') : null;
    const tvStill = selectedItem ? resolveTvImage(selectedItem.jobId, tvMetadata, 'episode') : null;
    const youtubeThumbnail = selectedItem
      ? resolveYoutubeThumbnail(selectedItem.jobId, youtubeMetadata)
      : null;
    const displayedCoverUrl = isEditing && previewCoverUrl ? previewCoverUrl : coverUrl;

    return {
      itemType,
      title,
      author,
      genre,
      jobType,
      jobGlyph,
      bookMetadata,
      tvMetadata,
      youtubeMetadata,
      coverUrl,
      displayedCoverUrl,
      tvPoster,
      tvStill,
      youtubeThumbnail,
    };
  }, [isEditing, previewCoverUrl, selectedItem]);
}
