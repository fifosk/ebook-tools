/**
 * Client-side normalization: convert a flat media_metadata dict to
 * StructuredMediaMetadata when the API returns an old-format response
 * (i.e., `structured_metadata` is absent).
 *
 * This mirrors the Python `structure_from_flat()` logic so the frontend
 * can always work with the structured interface regardless of backend version.
 */

import type {
  CoverAssets,
  ContentStructure,
  EnrichmentProvenance,
  LanguageConfig,
  MediaType,
  SeriesInfo,
  SourceIds,
  SourceMetadata,
  StructuredMediaMetadata,
  YouTubeInfo,
} from '../../api/mediaMetadata';

type Flat = Record<string, unknown>;

function str(v: unknown): string | undefined {
  return typeof v === 'string' && v ? v : undefined;
}

function num(v: unknown): number | undefined {
  if (typeof v === 'number') return v;
  if (typeof v === 'string') {
    const n = Number(v);
    return Number.isFinite(n) ? n : undefined;
  }
  return undefined;
}

function strArr(v: unknown): string[] | undefined {
  if (Array.isArray(v)) return v.filter((x): x is string => typeof x === 'string');
  return undefined;
}

function detectMediaType(flat: Flat): MediaType {
  const jobType = str(flat.job_type ?? flat.type)?.toLowerCase();
  if (jobType === 'youtube' || jobType === 'youtube_video') return 'youtube_video';
  if (jobType === 'movie' || jobType === 'film') return 'movie';
  if (jobType === 'tv_series' || jobType === 'tv_show' || jobType === 'series') return 'tv_series';
  if (jobType === 'tv_episode' || jobType === 'episode') return 'tv_episode';
  if (flat.youtube_video_id || flat.youtube_url) return 'youtube_video';
  if (flat.series_name && (flat.season || flat.episode)) return 'tv_episode';
  if (flat.series_name) return 'tv_series';
  if (flat.isbn || flat.isbn_13) return 'book';
  if (flat.imdb_id || flat.tmdb_id) return 'movie';
  return 'book';
}

function extractSeriesInfo(flat: Flat): SeriesInfo | null {
  const seriesTitle = str(flat.series_name ?? flat.series_title);
  if (!seriesTitle) return null;
  return {
    seriesTitle,
    season: num(flat.season),
    episode: num(flat.episode),
    episodeTitle: str(flat.episode_title),
    seriesId: str(flat.series_id),
    episodeId: str(flat.episode_id),
  };
}

function extractYouTubeInfo(flat: Flat): YouTubeInfo | null {
  const videoId = str(flat.youtube_video_id);
  if (!videoId) return null;
  return {
    videoId,
    channelId: str(flat.youtube_channel_id),
    channelName: str(flat.channel_name ?? flat.youtube_channel_name),
    uploadDate: str(flat.upload_date ?? flat.youtube_upload_date),
  };
}

function extractSourceIds(flat: Flat): SourceIds | undefined {
  const ids: SourceIds = {};
  let hasAny = false;

  const set = (key: keyof SourceIds, v: unknown) => {
    const sv = typeof v === 'number' ? v : str(v);
    if (sv != null) {
      (ids as Record<string, unknown>)[key] = sv;
      hasAny = true;
    }
  };

  set('isbn', flat.isbn);
  set('isbn13', flat.isbn_13);
  set('openlibrary', flat.openlibrary_work_key);
  set('openlibraryBook', flat.openlibrary_book_key);
  set('googleBooks', flat.google_books_id);
  set('tmdb', flat.tmdb_id);
  set('imdb', flat.imdb_id);
  set('tvmazeShow', flat.tvmaze_show_id);
  set('tvmazeEpisode', flat.tvmaze_episode_id);
  set('wikidata', flat.wikidata_qid);
  set('youtubeVideo', flat.youtube_video_id);
  set('youtubeChannel', flat.youtube_channel_id);

  return hasAny ? ids : undefined;
}

/**
 * Convert a flat `media_metadata` / `book_metadata` dict to
 * {@link StructuredMediaMetadata}.
 */
export function normalizeMediaMetadata(flat: Flat): StructuredMediaMetadata {
  const genres = strArr(flat.book_genres) ??
    (str(flat.book_genre) ? [flat.book_genre as string] : undefined);

  const source: SourceMetadata = {
    title: str(flat.book_title),
    author: str(flat.book_author),
    year: num(flat.book_year),
    summary: str(flat.book_summary),
    genres: genres ?? [],
    language: str(flat.book_language),
    isbn: str(flat.isbn),
    isbn13: str(flat.isbn_13),
    series: extractSeriesInfo(flat),
    youtube: extractYouTubeInfo(flat),
    runtimeMinutes: num(flat.runtime_minutes),
    rating: num(flat.rating),
    votes: num(flat.votes),
  };

  const languageConfig: LanguageConfig = {
    inputLanguage: str(flat.input_language),
    originalLanguage: str(flat.original_language),
    targetLanguage: str(flat.target_language ?? flat.translation_language),
    targetLanguages: strArr(flat.target_languages),
    translationProvider: str(flat.translation_provider),
    translationModel: str(flat.translation_model),
    translationModelRequested: str(flat.translation_model_requested),
    transliterationMode: str(flat.transliteration_mode),
    transliterationModel: str(flat.transliteration_model),
    transliterationModule: str(flat.transliteration_module),
  };

  const contentStructure: ContentStructure = {
    totalSentences: num(flat.total_sentences ?? flat.book_sentence_count),
    contentIndexPath: str(flat.content_index_path),
    contentIndexUrl: str(flat.content_index_url),
    contentIndexSummary: flat.content_index_summary as ContentStructure['contentIndexSummary'],
  };

  const coverAssets: CoverAssets = {
    coverFile: str(flat.book_cover_file),
    coverUrl: str(flat.cover_url),
    bookCoverUrl: str(flat.book_cover_url),
    jobCoverAsset: str(flat.job_cover_asset),
    jobCoverAssetUrl: str(flat.job_cover_asset_url),
  };

  const enrichment: EnrichmentProvenance = {
    source: str(flat._enrichment_source),
    confidence: str(flat._enrichment_confidence),
    queriedAt: str(flat.metadata_queried_at),
    sourceIds: extractSourceIds(flat),
    lookupResult: (flat.media_metadata_lookup ?? flat.book_metadata_lookup) as
      Record<string, unknown> | undefined,
  };

  return {
    metadataVersion: 2,
    mediaType: detectMediaType(flat),
    source,
    languageConfig,
    contentStructure,
    coverAssets,
    enrichment,
    jobLabel: str(flat.job_label),
  };
}

/**
 * Get structured metadata from a job result, preferring the pre-computed
 * `structured_metadata` field from the API, falling back to client-side
 * conversion of the flat `media_metadata` / `book_metadata`.
 */
export function getStructuredMetadata(
  result: Record<string, unknown> | null | undefined,
): StructuredMediaMetadata | null {
  if (!result) return null;

  // Prefer server-computed structured_metadata
  const structured = result.structured_metadata as StructuredMediaMetadata | undefined;
  if (structured && typeof structured === 'object' && structured.metadataVersion) {
    return structured;
  }

  // Fall back to client-side conversion
  const flat = (result.media_metadata ?? result.book_metadata) as Flat | undefined;
  if (flat && typeof flat === 'object') {
    return normalizeMediaMetadata(flat);
  }

  return null;
}
