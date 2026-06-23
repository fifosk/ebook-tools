import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { deleteSubtitleSource, fetchSubtitleSources } from '../../api/client';
import type { SubtitleSourceEntry } from '../../api/dtos';
import {
  resolveSubtitleSourceSelectionAfterRefresh,
  sortSubtitleSourcesForSelection
} from './subtitleToolUtils';

type UseSubtitleSourcesOptions = {
  sourceDirectory: string;
  refreshSignal: number;
};

export function useSubtitleSources({ sourceDirectory, refreshSignal }: UseSubtitleSourcesOptions) {
  const [sources, setSources] = useState<SubtitleSourceEntry[]>([]);
  const [selectedSource, setSelectedSource] = useState<string>('');
  const selectedSourceRef = useRef<string>('');
  const [isLoadingSources, setLoadingSources] = useState<boolean>(false);
  const [deletingSourcePath, setDeletingSourcePath] = useState<string | null>(null);
  const [sourceMessage, setSourceMessage] = useState<string | null>(null);
  const [sourceError, setSourceError] = useState<string | null>(null);

  useEffect(() => {
    selectedSourceRef.current = selectedSource;
  }, [selectedSource]);

  const selectedSourceEntry = useMemo(
    () => sources.find((entry) => entry.path === selectedSource) ?? null,
    [selectedSource, sources]
  );
  const sortedSources = useMemo(() => sortSubtitleSourcesForSelection(sources), [sources]);

  const refreshSources = useCallback(
    async (resetSelection: boolean = false) => {
      const directory = sourceDirectory;
      setLoadingSources(true);
      setSourceError(null);
      setSourceMessage(null);
      try {
        const entries = await fetchSubtitleSources(directory);
        setSources(entries);
        const currentSelection = resetSelection ? '' : selectedSourceRef.current;
        setSelectedSource(resolveSubtitleSourceSelectionAfterRefresh({
          sources: entries,
          currentSelection,
          resetSelection
        }));
        if (entries.length === 0) {
          setSourceMessage(`No subtitles found in ${directory}`);
        }
      } catch (error) {
        console.warn('Unable to list subtitle sources', error);
        const message = error instanceof Error ? error.message : 'Unable to list subtitle sources.';
        setSourceError(message);
      } finally {
        setLoadingSources(false);
      }
    },
    [sourceDirectory]
  );

  useEffect(() => {
    refreshSources();
  }, [refreshSignal, refreshSources]);

  const handleDeleteSource = useCallback(
    async (entry: SubtitleSourceEntry) => {
      const confirmed =
        typeof window === 'undefined' ||
        window.confirm(
          `Delete ${entry.name}? This removes the subtitle and any mirrored HTML transcript copies.`,
        );
      if (!confirmed) {
        return;
      }
      setSourceError(null);
      setSourceMessage(null);
      setDeletingSourcePath(entry.path);
      try {
        await deleteSubtitleSource(entry.path);
        const resetSelection = selectedSource === entry.path;
        await refreshSources(resetSelection);
        setSourceMessage(`Deleted ${entry.name}`);
      } catch (error) {
        const message = error instanceof Error ? error.message : 'Unable to delete subtitle.';
        setSourceError(message);
      } finally {
        setDeletingSourcePath(null);
      }
    },
    [refreshSources, selectedSource]
  );

  return {
    sources,
    sortedSources,
    selectedSource,
    setSelectedSource,
    selectedSourceEntry,
    isLoadingSources,
    deletingSourcePath,
    sourceMessage,
    sourceError,
    refreshSources,
    handleDeleteSource
  };
}
