import { useCallback, useEffect, useMemo } from 'react';
import type { LiveMediaChunk, LiveMediaItem } from '../../hooks/useLiveMedia';
import type { AudioTrackMetadata } from '../../api/dtos';
import { appendAccessToken, buildStorageUrl, resolveLibraryMediaUrl } from '../../api/client';
import { formatChunkLabel, isAudioFileType } from './utils';
import { isCombinedAudioCandidate, isOriginalAudioCandidate } from './helpers';

export type InlineAudioKind = 'translation' | 'combined' | 'other';

export type InlineAudioOption = {
  url: string;
  label: string;
  kind: InlineAudioKind;
};

type UseInlineAudioOptionsArgs = {
  jobId: string | null;
  origin: 'job' | 'library';
  activeTextChunk: LiveMediaChunk | null;
  resolvedActiveTextChunk: LiveMediaChunk | null;
  activeTextChunkIndex: number;
  interactiveAudioNameMap: Map<string, string>;
  interactiveAudioPlaylist: LiveMediaItem[];
  inlineAudioSelection: string | null;
  showOriginalAudio: boolean;
  setShowOriginalAudio: React.Dispatch<React.SetStateAction<boolean>>;
  setInlineAudioSelection: React.Dispatch<React.SetStateAction<string | null>>;
};

type UseInlineAudioOptionsResult = {
  activeAudioTracks: Record<string, AudioTrackMetadata> | null;
  inlineAudioOptions: InlineAudioOption[];
  visibleInlineAudioOptions: InlineAudioOption[];
  inlineAudioUnavailable: boolean;
  hasCombinedAudio: boolean;
  canToggleOriginalAudio: boolean;
  effectiveOriginalAudioEnabled: boolean;
  handleOriginalAudioToggle: () => void;
  activeTimingTrack: 'mix' | 'translation';
  combinedTrackUrl: string | null;
  translationTrackUrl: string | null;
};

export function useInlineAudioOptions({
  jobId,
  origin,
  activeTextChunk,
  resolvedActiveTextChunk,
  activeTextChunkIndex,
  interactiveAudioNameMap,
  interactiveAudioPlaylist,
  inlineAudioSelection,
  showOriginalAudio,
  setShowOriginalAudio,
  setInlineAudioSelection,
}: UseInlineAudioOptionsArgs): UseInlineAudioOptionsResult {
  const normalisedJobId = jobId ?? '';

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
  }, [normalisedJobId, origin, resolvedActiveTextChunk]);

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

  const hasCombinedAudio = Boolean(
    activeAudioTracks?.orig_trans?.url || activeAudioTracks?.orig_trans?.path,
  );
  const hasLegacyOriginal = Boolean(activeAudioTracks?.orig?.url || activeAudioTracks?.orig?.path);
  const canToggleOriginalAudio = hasCombinedAudio || hasLegacyOriginal;
  const effectiveOriginalAudioEnabled = showOriginalAudio && hasCombinedAudio;
  const visibleInlineAudioOptions = useMemo<InlineAudioOption[]>(() => {
    if (showOriginalAudio && hasCombinedAudio) {
      return inlineAudioOptions.filter((option) => option.kind === 'combined');
    }
    return inlineAudioOptions.filter((option) => option.kind !== 'combined' || !hasCombinedAudio);
  }, [hasCombinedAudio, inlineAudioOptions, showOriginalAudio]);

  const inlineAudioUnavailable = visibleInlineAudioOptions.length === 0;
  const handleOriginalAudioToggle = useCallback(() => {
    if (!hasCombinedAudio) {
      return;
    }
    setShowOriginalAudio((current) => !current);
  }, [hasCombinedAudio, setShowOriginalAudio]);

  useEffect(() => {
    if (!hasCombinedAudio && showOriginalAudio) {
      setShowOriginalAudio(false);
    }
  }, [hasCombinedAudio, setShowOriginalAudio, showOriginalAudio]);

  const combinedTrackUrl = activeAudioTracks?.orig_trans?.url ?? null;
  const translationTrackUrl =
    activeAudioTracks?.translation?.url ?? activeAudioTracks?.trans?.url ?? null;

  useEffect(() => {
    if (!hasCombinedAudio) {
      return;
    }
    setInlineAudioSelection((current) => {
      if (showOriginalAudio) {
        if (combinedTrackUrl && current !== combinedTrackUrl) {
          return combinedTrackUrl;
        }
        return combinedTrackUrl ?? current;
      }
      if (combinedTrackUrl && current === combinedTrackUrl) {
        if (translationTrackUrl) {
          return translationTrackUrl;
        }
        return null;
      }
      return current;
    });
  }, [combinedTrackUrl, hasCombinedAudio, setInlineAudioSelection, showOriginalAudio, translationTrackUrl]);

  const activeTimingTrack: 'mix' | 'translation' =
    combinedTrackUrl &&
    ((inlineAudioSelection && inlineAudioSelection === combinedTrackUrl) ||
      (!inlineAudioSelection && effectiveOriginalAudioEnabled))
      ? 'mix'
      : 'translation';

  return {
    activeAudioTracks,
    inlineAudioOptions,
    visibleInlineAudioOptions,
    inlineAudioUnavailable,
    hasCombinedAudio,
    canToggleOriginalAudio,
    effectiveOriginalAudioEnabled,
    handleOriginalAudioToggle,
    activeTimingTrack,
    combinedTrackUrl,
    translationTrackUrl,
  };
}
