/**
 * Hook for fetching and managing YouTube/TV metadata for video playback.
 */

import { useEffect, useMemo, useState } from 'react';
import {
  fetchPipelineStatus,
  fetchSubtitleTvMetadata,
  fetchYoutubeVideoMetadata,
} from '../../api/client';
import type {
  LibraryItem,
  SubtitleTvMetadataResponse,
  YoutubeVideoMetadataResponse,
} from '../../api/dtos';
import { buildLibraryBookMetadata } from '../../utils/libraryMetadata';
import { extractMetadataFirstString, extractMetadataText } from '../player-panel/helpers';
import {
  coerceRecord,
  readStringValue,
} from './utils';
import {
  extractLanguagesFromResult,
  extractTvMediaMetadataFromPayload,
  extractYoutubeVideoMetadataFromTv,
} from './metadataResolvers';

export interface UseYoutubeMetadataOptions {
  jobId: string;
  libraryItem?: LibraryItem | null;
  mediaMetadata?: Record<string, unknown> | null;
  isExportMode: boolean;
}

export interface YoutubeMetadataState {
  /** TV metadata from job API (null in export mode or when using library item) */
  jobTvMetadata: Record<string, unknown> | null;
  /** YouTube metadata from job API (null in export mode or when using library item) */
  jobYoutubeMetadata: Record<string, unknown> | null;
  /** TV metadata extracted from export payload (only in export mode) */
  exportTvMetadata: Record<string, unknown> | null;
  /** YouTube metadata extracted from export payload (only in export mode) */
  exportYoutubeMetadata: Record<string, unknown> | null;
  /** Original language code */
  jobOriginalLanguage: string | null;
  /** Translation target language code */
  jobTranslationLanguage: string | null;
}

export function useYoutubeMetadata({
  jobId,
  libraryItem = null,
  mediaMetadata = null,
  isExportMode,
}: UseYoutubeMetadataOptions): YoutubeMetadataState {
  const [jobTvMetadata, setJobTvMetadata] = useState<Record<string, unknown> | null>(null);
  const [jobYoutubeMetadata, setJobYoutubeMetadata] = useState<Record<string, unknown> | null>(null);
  const [jobOriginalLanguage, setJobOriginalLanguage] = useState<string | null>(null);
  const [jobTranslationLanguage, setJobTranslationLanguage] = useState<string | null>(null);

  // Extract metadata from export payload (only in export mode)
  const exportTvMetadata = useMemo(
    () => (isExportMode ? extractTvMediaMetadataFromPayload(coerceRecord(mediaMetadata)) : null),
    [mediaMetadata, isExportMode],
  );

  const exportYoutubeMetadata = useMemo(() => {
    if (!isExportMode) {
      return null;
    }
    const record = coerceRecord(mediaMetadata);
    const direct = record ? coerceRecord(record['youtube']) : null;
    if (direct) {
      return direct;
    }
    return extractYoutubeVideoMetadataFromTv(exportTvMetadata);
  }, [mediaMetadata, exportTvMetadata, isExportMode]);

  // Fetch TV and YouTube metadata from API
  useEffect(() => {
    if (libraryItem || isExportMode) {
      setJobTvMetadata(null);
      setJobYoutubeMetadata(null);
      return;
    }
    let cancelled = false;
    void fetchSubtitleTvMetadata(jobId)
      .then((payload: SubtitleTvMetadataResponse) => {
        if (cancelled) {
          return;
        }
        setJobTvMetadata(payload.media_metadata ? { ...payload.media_metadata } : null);
      })
      .catch(() => {
        if (!cancelled) {
          setJobTvMetadata(null);
        }
      });
    void fetchYoutubeVideoMetadata(jobId)
      .then((payload: YoutubeVideoMetadataResponse) => {
        if (cancelled) {
          return;
        }
        setJobYoutubeMetadata(payload.youtube_metadata ? { ...payload.youtube_metadata } : null);
      })
      .catch(() => {
        if (!cancelled) {
          setJobYoutubeMetadata(null);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [isExportMode, jobId, libraryItem]);

  // Extract language information from various sources
  useEffect(() => {
    if (!jobId) {
      setJobOriginalLanguage(null);
      setJobTranslationLanguage(null);
      return;
    }
    if (libraryItem) {
      const metadata = buildLibraryBookMetadata(libraryItem);
      const original =
        extractMetadataText(metadata, [
          'input_language',
          'original_language',
          'source_language',
          'translation_source_language',
          'language',
          'lang',
        ]) ?? null;
      const target =
        extractMetadataFirstString(metadata, ['target_language', 'translation_language', 'target_languages']) ??
        null;
      setJobOriginalLanguage(original);
      setJobTranslationLanguage(target);
      return;
    }
    if (mediaMetadata) {
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
      return;
    }
    if (isExportMode) {
      setJobOriginalLanguage(null);
      setJobTranslationLanguage(null);
      return;
    }
    let cancelled = false;
    setJobOriginalLanguage(null);
    setJobTranslationLanguage(null);
    void fetchPipelineStatus(jobId)
      .then((status) => {
        if (cancelled) {
          return;
        }
        const resultLanguages = extractLanguagesFromResult(status.result);
        const parameters = status.parameters;
        const parameterRecord = coerceRecord(parameters);
        const original =
          typeof parameters?.input_language === 'string' && parameters.input_language.trim()
            ? parameters.input_language.trim()
            : readStringValue(parameterRecord, 'original_language') ??
              readStringValue(parameterRecord, 'source_language') ??
              readStringValue(parameterRecord, 'translation_source_language');
        const targetLanguages = Array.isArray(parameters?.target_languages) ? parameters.target_languages : [];
        const firstTarget =
          typeof targetLanguages[0] === 'string' && targetLanguages[0].trim() ? targetLanguages[0].trim() : null;
        const targetLanguage =
          readStringValue(parameterRecord, 'target_language') ?? readStringValue(parameterRecord, 'translation_language');
        setJobOriginalLanguage(original ?? resultLanguages.original);
        setJobTranslationLanguage(firstTarget ?? targetLanguage ?? resultLanguages.translation);
      })
      .catch(() => {
        if (!cancelled) {
          setJobOriginalLanguage(null);
          setJobTranslationLanguage(null);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [mediaMetadata, isExportMode, jobId, libraryItem]);

  return {
    jobTvMetadata,
    jobYoutubeMetadata,
    exportTvMetadata,
    exportYoutubeMetadata,
    jobOriginalLanguage,
    jobTranslationLanguage,
  };
}
