import { useCallback, useEffect, useId, useMemo, useRef, useState } from 'react';
import type { ChangeEvent, UIEvent } from 'react';
import VideoPlayer from './VideoPlayer';
import type { LiveMediaChunk, LiveMediaItem, LiveMediaState } from '../hooks/useLiveMedia';
import { useMediaMemory } from '../hooks/useMediaMemory';
import { Tabs, TabsContent, TabsList, TabsTrigger } from './ui/Tabs';
import { extractTextFromHtml } from '../utils/mediaFormatters';
import {
  DEFAULT_TRANSLATION_SPEED,
  TRANSLATION_SPEED_MAX,
  TRANSLATION_SPEED_MIN,
  TRANSLATION_SPEED_STEP,
  formatTranslationSpeedLabel,
  normaliseTranslationSpeed,
  type TranslationSpeed,
} from './player-panel/constants';
import MediaSearchPanel from './MediaSearchPanel';
import type { ChunkSentenceMetadata, MediaSearchResult } from '../api/dtos';
import { appendAccessToken, buildStorageUrl, resolveJobCoverUrl, resolveLibraryMediaUrl } from '../api/client';
import InteractiveTextViewer from './InteractiveTextViewer';
import { resolve as resolveStoragePath } from '../utils/storageResolver';
import type { LibraryOpenInput, LibraryOpenRequest, MediaSelectionRequest } from '../types/player';

const MEDIA_CATEGORIES = ['text', 'audio', 'video'] as const;
type MediaCategory = (typeof MEDIA_CATEGORIES)[number];
type SearchCategory = Exclude<MediaCategory, 'audio'> | 'library';
type NavigationIntent = 'first' | 'previous' | 'next' | 'last';
type PlaybackControls = {
  pause: () => void;
  play: () => void;
};

interface PlayerPanelProps {
  jobId: string;
  media: LiveMediaState;
  chunks: LiveMediaChunk[];
  mediaComplete: boolean;
  isLoading: boolean;
  error: Error | null;
  bookMetadata?: Record<string, unknown> | null;
  onVideoPlaybackStateChange?: (isPlaying: boolean) => void;
  onPlaybackStateChange?: (isPlaying: boolean) => void;
  onFullscreenChange?: (isFullscreen: boolean) => void;
  origin?: 'job' | 'library';
  onOpenLibraryItem?: (item: LibraryOpenInput) => void;
  selectionRequest?: MediaSelectionRequest | null;
}

interface TabDefinition {
  key: MediaCategory;
  label: string;
  emptyMessage: string;
}

const TAB_DEFINITIONS: TabDefinition[] = [
  { key: 'text', label: 'Interactive Reader', emptyMessage: 'No interactive reader media yet.' },
  { key: 'video', label: 'Video', emptyMessage: 'No video media yet.' },
];

const DEFAULT_COVER_URL = '/assets/default-cover.png';

interface NavigationControlsProps {
  context: 'panel' | 'fullscreen';
  onNavigate: (intent: NavigationIntent) => void;
  onToggleFullscreen: () => void;
  onTogglePlayback: () => void;
  disableFirst: boolean;
  disablePrevious: boolean;
  disableNext: boolean;
  disableLast: boolean;
  disablePlayback: boolean;
  disableFullscreen: boolean;
  isFullscreen: boolean;
  isPlaying: boolean;
  fullscreenLabel: string;
  inlineAudioOptions: { url: string; label: string }[];
  inlineAudioSelection: string | null;
  onSelectInlineAudio: (audioUrl: string) => void;
  showInlineAudio: boolean;
  showOriginalAudioToggle?: boolean;
  onToggleOriginalAudio?: () => void;
  originalAudioEnabled?: boolean;
  disableOriginalAudioToggle?: boolean;
  showTranslationSpeed: boolean;
  translationSpeed: TranslationSpeed;
  translationSpeedMin: number;
  translationSpeedMax: number;
  translationSpeedStep: number;
  onTranslationSpeedChange: (value: TranslationSpeed) => void;
}

function NavigationControls({
  context,
  onNavigate,
  onToggleFullscreen,
  onTogglePlayback,
  disableFirst,
  disablePrevious,
  disableNext,
  disableLast,
  disablePlayback,
  disableFullscreen,
  isFullscreen,
  isPlaying,
  fullscreenLabel,
  inlineAudioOptions,
  inlineAudioSelection,
  onSelectInlineAudio,
  showInlineAudio,
  showOriginalAudioToggle = false,
  onToggleOriginalAudio,
  originalAudioEnabled = false,
  disableOriginalAudioToggle = false,
  showTranslationSpeed,
  translationSpeed,
  translationSpeedMin,
  translationSpeedMax,
  translationSpeedStep,
  onTranslationSpeedChange,
}: NavigationControlsProps) {
  const inlineAudioId =
    context === 'fullscreen' ? 'player-panel-inline-audio-fullscreen' : 'player-panel-inline-audio';
  const groupClassName =
    context === 'fullscreen'
      ? 'player-panel__navigation-group player-panel__navigation-group--fullscreen'
      : 'player-panel__navigation-group';
  const navigationClassName =
    context === 'fullscreen'
      ? 'player-panel__navigation player-panel__navigation--fullscreen'
      : 'player-panel__navigation';
  const inlineAudioClassName =
    context === 'fullscreen'
      ? 'player-panel__inline-audio player-panel__inline-audio--fullscreen'
      : 'player-panel__inline-audio';
  const fullscreenTestId = context === 'panel' ? 'player-panel-interactive-fullscreen' : undefined;
  const playbackLabel = isPlaying ? 'Pause playback' : 'Play playback';
  const playbackIcon = isPlaying ? '⏸' : '▶';
  const originalToggleClassName = ['player-panel__nav-button', 'player-panel__nav-button--audio', originalAudioEnabled ? 'player-panel__nav-button--audio-on' : 'player-panel__nav-button--audio-off'].join(' ');
  const originalToggleTitle = disableOriginalAudioToggle
    ? 'Original audio will appear after interactive assets regenerate'
    : 'Toggle Original Audio';
  const sliderId = useId();
  const formattedSpeed = formatTranslationSpeedLabel(translationSpeed);
  const handleSpeedChange = (event: ChangeEvent<HTMLInputElement>) => {
    const raw = Number.parseFloat(event.target.value);
    if (!Number.isFinite(raw)) {
      return;
    }
    onTranslationSpeedChange(raw);
  };

  return (
    <div className={groupClassName}>
      <div className={navigationClassName} role="group" aria-label="Navigate media items">
        <button
          type="button"
          className="player-panel__nav-button"
          onClick={() => onNavigate('first')}
          disabled={disableFirst}
          aria-label="Go to first item"
        >
          <span aria-hidden="true">⏮</span>
        </button>
        <button
          type="button"
          className="player-panel__nav-button"
          onClick={() => onNavigate('previous')}
          disabled={disablePrevious}
          aria-label="Go to previous item"
        >
          <span aria-hidden="true">⏪</span>
        </button>
        <button
          type="button"
          className="player-panel__nav-button"
          onClick={onTogglePlayback}
          disabled={disablePlayback}
          aria-label={playbackLabel}
          aria-pressed={isPlaying ? 'true' : 'false'}
        >
          <span aria-hidden="true">{playbackIcon}</span>
        </button>
        <button
          type="button"
          className="player-panel__nav-button"
          onClick={() => onNavigate('next')}
          disabled={disableNext}
          aria-label="Go to next item"
        >
          <span aria-hidden="true">⏩</span>
        </button>
        <button
          type="button"
          className="player-panel__nav-button"
          onClick={() => onNavigate('last')}
          disabled={disableLast}
          aria-label="Go to last item"
        >
          <span aria-hidden="true">⏭</span>
        </button>
        {showOriginalAudioToggle ? (
          <button
            type="button"
            className={originalToggleClassName}
            onClick={onToggleOriginalAudio}
            disabled={disableOriginalAudioToggle}
            aria-label="Toggle Original Audio"
            aria-pressed={originalAudioEnabled}
            title={originalToggleTitle}
          >
            <span aria-hidden="true" className="player-panel__nav-button-icon">
              {originalAudioEnabled ? '🎧' : '🎵'}
            </span>
            <span aria-hidden="true" className="player-panel__nav-button-text">
              Orig
            </span>
          </button>
        ) : null}
        <button
          type="button"
          className="player-panel__nav-button"
          onClick={onToggleFullscreen}
          disabled={disableFullscreen}
          aria-pressed={isFullscreen}
          aria-label={fullscreenLabel}
          data-testid={fullscreenTestId}
        >
          <span aria-hidden="true">⛶</span>
        </button>
      </div>
      {showTranslationSpeed ? (
        <div className="player-panel__nav-speed" data-testid="player-panel-speed">
          <label className="player-panel__nav-speed-label" htmlFor={sliderId}>
            Translation speed
          </label>
          <div className="player-panel__nav-speed-control">
            <input
              id={sliderId}
              type="range"
              className="player-panel__nav-speed-slider"
              min={translationSpeedMin}
              max={translationSpeedMax}
              step={translationSpeedStep}
              value={translationSpeed}
              onChange={handleSpeedChange}
              aria-label="Translation speed"
              aria-valuetext={formattedSpeed}
            />
            <span className="player-panel__nav-speed-value" aria-live="polite">
              {formattedSpeed}
            </span>
          </div>
          <div className="player-panel__nav-speed-scale" aria-hidden="true">
            <span>{formatTranslationSpeedLabel(translationSpeedMin)}</span>
            <span>{formatTranslationSpeedLabel(translationSpeedMax)}</span>
          </div>
        </div>
      ) : null}
      {showInlineAudio && inlineAudioOptions.length > 0 ? (
        <div className={inlineAudioClassName} role="group" aria-label="Synchronized audio">
          <label className="player-panel__inline-audio-label" htmlFor={inlineAudioId}>
            Synchronized audio
          </label>
          <select
            id={inlineAudioId}
            value={inlineAudioSelection ?? inlineAudioOptions[0]?.url ?? ''}
            onChange={(event) => onSelectInlineAudio(event.target.value)}
            disabled={inlineAudioOptions.length === 1}
          >
            {inlineAudioOptions.map((option) => (
              <option key={`${context}-${option.url}`} value={option.url}>
                {option.label}
              </option>
            ))}
          </select>
        </div>
      ) : null}
    </div>
  );
}

function selectInitialTab(media: LiveMediaState): MediaCategory {
  const populated = TAB_DEFINITIONS.find((tab) => media[tab.key].length > 0);
  return populated?.key ?? 'text';
}

function toVideoFiles(media: LiveMediaState['video']) {
  return media
    .filter((item) => typeof item.url === 'string' && item.url.length > 0)
    .map((item, index) => ({
      id: item.url ?? `${item.type}-${index}`,
      url: item.url ?? '',
      name: item.name,
    }));
}

function deriveBaseIdFromReference(value: string | null | undefined): string | null {
  if (!value) {
    return null;
  }
  const normalised = value.replace(/^[\\/]+/, '').split(/[\\/]/).pop();
  if (!normalised) {
    return null;
  }
  const withoutQuery = normalised.replace(/[?#].*$/, '');
  const dotIndex = withoutQuery.lastIndexOf('.');
  const base = dotIndex > 0 ? withoutQuery.slice(0, dotIndex) : withoutQuery;
  const trimmed = base.trim();
  return trimmed ? trimmed.toLowerCase() : null;
}

function resolveBaseIdFromResult(result: MediaSearchResult, preferred: MediaCategory | null): string | null {
  if (result.base_id) {
    return result.base_id;
  }

  const categories: MediaCategory[] = [];
  if (preferred) {
    categories.push(preferred);
  }
  MEDIA_CATEGORIES.forEach((category) => {
    if (!categories.includes(category)) {
      categories.push(category);
    }
  });

  for (const category of categories) {
    const entries = result.media?.[category];
    if (!entries || entries.length === 0) {
      continue;
    }
    const primary = entries[0];
    const baseId =
      deriveBaseIdFromReference(primary.relative_path ?? null) ??
      deriveBaseIdFromReference(primary.name ?? null) ??
      deriveBaseIdFromReference(primary.url ?? null) ??
      deriveBaseIdFromReference(primary.path ?? null);
    if (baseId) {
      return baseId;
    }
  }

  return null;
}

function normaliseLookupToken(value: string | null | undefined): string | null {
  if (typeof value !== 'string') {
    return null;
  }
  const trimmed = value.trim();
  if (!trimmed) {
    return null;
  }
  const derived = deriveBaseIdFromReference(trimmed);
  if (derived) {
    return derived;
  }
  return trimmed.toLowerCase();
}

function normaliseAudioSignature(value: string | null | undefined): string {
  if (!value) {
    return '';
  }
  return value.toLowerCase().replace(/[^a-z0-9]+/g, '');
}

function isCombinedAudioCandidate(...values: (string | null | undefined)[]): boolean {
  return values.some((value) => normaliseAudioSignature(value).includes('origtrans'));
}

function isOriginalAudioCandidate(...values: (string | null | undefined)[]): boolean {
  return values.some((value) => {
    const signature = normaliseAudioSignature(value);
    return signature.includes('orig') && !signature.includes('origtrans');
  });
}

function findChunkIndexForBaseId(baseId: string | null, chunks: LiveMediaChunk[]): number {
  const target = normaliseLookupToken(baseId);
  if (!target) {
    return -1;
  }

  const matches = (candidate: string | null | undefined): boolean => {
    const normalised = normaliseLookupToken(candidate);
    return normalised !== null && normalised === target;
  };

  for (let index = 0; index < chunks.length; index += 1) {
    const chunk = chunks[index];
    if (
      matches(chunk.chunkId) ||
      matches(chunk.rangeFragment) ||
      matches(chunk.metadataPath) ||
      matches(chunk.metadataUrl)
    ) {
      return index;
    }
    for (const file of chunk.files) {
      if (
        matches(file.relative_path) ||
        matches(file.path) ||
        matches(file.url) ||
        matches(file.name)
      ) {
        return index;
      }
    }
  }

  return -1;
}

function normaliseMetadataText(value: unknown): string | null {
  if (typeof value === 'string') {
    const trimmed = value.trim();
    return trimmed.length > 0 ? trimmed : null;
  }

  if (typeof value === 'number' && Number.isFinite(value)) {
    return value.toString();
  }

  return null;
}

function extractMetadataText(
  metadata: Record<string, unknown> | null | undefined,
  keys: string[],
): string | null {
  if (!metadata) {
    return null;
  }

  for (const key of keys) {
    const raw = metadata[key];
    const normalised = normaliseMetadataText(raw);
    if (normalised) {
      return normalised;
    }
  }

  return null;
}

function formatSentenceRange(start: number | null | undefined, end: number | null | undefined): string {
  if (typeof start === 'number' && typeof end === 'number') {
    return start === end ? `${start}` : `${start}–${end}`;
  }
  if (typeof start === 'number') {
    return `${start}`;
  }
  if (typeof end === 'number') {
    return `${end}`;
  }
  return '—';
}

function formatChunkLabel(chunk: LiveMediaChunk, index: number): string {
  const rangeFragment = typeof chunk.rangeFragment === 'string' ? chunk.rangeFragment.trim() : '';
  if (rangeFragment) {
    return rangeFragment;
  }
  const chunkId = typeof chunk.chunkId === 'string' ? chunk.chunkId.trim() : '';
  if (chunkId) {
    return chunkId;
  }
  const sentenceRange = formatSentenceRange(chunk.startSentence ?? null, chunk.endSentence ?? null);
  if (sentenceRange && sentenceRange !== '—') {
    return `Chunk ${index + 1} · ${sentenceRange}`;
  }
  return `Chunk ${index + 1}`;
}

function buildInteractiveAudioCatalog(
  chunks: LiveMediaChunk[],
  audioMedia: LiveMediaItem[],
): {
  playlist: LiveMediaItem[];
  nameMap: Map<string, string>;
  chunkIndexMap: Map<string, number>;
} {
  const playlist: LiveMediaItem[] = [];
  const nameMap = new Map<string, string>();
  const chunkIndexMap = new Map<string, number>();
  const seen = new Set<string>();

  const register = (
    item: LiveMediaItem | null | undefined,
    chunkIndex: number | null,
    fallbackLabel?: string,
  ) => {
    if (!item || !item.url) {
      return;
    }
    const url = item.url;
    if (seen.has(url)) {
      return;
    }
    seen.add(url);
    const trimmedName = typeof item.name === 'string' ? item.name.trim() : '';
    const trimmedFallback = typeof fallbackLabel === 'string' ? fallbackLabel.trim() : '';
    const label = trimmedName || trimmedFallback || `Audio ${playlist.length + 1}`;
    const enriched = trimmedName ? item : { ...item, name: label };
    playlist.push(enriched);
    nameMap.set(url, label);
    if (typeof chunkIndex === 'number' && chunkIndex >= 0) {
      chunkIndexMap.set(url, chunkIndex);
    }
  };

  chunks.forEach((chunk, index) => {
    const chunkLabel = formatChunkLabel(chunk, index);
    chunk.files.forEach((file) => {
      if (file.type !== 'audio') {
        return;
      }
      register(file, index, chunkLabel);
    });
  });

  audioMedia.forEach((item) => {
    if (!item.url) {
      return;
    }
    const existingIndex = chunkIndexMap.get(item.url);
    register(item, typeof existingIndex === 'number' ? existingIndex : null, item.name);
  });

  return { playlist, nameMap, chunkIndexMap };
}

function chunkCacheKey(chunk: LiveMediaChunk): string | null {
  if (chunk.chunkId) {
    return `id:${chunk.chunkId}`;
  }
  if (chunk.rangeFragment) {
    return `range:${chunk.rangeFragment}`;
  }
  if (chunk.metadataPath) {
    return `path:${chunk.metadataPath}`;
  }
  if (chunk.metadataUrl) {
    return `url:${chunk.metadataUrl}`;
  }
  const audioUrl = chunk.files.find((file) => file.type === 'audio' && file.url)?.url;
  if (audioUrl) {
    return `audio:${audioUrl}`;
  }
  return null;
}

const CHUNK_METADATA_PREFETCH_RADIUS = 2;

async function requestChunkMetadata(
  jobId: string,
  chunk: LiveMediaChunk,
): Promise<ChunkSentenceMetadata[] | null> {
  let targetUrl: string | null = chunk.metadataUrl ?? null;

  if (!targetUrl) {
    const metadataPath = chunk.metadataPath ?? null;
    if (metadataPath) {
      try {
        targetUrl = resolveStoragePath(jobId, metadataPath);
      } catch (error) {
        if (jobId) {
          const encodedJobId = encodeURIComponent(jobId);
          const sanitizedPath = metadataPath.replace(/^\/+/, '');
          targetUrl = `/pipelines/jobs/${encodedJobId}/${encodeURI(sanitizedPath)}`;
        } else {
          console.warn('Unable to resolve chunk metadata path', metadataPath, error);
        }
      }
    }
  }

  if (!targetUrl) {
    return null;
  }

  try {
    const response = await fetch(targetUrl, { credentials: 'include' });
    if (!response.ok) {
      throw new Error(`Chunk metadata request failed with status ${response.status}`);
    }
    const payload = await response.json();
    const sentences = payload?.sentences;
    if (Array.isArray(sentences)) {
      return sentences as ChunkSentenceMetadata[];
    }
    return [];
  } catch (error) {
    console.warn('Unable to load chunk metadata', targetUrl, error);
    return null;
  }
}

export default function PlayerPanel({
  jobId,
  media,
  chunks,
  mediaComplete,
  isLoading,
  error,
  bookMetadata = null,
  onVideoPlaybackStateChange,
  onPlaybackStateChange,
  onFullscreenChange,
  origin = 'job',
  onOpenLibraryItem,
  selectionRequest = null,
}: PlayerPanelProps) {
  const interactiveViewerAvailable = chunks.length > 0;
  const [selectedMediaType, setSelectedMediaType] = useState<MediaCategory>(() =>
    interactiveViewerAvailable ? 'text' : selectInitialTab(media),
  );
  const [selectedItemIds, setSelectedItemIds] = useState<Record<MediaCategory, string | null>>(() => {
    const initial: Record<MediaCategory, string | null> = {
      text: null,
      audio: null,
      video: null,
    };

    MEDIA_CATEGORIES.forEach((category) => {
      const firstItem = media[category][0];
      initial[category] = firstItem?.url ?? null;
  });

  return initial;
});
const [pendingSelection, setPendingSelection] = useState<MediaSelectionRequest | null>(null);
const [pendingChunkSelection, setPendingChunkSelection] = useState<{ index: number; token: number } | null>(null);
const [pendingTextScrollRatio, setPendingTextScrollRatio] = useState<number | null>(null);
  const [showOriginalAudio, setShowOriginalAudio] = useState<boolean>(() => {
    if (typeof window === 'undefined') {
      return true;
    }
    const stored = window.localStorage.getItem('player.showOriginalAudio');
    if (stored === null) {
      return true;
    }
    return stored === 'true';
  });
  const [inlineAudioSelection, setInlineAudioSelection] = useState<string | null>(null);
  const [chunkMetadataStore, setChunkMetadataStore] = useState<Record<string, ChunkSentenceMetadata[]>>({});
  const chunkMetadataStoreRef = useRef(chunkMetadataStore);
  const chunkMetadataLoadingRef = useRef<Set<string>>(new Set());
  const [isVideoPlaying, setIsVideoPlaying] = useState(false);
  const [isInlineAudioPlaying, setIsInlineAudioPlaying] = useState(false);
  const [coverSourceIndex, setCoverSourceIndex] = useState(0);
  const resolveStoredInteractiveFullscreenPreference = () => {
    if (typeof window === 'undefined') {
      return false;
    }
    return window.localStorage.getItem('player.textFullscreenPreferred') === 'true';
  };
  const [isImmersiveMode, setIsImmersiveMode] = useState(false);
  const [isInteractiveFullscreen, setIsInteractiveFullscreen] = useState<boolean>(() =>
    resolveStoredInteractiveFullscreenPreference(),
  );
  const interactiveFullscreenPreferenceRef = useRef<boolean>(isInteractiveFullscreen);
  const updateInteractiveFullscreenPreference = useCallback((next: boolean) => {
    interactiveFullscreenPreferenceRef.current = next;
    if (typeof window !== 'undefined') {
      window.localStorage.setItem('player.textFullscreenPreferred', next ? 'true' : 'false');
    }
  }, []);
  const hasJobId = Boolean(jobId);
  const normalisedJobId = jobId ?? '';
  const isVideoTabActive = selectedMediaType === 'video';
  const isTextTabActive = selectedMediaType === 'text';
  const visibleTabs = useMemo(() => {
    return TAB_DEFINITIONS.filter((tab) => tab.key !== 'video' || media.video.length > 0);
  }, [media.video.length]);
  const defaultTab = useMemo(() => selectInitialTab(media), [media]);
  const mediaMemory = useMediaMemory({ jobId });
  const { state: memoryState, rememberSelection, rememberPosition, getPosition, findMatchingMediaId, deriveBaseId } = mediaMemory;
  const textScrollRef = useRef<HTMLDivElement | null>(null);
  const videoControlsRef = useRef<PlaybackControls | null>(null);
  const inlineAudioControlsRef = useRef<PlaybackControls | null>(null);
  const hasSkippedInitialRememberRef = useRef(false);
  const inlineAudioBaseRef = useRef<string | null>(null);
  const [hasVideoControls, setHasVideoControls] = useState(false);
  const [hasInlineAudioControls, setHasInlineAudioControls] = useState(false);
  const [translationSpeed, setTranslationSpeed] = useState<TranslationSpeed>(DEFAULT_TRANSLATION_SPEED);

  useEffect(() => {
    if (!selectionRequest) {
      return;
    }
    setPendingSelection({
      baseId: selectionRequest.baseId,
      preferredType: selectionRequest.preferredType ?? null,
      offsetRatio: selectionRequest.offsetRatio ?? null,
      approximateTime: selectionRequest.approximateTime ?? null,
      token: selectionRequest.token ?? Date.now(),
    });
  }, [selectionRequest]);

  useEffect(() => {
    chunkMetadataStoreRef.current = chunkMetadataStore;
  }, [chunkMetadataStore]);
  const mediaIndex = useMemo(() => {
    const map: Record<MediaCategory, Map<string, LiveMediaItem>> = {
      text: new Map(),
      audio: new Map(),
      video: new Map(),
    };

    MEDIA_CATEGORIES.forEach((category) => {
      media[category].forEach((item) => {
        if (item.url) {
          map[category].set(item.url, item);
        }
      });
    });

    return map;
  }, [media]);

  const jobCoverAsset = useMemo(() => {
    const value = bookMetadata?.['job_cover_asset'];
    if (typeof value !== 'string') {
      return null;
    }
    const trimmed = value.trim();
    return trimmed.length > 0 ? trimmed : null;
  }, [bookMetadata]);

  const legacyCoverFile = useMemo(() => {
    const value = bookMetadata?.['book_cover_file'];
    if (typeof value !== 'string') {
      return null;
    }
    const trimmed = value.trim();
    return trimmed.length > 0 ? trimmed : null;
  }, [bookMetadata]);

  const apiCoverUrl = useMemo(() => {
    if (!hasJobId || origin === 'library') {
      return null;
    }
    return resolveJobCoverUrl(normalisedJobId);
  }, [hasJobId, normalisedJobId, origin]);

  const coverCandidates = useMemo(() => {
    const candidates: string[] = [];
    const unique = new Set<string>();

    const convertCandidate = (value: string | null | undefined): string | null => {
      if (typeof value !== 'string') {
        return null;
      }
      const trimmed = value.trim();
      if (!trimmed) {
        return null;
      }

      if (origin === 'library' && trimmed.includes('/pipelines/')) {
        return null;
      }

      if (/^https?:\/\//i.test(trimmed)) {
        if (origin === 'library' && trimmed.includes('/pipelines/')) {
          return null;
        }
        return appendAccessToken(trimmed);
      }

      if (/^\/?assets\//i.test(trimmed)) {
        return trimmed.startsWith('/') ? trimmed : `/${trimmed}`;
      }

       if (origin === 'library' && trimmed.startsWith('/') && !trimmed.startsWith('/api/library/')) {
         return null;
       }

      if (origin === 'library') {
        if (trimmed.includes('/pipelines/')) {
          return null;
        }
        if (trimmed.startsWith('/api/library/')) {
          return appendAccessToken(trimmed);
        }
        if (trimmed.startsWith('/')) {
          return null;
        }
        const resolved = resolveLibraryMediaUrl(normalisedJobId, trimmed);
        return resolved ? appendAccessToken(resolved) : null;
      }

      if (trimmed.startsWith('/api/library/')) {
        return appendAccessToken(trimmed);
      }
      if (trimmed.startsWith('/pipelines/')) {
        return appendAccessToken(trimmed);
      }

      const stripped = trimmed.replace(/^\/+/, '');
      if (!stripped) {
        return null;
      }
      try {
        return buildStorageUrl(stripped, normalisedJobId);
      } catch (error) {
        console.warn('Unable to build storage URL for cover image', error);
        return `/${stripped}`;
      }
    };

    const push = (candidate: string | null | undefined) => {
      const resolved = convertCandidate(candidate);
      if (!resolved || unique.has(resolved)) {
        return;
      }
      unique.add(resolved);
      candidates.push(resolved);
    };

    if (apiCoverUrl) {
      push(apiCoverUrl);
    }

    const metadataCoverUrl = (() => {
      const value = bookMetadata?.['job_cover_asset_url'];
      return typeof value === 'string' ? value : null;
    })();

    if (metadataCoverUrl && !(origin === 'library' && /\/pipelines\//.test(metadataCoverUrl))) {
      push(metadataCoverUrl);
    }

    push(jobCoverAsset);
    if (legacyCoverFile && legacyCoverFile !== jobCoverAsset) {
      push(legacyCoverFile);
    }

    push(DEFAULT_COVER_URL);

    return candidates;
  }, [apiCoverUrl, bookMetadata, jobCoverAsset, legacyCoverFile, normalisedJobId, origin]);

  useEffect(() => {
    if (coverSourceIndex !== 0) {
      setCoverSourceIndex(0);
    }
  }, [coverCandidates, coverSourceIndex]);

  const displayCoverUrl = coverCandidates[coverSourceIndex] ?? DEFAULT_COVER_URL;
  const handleCoverError = useCallback(() => {
    setCoverSourceIndex((currentIndex) => {
      const nextIndex = currentIndex + 1;
      if (nextIndex >= coverCandidates.length) {
        return currentIndex;
      }
      return nextIndex;
    });
  }, [coverCandidates]);
  const shouldHandleCoverError = coverSourceIndex < coverCandidates.length - 1;
  const shouldShowCoverImage = origin === 'library' || mediaComplete;
  const coverErrorHandler = shouldShowCoverImage && shouldHandleCoverError ? handleCoverError : undefined;

  const handleSearchSelection = useCallback(
    (result: MediaSearchResult, category: SearchCategory) => {
      const preferredCategory: MediaCategory | null = category === 'library' ? 'text' : category;
      const baseId = resolveBaseIdFromResult(result, preferredCategory);
      const offsetRatio = typeof result.offset_ratio === 'number' ? result.offset_ratio : null;
      const approximateTime =
        typeof result.approximate_time_seconds === 'number' ? result.approximate_time_seconds : null;
      const selection: MediaSelectionRequest = {
        baseId,
        preferredType: preferredCategory,
        offsetRatio,
        approximateTime,
        token: Date.now(),
      };

      if (category === 'library') {
        if (!result.job_id) {
          return;
        }
        if (result.job_id === jobId) {
          setPendingSelection(selection);
          return;
        }
        const payload: LibraryOpenRequest = {
          kind: 'library-open',
          jobId: result.job_id,
          selection,
        };
        onOpenLibraryItem?.(payload);
        return;
      }

      if (result.job_id && result.job_id !== jobId) {
        return;
      }

      setPendingSelection(selection);
    },
    [jobId, onOpenLibraryItem],
  );

  const getMediaItem = useCallback(
    (category: MediaCategory, id: string | null | undefined) => {
      if (!id) {
        return null;
      }
      return mediaIndex[category].get(id) ?? null;
    },
    [mediaIndex],
  );

  const activeItemId = selectedItemIds[selectedMediaType];

  const hasResolvedInitialTabRef = useRef(false);

  useEffect(() => {
    setSelectedMediaType((current) => {
      const currentHasContent = current ? media[current].length > 0 : false;

      if (!hasResolvedInitialTabRef.current) {
        hasResolvedInitialTabRef.current = true;
        if (interactiveViewerAvailable) {
          return 'text';
        }
        if (current && currentHasContent) {
          return current;
        }
        return selectInitialTab(media);
      }

      if (current && currentHasContent) {
        return current;
      }
      if (interactiveViewerAvailable) {
        return 'text';
      }
      return selectInitialTab(media);
    });
  }, [interactiveViewerAvailable, media]);

  useEffect(() => {
    if (media.video.length > 0 || selectedMediaType !== 'video') {
      return;
    }
    setSelectedMediaType(defaultTab);
  }, [defaultTab, media.video.length, selectedMediaType]);

  useEffect(() => {
    const rememberedType = memoryState.currentMediaType;
    const rememberedId = memoryState.currentMediaId;
    if (!rememberedType || !rememberedId) {
      return;
    }

    if (!mediaIndex[rememberedType].has(rememberedId)) {
      return;
    }

    setSelectedItemIds((current) => {
      if (current[rememberedType] === rememberedId) {
        return current;
      }
      return { ...current, [rememberedType]: rememberedId };
    });

    setSelectedMediaType((current) => (current === rememberedType ? current : rememberedType));
  }, [memoryState.currentMediaId, memoryState.currentMediaType, mediaIndex]);

  useEffect(() => {
    setSelectedItemIds((current) => {
      let changed = false;
      const next: Record<MediaCategory, string | null> = { ...current };

      MEDIA_CATEGORIES.forEach((category) => {
        const items = media[category];
        const currentId = current[category];

        if (items.length === 0) {
          if (currentId !== null) {
            next[category] = null;
            changed = true;
          }
          return;
        }

        const hasCurrent = currentId !== null && items.some((item) => item.url === currentId);

        if (!hasCurrent) {
          next[category] = items[0].url ?? null;
          if (next[category] !== currentId) {
            changed = true;
          }
        }
      });

      return changed ? next : current;
    });
  }, [media]);

  useEffect(() => {
    if (!activeItemId) {
      return;
    }

    if (
      !hasSkippedInitialRememberRef.current &&
      memoryState.currentMediaType &&
      memoryState.currentMediaId
    ) {
      hasSkippedInitialRememberRef.current = true;
      return;
    }

    const currentItem = getMediaItem(selectedMediaType, activeItemId);
    if (!currentItem) {
      return;
    }

    rememberSelection({ media: currentItem });
  }, [
    activeItemId,
    selectedMediaType,
    getMediaItem,
    rememberSelection,
    memoryState.currentMediaId,
    memoryState.currentMediaType,
  ]);

  const handleTabChange = useCallback(
    (nextValue: string) => {
      const nextType = nextValue as MediaCategory;
      setSelectedMediaType(nextType);
      setSelectedItemIds((current) => {
        const baseId = memoryState.baseId;
        if (!baseId) {
          return current;
        }

        const match = findMatchingMediaId(baseId, nextType, media[nextType]);
        if (!match || current[nextType] === match) {
          return current;
        }

        return { ...current, [nextType]: match };
      });
    },
    [findMatchingMediaId, media, memoryState.baseId],
  );

  const handleSelectMedia = useCallback((category: MediaCategory, fileId: string) => {
    setSelectedItemIds((current) => {
      if (current[category] === fileId) {
        return current;
      }

      return { ...current, [category]: fileId };
    });
  }, []);

  const updateSelection = useCallback(
    (category: MediaCategory, intent: NavigationIntent) => {
      setSelectedItemIds((current) => {
        const navigableItems = media[category].filter(
          (item) => typeof item.url === 'string' && item.url.length > 0,
        );
        if (navigableItems.length === 0) {
          return current;
        }

        const currentId = current[category];
        const currentIndex = currentId
          ? navigableItems.findIndex((item) => item.url === currentId)
          : -1;

        let nextIndex = currentIndex;
        switch (intent) {
          case 'first':
            nextIndex = 0;
            break;
          case 'last':
            nextIndex = navigableItems.length - 1;
            break;
          case 'previous':
            nextIndex = currentIndex <= 0 ? 0 : currentIndex - 1;
            break;
          case 'next':
            nextIndex = currentIndex < 0 ? 0 : Math.min(currentIndex + 1, navigableItems.length - 1);
            break;
          default:
            nextIndex = currentIndex;
        }

        if (nextIndex === currentIndex && currentId !== null) {
          return current;
        }

        const nextItem = navigableItems[nextIndex];
        if (!nextItem?.url) {
          return current;
        }

        if (nextItem.url === currentId) {
          return current;
        }

        return { ...current, [category]: nextItem.url };
      });
    },
    [media],
  );

  const videoFiles = useMemo(() => toVideoFiles(media.video), [media.video]);
  useEffect(() => {
    if (videoFiles.length === 0 && isVideoPlaying) {
      setIsVideoPlaying(false);
    }
  }, [videoFiles.length, isVideoPlaying]);
  const textContentCache = useRef(new Map<string, { raw: string; plain: string }>());
  const [textPreview, setTextPreview] = useState<{ url: string; content: string; raw: string } | null>(null);
  const [textLoading, setTextLoading] = useState(false);
  const [textError, setTextError] = useState<string | null>(null);

  useEffect(() => {
    onVideoPlaybackStateChange?.(isVideoPlaying);
  }, [isVideoPlaying, onVideoPlaybackStateChange]);
  useEffect(() => {
    onPlaybackStateChange?.(isVideoPlaying || isInlineAudioPlaying);
  }, [isInlineAudioPlaying, isVideoPlaying, onPlaybackStateChange]);

  useEffect(() => {
    if (!isVideoTabActive && isVideoPlaying) {
      setIsVideoPlaying(false);
    }
  }, [isVideoPlaying, isVideoTabActive]);
  const combinedMedia = useMemo(
    () =>
      MEDIA_CATEGORIES.flatMap((category) =>
        media[category].map((item) => ({ ...item, type: category })),
      ),
    [media],
  );
  const filteredMedia = useMemo(
    () => combinedMedia.filter((item) => item.type === selectedMediaType),
    [combinedMedia, selectedMediaType],
  );
  const selectedItemId = selectedItemIds[selectedMediaType];
  const videoPlaybackPosition = getPosition(selectedItemIds.video);
  const textPlaybackPosition = getPosition(selectedItemIds.text);
  const selectedItem = useMemo(() => {
    if (filteredMedia.length === 0) {
      return null;
    }

    if (!selectedItemId) {
      return filteredMedia[0];
    }

    return filteredMedia.find((item) => item.url === selectedItemId) ?? filteredMedia[0];
  }, [filteredMedia, selectedItemId]);
  const hasInteractiveChunks = useMemo(() => {
    return chunks.some((chunk) => {
      if (Array.isArray(chunk.sentences) && chunk.sentences.length > 0) {
        return true;
      }
      if (typeof chunk.sentenceCount === 'number' && chunk.sentenceCount > 0) {
        return true;
      }
      const cacheKey = chunkCacheKey(chunk);
      if (!cacheKey) {
        return false;
      }
      const cached = chunkMetadataStore[cacheKey];
      return cached !== undefined;
    });
  }, [chunks, chunkMetadataStore]);
  const selectedChunk = useMemo(() => {
    if (!selectedItem) {
      return null;
    }
    return (
      chunks.find((chunk) => {
        if (selectedItem.chunk_id && chunk.chunkId) {
          return chunk.chunkId === selectedItem.chunk_id;
        }
        if (selectedItem.range_fragment && chunk.rangeFragment) {
          return chunk.rangeFragment === selectedItem.range_fragment;
        }
        if (selectedItem.url) {
          return chunk.files.some((file) => file.url === selectedItem.url);
        }
        return false;
      }) ?? null
    );
  }, [chunks, selectedItem]);
  const {
    playlist: interactiveAudioPlaylist,
    nameMap: interactiveAudioNameMap,
    chunkIndexMap: audioChunkIndexMap,
  } = useMemo(() => buildInteractiveAudioCatalog(chunks, media.audio), [chunks, media.audio]);
  const activeTextChunk = useMemo(() => {
    if (selectedChunk) {
      return selectedChunk;
    }
    if (!chunks.length) {
      return null;
    }
    if (inlineAudioSelection) {
      const mappedIndex = audioChunkIndexMap.get(inlineAudioSelection);
      if (typeof mappedIndex === 'number' && mappedIndex >= 0 && mappedIndex < chunks.length) {
        return chunks[mappedIndex];
      }
    }
    const audioId = selectedItemIds.audio;
    if (audioId) {
      const mappedIndex = audioChunkIndexMap.get(audioId);
      if (typeof mappedIndex === 'number' && mappedIndex >= 0 && mappedIndex < chunks.length) {
        return chunks[mappedIndex];
      }
      const matchedByAudio = chunks.find((chunk) =>
        chunk.files.some((file) => file.type === 'audio' && file.url === audioId),
      );
      if (matchedByAudio) {
        return matchedByAudio;
      }
    }
    const firstWithSentences = chunks.find(
      (chunk) => Array.isArray(chunk.sentences) && chunk.sentences.length > 0,
    );
    return firstWithSentences ?? chunks[0];
  }, [audioChunkIndexMap, chunks, inlineAudioSelection, selectedChunk, selectedItemIds.audio]);
  const activeTextChunkIndex = useMemo(
    () => (activeTextChunk ? chunks.findIndex((chunk) => chunk === activeTextChunk) : -1),
    [activeTextChunk, chunks],
  );

  const queueChunkMetadataFetch = useCallback(
    (chunk: LiveMediaChunk | null | undefined) => {
      if (!jobId || !chunk) {
        return;
      }
      if (Array.isArray(chunk.sentences) && chunk.sentences.length > 0) {
        return;
      }
      const cacheKey = chunkCacheKey(chunk);
      if (!cacheKey) {
        return;
      }
      if (chunkMetadataStoreRef.current[cacheKey] !== undefined) {
        return;
      }
      if (chunkMetadataLoadingRef.current.has(cacheKey)) {
        return;
      }
      chunkMetadataLoadingRef.current.add(cacheKey);
      requestChunkMetadata(jobId, chunk)
        .then((sentences) => {
          if (sentences !== null) {
            setChunkMetadataStore((current) => {
              if (current[cacheKey] !== undefined) {
                return current;
              }
              return { ...current, [cacheKey]: sentences };
            });
          }
        })
        .catch((error) => {
          console.warn('Unable to load interactive chunk metadata', error);
        })
        .finally(() => {
          chunkMetadataLoadingRef.current.delete(cacheKey);
        });
    },
    [jobId],
  );

  useEffect(() => {
    if (!jobId) {
      return;
    }
    const targets = new Set<LiveMediaChunk>();

    if (activeTextChunk) {
      targets.add(activeTextChunk);
    }

    if (activeTextChunkIndex >= 0) {
      for (let offset = -CHUNK_METADATA_PREFETCH_RADIUS; offset <= CHUNK_METADATA_PREFETCH_RADIUS; offset += 1) {
        const neighbourIndex = activeTextChunkIndex + offset;
        if (neighbourIndex < 0 || neighbourIndex >= chunks.length) {
          continue;
        }
        const neighbour = chunks[neighbourIndex];
        if (neighbour) {
          targets.add(neighbour);
        }
      }
    }

    targets.forEach((chunk) => {
      queueChunkMetadataFetch(chunk);
    });
  }, [jobId, chunks, activeTextChunk, activeTextChunkIndex, queueChunkMetadataFetch]);

  const resolvedActiveTextChunk = useMemo(() => {
    if (!activeTextChunk) {
      return null;
    }
    if (Array.isArray(activeTextChunk.sentences) && activeTextChunk.sentences.length > 0) {
      return activeTextChunk;
    }
    const cacheKey = chunkCacheKey(activeTextChunk);
    if (!cacheKey) {
      return activeTextChunk;
    }
    const cached = chunkMetadataStore[cacheKey];
    if (cached !== undefined) {
      return {
        ...activeTextChunk,
        sentences: cached,
        sentenceCount: cached.length,
      };
    }
    return activeTextChunk;
  }, [activeTextChunk, chunkMetadataStore]);
  const activeAudioTracks = useMemo(() => {
    const chunkRef = resolvedActiveTextChunk;
    if (!normalisedJobId || !chunkRef) {
      return null;
    }
    const tracks = chunkRef.audioTracks ?? null;
    const files = chunkRef.files ?? [];
    const mapping: Record<string, string> = {};

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

    const registerTrack = (key: string, source: string | null | undefined) => {
      const normalised = normaliseSource(source);
      if (!normalised) {
        return;
      }
      mapping[key] = normalised;
    };

    if (tracks) {
      if (typeof tracks.orig_trans === 'string' && tracks.orig_trans.trim()) {
        registerTrack('orig_trans', tracks.orig_trans.trim());
      }
      if (typeof tracks.trans === 'string' && tracks.trans.trim()) {
        registerTrack('trans', tracks.trans.trim());
      }
      if (typeof tracks.orig === 'string' && tracks.orig.trim()) {
        registerTrack('orig', tracks.orig.trim());
      }
    }

    files.forEach((file) => {
      if (!file || typeof file !== 'object') {
        return;
      }
      if (file.type !== 'audio') {
        return;
      }
      const relativePath = typeof file.relative_path === 'string' ? file.relative_path : '';
      const displayName = typeof file.name === 'string' ? file.name : '';
      const isCombinedCandidate = isCombinedAudioCandidate(relativePath, displayName);
      if (isCombinedCandidate && typeof file.url === 'string') {
        registerTrack('orig_trans', file.url);
        return;
      }
      const isOriginalCandidate = isOriginalAudioCandidate(relativePath, displayName);
      if (isOriginalCandidate && typeof file.url === 'string') {
        registerTrack('orig', file.url);
        return;
      }
      if (!mapping.trans && typeof file.url === 'string') {
        registerTrack('trans', file.url);
      }
    });

    return Object.keys(mapping).length > 0 ? mapping : null;
  }, [normalisedJobId, origin, resolvedActiveTextChunk]);
  const inlineAudioOptions = useMemo(() => {
    const seen = new Set<string>();
    const options: { url: string; label: string }[] = [];
    const register = (url: string | null | undefined, label: string | null | undefined) => {
      if (!url || seen.has(url)) {
        return;
      }
      const trimmedLabel = typeof label === 'string' ? label.trim() : '';
      options.push({
        url,
        label: trimmedLabel || `Audio ${options.length + 1}`,
      });
      seen.add(url);
    };
    const chunkForOptions = resolvedActiveTextChunk ?? activeTextChunk;
    if (chunkForOptions && activeTextChunkIndex >= 0) {
      chunkForOptions.files.forEach((file) => {
        if (file.type !== 'audio' || !file.url) {
          return;
        }
        const relativePath = typeof file.relative_path === 'string' ? file.relative_path : '';
        const displayName = typeof file.name === 'string' ? file.name : '';
        if (isOriginalAudioCandidate(relativePath, displayName) && !isCombinedAudioCandidate(relativePath, displayName)) {
          return;
        }
        const label =
          interactiveAudioNameMap.get(file.url) ??
          (typeof file.name === 'string' ? file.name.trim() : '') ??
          formatChunkLabel(chunkForOptions, activeTextChunkIndex);
        register(file.url, label);
      });
    }
    interactiveAudioPlaylist.forEach((item, index) => {
      register(item.url, item.name ?? `Audio ${index + 1}`);
    });
    return options;
  }, [activeTextChunk, activeTextChunkIndex, interactiveAudioNameMap, interactiveAudioPlaylist, resolvedActiveTextChunk]);

  const inlineAudioUnavailable = inlineAudioOptions.length === 0;
  const hasCombinedAudio = Boolean(activeAudioTracks?.orig_trans);
  const hasLegacyOriginal = Boolean(activeAudioTracks?.orig);
  const canToggleOriginalAudio = hasCombinedAudio || hasLegacyOriginal;
  const effectiveOriginalAudioEnabled = showOriginalAudio && hasCombinedAudio;
  const handleOriginalAudioToggle = useCallback(() => {
    if (!hasCombinedAudio) {
      return;
    }
    setShowOriginalAudio((current) => !current);
  }, [hasCombinedAudio]);

  useEffect(() => {
    if (!hasCombinedAudio && showOriginalAudio) {
      setShowOriginalAudio(false);
    }
  }, [hasCombinedAudio, showOriginalAudio]);

  useEffect(() => {
    if (!hasCombinedAudio) {
      return;
    }
    const combinedUrl = activeAudioTracks?.orig_trans ?? null;
    const translationUrl = activeAudioTracks?.trans ?? null;
    setInlineAudioSelection((current) => {
      if (showOriginalAudio) {
        if (combinedUrl && current !== combinedUrl) {
          return combinedUrl;
        }
        return combinedUrl ?? current;
      }
      if (combinedUrl && current === combinedUrl) {
        if (translationUrl) {
          return translationUrl;
        }
        return null;
      }
      return current;
    });
  }, [activeAudioTracks?.orig_trans, activeAudioTracks?.trans, hasCombinedAudio, showOriginalAudio]);
  useEffect(() => {
    if (!pendingSelection) {
      return;
    }

    const hasLoadedMedia = MEDIA_CATEGORIES.some((category) => media[category].length > 0);
    if (!hasLoadedMedia) {
      return;
    }

    const { baseId, preferredType, offsetRatio = null, approximateTime = null } = pendingSelection;
    const selectionToken = pendingSelection.token ?? Date.now();
    const chunkMatchIndex = findChunkIndexForBaseId(baseId, chunks);

    const candidateOrder: MediaCategory[] = [];
    if (preferredType) {
      candidateOrder.push(preferredType);
    }
    MEDIA_CATEGORIES.forEach((category) => {
      if (!candidateOrder.includes(category)) {
        candidateOrder.push(category);
      }
    });

    const matchByCategory: Record<MediaCategory, string | null> = {
      text: baseId ? findMatchingMediaId(baseId, 'text', media.text) : null,
      audio: baseId ? findMatchingMediaId(baseId, 'audio', media.audio) : null,
      video: baseId ? findMatchingMediaId(baseId, 'video', media.video) : null,
    };

    if (matchByCategory.audio) {
      setSelectedItemIds((current) =>
        current.audio === matchByCategory.audio ? current : { ...current, audio: matchByCategory.audio },
      );
    }

    const tabCandidates = candidateOrder.filter(
      (category): category is Extract<MediaCategory, 'text' | 'video'> =>
        category === 'text' || category === 'video',
    );

    let appliedCategory: MediaCategory | null = null;

    for (const category of tabCandidates) {
      if (category === 'text' && !matchByCategory.text && chunkMatchIndex >= 0) {
        setSelectedMediaType((current) => (current === 'text' ? current : 'text'));
        setPendingChunkSelection({ index: chunkMatchIndex, token: selectionToken });
        appliedCategory = 'text';
        break;
      }

      const matchId = matchByCategory[category];
      if (!matchId) {
        continue;
      }

      setSelectedItemIds((current) => {
        if (current[category] === matchId) {
          return current;
        }
        return { ...current, [category]: matchId };
      });
      setSelectedMediaType((current) => (current === category ? current : category));
      appliedCategory = category;
      break;
    }

    if (!appliedCategory && preferredType) {
      if (preferredType === 'audio') {
        setSelectedItemIds((current) => {
          if (current.audio !== null) {
            return current;
          }
          const firstAudio = media.audio.find((item) => item.url);
          if (!firstAudio?.url) {
            return current;
          }
          return { ...current, audio: firstAudio.url };
        });

        if (chunkMatchIndex >= 0) {
          setSelectedMediaType((current) => (current === 'text' ? current : 'text'));
          setPendingChunkSelection({ index: chunkMatchIndex, token: selectionToken });
          appliedCategory = 'text';
        } else if (media.text.length > 0) {
          setSelectedMediaType((current) => (current === 'text' ? current : 'text'));
          setSelectedItemIds((current) => {
            if (current.text) {
              return current;
            }
            const firstText = media.text.find((item) => item.url);
            if (!firstText?.url) {
              return current;
            }
            return { ...current, text: firstText.url };
          });
          appliedCategory = 'text';
        } else if (media.video.length > 0) {
          setSelectedMediaType((current) => (current === 'video' ? current : 'video'));
          setSelectedItemIds((current) => {
            if (current.video) {
              return current;
            }
            const firstVideo = media.video.find((item) => item.url);
            if (!firstVideo?.url) {
              return current;
            }
            return { ...current, video: firstVideo.url };
          });
          appliedCategory = 'video';
        }
      } else {
        const category = preferredType;
        setSelectedMediaType((current) => (current === category ? current : category));
        if (category === 'text' && chunkMatchIndex >= 0) {
          setPendingChunkSelection({ index: chunkMatchIndex, token: selectionToken });
          appliedCategory = 'text';
        } else {
          setSelectedItemIds((current) => {
            const hasCurrent = current[category] !== null;
            if (hasCurrent) {
              return current;
            }
            const firstItem = media[category].find((item) => item.url);
            if (!firstItem?.url) {
              return current;
            }
            return { ...current, [category]: firstItem.url };
          });
          appliedCategory = media[category].length > 0 ? category : null;
        }
      }
    }

    if (matchByCategory.audio && approximateTime != null && Number.isFinite(approximateTime)) {
      const audioItem = getMediaItem('audio', matchByCategory.audio);
      const audioBaseId = audioItem ? deriveBaseId(audioItem) : null;
      rememberPosition({
        mediaId: matchByCategory.audio,
        mediaType: 'audio',
        baseId: audioBaseId,
        position: Math.max(approximateTime, 0),
      });
    }

    if (matchByCategory.video && approximateTime != null && Number.isFinite(approximateTime)) {
      const videoItem = getMediaItem('video', matchByCategory.video);
      const videoBaseId = videoItem ? deriveBaseId(videoItem) : null;
      rememberPosition({
        mediaId: matchByCategory.video,
        mediaType: 'video',
        baseId: videoBaseId,
        position: Math.max(approximateTime, 0),
      });
    }

    if ((matchByCategory.text || chunkMatchIndex >= 0) && offsetRatio != null && Number.isFinite(offsetRatio)) {
      setPendingTextScrollRatio(Math.max(Math.min(offsetRatio, 1), 0));
    } else {
      setPendingTextScrollRatio(null);
    }

    if (matchByCategory.audio && inlineAudioOptions.some((option) => option.url === matchByCategory.audio)) {
      setInlineAudioSelection((current) => (current === matchByCategory.audio ? current : matchByCategory.audio));
    }

    setPendingSelection(null);
  }, [
    pendingSelection,
    findMatchingMediaId,
    media,
    getMediaItem,
    deriveBaseId,
    rememberPosition,
    inlineAudioOptions,
    chunks,
    setPendingChunkSelection,
  ]);

  useEffect(() => {
    if (!pendingChunkSelection) {
      return;
    }

    const { index } = pendingChunkSelection;
    if (index < 0 || index >= chunks.length) {
      setPendingChunkSelection(null);
      return;
    }

    const targetChunk = chunks[index];
    setSelectedMediaType((current) => (current === 'text' ? current : 'text'));

    const audioFile = targetChunk.files.find(
      (file) => file.type === 'audio' && typeof file.url === 'string' && file.url.length > 0,
    );
    if (audioFile?.url) {
      setSelectedItemIds((current) =>
        current.audio === audioFile.url ? current : { ...current, audio: audioFile.url },
      );
      setInlineAudioSelection((current) => (current === audioFile.url ? current : audioFile.url));
    }

    setPendingChunkSelection(null);
  }, [pendingChunkSelection, chunks, setSelectedMediaType, setSelectedItemIds, setInlineAudioSelection]);

  const fallbackTextContent = useMemo(() => {
    if (!resolvedActiveTextChunk || !Array.isArray(resolvedActiveTextChunk.sentences)) {
      return '';
    }
    const blocks = resolvedActiveTextChunk.sentences
      .map((sentence) => {
        if (!sentence) {
          return '';
        }
        const lines: string[] = [];
        if (sentence.original?.text) {
          lines.push(sentence.original.text);
        }
        if (sentence.translation?.text) {
          lines.push(sentence.translation.text);
        }
        if (sentence.transliteration?.text) {
          lines.push(sentence.transliteration.text);
        }
        return lines.filter(Boolean).join('\n');
      })
      .filter((block) => block.trim().length > 0);
    return blocks.join('\n\n');
  }, [resolvedActiveTextChunk]);
  const interactiveViewerContent = (textPreview?.content ?? fallbackTextContent) || '';
  const interactiveViewerRaw = textPreview?.raw ?? fallbackTextContent;
  const canRenderInteractiveViewer =
    Boolean(resolvedActiveTextChunk) || interactiveViewerContent.trim().length > 0;
  const handleInteractiveFullscreenToggle = useCallback(() => {
    if (!isTextTabActive || !canRenderInteractiveViewer) {
      updateInteractiveFullscreenPreference(false);
      setIsInteractiveFullscreen(false);
      return;
    }
    setIsInteractiveFullscreen((current) => {
      const next = !current;
      updateInteractiveFullscreenPreference(next);
      return next;
    });
  }, [canRenderInteractiveViewer, isTextTabActive, updateInteractiveFullscreenPreference]);

  const handleExitInteractiveFullscreen = useCallback(() => {
    updateInteractiveFullscreenPreference(false);
    setIsInteractiveFullscreen(false);
  }, [updateInteractiveFullscreenPreference]);
  const isImmersiveLayout = isVideoTabActive && isImmersiveMode;
  const panelClassName = isImmersiveLayout ? 'player-panel player-panel--immersive' : 'player-panel';
  useEffect(() => {
    if (!isTextTabActive) {
      if (isInteractiveFullscreen) {
        setIsInteractiveFullscreen(false);
      }
    }
  }, [isInteractiveFullscreen, isTextTabActive]);

  useEffect(() => {
    if (!canRenderInteractiveViewer) {
      if (isInteractiveFullscreen) {
        setIsInteractiveFullscreen(false);
      }
      return;
    }
    if (interactiveFullscreenPreferenceRef.current && !isInteractiveFullscreen) {
      updateInteractiveFullscreenPreference(true);
      setIsInteractiveFullscreen(true);
    }
  }, [canRenderInteractiveViewer, isInteractiveFullscreen, updateInteractiveFullscreenPreference]);
  const hasTextItems = media.text.length > 0;
  const navigableItems = useMemo(
    () =>
      media[selectedMediaType].filter((item) => typeof item.url === 'string' && item.url.length > 0),
    [media, selectedMediaType],
  );
  const activeNavigableIndex = useMemo(() => {
    const currentId = selectedItemIds[selectedMediaType];
    if (!currentId) {
      return navigableItems.length > 0 ? 0 : -1;
    }

    const matchIndex = navigableItems.findIndex((item) => item.url === currentId);
    if (matchIndex >= 0) {
      return matchIndex;
    }

    return navigableItems.length > 0 ? 0 : -1;
  }, [navigableItems, selectedItemIds, selectedMediaType]);
  const derivedNavigation = useMemo(() => {
    if (navigableItems.length > 0) {
      return {
        mode: 'media' as const,
        count: navigableItems.length,
        index: Math.max(0, activeNavigableIndex),
      };
    }
    if (selectedMediaType === 'text' && chunks.length > 0) {
      const index = activeTextChunkIndex >= 0 ? activeTextChunkIndex : 0;
      return {
        mode: 'chunks' as const,
        count: chunks.length,
        index: Math.max(0, Math.min(index, Math.max(chunks.length - 1, 0))),
      };
    }
    return { mode: 'none' as const, count: 0, index: -1 };
  }, [activeNavigableIndex, activeTextChunkIndex, chunks.length, navigableItems.length, selectedMediaType]);
  const isFirstDisabled =
    derivedNavigation.count === 0 || derivedNavigation.index <= 0;
  const isPreviousDisabled =
    derivedNavigation.count === 0 || derivedNavigation.index <= 0;
  const isNextDisabled =
    derivedNavigation.count === 0 || derivedNavigation.index >= derivedNavigation.count - 1;
  const isLastDisabled =
    derivedNavigation.count === 0 || derivedNavigation.index >= derivedNavigation.count - 1;
  const playbackControlsAvailable =
    selectedMediaType === 'video'
      ? hasVideoControls
      : selectedMediaType === 'text'
      ? hasInlineAudioControls
      : false;
  const isActiveMediaPlaying =
    selectedMediaType === 'video'
      ? isVideoPlaying
      : selectedMediaType === 'text'
      ? isInlineAudioPlaying
      : false;
  const isPlaybackDisabled = !playbackControlsAvailable;
  const isFullscreenDisabled = !isTextTabActive || !canRenderInteractiveViewer;
  const handleTranslationSpeedChange = useCallback((speed: TranslationSpeed) => {
    setTranslationSpeed(normaliseTranslationSpeed(speed));
  }, []);

  const handleAdvanceMedia = useCallback(
    (category: MediaCategory) => {
      updateSelection(category, 'next');
    },
    [updateSelection],
  );

  const handleVideoControlsRegistration = useCallback((controls: PlaybackControls | null) => {
    videoControlsRef.current = controls;
    setHasVideoControls(Boolean(controls));
    if (!controls) {
      setIsVideoPlaying(false);
    }
  }, []);

  const syncInteractiveSelection = useCallback(
    (audioUrl: string | null) => {
      if (!audioUrl) {
        return;
      }
      setSelectedItemIds((current) =>
        current.audio === audioUrl ? current : { ...current, audio: audioUrl },
      );
      const chunkIndex = audioChunkIndexMap.get(audioUrl);
      if (typeof chunkIndex === 'number' && chunkIndex >= 0 && chunkIndex < chunks.length) {
        const targetChunk = chunks[chunkIndex];
        const nextTextFile = targetChunk.files.find((file) => file.type === 'text' && file.url);
        if (nextTextFile?.url) {
          setSelectedItemIds((current) =>
            current.text === nextTextFile.url ? current : { ...current, text: nextTextFile.url },
          );
        }
      }
    },
    [
      audioChunkIndexMap,
      chunks,
      setSelectedItemIds,
    ],
  );

  const handleInlineAudioSelect = useCallback(
    (audioUrl: string) => {
      if (!audioUrl) {
        return;
      }
      setInlineAudioSelection((current) => (current === audioUrl ? current : audioUrl));
      syncInteractiveSelection(audioUrl);
    },
    [syncInteractiveSelection],
  );

  const handleInlineAudioPlaybackStateChange = useCallback((state: 'playing' | 'paused') => {
    setIsInlineAudioPlaying(state === 'playing');
  }, []);

  const handleInlineAudioControlsRegistration = useCallback((controls: PlaybackControls | null) => {
    inlineAudioControlsRef.current = controls;
    setHasInlineAudioControls(Boolean(controls));
    if (!controls) {
      setIsInlineAudioPlaying(false);
    }
  }, []);

  const handleNavigate = useCallback(
    (intent: NavigationIntent) => {
      const textItems = selectedMediaType === 'text' ? navigableItems : [];
      if (
        selectedMediaType === 'text' &&
        textItems.length === 0 &&
        chunks.length > 0
      ) {
        const currentIndex = activeTextChunkIndex >= 0 ? activeTextChunkIndex : 0;
        const lastIndex = chunks.length - 1;
        let nextIndex = currentIndex;
        switch (intent) {
          case 'first':
            nextIndex = 0;
            break;
          case 'last':
            nextIndex = lastIndex;
            break;
          case 'previous':
            nextIndex = currentIndex <= 0 ? 0 : currentIndex - 1;
            break;
          case 'next':
            nextIndex = currentIndex < 0 ? 0 : Math.min(currentIndex + 1, lastIndex);
            break;
          default:
            nextIndex = currentIndex;
        }

        if (nextIndex === currentIndex) {
          return;
        }

        const targetChunk = chunks[nextIndex];
        if (!targetChunk) {
          return;
        }
        const nextAudio = targetChunk.files.find((file) => file.type === 'audio' && file.url);
        if (nextAudio?.url) {
          setInlineAudioSelection((current) => (current === nextAudio.url ? current : nextAudio.url));
          syncInteractiveSelection(nextAudio.url);
        } else {
          const nextText = targetChunk.files.find((file) => file.type === 'text' && file.url);
          if (nextText?.url) {
            setSelectedItemIds((current) =>
              current.text === nextText.url ? current : { ...current, text: nextText.url },
            );
          }
        }
        setPendingTextScrollRatio(0);
        return;
      }

      updateSelection(selectedMediaType, intent);
    },
    [
      activeTextChunkIndex,
      chunks,
      navigableItems,
      selectedMediaType,
      setInlineAudioSelection,
      setPendingTextScrollRatio,
      setSelectedItemIds,
      syncInteractiveSelection,
      updateSelection,
    ],
  );

  const handlePauseActiveMedia = useCallback(() => {
    if (selectedMediaType === 'video') {
      videoControlsRef.current?.pause();
      setIsVideoPlaying(false);
    } else if (selectedMediaType === 'text') {
      inlineAudioControlsRef.current?.pause();
      setIsInlineAudioPlaying(false);
    }
  }, [selectedMediaType]);

  const handlePlayActiveMedia = useCallback(() => {
    if (selectedMediaType === 'video') {
      videoControlsRef.current?.play();
      setIsVideoPlaying(true);
    } else if (selectedMediaType === 'text') {
      inlineAudioControlsRef.current?.play();
      setIsInlineAudioPlaying(true);
    }
  }, [selectedMediaType]);

  const handleToggleActiveMedia = useCallback(() => {
    if (isActiveMediaPlaying) {
      handlePauseActiveMedia();
    } else {
      handlePlayActiveMedia();
    }
  }, [handlePauseActiveMedia, handlePlayActiveMedia, isActiveMediaPlaying]);

  const handleTextScroll = useCallback(
    (event: UIEvent<HTMLElement>) => {
      const mediaId = selectedItemIds.text;
      if (!mediaId) {
        return;
      }

      const current = getMediaItem('text', mediaId);
      const baseId = current ? deriveBaseId(current) : null;
      const target = event.currentTarget as HTMLElement;
      rememberPosition({ mediaId, mediaType: 'text', baseId, position: target.scrollTop ?? 0 });
    },
    [selectedItemIds.text, getMediaItem, deriveBaseId, rememberPosition],
  );

  const handleInlineAudioProgress = useCallback(
    (audioUrl: string, position: number) => {
      if (!audioUrl) {
        return;
      }
      const current = getMediaItem('audio', audioUrl);
      const baseId = current ? deriveBaseId(current) : null;
      rememberPosition({ mediaId: audioUrl, mediaType: 'audio', baseId, position });
    },
    [deriveBaseId, getMediaItem, rememberPosition],
  );

  const getInlineAudioPosition = useCallback(
    (audioUrl: string) => getPosition(audioUrl),
    [getPosition],
  );

  const advanceInteractiveChunk = useCallback(() => {
    if (chunks.length === 0) {
      return false;
    }
    let currentIndex = activeTextChunkIndex;
    if (currentIndex < 0 && inlineAudioSelection) {
      const mappedIndex = audioChunkIndexMap.get(inlineAudioSelection);
      if (typeof mappedIndex === 'number' && mappedIndex >= 0) {
        currentIndex = mappedIndex;
      }
    }
    const nextIndex = currentIndex >= 0 ? currentIndex + 1 : 0;
    if (nextIndex >= chunks.length) {
      return false;
    }
    const nextChunk = chunks[nextIndex];
    const nextAudio = nextChunk.files.find((file) => file.type === 'audio' && file.url);
    if (nextAudio?.url) {
      setInlineAudioSelection(nextAudio.url);
      syncInteractiveSelection(nextAudio.url);
    } else {
      const nextText = nextChunk.files.find((file) => file.type === 'text' && file.url);
      if (nextText?.url) {
        setSelectedItemIds((current) =>
          current.text === nextText.url ? current : { ...current, text: nextText.url },
        );
      }
    }
    setPendingTextScrollRatio(0);
    return true;
  }, [
    activeTextChunkIndex,
    audioChunkIndexMap,
    chunks,
    inlineAudioSelection,
    setPendingTextScrollRatio,
    setSelectedItemIds,
    syncInteractiveSelection,
  ]);

  const handleInlineAudioEnded = useCallback(() => {
    const advanced = advanceInteractiveChunk();
    if (!advanced) {
      updateSelection('text', 'next');
    }
  }, [advanceInteractiveChunk, updateSelection]);

  useEffect(() => {
    if (inlineAudioOptions.length === 0) {
      if (inlineAudioSelection) {
        const currentAudio = getMediaItem('audio', inlineAudioSelection);
        if (!currentAudio) {
          setInlineAudioSelection(null);
        }
      }
      return;
    }

    if (inlineAudioSelection) {
      const hasExactMatch = inlineAudioOptions.some((option) => option.url === inlineAudioSelection);
      if (hasExactMatch) {
        return;
      }

      const currentAudio = getMediaItem('audio', inlineAudioSelection);
      const currentBaseId =
        currentAudio ? deriveBaseId(currentAudio) : inlineAudioBaseRef.current ?? deriveBaseIdFromReference(inlineAudioSelection);

      if (currentBaseId) {
        const remapped = inlineAudioOptions.find((option) => {
          const optionAudio = getMediaItem('audio', option.url);
          if (optionAudio) {
            return deriveBaseId(optionAudio) === currentBaseId;
          }
          return deriveBaseIdFromReference(option.url) === currentBaseId;
        });

        if (remapped?.url) {
          setInlineAudioSelection((current) => (current === remapped.url ? current : remapped.url));
          if (remapped.url !== inlineAudioSelection) {
            syncInteractiveSelection(remapped.url);
          }
          return;
        }
      }
    }

    const desiredBaseId = inlineAudioBaseRef.current;
    if (!inlineAudioSelection) {
      const fallbackUrl = inlineAudioOptions[0]?.url ?? null;
      if (fallbackUrl) {
        setInlineAudioSelection(fallbackUrl);
        syncInteractiveSelection(fallbackUrl);
      }
      return;
    }

    if (!desiredBaseId) {
      return;
    }

    const preferredOption = inlineAudioOptions.find((option) => {
      const optionAudio = getMediaItem('audio', option.url);
      if (optionAudio) {
        return deriveBaseId(optionAudio) === desiredBaseId;
      }
      return deriveBaseIdFromReference(option.url) === desiredBaseId;
    });

    if (!preferredOption?.url || preferredOption.url === inlineAudioSelection) {
      return;
    }

    setInlineAudioSelection(preferredOption.url);
    syncInteractiveSelection(preferredOption.url);
  }, [
    deriveBaseId,
    getMediaItem,
    inlineAudioOptions,
    inlineAudioSelection,
    syncInteractiveSelection,
  ]);

  useEffect(() => {
    if (!inlineAudioSelection) {
      inlineAudioBaseRef.current = null;
      return;
    }
    const currentAudio = getMediaItem('audio', inlineAudioSelection);
    const baseId = currentAudio ? deriveBaseId(currentAudio) : deriveBaseIdFromReference(inlineAudioSelection);
    inlineAudioBaseRef.current = baseId;
  }, [deriveBaseId, getMediaItem, inlineAudioSelection]);

  useEffect(() => {
    if (!inlineAudioSelection) {
      return;
    }
    const currentAudio = getMediaItem('audio', inlineAudioSelection);
    if (currentAudio) {
      return;
    }
    const baseId = inlineAudioBaseRef.current ?? deriveBaseIdFromReference(inlineAudioSelection);
    if (!baseId) {
      return;
    }

    const replacement = media.audio.find((item) => {
      if (!item.url) {
        return false;
      }
      const optionAudio = getMediaItem('audio', item.url);
      if (optionAudio) {
        return deriveBaseId(optionAudio) === baseId;
      }
      return deriveBaseIdFromReference(item.url) === baseId;
    });

    if (replacement?.url) {
      setInlineAudioSelection(replacement.url);
      syncInteractiveSelection(replacement.url);
    }
  }, [
    deriveBaseId,
    deriveBaseIdFromReference,
    getMediaItem,
    inlineAudioSelection,
    media.audio,
    syncInteractiveSelection,
  ]);

  const handleVideoProgress = useCallback(
    (position: number) => {
      const mediaId = selectedItemIds.video;
      if (!mediaId) {
        return;
      }

      const current = getMediaItem('video', mediaId);
      const baseId = current ? deriveBaseId(current) : null;
      rememberPosition({ mediaId, mediaType: 'video', baseId, position });
    },
    [selectedItemIds.video, getMediaItem, deriveBaseId, rememberPosition],
  );

  const handleVideoPlaybackStateChange = useCallback((state: 'playing' | 'paused') => {
    setIsVideoPlaying(state === 'playing');
  }, []);

  useEffect(() => {
    if (selectedMediaType !== 'text') {
      return;
    }

    const mediaId = selectedItemIds.text;
    if (!mediaId) {
      return;
    }

    const element = textScrollRef.current;
    if (!element) {
      return;
    }

    if (pendingTextScrollRatio !== null) {
      const maxScroll = Math.max(element.scrollHeight - element.clientHeight, 0);
      const target = Math.min(Math.max(pendingTextScrollRatio, 0), 1) * maxScroll;
      try {
        element.scrollTop = target;
        if (typeof element.scrollTo === 'function') {
          element.scrollTo({ top: target });
        }
      } catch (error) {
        // Ignore scroll assignment failures in non-browser environments.
      }

      const current = getMediaItem('text', mediaId);
      const baseId = current ? deriveBaseId(current) : null;
      rememberPosition({ mediaId, mediaType: 'text', baseId, position: target });
      setPendingTextScrollRatio(null);
      return;
    }

    const storedPosition = textPlaybackPosition;
    if (Math.abs(element.scrollTop - storedPosition) < 1) {
      return;
    }

    try {
      element.scrollTop = storedPosition;
      if (typeof element.scrollTo === 'function') {
        element.scrollTo({ top: storedPosition });
      }
    } catch (error) {
      // Swallow assignment errors triggered by unsupported scrolling APIs in tests.
    }
  }, [
    selectedMediaType,
    selectedItemIds.text,
    textPlaybackPosition,
    textPreview?.url,
    pendingTextScrollRatio,
    getMediaItem,
    deriveBaseId,
    rememberPosition,
  ]);

  useEffect(() => {
    if (selectedMediaType !== 'text') {
      return;
    }

    const url = selectedItem?.url;
    if (!url) {
      setTextPreview(null);
      setTextError(null);
      setTextLoading(false);
      return;
    }

    const cached = textContentCache.current.get(url);
    if (cached) {
      setTextPreview({ url, content: cached.plain, raw: cached.raw });
      setTextError(null);
      setTextLoading(false);
      return;
    }

    let cancelled = false;

    setTextLoading(true);
    setTextError(null);
    setTextPreview(null);

    if (typeof fetch !== 'function') {
      setTextLoading(false);
      setTextPreview(null);
      setTextError('Document preview is unavailable in this environment.');
      return;
    }

    fetch(url, { credentials: 'include' })
      .then((response) => {
        if (!response.ok) {
          throw new Error(`Failed to load document (status ${response.status})`);
        }
        return response.text();
      })
      .then((raw) => {
        if (cancelled) {
          return;
        }

        const normalised = extractTextFromHtml(raw);
        textContentCache.current.set(url, { raw, plain: normalised });
        setTextPreview({ url, content: normalised, raw });
        setTextError(null);
      })
      .catch((requestError) => {
        if (cancelled) {
          return;
        }
        const message =
          requestError instanceof Error
            ? requestError.message
            : 'Failed to load document.';
        setTextError(message);
      })
      .finally(() => {
        if (!cancelled) {
          setTextLoading(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [selectedMediaType, selectedItem?.url]);

  const handleImmersiveToggle = useCallback(() => {
    if (!isVideoTabActive || media.video.length === 0) {
      return;
    }
    setIsImmersiveMode((current) => !current);
  }, [isVideoTabActive, media.video.length]);

  const handleExitImmersiveMode = useCallback(() => {
    setIsImmersiveMode(false);
  }, []);

  useEffect(() => {
    if (!isVideoTabActive) {
      setIsImmersiveMode(false);
    }
  }, [isVideoTabActive]);

  useEffect(() => {
    setIsImmersiveMode(false);
    setIsInteractiveFullscreen(false);
    setPendingSelection(null);
    setPendingChunkSelection(null);
    setPendingTextScrollRatio(null);
  }, [normalisedJobId]);

  useEffect(() => {
    const fullscreenActive = isInteractiveFullscreen || isImmersiveMode;
    onFullscreenChange?.(fullscreenActive);
  }, [isInteractiveFullscreen, isImmersiveMode, onFullscreenChange]);

  useEffect(() => {
    if (typeof window === 'undefined') {
      return;
    }
    window.localStorage.setItem('player.showOriginalAudio', showOriginalAudio ? 'true' : 'false');
  }, [showOriginalAudio]);

  const bookTitle = extractMetadataText(bookMetadata, ['book_title', 'title', 'book_name', 'name']);
  const bookAuthor = extractMetadataText(bookMetadata, ['book_author', 'author', 'writer', 'creator']);
  const sectionLabel = bookTitle ? `Player for ${bookTitle}` : 'Player';
  const loadingMessage = bookTitle ? `Loading generated media for ${bookTitle}…` : 'Loading generated media…';
  const emptyMediaMessage = bookTitle ? `No generated media yet for ${bookTitle}.` : 'No generated media yet.';

  const hasAnyMedia = media.text.length + media.audio.length + media.video.length > 0;
  const headingLabel = bookTitle ?? 'Player';
  const jobLabelParts: string[] = [];
  if (bookAuthor) {
    jobLabelParts.push(`By ${bookAuthor}`);
  }
  if (hasJobId) {
    jobLabelParts.push(`Job ${jobId}`);
  }
  const jobLabel = jobLabelParts.join(' • ');
  const coverAltText =
    bookTitle && bookAuthor
      ? `Cover of ${bookTitle} by ${bookAuthor}`
      : bookTitle
      ? `Cover of ${bookTitle}`
      : bookAuthor
      ? `Book cover for ${bookAuthor}`
      : 'Book cover preview';
  const immersiveToggleLabel = isImmersiveMode ? 'Exit immersive mode' : 'Enter immersive mode';
  const interactiveFullscreenLabel = isInteractiveFullscreen ? 'Exit fullscreen' : 'Enter fullscreen';

  const navigationGroup = (
    <NavigationControls
      context="panel"
      onNavigate={handleNavigate}
      onToggleFullscreen={handleInteractiveFullscreenToggle}
      onTogglePlayback={handleToggleActiveMedia}
      disableFirst={isFirstDisabled}
      disablePrevious={isPreviousDisabled}
      disableNext={isNextDisabled}
      disableLast={isLastDisabled}
      disablePlayback={isPlaybackDisabled}
      disableFullscreen={isFullscreenDisabled}
      isFullscreen={isInteractiveFullscreen}
      isPlaying={isActiveMediaPlaying}
      fullscreenLabel={interactiveFullscreenLabel}
      inlineAudioOptions={inlineAudioOptions}
      inlineAudioSelection={inlineAudioSelection}
      onSelectInlineAudio={handleInlineAudioSelect}
      showInlineAudio={selectedMediaType === 'text'}
      showOriginalAudioToggle={selectedMediaType === 'text' && canToggleOriginalAudio}
      onToggleOriginalAudio={handleOriginalAudioToggle}
      originalAudioEnabled={effectiveOriginalAudioEnabled}
      disableOriginalAudioToggle={!hasCombinedAudio}
      showTranslationSpeed={selectedMediaType === 'text'}
      translationSpeed={translationSpeed}
      translationSpeedMin={TRANSLATION_SPEED_MIN}
      translationSpeedMax={TRANSLATION_SPEED_MAX}
      translationSpeedStep={TRANSLATION_SPEED_STEP}
      onTranslationSpeedChange={handleTranslationSpeedChange}
    />
  );
  const fullscreenNavigationGroup = isInteractiveFullscreen ? (
    <NavigationControls
      context="fullscreen"
      onNavigate={handleNavigate}
      onToggleFullscreen={handleInteractiveFullscreenToggle}
      onTogglePlayback={handleToggleActiveMedia}
      disableFirst={isFirstDisabled}
      disablePrevious={isPreviousDisabled}
      disableNext={isNextDisabled}
      disableLast={isLastDisabled}
      disablePlayback={isPlaybackDisabled}
      disableFullscreen={isFullscreenDisabled}
      isFullscreen={isInteractiveFullscreen}
      isPlaying={isActiveMediaPlaying}
      fullscreenLabel={interactiveFullscreenLabel}
      inlineAudioOptions={inlineAudioOptions}
      inlineAudioSelection={inlineAudioSelection}
      onSelectInlineAudio={handleInlineAudioSelect}
      showInlineAudio={selectedMediaType === 'text'}
      showOriginalAudioToggle={selectedMediaType === 'text' && canToggleOriginalAudio}
      onToggleOriginalAudio={handleOriginalAudioToggle}
      originalAudioEnabled={effectiveOriginalAudioEnabled}
      disableOriginalAudioToggle={!hasCombinedAudio}
      showTranslationSpeed={selectedMediaType === 'text'}
      translationSpeed={translationSpeed}
      translationSpeedMin={TRANSLATION_SPEED_MIN}
      translationSpeedMax={TRANSLATION_SPEED_MAX}
      translationSpeedStep={TRANSLATION_SPEED_STEP}
      onTranslationSpeedChange={handleTranslationSpeedChange}
    />
  ) : null;

  const fullscreenHeader = isInteractiveFullscreen ? (
    <div className="player-panel__fullscreen-header">
      {shouldShowCoverImage ? (
        <div className="player-panel__fullscreen-cover" aria-hidden={false}>
          <img
            src={displayCoverUrl}
            alt={coverAltText}
            data-testid="player-panel-fullscreen-cover"
            onError={coverErrorHandler}
          />
        </div>
      ) : null}
      <div className="player-panel__fullscreen-meta">
        <h3>{headingLabel}</h3>
        {jobLabel ? <span className="player-panel__fullscreen-job">{jobLabel}</span> : null}
      </div>
    </div>
  ) : null;

  if (error) {
    return (
      <section className="player-panel" aria-label={sectionLabel}>
        <p role="alert">Unable to load generated media: {error.message}</p>
      </section>
    );
  }

  if (isLoading && media.text.length === 0 && media.audio.length === 0 && media.video.length === 0) {
    return (
      <section className="player-panel" aria-label={sectionLabel}>
        <p role="status">{loadingMessage}</p>
      </section>
    );
  }

  return (
    <section className={panelClassName} aria-label={sectionLabel}>
      {!hasJobId ? (
        <div className="player-panel__empty" role="status">
          <p>No job selected.</p>
        </div>
      ) : (
        <>
          <div className="player-panel__search">
            <MediaSearchPanel currentJobId={jobId} onResultAction={handleSearchSelection} />
          </div>
          <Tabs className="player-panel__tabs-container" value={selectedMediaType} onValueChange={handleTabChange}>
            <header className="player-panel__header">
              <div className="player-panel__heading">
                {shouldShowCoverImage ? (
                  <div className="player-panel__cover" aria-hidden={false}>
                    <img
                      src={displayCoverUrl}
                      alt={coverAltText}
                      data-testid="player-cover-image"
                      onError={coverErrorHandler}
                    />
                  </div>
                ) : null}
                <div className="player-panel__heading-text">
                  <h2>{headingLabel}</h2>
                  <span className="player-panel__job">{jobLabel}</span>
                </div>
              </div>
          <div className="player-panel__tabs-row">
            {navigationGroup}
            {media.video.length > 0 ? (
              <button
                type="button"
                className="player-panel__immersive-toggle"
                onClick={handleImmersiveToggle}
                disabled={!isVideoTabActive}
                aria-pressed={isImmersiveMode}
                aria-label={immersiveToggleLabel}
                data-testid="player-panel-immersive-toggle"
              >
                {immersiveToggleLabel}
              </button>
            ) : null}
            <TabsList className="player-panel__tabs" aria-label="Media categories">
            {visibleTabs.map((tab) => {
                const count =
                  tab.key === 'text'
                    ? (chunks.length > 0 ? chunks.length : media[tab.key].length)
                    : media[tab.key].length;
                return (
                  <TabsTrigger
                    key={tab.key}
                    className="player-panel__tab"
                    value={tab.key}
                    data-testid={`media-tab-${tab.key}`}
                  >
                    {tab.label} ({count})
                  </TabsTrigger>
                );
              })}
            </TabsList>
          </div>
        </header>
        {visibleTabs.map((tab) => {
          const isActive = tab.key === selectedMediaType;
          const tabItems = media[tab.key];
          const tabHasInteractiveContent = tab.key === 'text' && hasInteractiveChunks;
          const tabHasContent = tabItems.length > 0 || tabHasInteractiveContent;
          return (
            <TabsContent key={tab.key} value={tab.key} className="player-panel__panel">
              {!hasAnyMedia && !isLoading ? (
                <p role="status">{emptyMediaMessage}</p>
              ) : !tabHasContent ? (
                <p role="status">{tab.emptyMessage}</p>
              ) : (
                isActive ? (
                  <div className="player-panel__stage">
                    {!mediaComplete ? (
                      <div className="player-panel__notice" role="status">
                        Media generation is still finishing. Newly generated files will appear automatically.
                      </div>
                    ) : null}
                    <div className="player-panel__viewer">
                      {tab.key === 'video' ? (
                        <VideoPlayer
                          files={videoFiles}
                          activeId={selectedItemIds.video}
                          onSelectFile={(fileId) => handleSelectMedia('video', fileId)}
                          autoPlay
                          onPlaybackEnded={() => handleAdvanceMedia('video')}
                          playbackPosition={videoPlaybackPosition}
                          onPlaybackPositionChange={handleVideoProgress}
                          onPlaybackStateChange={handleVideoPlaybackStateChange}
                          isTheaterMode={isImmersiveMode}
                          onExitTheaterMode={handleExitImmersiveMode}
                          onRegisterControls={handleVideoControlsRegistration}
                        />
                      ) : null}
                      {tab.key === 'text' ? (
                        <div className="player-panel__document">
                          {hasTextItems && !selectedItem ? (
                            <div className="player-panel__empty-viewer" role="status">
                              Select a file to preview.
                            </div>
                          ) : textLoading && selectedItem ? (
                            <div className="player-panel__document-status" role="status">
                              Loading document…
                            </div>
                          ) : textError ? (
                            <div className="player-panel__document-error" role="alert">
                              {textError}
                            </div>
                          ) : canRenderInteractiveViewer ? (
                            <InteractiveTextViewer
                              ref={textScrollRef}
                              content={interactiveViewerContent}
                              rawContent={interactiveViewerRaw}
                              chunk={resolvedActiveTextChunk}
                              activeAudioUrl={inlineAudioSelection}
                              noAudioAvailable={inlineAudioUnavailable}
                              onScroll={handleTextScroll}
                              onAudioProgress={handleInlineAudioProgress}
                              getStoredAudioPosition={getInlineAudioPosition}
                              onRegisterInlineAudioControls={handleInlineAudioControlsRegistration}
                              onInlineAudioPlaybackStateChange={handleInlineAudioPlaybackStateChange}
                              onRequestAdvanceChunk={handleInlineAudioEnded}
                              isFullscreen={isInteractiveFullscreen}
                              onRequestExitFullscreen={handleExitInteractiveFullscreen}
                              fullscreenControls={
                                isInteractiveFullscreen ? (
                                  <>
                                    {fullscreenHeader}
                                  {fullscreenNavigationGroup}
                                </>
                              ) : null
                            }
                              translationSpeed={translationSpeed}
                              audioTracks={activeAudioTracks}
                              originalAudioEnabled={effectiveOriginalAudioEnabled}
                              fontScale={isInteractiveFullscreen ? 1.35 : 1}
                          />
                          ) : (
                            <div className="player-panel__document-status" role="status">
                              Interactive reader assets are still being prepared.
                            </div>
                          )}
                        </div>
                      ) : null}
                    </div>
                  </div>
                ) : null
              )}
            </TabsContent>
          );
        })}
        </Tabs>
        </>
      )}
    </section>
  );
}
