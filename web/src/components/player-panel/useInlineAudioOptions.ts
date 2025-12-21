import { useCallback, useEffect, useMemo } from 'react';
import type { LiveMediaChunk, LiveMediaItem } from '../../hooks/useLiveMedia';
import type { AudioTrackMetadata } from '../../api/dtos';
import { appendAccessToken, buildStorageUrl, resolveLibraryMediaUrl } from '../../api/client';
import { coerceExportPath } from '../../utils/storageResolver';
import { formatChunkLabel, isAudioFileType } from './utils';
import { isCombinedAudioCandidate, isOriginalAudioCandidate } from './helpers';

export type InlineAudioKind = 'translation' | 'combined' | 'original' | 'other';

export type InlineAudioOption = {
  url: string;
  label: string;
  kind: InlineAudioKind;
};

type UseInlineAudioOptionsArgs = {
  jobId: string | null;
  origin: 'job' | 'library';
  playerMode?: 'online' | 'export';
  activeTextChunk: LiveMediaChunk | null;
  resolvedActiveTextChunk: LiveMediaChunk | null;
  activeTextChunkIndex: number;
  interactiveAudioNameMap: Map<string, string>;
  interactiveAudioPlaylist: LiveMediaItem[];
  inlineAudioSelection: string | null;
  showOriginalAudio: boolean;
  setShowOriginalAudio: React.Dispatch<React.SetStateAction<boolean>>;
  showTranslationAudio: boolean;
  setShowTranslationAudio: React.Dispatch<React.SetStateAction<boolean>>;
  setInlineAudioSelection: React.Dispatch<React.SetStateAction<string | null>>;
};

type UseInlineAudioOptionsResult = {
  activeAudioTracks: Record<string, AudioTrackMetadata> | null;
  inlineAudioOptions: InlineAudioOption[];
  visibleInlineAudioOptions: InlineAudioOption[];
  inlineAudioUnavailable: boolean;
  hasCombinedAudio: boolean;
  canToggleOriginalAudio: boolean;
  canToggleTranslationAudio: boolean;
  effectiveOriginalAudioEnabled: boolean;
  effectiveTranslationAudioEnabled: boolean;
  handleOriginalAudioToggle: () => void;
  handleTranslationAudioToggle: () => void;
  activeTimingTrack: 'mix' | 'translation' | 'original';
  combinedTrackUrl: string | null;
  originalTrackUrl: string | null;
  translationTrackUrl: string | null;
};

export function useInlineAudioOptions({
  jobId,
  origin,
  playerMode = 'online',
  activeTextChunk,
  resolvedActiveTextChunk,
  activeTextChunkIndex,
  interactiveAudioNameMap,
  interactiveAudioPlaylist,
  inlineAudioSelection,
  showOriginalAudio,
  setShowOriginalAudio,
  showTranslationAudio,
  setShowTranslationAudio,
  setInlineAudioSelection,
}: UseInlineAudioOptionsArgs): UseInlineAudioOptionsResult {
  const normalisedJobId = jobId ?? '';
  const isExportMode = playerMode === 'export';

  const activeAudioTracks = useMemo(() => {
    const chunkRef = resolvedActiveTextChunk;
    if (!normalisedJobId || !chunkRef) {
      return null;
    }
    const tracks = chunkRef.audioTracks ?? null;
    const files = chunkRef.files ?? [];
    const mapping: Record<string, AudioTrackMetadata> = {};

    const normaliseSource = (source: string | null | undefined) => {
      if (!source) {
        return null;
      }
      const trimmed = source.trim();
      if (!trimmed) {
        return null;
      }
      if (isExportMode) {
        return coerceExportPath(trimmed, normalisedJobId);
      }
      if (trimmed.includes('://')) {
        return trimmed;
      }
      if (trimmed.startsWith('/')) {
        if (origin === 'library') {
          return appendAccessToken(trimmed);
        }
        return trimmed;
      }
      if (origin === 'library') {
        const resolved = resolveLibraryMediaUrl(normalisedJobId, trimmed);
        return resolved ?? appendAccessToken(trimmed);
      }
      return buildStorageUrl(trimmed, normalisedJobId);
    };

    const registerTrack = (key: string, descriptor: AudioTrackMetadata | string | null | undefined) => {
      if (!key || !descriptor) {
        return;
      }
      let payload: AudioTrackMetadata;
      if (typeof descriptor === 'string') {
        payload = { path: descriptor };
      } else {
        payload = { ...descriptor };
      }
      const resolved = normaliseSource(payload.url ?? payload.path ?? null);
      if (resolved) {
        payload.url = resolved;
      }
      if (payload.path && !payload.url) {
        payload.url = normaliseSource(payload.path);
      }
      const existing = mapping[key] ?? {};
      mapping[key] = { ...existing, ...payload };
    };

    if (tracks) {
      Object.entries(tracks).forEach(([key, value]) => {
        const normalisedKey = key === 'trans' ? 'translation' : key;
        if (typeof value === 'string' || (value && typeof value === 'object')) {
          registerTrack(normalisedKey, value as AudioTrackMetadata | string);
        }
      });
    }

    files.forEach((file) => {
      if (!file || typeof file !== 'object') {
        return;
      }
      if (!isAudioFileType(file.type)) {
        return;
      }
      const relativePath = typeof file.relative_path === 'string' ? file.relative_path : '';
      const displayName = typeof file.name === 'string' ? file.name : '';
      const isCombinedCandidate = isCombinedAudioCandidate(relativePath, displayName);
      const descriptor: AudioTrackMetadata = {
        path: typeof file.relative_path === 'string' ? file.relative_path : undefined,
        url: typeof file.url === 'string' ? file.url : undefined,
      };
      if (isCombinedCandidate) {
        registerTrack('orig_trans', descriptor);
        return;
      }
      const isOriginalCandidate = isOriginalAudioCandidate(relativePath, displayName);
      if (isOriginalCandidate) {
        registerTrack('orig', descriptor);
        return;
      }
      if (!mapping.translation) {
        registerTrack('translation', descriptor);
      }
    });

    return Object.keys(mapping).length > 0 ? mapping : null;
  }, [isExportMode, normalisedJobId, origin, resolvedActiveTextChunk]);

  const inlineAudioOptions = useMemo<InlineAudioOption[]>(() => {
    const seen = new Set<string>();
    const options: InlineAudioOption[] = [];
    const register = (
      url: string | null | undefined,
      label: string | null | undefined,
      kind: InlineAudioKind,
    ) => {
      if (!url || seen.has(url)) {
        return;
      }
      const trimmedLabel = typeof label === 'string' ? label.trim() : '';
      options.push({
        url,
        label: trimmedLabel || `Audio ${options.length + 1}`,
        kind,
      });
      seen.add(url);
    };
    const chunkForOptions = resolvedActiveTextChunk ?? activeTextChunk;
    if (chunkForOptions && activeTextChunkIndex >= 0) {
      chunkForOptions.files.forEach((file) => {
        if (!isAudioFileType(file.type) || !file.url) {
          return;
        }
        const relativePath = typeof file.relative_path === 'string' ? file.relative_path : '';
        const displayName = typeof file.name === 'string' ? file.name : '';
        const isCombined = isCombinedAudioCandidate(relativePath, displayName);
        if (isOriginalAudioCandidate(relativePath, displayName) && !isCombined) {
          return;
        }
        const label =
          interactiveAudioNameMap.get(file.url) ??
          (typeof file.name === 'string' ? file.name.trim() : '') ??
          formatChunkLabel(chunkForOptions, activeTextChunkIndex);
        register(file.url, label, isCombined ? 'combined' : 'translation');
      });
    }
    if (activeAudioTracks) {
      Object.entries(activeAudioTracks).forEach(([key, metadata]) => {
        if (!metadata?.url || seen.has(metadata.url)) {
          return;
        }
        const label =
          key === 'orig_trans'
            ? 'Original + Translation'
            : key === 'translation'
              ? 'Translation'
              : key === 'orig'
                ? 'Original'
                : `Audio (${key})`;
        let kind: InlineAudioKind = 'other';
        if (key === 'orig_trans') {
          kind = 'combined';
        } else if (key === 'translation' || key === 'trans') {
          kind = 'translation';
        } else if (key === 'orig') {
          kind = 'original';
        }
        register(metadata.url, label, kind);
      });
    }
    interactiveAudioPlaylist.forEach((item, index) => {
      register(item.url, item.name ?? `Audio ${index + 1}`, 'translation');
    });
    return options;
  }, [
    activeAudioTracks,
    activeTextChunk,
    activeTextChunkIndex,
    interactiveAudioNameMap,
    interactiveAudioPlaylist,
    resolvedActiveTextChunk,
  ]);

  const combinedTrackUrl =
    activeAudioTracks?.orig_trans?.url ?? activeAudioTracks?.orig_trans?.path ?? null;
  const originalTrackUrl = activeAudioTracks?.orig?.url ?? activeAudioTracks?.orig?.path ?? null;
  const translationTrackUrl =
    activeAudioTracks?.translation?.url ??
    activeAudioTracks?.translation?.path ??
    activeAudioTracks?.trans?.url ??
    activeAudioTracks?.trans?.path ??
    null;

  const hasOriginalAudio = Boolean(originalTrackUrl);
  const hasTranslationAudio = Boolean(translationTrackUrl);
  const hasCombinedAudio = Boolean(combinedTrackUrl) && (!hasOriginalAudio || !hasTranslationAudio);
  const canToggleOriginalAudio = hasOriginalAudio || hasCombinedAudio;
  const canToggleTranslationAudio = hasTranslationAudio || hasCombinedAudio;
  const effectiveOriginalAudioEnabled = showOriginalAudio && canToggleOriginalAudio;
  const effectiveTranslationAudioEnabled = showTranslationAudio && canToggleTranslationAudio;
  const visibleInlineAudioOptions = useMemo<InlineAudioOption[]>(() => {
    if (!showOriginalAudio && !showTranslationAudio) {
      return [];
    }
    return inlineAudioOptions.filter((option) => {
      if (option.kind === 'combined') {
        return hasCombinedAudio && (showOriginalAudio || showTranslationAudio);
      }
      if (option.kind === 'original') {
        return showOriginalAudio;
      }
      if (option.kind === 'translation') {
        return showTranslationAudio;
      }
      return true;
    });
  }, [hasCombinedAudio, inlineAudioOptions, showOriginalAudio, showTranslationAudio]);

  const inlineAudioUnavailable = inlineAudioOptions.length === 0;
  const handleOriginalAudioToggle = useCallback(() => {
    if (!hasOriginalAudio && !hasCombinedAudio) {
      return;
    }
    setShowOriginalAudio((current) => !current);
  }, [hasCombinedAudio, hasOriginalAudio, setShowOriginalAudio]);
  const handleTranslationAudioToggle = useCallback(() => {
    if (!hasTranslationAudio && !hasCombinedAudio) {
      return;
    }
    setShowTranslationAudio((current) => !current);
  }, [hasCombinedAudio, hasTranslationAudio, setShowTranslationAudio]);

  useEffect(() => {
    if (!hasCombinedAudio && !hasOriginalAudio && showOriginalAudio) {
      setShowOriginalAudio(false);
    }
  }, [hasCombinedAudio, hasOriginalAudio, setShowOriginalAudio, showOriginalAudio]);
  useEffect(() => {
    if (!hasCombinedAudio && !hasTranslationAudio && showTranslationAudio) {
      setShowTranslationAudio(false);
    }
  }, [hasCombinedAudio, hasTranslationAudio, setShowTranslationAudio, showTranslationAudio]);

  useEffect(() => {
    if (!hasCombinedAudio && !hasOriginalAudio && !hasTranslationAudio) {
      return;
    }
    const preferredOriginalUrl = originalTrackUrl ?? (hasCombinedAudio ? combinedTrackUrl : null) ?? translationTrackUrl;
    const preferredTranslationUrl =
      translationTrackUrl ?? (hasCombinedAudio ? combinedTrackUrl : null) ?? originalTrackUrl;
    setInlineAudioSelection(() => {
      if (showOriginalAudio && showTranslationAudio) {
        return preferredTranslationUrl ?? preferredOriginalUrl ?? null;
      }
      if (showOriginalAudio) {
        return preferredOriginalUrl ?? null;
      }
      if (showTranslationAudio) {
        return preferredTranslationUrl ?? null;
      }
      return null;
    });
  }, [
    combinedTrackUrl,
    hasCombinedAudio,
    hasOriginalAudio,
    hasTranslationAudio,
    originalTrackUrl,
    setInlineAudioSelection,
    showOriginalAudio,
    showTranslationAudio,
    translationTrackUrl,
  ]);

  const activeTimingTrack: 'mix' | 'translation' | 'original' = (() => {
    if (inlineAudioSelection) {
      if (originalTrackUrl && inlineAudioSelection === originalTrackUrl) {
        return 'original';
      }
      if (combinedTrackUrl && inlineAudioSelection === combinedTrackUrl) {
        return 'mix';
      }
      return 'translation';
    }
    if (showOriginalAudio && !showTranslationAudio) {
      if (originalTrackUrl) {
        return 'original';
      }
      if (hasCombinedAudio && combinedTrackUrl) {
        return 'mix';
      }
      return 'translation';
    }
    if (showTranslationAudio) {
      if (translationTrackUrl) {
        return 'translation';
      }
      if (hasCombinedAudio && combinedTrackUrl) {
        return 'mix';
      }
      if (originalTrackUrl) {
        return 'original';
      }
    }
    return 'translation';
  })();

  return {
    activeAudioTracks,
    inlineAudioOptions,
    visibleInlineAudioOptions,
    inlineAudioUnavailable,
    hasCombinedAudio,
    canToggleOriginalAudio,
    canToggleTranslationAudio,
    effectiveOriginalAudioEnabled,
    effectiveTranslationAudioEnabled,
    handleOriginalAudioToggle,
    handleTranslationAudioToggle,
    activeTimingTrack,
    combinedTrackUrl,
    originalTrackUrl,
    translationTrackUrl,
  };
}
