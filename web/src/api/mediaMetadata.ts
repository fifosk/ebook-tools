/**
 * Typed interfaces for structured media metadata (v2).
 *
 * These mirror the backend Pydantic models in
 * `modules/services/metadata/structured_schema.py` and use camelCase
 * matching the API response format.
 */

// ---------------------------------------------------------------------------
// Nested sub-types
// ---------------------------------------------------------------------------

export interface SourceIds {
  isbn?: string;
  isbn13?: string;
  openlibrary?: string;
  openlibraryBook?: string;
  googleBooks?: string;
  tmdb?: number;
  imdb?: string;
  tvmazeShow?: number;
  tvmazeEpisode?: number;
  wikidata?: string;
  youtubeVideo?: string;
  youtubeChannel?: string;
}

export interface SeriesInfo {
  seriesTitle?: string;
  season?: number;
  episode?: number;
  episodeTitle?: string;
  seriesId?: string;
  episodeId?: string;
}

export interface YouTubeInfo {
  videoId?: string;
  channelId?: string;
  channelName?: string;
  uploadDate?: string;
}

// ---------------------------------------------------------------------------
// Main sections
// ---------------------------------------------------------------------------

export interface SourceMetadata {
  title?: string;
  author?: string;
  year?: number;
  summary?: string;
  genres?: string[];
  language?: string;
  isbn?: string;
  isbn13?: string;
  series?: SeriesInfo | null;
  youtube?: YouTubeInfo | null;
  runtimeMinutes?: number;
  rating?: number;
  votes?: number;
}

export interface LanguageConfig {
  inputLanguage?: string;
  originalLanguage?: string;
  targetLanguage?: string;
  targetLanguages?: string[];
  translationProvider?: string;
  translationModel?: string;
  translationModelRequested?: string;
  transliterationMode?: string;
  transliterationModel?: string;
  transliterationModule?: string;
}

export interface ContentStructure {
  totalSentences?: number;
  contentIndexPath?: string;
  contentIndexUrl?: string;
  contentIndexSummary?: {
    chapterCount?: number;
    alignment?: string;
  };
}

export interface CoverAssets {
  coverFile?: string;
  coverUrl?: string;
  bookCoverUrl?: string;
  jobCoverAsset?: string;
  jobCoverAssetUrl?: string;
}

export interface EnrichmentProvenance {
  source?: string;
  confidence?: string;
  queriedAt?: string;
  sourceIds?: SourceIds;
  lookupResult?: Record<string, unknown>;
}

// ---------------------------------------------------------------------------
// Top-level container
// ---------------------------------------------------------------------------

export type MediaType =
  | 'book'
  | 'movie'
  | 'tv_series'
  | 'tv_episode'
  | 'youtube_video';

export interface StructuredMediaMetadata {
  metadataVersion: number;
  mediaType: MediaType;
  source: SourceMetadata;
  languageConfig: LanguageConfig;
  contentStructure: ContentStructure;
  coverAssets: CoverAssets;
  enrichment: EnrichmentProvenance;
  jobLabel?: string;
  extras?: Record<string, unknown>;
}
