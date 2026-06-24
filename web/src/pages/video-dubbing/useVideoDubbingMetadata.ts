import { useCallback, useEffect, useRef, useState } from 'react';
import {
  clearTvMetadataCache,
  clearYoutubeMetadataCache,
  lookupSubtitleTvMetadataPreview,
  lookupYoutubeVideoMetadataPreview
} from '../../api/client';
import type {
  SubtitleTvMetadataPreviewResponse,
  YoutubeVideoMetadataPreviewResponse
} from '../../api/dtos';
import type { VideoDubbingTab, VideoMetadataSection } from './videoDubbingTypes';
import {
  hasYoutubeMetadataTitle,
  mergeTvMetadataPreviewWithPreservedYoutubeMetadata,
  updateVideoDubbingMediaMetadataDraft,
  updateVideoDubbingMediaMetadataSection
} from './videoDubbingUtils';

type VideoDubbingMetadataOptions = {
  activeTab: VideoDubbingTab;
  metadataSourceName: string;
};

export function useVideoDubbingMetadata({
  activeTab,
  metadataSourceName
}: VideoDubbingMetadataOptions) {
  const [metadataLookupSourceName, setMetadataLookupSourceName] = useState<string>('');
  const [metadataPreview, setMetadataPreview] = useState<SubtitleTvMetadataPreviewResponse | null>(null);
  const [mediaMetadataDraft, setMediaMetadataDraft] = useState<Record<string, unknown> | null>(null);
  const [metadataLoading, setMetadataLoading] = useState<boolean>(false);
  const [metadataError, setMetadataError] = useState<string | null>(null);
  const metadataLookupIdRef = useRef<number>(0);
  const [metadataSection, setMetadataSection] = useState<VideoMetadataSection>('tv');

  const [youtubeLookupSourceName, setYoutubeLookupSourceName] = useState<string>('');
  const [youtubeMetadataPreview, setYoutubeMetadataPreview] =
    useState<YoutubeVideoMetadataPreviewResponse | null>(null);
  const [youtubeMetadataLoading, setYoutubeMetadataLoading] = useState<boolean>(false);
  const [youtubeMetadataError, setYoutubeMetadataError] = useState<string | null>(null);
  const youtubeLookupIdRef = useRef<number>(0);

  const updateMediaMetadataDraft = useCallback((updater: (draft: Record<string, unknown>) => void) => {
    setMediaMetadataDraft((current) => updateVideoDubbingMediaMetadataDraft(current, updater));
  }, []);

  const updateMediaMetadataSection = useCallback(
    (sectionKey: string, updater: (section: Record<string, unknown>) => void) => {
      setMediaMetadataDraft((current) => updateVideoDubbingMediaMetadataSection(current, sectionKey, updater));
    },
    []
  );

  const performMetadataLookup = useCallback(async (sourceName: string, force: boolean) => {
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
      setMediaMetadataDraft((current) =>
        mergeTvMetadataPreviewWithPreservedYoutubeMetadata(current, payload.media_metadata)
      );
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
  }, []);

  const performYoutubeMetadataLookup = useCallback(
    async (sourceName: string, force: boolean) => {
      const normalized = sourceName.trim();
      if (!normalized) {
        setYoutubeMetadataPreview(null);
        setYoutubeMetadataError(null);
        setYoutubeMetadataLoading(false);
        updateMediaMetadataDraft((draft) => {
          delete draft['youtube'];
        });
        return;
      }

      const requestId = youtubeLookupIdRef.current + 1;
      youtubeLookupIdRef.current = requestId;
      setYoutubeMetadataLoading(true);
      setYoutubeMetadataError(null);
      try {
        const payload = await lookupYoutubeVideoMetadataPreview({ source_name: normalized, force });
        if (youtubeLookupIdRef.current !== requestId) {
          return;
        }
        setYoutubeMetadataPreview(payload);
        if (payload.youtube_metadata) {
          updateMediaMetadataDraft((draft) => {
            draft['youtube'] = { ...payload.youtube_metadata };
          });
        } else {
          updateMediaMetadataDraft((draft) => {
            delete draft['youtube'];
          });
        }
      } catch (error) {
        if (youtubeLookupIdRef.current !== requestId) {
          return;
        }
        const message = error instanceof Error ? error.message : 'Unable to lookup YouTube metadata.';
        setYoutubeMetadataError(message);
        setYoutubeMetadataPreview(null);
        updateMediaMetadataDraft((draft) => {
          delete draft['youtube'];
        });
      } finally {
        if (youtubeLookupIdRef.current === requestId) {
          setYoutubeMetadataLoading(false);
        }
      }
    },
    [updateMediaMetadataDraft]
  );

  const handleClearTvMetadata = useCallback(async () => {
    setMetadataPreview(null);
    setMediaMetadataDraft(null);
    setMetadataError(null);

    const query = metadataLookupSourceName.trim();
    if (query) {
      try {
        await clearTvMetadataCache(query);
      } catch {
        // Frontend state is already clear; cache clear is best-effort.
      }
    }
  }, [metadataLookupSourceName]);

  const handleClearYoutubeMetadata = useCallback(async () => {
    setYoutubeMetadataPreview(null);
    setYoutubeMetadataError(null);
    updateMediaMetadataDraft((draft) => {
      delete draft['youtube'];
    });

    const query = youtubeLookupSourceName.trim();
    if (query) {
      try {
        await clearYoutubeMetadataCache(query);
      } catch {
        // Frontend state is already clear; cache clear is best-effort.
      }
    }
  }, [updateMediaMetadataDraft, youtubeLookupSourceName]);

  useEffect(() => {
    const normalized = metadataSourceName.trim();
    setMetadataLookupSourceName(normalized);
    setYoutubeLookupSourceName(normalized);
    setYoutubeMetadataPreview(null);
    setYoutubeMetadataError(null);
    setYoutubeMetadataLoading(false);
    setMediaMetadataDraft(null);
    if (!normalized) {
      setMetadataPreview(null);
      setMetadataError(null);
      setMetadataLoading(false);
      return;
    }
    void performMetadataLookup(normalized, false);
  }, [metadataSourceName, performMetadataLookup]);

  useEffect(() => {
    if (activeTab !== 'metadata' || metadataSection !== 'youtube') {
      return;
    }
    const normalized = youtubeLookupSourceName.trim();
    if (!normalized) {
      return;
    }
    if (hasYoutubeMetadataTitle(mediaMetadataDraft)) {
      return;
    }
    if (youtubeMetadataLoading || youtubeMetadataError) {
      return;
    }
    void performYoutubeMetadataLookup(normalized, false);
  }, [
    activeTab,
    mediaMetadataDraft,
    metadataSection,
    performYoutubeMetadataLookup,
    youtubeLookupSourceName,
    youtubeMetadataError,
    youtubeMetadataLoading
  ]);

  return {
    metadataSection,
    setMetadataSection,
    metadataLookupSourceName,
    setMetadataLookupSourceName,
    metadataPreview,
    metadataLoading,
    metadataError,
    youtubeLookupSourceName,
    setYoutubeLookupSourceName,
    youtubeMetadataPreview,
    youtubeMetadataLoading,
    youtubeMetadataError,
    mediaMetadataDraft,
    performMetadataLookup,
    performYoutubeMetadataLookup,
    handleClearTvMetadata,
    handleClearYoutubeMetadata,
    updateMediaMetadataDraft,
    updateMediaMetadataSection
  };
}
