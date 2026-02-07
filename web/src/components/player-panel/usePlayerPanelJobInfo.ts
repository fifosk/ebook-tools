import { useEffect, useMemo, useState } from 'react';
import type { LiveMediaChunk } from '../../hooks/useLiveMedia';
import type { ChapterNavigationEntry } from './NavigationControls';
import type { PlayerMode } from '../../types/player';
import {
  appendAccessTokenToStorageUrl,
  buildStorageUrl,
  fetchPipelineStatus,
  resolveLibraryMediaUrl,
} from '../../api/client';
import { coerceExportPath } from '../../utils/storageResolver';
import { normaliseContentIndexChapters, toFiniteNumber } from '../../utils/contentIndex';
import { isTvSeriesMetadata } from '../../utils/jobGlyphs';
import {
  coerceRecord,
  extractMetadataFirstString,
  extractMetadataText,
  normaliseBookSentenceCount,
  readNestedValue,
} from './helpers';
import { deriveSentenceCountFromChunks } from './utils';

type UsePlayerPanelJobInfoArgs = {
  jobId: string;
  jobType?: string | null;
  itemType?: 'book' | 'video' | 'narrated_subtitle' | null;
  origin?: 'job' | 'library';
  playerMode?: PlayerMode;
  mediaMetadata?: Record<string, unknown> | null;
  chunks: LiveMediaChunk[];
};

type PlayerPanelJobInfo = {
  bookTitle: string | null;
  bookAuthor: string | null;
  bookYear: string | null;
  bookGenre: string | null;
  isBookLike: boolean;
  channelBug: { glyph: string; label: string };
  sectionLabel: string;
  loadingMessage: string;
  emptyMediaMessage: string;
  coverAltText: string;
  bookSentenceCount: number | null;
  chapterEntries: ChapterNavigationEntry[];
  jobOriginalLanguage: string | null;
  jobTranslationLanguage: string | null;
  jobScopeStartSentence: number | null;
  jobScopeEndSentence: number | null;
};

export function usePlayerPanelJobInfo({
  jobId,
  jobType = null,
  itemType = null,
  origin = 'job',
  playerMode = 'online',
  mediaMetadata = null,
  chunks,
}: UsePlayerPanelJobInfoArgs): PlayerPanelJobInfo {
  const [bookSentenceCount, setBookSentenceCount] = useState<number | null>(null);
  const [chapterEntries, setChapterEntries] = useState<ChapterNavigationEntry[]>([]);
  const [jobOriginalLanguage, setJobOriginalLanguage] = useState<string | null>(null);
  const [jobTranslationLanguage, setJobTranslationLanguage] = useState<string | null>(null);
  const [jobScopeStartSentence, setJobScopeStartSentence] = useState<number | null>(null);
  const [jobScopeEndSentence, setJobScopeEndSentence] = useState<number | null>(null);

  useEffect(() => {
    if (origin !== 'library' && playerMode !== 'export') {
      return;
    }
    const original =
      extractMetadataText(mediaMetadata, [
        'input_language',
        'original_language',
        'source_language',
        'translation_source_language',
        'language',
        'lang',
      ]) ?? null;
    const target =
      extractMetadataFirstString(mediaMetadata, ['target_language', 'translation_language', 'target_languages']) ??
      null;
    setJobOriginalLanguage(original);
    setJobTranslationLanguage(target);
  }, [mediaMetadata, origin, playerMode]);

  useEffect(() => {
    if (!jobId || origin === 'library' || playerMode === 'export') {
      setJobScopeStartSentence(null);
      setJobScopeEndSentence(null);
      return;
    }
    let cancelled = false;
    void fetchPipelineStatus(jobId)
      .then((status) => {
        if (cancelled) {
          return;
        }
        const parameters = status.parameters;
        const parameterRecord = parameters && typeof parameters === 'object' ? (parameters as Record<string, unknown>) : null;
        const original =
          typeof parameters?.input_language === 'string' && parameters.input_language.trim()
            ? parameters.input_language.trim()
            : extractMetadataText(parameterRecord, [
                'original_language',
                'source_language',
                'translation_source_language',
              ]);
        const targetLanguages = Array.isArray(parameters?.target_languages) ? parameters.target_languages : [];
        const firstTarget =
          typeof targetLanguages[0] === 'string' && targetLanguages[0].trim() ? targetLanguages[0].trim() : null;
        const fallbackTarget =
          extractMetadataFirstString(parameterRecord, ['target_language', 'translation_language', 'target_languages']) ??
          null;
        const rawStart = toFiniteNumber(
          parameters?.start_sentence ?? (parameters as Record<string, unknown> | null)?.startSentence,
        );
        const rawEnd = toFiniteNumber(
          parameters?.end_sentence ?? (parameters as Record<string, unknown> | null)?.endSentence,
        );
        const normalizedStart = rawStart !== null && rawStart > 0 ? rawStart : null;
        const normalizedEnd = rawEnd !== null && rawEnd > 0 ? rawEnd : null;
        setJobOriginalLanguage(original);
        setJobTranslationLanguage(firstTarget ?? fallbackTarget);
        setJobScopeStartSentence(normalizedStart);
        setJobScopeEndSentence(normalizedEnd);
      })
      .catch(() => {
        if (cancelled) {
          return;
        }
        setJobOriginalLanguage(null);
        setJobTranslationLanguage(null);
        setJobScopeStartSentence(null);
        setJobScopeEndSentence(null);
      });
    return () => {
      cancelled = true;
    };
  }, [jobId, origin, playerMode]);

  useEffect(() => {
    setBookSentenceCount(null);
    setJobScopeStartSentence(null);
    setJobScopeEndSentence(null);
  }, [jobId]);

  useEffect(() => {
    setChapterEntries([]);
  }, [jobId]);

  useEffect(() => {
    if (!jobId || chunks.length === 0) {
      setBookSentenceCount(null);
      return;
    }

    const metadataCount = normaliseBookSentenceCount(mediaMetadata);
    if (metadataCount !== null) {
      setBookSentenceCount((current) => (current === metadataCount ? current : metadataCount));
      return;
    }

    if (bookSentenceCount !== null) {
      return;
    }

    const derivedCount = deriveSentenceCountFromChunks(chunks);
    if (derivedCount !== null) {
      setBookSentenceCount((current) => (current === derivedCount ? current : derivedCount));
    }
  }, [mediaMetadata, bookSentenceCount, chunks.length, jobId, playerMode]);

  useEffect(() => {
    let cancelled = false;
    if (!jobId) {
      setChapterEntries([]);
      return () => {
        cancelled = true;
      };
    }

    const inlineIndex =
      mediaMetadata && typeof mediaMetadata === 'object'
        ? (mediaMetadata as Record<string, unknown>).content_index
        : null;
    if (inlineIndex) {
      const chapters = normaliseContentIndexChapters(inlineIndex);
      if (chapters.length > 0) {
        setChapterEntries(chapters);
        return () => {
          cancelled = true;
        };
      }
    }

    const contentIndexUrl =
      extractMetadataText(mediaMetadata, ['content_index_url', 'contentIndexUrl']) ?? null;
    const contentIndexPath =
      extractMetadataText(mediaMetadata, ['content_index_path', 'contentIndexPath']) ?? null;
    let targetUrl: string | null = contentIndexUrl;
    if (playerMode === 'export') {
      const candidate = contentIndexPath ?? contentIndexUrl;
      if (candidate) {
        targetUrl = coerceExportPath(candidate, jobId) ?? candidate;
      }
    } else if (!targetUrl && contentIndexPath) {
      try {
        if (origin === 'library') {
          if (contentIndexPath.startsWith('/api/library/') || contentIndexPath.includes('://')) {
            targetUrl = contentIndexPath;
          } else {
            targetUrl = resolveLibraryMediaUrl(jobId, contentIndexPath);
          }
        } else {
          targetUrl = buildStorageUrl(contentIndexPath, jobId);
        }
      } catch (error) {
        const encodedJobId = encodeURIComponent(jobId);
        const sanitizedPath = contentIndexPath.replace(/^\/+/, '');
        targetUrl = `/pipelines/jobs/${encodedJobId}/${encodeURI(sanitizedPath)}`;
        if (import.meta.env.DEV) {
          console.warn('Unable to resolve content index path', contentIndexPath, error);
        }
      }
    }

    if (!targetUrl || typeof fetch !== 'function') {
      setChapterEntries([]);
      return () => {
        cancelled = true;
      };
    }

    (async () => {
      try {
        const url = playerMode !== 'export' ? appendAccessTokenToStorageUrl(targetUrl) : targetUrl;
        const response = await fetch(url, { credentials: 'include' });
        if (!response.ok) {
          return;
        }
        const payload = await response.json();
        const chapters = normaliseContentIndexChapters(payload);
        if (!cancelled) {
          setChapterEntries(chapters);
        }
      } catch (error) {
        if (import.meta.env.DEV) {
          console.warn('Unable to load content index', targetUrl, error);
        }
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [mediaMetadata, jobId, origin, playerMode]);

  const bookTitle = extractMetadataText(mediaMetadata, ['book_title', 'title', 'book_name', 'name']);
  const bookAuthor = extractMetadataText(mediaMetadata, ['book_author', 'author', 'writer', 'creator']);
  const bookYear = extractMetadataText(mediaMetadata, ['book_year', 'year', 'publication_year', 'published_year', 'first_publish_year']);
  const bookGenre = extractMetadataFirstString(mediaMetadata, ['genre', 'book_genre', 'series_genre', 'category', 'subjects']);
  const isBookLike =
    itemType === 'book' || (jobType ?? '').trim().toLowerCase().includes('book') || Boolean(bookTitle);
  const youtubeMetadata = useMemo(() => {
    if (!mediaMetadata || typeof mediaMetadata !== 'object') {
      return null;
    }
    const payload = mediaMetadata as Record<string, unknown>;
    const direct = coerceRecord(payload['youtube']);
    if (direct) {
      return direct;
    }
    const nestedMediaMetadata =
      readNestedValue(payload, ['result', 'subtitle', 'metadata', 'media_metadata']) ??
      readNestedValue(payload, ['result', 'youtube_dub', 'media_metadata']) ??
      readNestedValue(payload, ['request', 'media_metadata']) ??
      readNestedValue(payload, ['media_metadata']) ??
      null;
    const nestedRecord = coerceRecord(nestedMediaMetadata);
    return coerceRecord(nestedRecord?.['youtube']);
  }, [mediaMetadata]);
  const tvMetadata = useMemo(() => {
    if (!mediaMetadata || typeof mediaMetadata !== 'object') {
      return null;
    }
    const payload = mediaMetadata as Record<string, unknown>;
    const candidate =
      readNestedValue(payload, ['result', 'youtube_dub', 'media_metadata']) ??
      readNestedValue(payload, ['result', 'subtitle', 'metadata', 'media_metadata']) ??
      readNestedValue(payload, ['request', 'media_metadata']) ??
      readNestedValue(payload, ['media_metadata']) ??
      null;
    return coerceRecord(candidate);
  }, [mediaMetadata]);
  const hasYoutubeMetadata = Boolean(youtubeMetadata);
  const hasTvSeriesMetadata = isTvSeriesMetadata(tvMetadata);
  const channelBug = useMemo(() => {
    const normalisedJobType = (jobType ?? '').trim().toLowerCase();
    if (hasTvSeriesMetadata) {
      return { glyph: 'TV', label: 'TV series' };
    }
    if (normalisedJobType.includes('youtube') || hasYoutubeMetadata) {
      return { glyph: 'YT', label: 'YouTube' };
    }
    if (itemType === 'book') {
      return { glyph: 'BK', label: 'Book' };
    }
    if (itemType === 'narrated_subtitle') {
      return { glyph: 'SUB', label: 'Subtitles' };
    }
    if (itemType === 'video') {
      return { glyph: 'VID', label: 'Video' };
    }
    if (normalisedJobType.includes('subtitle')) {
      return { glyph: 'SUB', label: 'Subtitles' };
    }
    if (normalisedJobType.includes('video')) {
      return { glyph: 'VID', label: 'Video' };
    }
    if (normalisedJobType.includes('book') || Boolean(bookTitle || bookAuthor)) {
      return { glyph: 'BK', label: 'Book' };
    }
    return { glyph: 'JOB', label: 'Job' };
  }, [bookAuthor, bookTitle, hasTvSeriesMetadata, hasYoutubeMetadata, itemType, jobType]);
  const sectionLabel = bookTitle ? `Player for ${bookTitle}` : 'Player';
  const loadingMessage = bookTitle ? `Loading generated media for ${bookTitle}…` : 'Loading generated media…';
  const emptyMediaMessage = bookTitle ? `No generated media yet for ${bookTitle}.` : 'No generated media yet.';
  const coverAltText =
    bookTitle && bookAuthor
      ? `Cover of ${bookTitle} by ${bookAuthor}`
      : bookTitle
        ? `Cover of ${bookTitle}`
        : bookAuthor
          ? `Book cover for ${bookAuthor}`
          : 'Book cover preview';

  return {
    bookTitle,
    bookAuthor,
    bookYear,
    bookGenre,
    isBookLike,
    channelBug,
    sectionLabel,
    loadingMessage,
    emptyMediaMessage,
    coverAltText,
    bookSentenceCount,
    chapterEntries,
    jobOriginalLanguage,
    jobTranslationLanguage,
    jobScopeStartSentence,
    jobScopeEndSentence,
  };
}
