import { useCallback, useEffect, useMemo, useState } from 'react';
import {
  deleteNasSubtitle,
  extractInlineSubtitles,
  fetchInlineSubtitleStreams
} from '../../api/client';
import type {
  YoutubeInlineSubtitleStream,
  YoutubeNasSubtitle,
  YoutubeNasVideo
} from '../../api/dtos';
import {
  formatSubtitleExtractionStatus,
  resolveDefaultStreamLanguages
} from './videoDubbingUtils';

type VideoDubbingSubtitleExtractionOptions = {
  selectedVideo: YoutubeNasVideo | null;
  selectedSubtitlePath: string | null;
  onRefresh: () => Promise<void>;
  onSelectedVideoPathChange: (path: string | null) => void;
  onSelectedSubtitlePathChange: (path: string | null) => void;
  onStatusMessageChange: (message: string | null) => void;
};

export function useVideoDubbingSubtitleExtraction({
  selectedVideo,
  selectedSubtitlePath,
  onRefresh,
  onSelectedVideoPathChange,
  onSelectedSubtitlePathChange,
  onStatusMessageChange
}: VideoDubbingSubtitleExtractionOptions) {
  const [isExtractingSubtitles, setIsExtractingSubtitles] = useState(false);
  const [deletingSubtitlePath, setDeletingSubtitlePath] = useState<string | null>(null);
  const [extractError, setExtractError] = useState<string | null>(null);
  const [availableSubtitleStreams, setAvailableSubtitleStreams] = useState<YoutubeInlineSubtitleStream[]>([]);
  const [selectedStreamLanguages, setSelectedStreamLanguages] = useState<Set<string>>(new Set());
  const [isChoosingStreams, setIsChoosingStreams] = useState(false);
  const [isLoadingStreams, setIsLoadingStreams] = useState(false);

  const extractableStreams = useMemo(
    () => availableSubtitleStreams.filter((stream) => stream.can_extract),
    [availableSubtitleStreams]
  );

  useEffect(() => {
    setAvailableSubtitleStreams([]);
    setSelectedStreamLanguages(new Set());
    setIsChoosingStreams(false);
    setDeletingSubtitlePath(null);
  }, [selectedVideo?.path]);

  const deleteSubtitle = useCallback(
    async (subtitle: YoutubeNasSubtitle) => {
      if (!selectedVideo) {
        return;
      }
      const confirmed =
        typeof window === 'undefined' ||
        window.confirm(
          `Delete ${subtitle.filename}? This removes the subtitle and any mirrored HTML transcript copies.`,
        );
      if (!confirmed) {
        return;
      }
      setExtractError(null);
      onStatusMessageChange(null);
      setDeletingSubtitlePath(subtitle.path);
      try {
        await deleteNasSubtitle(selectedVideo.path, subtitle.path);
        await onRefresh();
        onSelectedVideoPathChange(selectedVideo.path);
        if (selectedSubtitlePath === subtitle.path) {
          onSelectedSubtitlePathChange(null);
        }
        onStatusMessageChange(`Deleted ${subtitle.filename}`);
      } catch (error) {
        const message =
          error instanceof Error ? error.message || 'Unable to delete subtitle.' : 'Unable to delete subtitle.';
        setExtractError(message);
      } finally {
        setDeletingSubtitlePath(null);
      }
    },
    [
      onRefresh,
      onSelectedSubtitlePathChange,
      onSelectedVideoPathChange,
      onStatusMessageChange,
      selectedSubtitlePath,
      selectedVideo
    ]
  );

  const performSubtitleExtraction = useCallback(
    async (languages?: string[]) => {
      if (!selectedVideo) {
        return;
      }
      setIsExtractingSubtitles(true);
      setExtractError(null);
      onStatusMessageChange(null);
      try {
        const response = await extractInlineSubtitles(selectedVideo.path, languages);
        const count = response.extracted?.length ?? 0;
        onStatusMessageChange(formatSubtitleExtractionStatus(count, selectedVideo.filename));
        await onRefresh();
        onSelectedVideoPathChange(selectedVideo.path);
        setAvailableSubtitleStreams([]);
        setSelectedStreamLanguages(new Set());
      } catch (error) {
        const message =
          error instanceof Error ? error.message || 'Unable to extract subtitles.' : 'Unable to extract subtitles.';
        setExtractError(message);
      } finally {
        setIsExtractingSubtitles(false);
      }
    },
    [onRefresh, onSelectedVideoPathChange, onStatusMessageChange, selectedVideo]
  );

  const inspectSubtitleStreams = useCallback(async () => {
    if (!selectedVideo) {
      return;
    }
    setIsLoadingStreams(true);
    setIsChoosingStreams(false);
    setExtractError(null);
    onStatusMessageChange(null);
    try {
      const response = await fetchInlineSubtitleStreams(selectedVideo.path);
      const streams = response.streams ?? [];
      setAvailableSubtitleStreams(streams);
      const extractable = streams.filter((stream) => stream.can_extract);
      const defaults = resolveDefaultStreamLanguages(streams);
      setSelectedStreamLanguages(defaults);
      if (extractable.length === 0) {
        setExtractError(
          'No text-based subtitle streams were found. Image-based subtitle tracks cannot be extracted automatically.'
        );
        return;
      }
      if (extractable.length === 1) {
        const languages = Array.from(defaults).filter(Boolean);
        await performSubtitleExtraction(languages.length > 0 ? languages : undefined);
        return;
      }
      setIsChoosingStreams(true);
    } catch (error) {
      const message =
        error instanceof Error ? error.message || 'Unable to inspect subtitle streams.' : 'Unable to inspect subtitle streams.';
      setExtractError(message);
    } finally {
      setIsLoadingStreams(false);
    }
  }, [onStatusMessageChange, performSubtitleExtraction, selectedVideo]);

  const toggleSubtitleStream = useCallback((language: string, enabled: boolean) => {
    if (!language) {
      return;
    }
    setSelectedStreamLanguages((previous) => {
      const next = new Set(previous);
      if (enabled) {
        next.add(language);
      } else {
        next.delete(language);
      }
      return next;
    });
  }, []);

  const confirmSubtitleStreams = useCallback(async () => {
    if (!selectedVideo) {
      return;
    }
    if (availableSubtitleStreams.length > 1 && selectedStreamLanguages.size === 0) {
      setExtractError('Select at least one subtitle language to extract.');
      return;
    }
    setIsChoosingStreams(false);
    const languages = Array.from(selectedStreamLanguages).filter(Boolean);
    await performSubtitleExtraction(languages.length > 0 ? languages : undefined);
  }, [availableSubtitleStreams.length, performSubtitleExtraction, selectedStreamLanguages, selectedVideo]);

  const cancelStreamSelection = useCallback(() => {
    setIsChoosingStreams(false);
    setAvailableSubtitleStreams([]);
  }, []);

  const extractAllStreams = useCallback(() => {
    void performSubtitleExtraction(undefined);
  }, [performSubtitleExtraction]);

  return {
    isExtractingSubtitles,
    isLoadingStreams,
    isChoosingStreams,
    availableSubtitleStreams,
    selectedStreamLanguages,
    extractableStreams,
    extractError,
    deletingSubtitlePath,
    deleteSubtitle,
    inspectSubtitleStreams,
    toggleSubtitleStream,
    confirmSubtitleStreams,
    cancelStreamSelection,
    extractAllStreams
  };
}
