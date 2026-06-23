import { useCallback, useEffect, useRef, useState } from 'react';
import { lookupSubtitleTvMetadataPreview } from '../../api/client';
import type { SubtitleTvMetadataPreviewResponse } from '../../api/dtos';
import {
  updateSubtitleMediaMetadataDraft,
  updateSubtitleMediaMetadataSection
} from './subtitleMetadataUtils';

export function useSubtitleTvMetadata(metadataSourceName: string) {
  const [metadataLookupSourceName, setMetadataLookupSourceName] = useState<string>('');
  const [metadataPreview, setMetadataPreview] = useState<SubtitleTvMetadataPreviewResponse | null>(null);
  const [mediaMetadataDraft, setMediaMetadataDraft] = useState<Record<string, unknown> | null>(null);
  const [metadataLoading, setMetadataLoading] = useState<boolean>(false);
  const [metadataError, setMetadataError] = useState<string | null>(null);
  const metadataLookupIdRef = useRef<number>(0);

  const updateMediaMetadataDraft = useCallback((updater: (draft: Record<string, unknown>) => void) => {
    setMediaMetadataDraft((current) => updateSubtitleMediaMetadataDraft(current, updater));
  }, []);

  const updateMediaMetadataSection = useCallback(
    (sectionKey: string, updater: (section: Record<string, unknown>) => void) => {
      setMediaMetadataDraft((current) => updateSubtitleMediaMetadataSection(current, sectionKey, updater));
    },
    []
  );

  const performMetadataLookup = useCallback(
    async (sourceName: string, force: boolean) => {
      const normalized = sourceName.trim();
      if (!normalized) {
        setMetadataPreview(null);
        setMediaMetadataDraft(null);
        setMetadataError(null);
        setMetadataLoading(false);
        return;
      }
      const requestId = metadataLookupIdRef.current + 1;
      metadataLookupIdRef.current = requestId;
      setMetadataLoading(true);
      setMetadataError(null);
      try {
        const payload = await lookupSubtitleTvMetadataPreview({ source_name: normalized, force });
        if (metadataLookupIdRef.current !== requestId) {
          return;
        }
        setMetadataPreview(payload);
        setMediaMetadataDraft(payload.media_metadata ? { ...payload.media_metadata } : null);
      } catch (error) {
        if (metadataLookupIdRef.current !== requestId) {
          return;
        }
        const message = error instanceof Error ? error.message : 'Unable to lookup TV metadata.';
        setMetadataError(message);
        setMetadataPreview(null);
        setMediaMetadataDraft(null);
      } finally {
        if (metadataLookupIdRef.current === requestId) {
          setMetadataLoading(false);
        }
      }
    },
    []
  );

  const handleMetadataClear = useCallback(() => {
    setMetadataPreview(null);
    setMediaMetadataDraft(null);
    setMetadataError(null);
  }, []);

  useEffect(() => {
    const normalized = metadataSourceName.trim();
    setMetadataLookupSourceName(normalized);
    if (!normalized) {
      setMetadataPreview(null);
      setMediaMetadataDraft(null);
      setMetadataError(null);
      setMetadataLoading(false);
      return;
    }
    void performMetadataLookup(normalized, false);
  }, [metadataSourceName, performMetadataLookup]);

  return {
    metadataLookupSourceName,
    setMetadataLookupSourceName,
    metadataPreview,
    metadataLoading,
    metadataError,
    mediaMetadataDraft,
    performMetadataLookup,
    handleMetadataClear,
    updateMediaMetadataDraft,
    updateMediaMetadataSection
  };
}
