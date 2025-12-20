import { useCallback, useEffect, useMemo, useState } from 'react';
import type { ReadingBedEntry, ReadingBedListResponse } from '../../api/dtos';
import { fetchReadingBeds, withBase } from '../../api/client';
import { useReadingBed } from '../../hooks/useReadingBed';
import { DEFAULT_READING_BED_VOLUME_PERCENT } from './constants';

const READING_BED_ENABLED_STORAGE_KEY = 'player-panel.readingBed.enabled';
const READING_BED_VOLUME_STORAGE_KEY = 'player-panel.readingBed.volumePercent';
const READING_BED_TRACK_STORAGE_KEY = 'player-panel.readingBed.track';
const DEFAULT_READING_BED_TRACK_ID = 'lost-in-the-pages';

type ReadingBedOption = { value: string; label: string };

type UseReadingBedControlsResult = {
  readingBedEnabled: boolean;
  readingBedVolumePercent: number;
  readingBedTrackSelection: string | null;
  readingBedTrackOptions: ReadingBedOption[];
  readingBedSupported: boolean;
  toggleReadingBed: () => void;
  onReadingBedVolumeChange: (value: number) => void;
  onReadingBedTrackChange: (value: string) => void;
  playReadingBed: () => void;
  pauseReadingBed: () => void;
  resetReadingBed: () => void;
};

type UseReadingBedControlsArgs = {
  bedOverride?: { id: string; label: string; url: string } | null;
  playerMode?: 'online' | 'export';
};

export function useReadingBedControls({
  bedOverride = null,
  playerMode = 'online',
}: UseReadingBedControlsArgs = {}): UseReadingBedControlsResult {
  const isExportMode = playerMode === 'export';
  const normalizedOverride = useMemo(() => {
    if (!bedOverride) {
      return null;
    }
    const id = bedOverride.id?.trim() ?? '';
    const label = bedOverride.label?.trim() ?? '';
    const url = bedOverride.url?.trim() ?? '';
    if (!id || !label || !url) {
      return null;
    }
    return {
      id,
      label,
      url,
      kind: 'bundled',
    } satisfies ReadingBedEntry;
  }, [bedOverride]);
  const readingBed = useReadingBed();
  const [readingBedEnabled, setReadingBedEnabled] = useState<boolean>(() => {
    if (typeof window === 'undefined') {
      return true;
    }
    const stored = window.localStorage.getItem(READING_BED_ENABLED_STORAGE_KEY);
    if (stored === null) {
      return true;
    }
    return stored === 'true';
  });
  const [readingBedVolumePercent, setReadingBedVolumePercent] = useState<number>(() => {
    if (typeof window === 'undefined') {
      return DEFAULT_READING_BED_VOLUME_PERCENT;
    }
    const raw = Number.parseFloat(window.localStorage.getItem(READING_BED_VOLUME_STORAGE_KEY) ?? '');
    if (!Number.isFinite(raw)) {
      return DEFAULT_READING_BED_VOLUME_PERCENT;
    }
    return Math.round(Math.min(Math.max(raw, 0), 100));
  });
  const fallbackReadingBeds = useMemo(
    () =>
      [
        {
          id: DEFAULT_READING_BED_TRACK_ID,
          label: 'Lost in the Pages',
          url: isExportMode ? 'assets/reading-beds/lost-in-the-pages.mp3' : '/assets/reading-beds/lost-in-the-pages.mp3',
          kind: 'bundled',
        },
      ] as ReadingBedEntry[],
    [isExportMode],
  );
  const [readingBedCatalog, setReadingBedCatalog] = useState<ReadingBedListResponse | null>(null);
  useEffect(() => {
    if (normalizedOverride) {
      setReadingBedCatalog({ beds: [normalizedOverride], default_id: normalizedOverride.id });
      return;
    }
    setReadingBedCatalog(null);
    const controller = new AbortController();
    void (async () => {
      try {
        const catalog = await fetchReadingBeds(controller.signal);
        setReadingBedCatalog(catalog);
      } catch {
        setReadingBedCatalog(null);
      }
    })();
    return () => {
      controller.abort();
    };
  }, [normalizedOverride]);

  const resolvedReadingBeds =
    (readingBedCatalog?.beds?.length ?? 0) > 0 ? readingBedCatalog!.beds : fallbackReadingBeds;
  const resolvedReadingBedDefaultId =
    (typeof readingBedCatalog?.default_id === 'string' && readingBedCatalog.default_id.trim()
      ? readingBedCatalog.default_id.trim()
      : null) ?? resolvedReadingBeds[0]?.id ?? DEFAULT_READING_BED_TRACK_ID;
  const readingBedTrackSrcById = useMemo(() => {
    const entries = resolvedReadingBeds.map((bed) => {
      const url = bed.url.startsWith('/api/') ? withBase(bed.url) : bed.url;
      return [bed.id, url] as const;
    });
    return Object.fromEntries(entries) as Record<string, string>;
  }, [resolvedReadingBeds]);

  const [readingBedTrackSelection, setReadingBedTrackSelection] = useState<string | null>(() => {
    if (typeof window === 'undefined') {
      return null;
    }
    const raw = window.localStorage.getItem(READING_BED_TRACK_STORAGE_KEY) ?? '';
    return raw.trim() ? raw.trim() : null;
  });

  useEffect(() => {
    if (!readingBedTrackSelection) {
      return;
    }
    if (readingBedTrackSrcById[readingBedTrackSelection]) {
      return;
    }
    setReadingBedTrackSelection(null);
  }, [readingBedTrackSelection, readingBedTrackSrcById]);

  const resolvedReadingBedTrackId = useMemo(() => {
    if (readingBedTrackSelection && readingBedTrackSrcById[readingBedTrackSelection]) {
      return readingBedTrackSelection;
    }
    if (readingBedTrackSrcById[resolvedReadingBedDefaultId]) {
      return resolvedReadingBedDefaultId;
    }
    return resolvedReadingBeds[0]?.id ?? DEFAULT_READING_BED_TRACK_ID;
  }, [readingBedTrackSelection, readingBedTrackSrcById, resolvedReadingBedDefaultId, resolvedReadingBeds]);

  const readingBedTrackOptions = useMemo(() => {
    return [
      { value: '', label: 'Default' },
      ...resolvedReadingBeds.map((bed) => ({ value: bed.id, label: bed.label })),
    ] satisfies ReadingBedOption[];
  }, [resolvedReadingBeds]);

  useEffect(() => {
    if (typeof window === 'undefined') {
      return;
    }
    window.localStorage.setItem(READING_BED_ENABLED_STORAGE_KEY, readingBedEnabled ? 'true' : 'false');
  }, [readingBedEnabled]);

  useEffect(() => {
    if (typeof window === 'undefined') {
      return;
    }
    window.localStorage.setItem(READING_BED_VOLUME_STORAGE_KEY, String(readingBedVolumePercent));
  }, [readingBedVolumePercent]);

  useEffect(() => {
    if (typeof window === 'undefined') {
      return;
    }
    if (!readingBedTrackSelection) {
      window.localStorage.removeItem(READING_BED_TRACK_STORAGE_KEY);
      return;
    }
    window.localStorage.setItem(READING_BED_TRACK_STORAGE_KEY, String(readingBedTrackSelection));
  }, [readingBedTrackSelection]);

  useEffect(() => {
    readingBed.setVolume((Math.min(Math.max(readingBedVolumePercent, 0), 100) / 100) * 0.8);
  }, [readingBed, readingBedVolumePercent]);

  useEffect(() => {
    const src =
      readingBedTrackSrcById[resolvedReadingBedTrackId] ?? readingBedTrackSrcById[DEFAULT_READING_BED_TRACK_ID];
    readingBed.setSource(src);
  }, [readingBed, readingBedTrackSrcById, resolvedReadingBedTrackId]);

  useEffect(() => {
    if (!readingBedEnabled) {
      void readingBed.pause();
      return;
    }
    void readingBed.play();
  }, [readingBed, readingBedEnabled]);

  const playReadingBed = useCallback(() => {
    void readingBed.play();
  }, [readingBed]);

  const pauseReadingBed = useCallback(() => {
    void readingBed.pause();
  }, [readingBed]);

  const resetReadingBed = useCallback(() => {
    setReadingBedEnabled(true);
    setReadingBedVolumePercent(DEFAULT_READING_BED_VOLUME_PERCENT);
    setReadingBedTrackSelection(null);
    void readingBed.pause();
  }, [readingBed]);

  const toggleReadingBed = useCallback(() => {
    setReadingBedEnabled((current) => {
      const next = !current;
      if (next) {
        void readingBed.play();
      } else {
        void readingBed.pause();
      }
      return next;
    });
  }, [readingBed]);

  const handleReadingBedVolumeChange = useCallback(
    (value: number) => {
      const clamped = Math.round(Math.min(Math.max(value, 0), 100));
      setReadingBedVolumePercent(clamped);
      if (readingBedEnabled) {
        void readingBed.play();
      }
    },
    [readingBed, readingBedEnabled],
  );

  const handleReadingBedTrackChange = useCallback(
    (value: string) => {
      const nextSelection = value.trim() ? value.trim() : null;
      setReadingBedTrackSelection(nextSelection);
      const resolvedId =
        (nextSelection && readingBedTrackSrcById[nextSelection] ? nextSelection : null) ?? resolvedReadingBedDefaultId;
      const src = readingBedTrackSrcById[resolvedId] ?? readingBedTrackSrcById[DEFAULT_READING_BED_TRACK_ID];
      readingBed.setSource(src);
      if (readingBedEnabled) {
        void readingBed.play();
      }
    },
    [readingBed, readingBedEnabled, readingBedTrackSrcById, resolvedReadingBedDefaultId],
  );

  return {
    readingBedEnabled,
    readingBedVolumePercent,
    readingBedTrackSelection,
    readingBedTrackOptions,
    readingBedSupported: readingBed.supported,
    toggleReadingBed,
    onReadingBedVolumeChange: handleReadingBedVolumeChange,
    onReadingBedTrackChange: handleReadingBedTrackChange,
    playReadingBed,
    pauseReadingBed,
    resetReadingBed,
  };
}
