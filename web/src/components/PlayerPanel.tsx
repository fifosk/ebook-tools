import { useCallback, useEffect, useId, useMemo, useRef, useState } from 'react';
import type { ChangeEvent, KeyboardEvent as ReactKeyboardEvent, UIEvent } from 'react';
import type { LiveMediaChunk, LiveMediaItem, LiveMediaState } from '../hooks/useLiveMedia';
import { useMediaMemory } from '../hooks/useMediaMemory';
import { useWakeLock } from '../hooks/useWakeLock';
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
import type { AudioTrackMetadata, ChunkSentenceMetadata, MediaSearchResult } from '../api/dtos';
import { appendAccessToken, buildStorageUrl, resolveJobCoverUrl, resolveLibraryMediaUrl } from '../api/client';
import InteractiveTextViewer from './InteractiveTextViewer';
import { resolve as resolveStoragePath } from '../utils/storageResolver';
import { isAudioFileType } from './player-panel/utils';
import { enableDebugOverlay } from '../player/AudioSyncController';
import type { LibraryOpenInput, LibraryOpenRequest, MediaSelectionRequest } from '../types/player';

const MEDIA_CATEGORIES = ['text', 'audio', 'video'] as const;
type MediaCategory = (typeof MEDIA_CATEGORIES)[number];
type SearchCategory = Exclude<MediaCategory, 'audio'> | 'library';
type NavigationIntent = 'first' | 'previous' | 'next' | 'last';
type PlaybackControls = {
  pause: () => void;
  play: () => void;
};

type InlineAudioKind = 'translation' | 'combined' | 'other';

type InlineAudioOption = {
  url: string;
  label: string;
  kind: InlineAudioKind;
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
];

const DEFAULT_COVER_URL = '/assets/default-cover.png';
const FONT_SCALE_STORAGE_KEY = 'player-panel.fontScalePercent';
const FONT_SCALE_MIN = 100;
const FONT_SCALE_MAX = 300;
const FONT_SCALE_STEP = 5;
const clampFontScalePercent = (value: number) =>
  Math.min(Math.max(value, FONT_SCALE_MIN), FONT_SCALE_MAX);

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
  showOriginalAudioToggle?: boolean;
  onToggleOriginalAudio?: () => void;
  originalAudioEnabled?: boolean;
  disableOriginalAudioToggle?: boolean;
  showSubtitleToggle?: boolean;
  onToggleSubtitles?: () => void;
  subtitlesEnabled?: boolean;
  disableSubtitleToggle?: boolean;
  showCueLayerToggles?: boolean;
  cueVisibility?: {
    original: boolean;
    transliteration: boolean;
    translation: boolean;
  };
  onToggleCueLayer?: (key: 'original' | 'transliteration' | 'translation') => void;
  disableCueLayerToggles?: boolean;
  showTranslationSpeed: boolean;
  translationSpeed: TranslationSpeed;
  translationSpeedMin: number;
  translationSpeedMax: number;
  translationSpeedStep: number;
  onTranslationSpeedChange: (value: TranslationSpeed) => void;
  showSubtitleScale?: boolean;
  subtitleScale?: number;
  subtitleScaleMin?: number;
  subtitleScaleMax?: number;
  subtitleScaleStep?: number;
  onSubtitleScaleChange?: (value: number) => void;
  showSentenceJump?: boolean;
  sentenceJumpValue?: string;
  sentenceJumpMin?: number | null;
  sentenceJumpMax?: number | null;
  sentenceJumpError?: string | null;
  sentenceJumpDisabled?: boolean;
  sentenceJumpInputId?: string;
  sentenceJumpListId?: string;
  sentenceJumpPlaceholder?: string;
  onSentenceJumpChange?: (value: string) => void;
  onSentenceJumpSubmit?: () => void;
  showFontScale?: boolean;
  fontScalePercent?: number;
  fontScaleMin?: number;
  fontScaleMax?: number;
  fontScaleStep?: number;
  onFontScaleChange?: (value: number) => void;
}

export function NavigationControls({
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
  showOriginalAudioToggle = false,
  onToggleOriginalAudio,
  originalAudioEnabled = false,
  disableOriginalAudioToggle = false,
  showSubtitleToggle = false,
  onToggleSubtitles,
  subtitlesEnabled = true,
  disableSubtitleToggle = false,
  showCueLayerToggles = false,
  cueVisibility,
  onToggleCueLayer,
  disableCueLayerToggles = false,
  showTranslationSpeed,
  translationSpeed,
  translationSpeedMin,
  translationSpeedMax,
  translationSpeedStep,
  onTranslationSpeedChange,
  showSubtitleScale = false,
  subtitleScale = 1,
  subtitleScaleMin = 0.5,
  subtitleScaleMax = 2,
  subtitleScaleStep = 0.25,
  onSubtitleScaleChange,
  showSentenceJump = false,
  sentenceJumpValue = '',
  sentenceJumpMin = null,
  sentenceJumpMax = null,
  sentenceJumpError = null,
  sentenceJumpDisabled = false,
  sentenceJumpInputId,
  sentenceJumpListId,
  sentenceJumpPlaceholder,
  onSentenceJumpChange,
  onSentenceJumpSubmit,
  showFontScale = false,
  fontScalePercent = 100,
  fontScaleMin = FONT_SCALE_MIN,
  fontScaleMax = FONT_SCALE_MAX,
  fontScaleStep = FONT_SCALE_STEP,
  onFontScaleChange,
}: NavigationControlsProps) {
  const groupClassName =
    context === 'fullscreen'
      ? 'player-panel__navigation-group player-panel__navigation-group--fullscreen'
      : 'player-panel__navigation-group';
  const navigationClassName =
    context === 'fullscreen'
      ? 'player-panel__navigation player-panel__navigation--fullscreen'
      : 'player-panel__navigation';
  const fullscreenTestId = context === 'panel' ? 'player-panel-interactive-fullscreen' : undefined;
  const playbackLabel = isPlaying ? 'Pause playback' : 'Play playback';
  const playbackIcon = isPlaying ? '⏸' : '▶';
  const auxiliaryToggleVariant = showSubtitleToggle ? 'subtitles' : showOriginalAudioToggle ? 'original' : null;
  const originalToggleClassName = ['player-panel__nav-button', 'player-panel__nav-button--audio', originalAudioEnabled ? 'player-panel__nav-button--audio-on' : 'player-panel__nav-button--audio-off'].join(' ');
  const originalToggleTitle = disableOriginalAudioToggle
    ? 'Original audio will appear after interactive assets regenerate'
    : 'Toggle Original Audio';
  const subtitleToggleClassName = ['player-panel__nav-button', 'player-panel__nav-button--audio', subtitlesEnabled ? 'player-panel__nav-button--audio-on' : 'player-panel__nav-button--audio-off'].join(' ');
  const subtitleToggleTitle = disableSubtitleToggle ? 'Subtitles will appear after media finalizes' : 'Toggle Subtitles';
  const sliderId = useId();
  const subtitleSliderId = useId();
  const jumpInputFallbackId = useId();
  const jumpInputId = sentenceJumpInputId ?? jumpInputFallbackId;
  const fontScaleSliderId = useId();
  const jumpRangeId = `${jumpInputId}-range`;
  const jumpErrorId = `${jumpInputId}-error`;
  const describedBy =
    sentenceJumpError && showSentenceJump
      ? jumpErrorId
      : showSentenceJump && sentenceJumpMin !== null && sentenceJumpMax !== null
      ? jumpRangeId
      : undefined;
  const fullscreenButtonClassName = ['player-panel__nav-button'];
  if (isFullscreen) {
    fullscreenButtonClassName.push('player-panel__nav-button--fullscreen-active');
  }
  const fullscreenIcon = isFullscreen ? '🗗' : '⛶';
  const formattedSpeed = formatTranslationSpeedLabel(translationSpeed);
  const resolvedCueVisibility =
    cueVisibility ??
    ({
      original: true,
      transliteration: true,
      translation: true,
    } as const);
  const handleToggleCueLayer = (key: 'original' | 'transliteration' | 'translation') => {
    onToggleCueLayer?.(key);
  };
  const handleSpeedChange = (event: ChangeEvent<HTMLInputElement>) => {
    const raw = Number.parseFloat(event.target.value);
    if (!Number.isFinite(raw)) {
      return;
    }
    onTranslationSpeedChange(raw);
  };
  const handleSentenceInputChange = (event: ChangeEvent<HTMLInputElement>) => {
    onSentenceJumpChange?.(event.target.value);
  };
  const handleSentenceInputKeyDown = (event: ReactKeyboardEvent<HTMLInputElement>) => {
    if (event.key === 'Enter') {
      event.preventDefault();
      onSentenceJumpSubmit?.();
    }
  };
  const handleFontScaleInputChange = (event: ChangeEvent<HTMLInputElement>) => {
    const raw = Number.parseFloat(event.target.value);
    if (!Number.isFinite(raw)) {
      return;
    }
    onFontScaleChange?.(raw);
  };
  const formattedFontScale = `${Math.round(
    Math.min(Math.max(fontScalePercent, fontScaleMin), fontScaleMax),
  )}%`;

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
        {auxiliaryToggleVariant === 'original' ? (
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
        {auxiliaryToggleVariant === 'subtitles' ? (
          <button
            type="button"
            className={subtitleToggleClassName}
            onClick={onToggleSubtitles}
            disabled={disableSubtitleToggle}
            aria-label="Toggle Subtitles"
            aria-pressed={subtitlesEnabled}
            title={subtitleToggleTitle}
          >
            <span aria-hidden="true" className="player-panel__nav-button-icon">
              {subtitlesEnabled ? '💬' : '🚫'}
            </span>
            <span aria-hidden="true" className="player-panel__nav-button-text">
              Subs
            </span>
          </button>
        ) : null}
        {showCueLayerToggles ? (
          <div
            className="player-panel__subtitle-flags player-panel__subtitle-flags--controls"
            role="group"
            aria-label="Subtitle layers"
          >
            {[
              { key: 'original' as const, label: 'Orig' },
              { key: 'transliteration' as const, label: 'Translit' },
              { key: 'translation' as const, label: 'Trans' },
            ].map((entry) => (
              <button
                key={entry.key}
                type="button"
                className="player-panel__subtitle-flag player-panel__subtitle-flag--compact"
                aria-pressed={resolvedCueVisibility[entry.key]}
                onClick={() => handleToggleCueLayer(entry.key)}
                disabled={disableCueLayerToggles || disableSubtitleToggle}
              >
                {entry.label}
              </button>
            ))}
          </div>
        ) : null}
        <button
          type="button"
          className={fullscreenButtonClassName.join(' ')}
          onClick={onToggleFullscreen}
          disabled={disableFullscreen}
          aria-pressed={isFullscreen}
          aria-label={fullscreenLabel}
          data-testid={fullscreenTestId}
        >
          <span aria-hidden="true">{fullscreenIcon}</span>
        </button>
      </div>
      {showTranslationSpeed ? (
        <div className="player-panel__nav-speed" data-testid="player-panel-speed">
          <label className="player-panel__nav-speed-label" htmlFor={sliderId}>
            Speed
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
              aria-label="Speed"
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
      {showSubtitleScale ? (
        <div className="player-panel__nav-subtitles" data-testid="player-panel-subtitle-scale">
          <label className="player-panel__nav-subtitles-label" htmlFor={subtitleSliderId}>
            Subtitles
          </label>
          <div className="player-panel__nav-subtitles-control">
            <input
              id={subtitleSliderId}
              type="range"
              className="player-panel__nav-subtitles-slider"
              min={subtitleScaleMin}
              max={subtitleScaleMax}
              step={subtitleScaleStep}
              value={subtitleScale}
              onChange={(event) => onSubtitleScaleChange?.(Number(event.target.value))}
              aria-label="Subtitle size"
              aria-valuetext={`${Math.round(subtitleScale * 100)}%`}
            />
            <span className="player-panel__nav-subtitles-value" aria-live="polite">
              {Math.round(subtitleScale * 100)}%
            </span>
          </div>
          <div className="player-panel__nav-subtitles-scale" aria-hidden="true">
            <span>{Math.round(subtitleScaleMin * 100)}%</span>
            <span>{Math.round(subtitleScaleMax * 100)}%</span>
          </div>
        </div>
      ) : null}
      {showSentenceJump ? (
        <div className="player-panel__nav-jump">
          <label className="player-panel__nav-speed-label" htmlFor={jumpInputId}>
            Jump to sentence
          </label>
          <div className="player-panel__nav-jump-control">
            <input
              id={jumpInputId}
              className="player-panel__nav-jump-input"
              type="number"
              inputMode="numeric"
              min={sentenceJumpMin ?? undefined}
              max={sentenceJumpMax ?? undefined}
              step={1}
              list={sentenceJumpListId}
              value={sentenceJumpValue}
              onChange={handleSentenceInputChange}
              onKeyDown={handleSentenceInputKeyDown}
              placeholder={sentenceJumpPlaceholder}
              aria-describedby={describedBy}
              aria-invalid={sentenceJumpError ? 'true' : undefined}
            />
            <button
              type="button"
              className="player-panel__nav-jump-button"
              onClick={onSentenceJumpSubmit}
              disabled={sentenceJumpDisabled || !onSentenceJumpSubmit}
            >
              Go
            </button>
          </div>
          <div className="player-panel__nav-jump-meta" aria-live="polite">
            {sentenceJumpError ? (
              <span id={jumpErrorId} className="player-panel__nav-jump-error">
                {sentenceJumpError}
              </span>
            ) : sentenceJumpMin !== null && sentenceJumpMax !== null ? (
              <span id={jumpRangeId}>
                Range {sentenceJumpMin}–{sentenceJumpMax}
              </span>
            ) : null}
          </div>
        </div>
      ) : null}
      {showFontScale ? (
        <div className="player-panel__nav-font">
          <label className="player-panel__nav-font-label" htmlFor={fontScaleSliderId}>
            Font size
          </label>
          <div className="player-panel__nav-font-control">
            <input
              id={fontScaleSliderId}
              className="player-panel__nav-font-input"
              type="range"
              min={fontScaleMin}
              max={fontScaleMax}
              step={fontScaleStep}
              value={Math.min(Math.max(fontScalePercent, fontScaleMin), fontScaleMax)}
              onChange={handleFontScaleInputChange}
              aria-valuemin={fontScaleMin}
              aria-valuemax={fontScaleMax}
              aria-valuenow={Math.round(fontScalePercent)}
              aria-valuetext={formattedFontScale}
              aria-label="Adjust font size"
            />
            <span className="player-panel__nav-font-value" aria-live="polite">
              {formattedFontScale}
            </span>
          </div>
        </div>
      ) : null}
    </div>
  );
}

function selectInitialTab(media: LiveMediaState): MediaCategory {
  const populated = TAB_DEFINITIONS.find((tab) => media[tab.key].length > 0);
  return populated?.key ?? 'text';
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

function resolveChunkBaseId(chunk: LiveMediaChunk): string | null {
  const textFile = chunk.files.find((file) => file.type === 'text' && typeof file.url === 'string' && file.url.length > 0);
  if (textFile?.url) {
    return deriveBaseIdFromReference(textFile.url) ?? textFile.url ?? null;
  }
  if (chunk.chunkId) {
    return chunk.chunkId;
  }
  if (chunk.rangeFragment) {
    return chunk.rangeFragment;
  }
  if (chunk.metadataPath) {
    return chunk.metadataPath;
  }
  if (chunk.metadataUrl) {
    return chunk.metadataUrl;
  }
  return null;
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

function normaliseBookSentenceCount(value: unknown): number | null {
  if (typeof value === 'number' && Number.isFinite(value)) {
    const safe = Math.max(Math.trunc(value), 0);
    return safe > 0 ? safe : null;
  }

  if (Array.isArray(value)) {
    return value.length;
  }

  if (value && typeof value === 'object') {
    const record = value as Record<string, unknown>;
    const sentences = record.sentences;
    if (Array.isArray(sentences)) {
      return sentences.length;
    }
    const total =
      record.total_sentences ??
      record.sentence_count ??
      record.book_sentence_count ??
      record.total ??
      record.count;
    if (typeof total === 'number' && Number.isFinite(total)) {
      const safe = Math.max(Math.trunc(total), 0);
      return safe > 0 ? safe : null;
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
      if (!isAudioFileType(file.type)) {
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
  const audioUrl = chunk.files.find((file) => isAudioFileType(file.type) && file.url)?.url;
  if (audioUrl) {
    return `audio:${audioUrl}`;
  }
  return null;
}

const CHUNK_METADATA_PREFETCH_RADIUS = 2;
const SINGLE_SENTENCE_PREFETCH_AHEAD = 3;
const MAX_SENTENCE_PREFETCH_COUNT = 400;
const CHUNK_SENTENCE_BOOTSTRAP_COUNT = 12;
const CHUNK_SENTENCE_APPEND_BATCH = 75;

type SentenceLookupEntry = {
  chunkIndex: number;
  localIndex: number;
  total: number;
  baseId: string | null;
};

type SentenceLookupRange = {
  start: number;
  end: number;
  chunkIndex: number;
  baseId: string | null;
};

type SentenceLookup = {
  min: number | null;
  max: number | null;
  exact: Map<number, SentenceLookupEntry>;
  ranges: SentenceLookupRange[];
  suggestions: number[];
};

function isSingleSentenceChunk(chunk: LiveMediaChunk | null | undefined): boolean {
  if (!chunk) {
    return false;
  }
  if (Array.isArray(chunk.sentences) && chunk.sentences.length > 0) {
    return chunk.sentences.length === 1;
  }
  if (typeof chunk.sentenceCount === 'number' && chunk.sentenceCount > 0) {
    return chunk.sentenceCount === 1;
  }
  return false;
}

function getKnownSentenceCount(chunk: LiveMediaChunk | null | undefined): number | null {
  if (!chunk) {
    return null;
  }
  if (Array.isArray(chunk.sentences) && chunk.sentences.length > 0) {
    return chunk.sentences.length;
  }
  if (typeof chunk.sentenceCount === 'number' && chunk.sentenceCount > 0) {
    return chunk.sentenceCount;
  }
  return null;
}

function shouldPrefetchChunk(chunk: LiveMediaChunk | null | undefined): boolean {
  const count = getKnownSentenceCount(chunk);
  if (count === null) {
    return true;
  }
  return count <= MAX_SENTENCE_PREFETCH_COUNT;
}

function partitionChunkSentences(
  sentences: ChunkSentenceMetadata[] | null | undefined,
  bootstrapCount: number,
): { immediate: ChunkSentenceMetadata[]; remainder: ChunkSentenceMetadata[] } {
  if (!Array.isArray(sentences) || sentences.length === 0) {
    return { immediate: [], remainder: [] };
  }
  const take = Math.max(bootstrapCount, 0);
  if (take <= 0 || sentences.length <= take) {
    return { immediate: sentences, remainder: [] };
  }
  return {
    immediate: sentences.slice(0, take),
    remainder: sentences.slice(take),
  };
}

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
  const [pendingChunkSelection, setPendingChunkSelection] =
    useState<{ index: number; token: number } | null>(null);
  const [pendingTextScrollRatio, setPendingTextScrollRatio] = useState<number | null>(null);
  const [sentenceJumpValue, setSentenceJumpValue] = useState('');
  const [sentenceJumpError, setSentenceJumpError] = useState<string | null>(null);
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
const pushChunkMetadata = useCallback(
  (cacheKey: string, payload: ChunkSentenceMetadata[] | null | undefined, append: boolean) => {
    const normalized = Array.isArray(payload) ? payload : [];
    setChunkMetadataStore((current) => {
      const existing = current[cacheKey];
      if (!append && existing !== undefined) {
        return current;
      }
      if (append && normalized.length === 0) {
        return current;
      }
      const base = append && Array.isArray(existing) ? existing : [];
      const nextSentences = append ? base.concat(normalized) : normalized;
      if (append && Array.isArray(existing) && nextSentences.length === existing.length) {
        return current;
      }
      if (!append && existing === nextSentences) {
        return current;
      }
      return {
        ...current,
        [cacheKey]: nextSentences,
      };
    });
  },
  [],
);
const scheduleChunkMetadataAppend = useCallback(
  (cacheKey: string, remainder: ChunkSentenceMetadata[]) => {
    if (!Array.isArray(remainder) || remainder.length === 0) {
      return;
    }
    let offset = 0;
    const batchSize = CHUNK_SENTENCE_APPEND_BATCH;
    const flush = () => {
      const slice = remainder.slice(offset, offset + batchSize);
      offset += slice.length;
      if (slice.length > 0) {
        pushChunkMetadata(cacheKey, slice, true);
      }
      if (offset < remainder.length) {
        if (typeof window !== 'undefined' && typeof window.requestAnimationFrame === 'function') {
          window.requestAnimationFrame(flush);
        } else {
          setTimeout(flush, 16);
        }
      }
    };
    flush();
  },
  [pushChunkMetadata],
);
  const [isInlineAudioPlaying, setIsInlineAudioPlaying] = useState(false);
  const [coverSourceIndex, setCoverSourceIndex] = useState(0);
  const resolveStoredInteractiveFullscreenPreference = () => {
    if (typeof window === 'undefined') {
      return false;
    }
    return window.localStorage.getItem('player.textFullscreenPreferred') === 'true';
  };
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
  const mediaMemory = useMediaMemory({ jobId });
  const { state: memoryState, rememberSelection, rememberPosition, getPosition, findMatchingMediaId, deriveBaseId } = mediaMemory;
  const textScrollRef = useRef<HTMLDivElement | null>(null);
  const inlineAudioControlsRef = useRef<PlaybackControls | null>(null);
  const hasSkippedInitialRememberRef = useRef(false);
  const inlineAudioBaseRef = useRef<string | null>(null);
  const pendingAutoPlayRef = useRef(false);
  const [hasInlineAudioControls, setHasInlineAudioControls] = useState(false);
  const [translationSpeed, setTranslationSpeed] = useState<TranslationSpeed>(DEFAULT_TRANSLATION_SPEED);
  const [fontScalePercent, setFontScalePercent] = useState<number>(() => {
    if (typeof window === 'undefined') {
      return 100;
    }
    const raw = Number.parseFloat(window.localStorage.getItem(FONT_SCALE_STORAGE_KEY) ?? '');
    return Number.isFinite(raw) ? clampFontScalePercent(raw) : 100;
  });
  const [bookSentenceCount, setBookSentenceCount] = useState<number | null>(null);
  const sentenceLookup = useMemo<SentenceLookup>(() => {
    const exact = new Map<number, SentenceLookupEntry>();
    const ranges: SentenceLookupRange[] = [];
    let min = Number.POSITIVE_INFINITY;
    let max = Number.NEGATIVE_INFINITY;
    const boundarySet = new Set<number>();

    const registerBoundary = (value: number | null | undefined): number | null => {
      if (typeof value !== 'number' || !Number.isFinite(value)) {
        return null;
      }
      const normalized = Math.trunc(value);
      boundarySet.add(normalized);
      if (normalized < min) {
        min = normalized;
      }
      if (normalized > max) {
        max = normalized;
      }
      return normalized;
    };

    chunks.forEach((chunk, chunkIndex) => {
      const baseId = resolveChunkBaseId(chunk);
      const start = registerBoundary(chunk.startSentence ?? null);
      const end = registerBoundary(chunk.endSentence ?? null);
      if (start !== null && end !== null && end >= start) {
        ranges.push({ start, end, chunkIndex, baseId });
      }
      if (Array.isArray(chunk.sentences) && chunk.sentences.length > 0) {
        const total = chunk.sentences.length;
        chunk.sentences.forEach((sentence, localIndex) => {
          if (!sentence) {
            return;
          }
          const absolute =
            typeof sentence.sentence_number === 'number' && Number.isFinite(sentence.sentence_number)
              ? Math.trunc(sentence.sentence_number)
              : null;
          if (absolute === null) {
            return;
          }
          boundarySet.add(absolute);
          if (absolute < min) {
            min = absolute;
          }
          if (absolute > max) {
            max = absolute;
          }
          exact.set(absolute, {
            chunkIndex,
            localIndex,
            total,
            baseId,
          });
        });
      }
    });

    const hasBounds = Number.isFinite(min) && Number.isFinite(max);
    const safeMin = hasBounds ? Math.trunc(min) : null;
    const safeMax = hasBounds ? Math.trunc(max) : null;
    const suggestions: number[] = [];
    if (safeMin !== null && safeMax !== null) {
      const span = safeMax - safeMin;
      if (span <= 200) {
        for (let value = safeMin; value <= safeMax; value += 1) {
          suggestions.push(value);
        }
      } else {
        boundarySet.add(safeMin);
        boundarySet.add(safeMax);
        const step = Math.max(1, Math.round(span / 25));
        for (let value = safeMin; value <= safeMax && boundarySet.size < 400; value += step) {
          boundarySet.add(value);
        }
        Array.from(boundarySet)
          .filter((value) => value >= safeMin && value <= safeMax)
          .sort((left, right) => left - right)
          .slice(0, 400)
          .forEach((value) => suggestions.push(value));
      }
    }

    return {
      min: safeMin,
      max: safeMax,
      exact,
      ranges,
      suggestions,
    };
  }, [chunks]);
  useEffect(() => {
    setBookSentenceCount(null);
  }, [jobId]);

  useEffect(() => {
    let cancelled = false;

    if (!jobId || chunks.length === 0) {
      setBookSentenceCount(null);
      return () => {
        cancelled = true;
      };
    }

    const metadataCount = normaliseBookSentenceCount(bookMetadata);
    if (metadataCount !== null) {
      setBookSentenceCount((current) => (current === metadataCount ? current : metadataCount));
      return () => {
        cancelled = true;
      };
    }

    if (bookSentenceCount !== null) {
      return () => {
        cancelled = true;
      };
    }

    const resolveTargetUrl = (): string | null => {
      try {
        return resolveStoragePath(jobId, 'metadata/sentences.json');
      } catch (error) {
        try {
          const encodedJobId = encodeURIComponent(jobId);
          return `/pipelines/jobs/${encodedJobId}/metadata/sentences.json`;
        } catch {
          return null;
        }
      }
    };

    const targetUrl = resolveTargetUrl();
    if (!targetUrl || typeof fetch !== 'function') {
      return () => {
        cancelled = true;
      };
    }

    (async () => {
      try {
        const response = await fetch(targetUrl, { credentials: 'include' });
        if (!response.ok) {
          return;
        }

        let payload: unknown = null;
        if (typeof response.json === 'function') {
          try {
            payload = await response.json();
          } catch {
            payload = null;
          }
        }
        if (payload === null && typeof response.text === 'function') {
          try {
            const raw = await response.text();
            payload = JSON.parse(raw);
          } catch {
            payload = null;
          }
        }

        const count = normaliseBookSentenceCount(payload);
        if (cancelled || count === null) {
          return;
        }
        setBookSentenceCount(count);
      } catch (error) {
        if (import.meta.env.DEV) {
          console.warn('Unable to load book sentence count', targetUrl, error);
        }
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [bookMetadata, bookSentenceCount, chunks.length, jobId]);

  const totalSentencesInBook = bookSentenceCount ?? sentenceLookup.max ?? null;
  const findSentenceTarget = useCallback(
    (sentenceNumber: number) => {
      if (!Number.isFinite(sentenceNumber)) {
        return null;
      }
      const target = Math.trunc(sentenceNumber);
      const exactEntry = sentenceLookup.exact.get(target);
      if (exactEntry) {
        const span = Math.max(exactEntry.total - 1, 1);
        const ratio =
          exactEntry.total > 1 ? exactEntry.localIndex / span : 0;
        return {
          chunkIndex: exactEntry.chunkIndex,
          baseId: exactEntry.baseId,
          ratio: Number.isFinite(ratio) ? Math.min(Math.max(ratio, 0), 1) : 0,
        };
      }
      for (const range of sentenceLookup.ranges) {
        if (target >= range.start && target <= range.end) {
          const span = range.end - range.start;
          const ratio = span > 0 ? (target - range.start) / span : 0;
          return {
            chunkIndex: range.chunkIndex,
            baseId: range.baseId,
            ratio: Number.isFinite(ratio) ? Math.min(Math.max(ratio, 0), 1) : 0,
          };
        }
      }
      return null;
    },
    [sentenceLookup],
  );
  const canJumpToSentence = sentenceLookup.min !== null && sentenceLookup.max !== null;
  const sentenceJumpPlaceholder =
    canJumpToSentence && sentenceLookup.min !== null && sentenceLookup.max !== null
      ? sentenceLookup.min === sentenceLookup.max
        ? `${sentenceLookup.min}`
        : `${sentenceLookup.min}–${sentenceLookup.max}`
      : undefined;
  const handleSentenceJumpChange = useCallback((value: string) => {
    setSentenceJumpValue(value);
    setSentenceJumpError(null);
  }, []);
  const handleSentenceJumpSubmit = useCallback(() => {
    if (!canJumpToSentence) {
      setSentenceJumpError('Sentence navigation unavailable.');
      return;
    }
    const trimmed = sentenceJumpValue.trim();
    if (!trimmed) {
      setSentenceJumpError('Enter a sentence number.');
      return;
    }
    const parsed = Number(trimmed);
    if (!Number.isFinite(parsed)) {
      setSentenceJumpError('Enter a valid sentence number.');
      return;
    }
    const target = Math.trunc(parsed);
    if (
      sentenceLookup.min !== null &&
      sentenceLookup.max !== null &&
      (target < sentenceLookup.min || target > sentenceLookup.max)
    ) {
      setSentenceJumpError(`Enter a number between ${sentenceLookup.min} and ${sentenceLookup.max}.`);
      return;
    }
    const resolution = findSentenceTarget(target);
    if (!resolution) {
      setSentenceJumpError('Sentence not found in current assets.');
      return;
    }
    const chunk = chunks[resolution.chunkIndex];
    if (!chunk) {
      setSentenceJumpError('Sentence chunk is unavailable.');
      return;
    }
    const baseId = resolution.baseId ?? resolveChunkBaseId(chunk);
    if (!baseId) {
      setSentenceJumpError('Unable to locate chunk for this sentence.');
      return;
    }
    setSentenceJumpValue(target.toString());
    setSentenceJumpError(null);
    setPendingSelection({
      baseId,
      preferredType: 'text',
      offsetRatio: resolution.ratio ?? null,
      approximateTime: null,
      token: Date.now(),
    });
  }, [
    canJumpToSentence,
    sentenceJumpValue,
    sentenceLookup.min,
    sentenceLookup.max,
    findSentenceTarget,
    chunks,
    setPendingSelection,
  ]);

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
  useEffect(() => {
    if (import.meta.env.DEV) {
      return enableDebugOverlay();
    }
    return undefined;
  }, []);
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

  const activeItemId = selectedItemIds.text;

  const hasResolvedInitialTabRef = useRef(false);

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

    const currentItem = getMediaItem('text', activeItemId);
    if (!currentItem) {
      return;
    }

    rememberSelection({ media: currentItem });
  }, [
    activeItemId,
    getMediaItem,
    rememberSelection,
    memoryState.currentMediaId,
    memoryState.currentMediaType,
  ]);

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

  const textContentCache = useRef(new Map<string, { raw: string; plain: string }>());
  const [textPreview, setTextPreview] = useState<{ url: string; content: string; raw: string } | null>(null);
  const [textLoading, setTextLoading] = useState(false);
  const [textError, setTextError] = useState<string | null>(null);

  useEffect(() => {
    onVideoPlaybackStateChange?.(false);
  }, [onVideoPlaybackStateChange]);

  useEffect(() => {
    onPlaybackStateChange?.(isInlineAudioPlaying);
  }, [isInlineAudioPlaying, onPlaybackStateChange]);
  const selectedItemId = selectedItemIds.text;
  const textPlaybackPosition = getPosition(selectedItemIds.text);
  const selectedItem = useMemo(() => {
    if (media.text.length === 0) {
      return null;
    }
    if (!selectedItemId) {
      return media.text[0] ?? null;
    }
    return media.text.find((item) => item.url === selectedItemId) ?? media.text[0] ?? null;
  }, [media.text, selectedItemId]);
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
    chunk.files.some((file) => isAudioFileType(file.type) && file.url === audioId),
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
          if (sentences === null) {
            return;
          }
          const { immediate, remainder } = partitionChunkSentences(
            sentences,
            CHUNK_SENTENCE_BOOTSTRAP_COUNT,
          );
          pushChunkMetadata(cacheKey, immediate, false);
          if (remainder.length > 0) {
            scheduleChunkMetadataAppend(cacheKey, remainder);
          }
        })
        .catch((error) => {
          console.warn('Unable to load interactive chunk metadata', error);
        })
        .finally(() => {
          chunkMetadataLoadingRef.current.delete(cacheKey);
        });
    },
    [jobId, pushChunkMetadata, scheduleChunkMetadataAppend],
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
        if (neighbour && (neighbour === activeTextChunk || shouldPrefetchChunk(neighbour))) {
          targets.add(neighbour);
        }
      }

      if (isSingleSentenceChunk(activeTextChunk)) {
        let aheadPrefetched = 0;
        for (
          let lookaheadIndex = activeTextChunkIndex + 1;
          lookaheadIndex < chunks.length && aheadPrefetched < SINGLE_SENTENCE_PREFETCH_AHEAD;
          lookaheadIndex += 1
        ) {
          const lookaheadChunk = chunks[lookaheadIndex];
          if (!lookaheadChunk) {
            continue;
          }
          if (shouldPrefetchChunk(lookaheadChunk)) {
            targets.add(lookaheadChunk);
          }
          aheadPrefetched += 1;
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
    const combinedUrl = activeAudioTracks?.orig_trans?.url ?? null;
    const translationUrl =
      activeAudioTracks?.translation?.url ?? activeAudioTracks?.trans?.url ?? null;
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
  }, [
    activeAudioTracks?.orig_trans?.url,
    activeAudioTracks?.translation?.url,
    activeAudioTracks?.trans?.url,
    hasCombinedAudio,
    showOriginalAudio,
  ]);
  const combinedTrackUrl = activeAudioTracks?.orig_trans?.url ?? null;
  const translationTrackUrl =
    activeAudioTracks?.translation?.url ?? activeAudioTracks?.trans?.url ?? null;
  const activeTimingTrack: 'mix' | 'translation' =
    combinedTrackUrl &&
    ((inlineAudioSelection && inlineAudioSelection === combinedTrackUrl) ||
      (!inlineAudioSelection && effectiveOriginalAudioEnabled))
      ? 'mix'
      : 'translation';
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
          setPendingChunkSelection({ index: chunkMatchIndex, token: selectionToken });
          appliedCategory = 'text';
        } else if (media.text.length > 0) {
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

    if (matchByCategory.audio && visibleInlineAudioOptions.some((option) => option.url === matchByCategory.audio)) {
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
    visibleInlineAudioOptions,
    chunks,
    setPendingChunkSelection,
  ]);

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
  const shouldForceInteractiveViewer = isInteractiveFullscreen;
  const handleInteractiveFullscreenToggle = useCallback(() => {
    setIsInteractiveFullscreen((current) => {
      const next = !current;
      updateInteractiveFullscreenPreference(next);
      return next;
    });
  }, [updateInteractiveFullscreenPreference]);

  const handleExitInteractiveFullscreen = useCallback(() => {
    updateInteractiveFullscreenPreference(false);
    setIsInteractiveFullscreen(false);
  }, [updateInteractiveFullscreenPreference]);
  const panelClassName = 'player-panel';
  useEffect(() => {
    if (!canRenderInteractiveViewer) {
      if (!hasInteractiveChunks && isInteractiveFullscreen) {
        updateInteractiveFullscreenPreference(false);
        setIsInteractiveFullscreen(false);
      }
      return;
    }
    if (interactiveFullscreenPreferenceRef.current && !isInteractiveFullscreen) {
      updateInteractiveFullscreenPreference(true);
      setIsInteractiveFullscreen(true);
    }
  }, [
    canRenderInteractiveViewer,
    hasInteractiveChunks,
    isInteractiveFullscreen,
    updateInteractiveFullscreenPreference,
  ]);
  const hasTextItems = media.text.length > 0;
  const shouldShowInteractiveViewer = canRenderInteractiveViewer || shouldForceInteractiveViewer;
  const shouldShowEmptySelectionPlaceholder =
    hasTextItems && !selectedItem && !shouldForceInteractiveViewer;
  const shouldShowLoadingPlaceholder =
    Boolean(textLoading && selectedItem && !shouldForceInteractiveViewer);
  const shouldShowStandaloneError = Boolean(textError) && !shouldForceInteractiveViewer;
  const navigableItems = useMemo(
    () => media.text.filter((item) => typeof item.url === 'string' && item.url.length > 0),
    [media.text],
  );
  const activeNavigableIndex = useMemo(() => {
    const currentId = selectedItemIds.text;
    if (!currentId) {
      return navigableItems.length > 0 ? 0 : -1;
    }

    const matchIndex = navigableItems.findIndex((item) => item.url === currentId);
    if (matchIndex >= 0) {
      return matchIndex;
    }

    return navigableItems.length > 0 ? 0 : -1;
  }, [navigableItems, selectedItemIds.text]);
  const derivedNavigation = useMemo(() => {
    if (navigableItems.length > 0) {
      return {
        mode: 'media' as const,
        count: navigableItems.length,
        index: Math.max(0, activeNavigableIndex),
      };
    }
    if (chunks.length > 0) {
      const index = activeTextChunkIndex >= 0 ? activeTextChunkIndex : 0;
      return {
        mode: 'chunks' as const,
        count: chunks.length,
        index: Math.max(0, Math.min(index, Math.max(chunks.length - 1, 0))),
      };
    }
    return { mode: 'none' as const, count: 0, index: -1 };
  }, [activeNavigableIndex, activeTextChunkIndex, chunks.length, navigableItems.length]);
  const isFirstDisabled =
    derivedNavigation.count === 0 || derivedNavigation.index <= 0;
  const isPreviousDisabled =
    derivedNavigation.count === 0 || derivedNavigation.index <= 0;
  const isNextDisabled =
    derivedNavigation.count === 0 || derivedNavigation.index >= derivedNavigation.count - 1;
  const isLastDisabled =
    derivedNavigation.count === 0 || derivedNavigation.index >= derivedNavigation.count - 1;
  const playbackControlsAvailable = hasInlineAudioControls;
  const isActiveMediaPlaying = isInlineAudioPlaying;
  const shouldHoldWakeLock = isInlineAudioPlaying;
  useWakeLock(shouldHoldWakeLock);
  const isPlaybackDisabled = !playbackControlsAvailable;
  const isFullscreenDisabled = !canRenderInteractiveViewer;
  const handleTranslationSpeedChange = useCallback((speed: TranslationSpeed) => {
    setTranslationSpeed(normaliseTranslationSpeed(speed));
  }, []);
  const handleFontScaleChange = useCallback((percent: number) => {
    setFontScalePercent(clampFontScalePercent(percent));
  }, []);
  const adjustFontScale = useCallback((direction: 'increase' | 'decrease') => {
    setFontScalePercent((current) => {
      const delta = direction === 'increase' ? FONT_SCALE_STEP : -FONT_SCALE_STEP;
      return clampFontScalePercent(current + delta);
    });
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

  const activateChunk = useCallback(
    (chunk: LiveMediaChunk | null | undefined, options?: { scrollRatio?: number; autoPlay?: boolean }) => {
      if (!chunk) {
        return false;
      }
      const scrollRatio =
        typeof options?.scrollRatio === 'number' ? Math.min(Math.max(options.scrollRatio, 0), 1) : null;
      if (scrollRatio !== null) {
        setPendingTextScrollRatio(scrollRatio);
      }
      const textFile = chunk.files.find(
        (file) => file.type === 'text' && typeof file.url === 'string' && file.url.length > 0,
      );
      if (textFile?.url) {
        setSelectedItemIds((current) =>
          current.text === textFile.url ? current : { ...current, text: textFile.url },
        );
        const textBaseId = deriveBaseIdFromReference(textFile.url);
        rememberPosition({ mediaId: textFile.url, mediaType: 'text', baseId: textBaseId, position: 0 });
      }
      const audioFile = chunk.files.find(
        (file) => isAudioFileType(file.type) && typeof file.url === 'string' && file.url.length > 0,
      );
      if (audioFile?.url) {
        const audioItem = getMediaItem('audio', audioFile.url);
        const audioBaseId = audioItem ? deriveBaseId(audioItem) : deriveBaseIdFromReference(audioFile.url);
        rememberPosition({ mediaId: audioFile.url, mediaType: 'audio', baseId: audioBaseId, position: 0 });
        setInlineAudioSelection((current) => (current === audioFile.url ? current : audioFile.url));
        syncInteractiveSelection(audioFile.url);
        if (options?.autoPlay) {
          pendingAutoPlayRef.current = true;
        }
      }
      return true;
    },
    [
      deriveBaseId,
      getMediaItem,
      rememberPosition,
      setInlineAudioSelection,
      setPendingTextScrollRatio,
      setSelectedItemIds,
      syncInteractiveSelection,
    ],
  );

  const activateTextItem = useCallback(
    (item: LiveMediaItem | null | undefined, options?: { scrollRatio?: number; autoPlay?: boolean }) => {
      if (!item?.url) {
        return false;
      }
      const baseId = deriveBaseId(item) ?? deriveBaseIdFromReference(item.url);
      const chunkIndex = baseId ? findChunkIndexForBaseId(baseId, chunks) : -1;
      if (chunkIndex >= 0) {
        return activateChunk(chunks[chunkIndex], options);
      }
      setSelectedItemIds((current) =>
        current.text === item.url ? current : { ...current, text: item.url },
      );
      if (typeof options?.scrollRatio === 'number') {
        setPendingTextScrollRatio(Math.min(Math.max(options.scrollRatio, 0), 1));
      }
      if (options?.autoPlay) {
        pendingAutoPlayRef.current = true;
      }
      return false;
    },
    [activateChunk, chunks, deriveBaseId, setPendingTextScrollRatio, setSelectedItemIds],
  );

  useEffect(() => {
    if (!pendingChunkSelection) {
      return;
    }

    const { index } = pendingChunkSelection;
    if (index < 0 || index >= chunks.length) {
      setPendingChunkSelection(null);
      return;
    }

    activateChunk(chunks[index], { scrollRatio: 0 });
    setPendingChunkSelection(null);
  }, [activateChunk, chunks, pendingChunkSelection]);

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
      if (navigableItems.length > 0) {
        const currentId = selectedItemIds.text;
        const currentIndex = currentId
          ? navigableItems.findIndex((item) => item.url === currentId)
          : -1;
        const lastIndex = navigableItems.length - 1;
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
        const nextItem = navigableItems[nextIndex];
        if (!nextItem) {
          return;
        }
        activateTextItem(nextItem, { autoPlay: true, scrollRatio: 0 });
        return;
      }

      if (chunks.length > 0) {
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
        activateChunk(targetChunk, { autoPlay: true, scrollRatio: 0 });
        return;
      }

      updateSelection('text', intent);
    },
    [activateChunk, activateTextItem, activeTextChunkIndex, chunks, navigableItems, selectedItemIds.text, updateSelection],
  );

  const handlePauseActiveMedia = useCallback(() => {
    inlineAudioControlsRef.current?.pause();
    setIsInlineAudioPlaying(false);
  }, []);

  const handlePlayActiveMedia = useCallback(() => {
    inlineAudioControlsRef.current?.play();
    setIsInlineAudioPlaying(true);
  }, []);

  const adjustTranslationSpeed = useCallback((direction: 'faster' | 'slower') => {
    setTranslationSpeed((current) => {
      const delta = direction === 'faster' ? TRANSLATION_SPEED_STEP : -TRANSLATION_SPEED_STEP;
      return normaliseTranslationSpeed(current + delta);
    });
  }, []);

  const handleToggleActiveMedia = useCallback(() => {
    if (isActiveMediaPlaying) {
      handlePauseActiveMedia();
    } else {
      handlePlayActiveMedia();
    }
  }, [handlePauseActiveMedia, handlePlayActiveMedia, isActiveMediaPlaying]);

  useEffect(() => {
    if (typeof window === 'undefined') {
      return undefined;
    }
    const isTypingTarget = (target: EventTarget | null): boolean => {
      if (!target || !(target instanceof HTMLElement)) {
        return false;
      }
      const tag = target.tagName;
      if (!tag) {
        return false;
      }
      const editable =
        target.isContentEditable ||
        tag === 'INPUT' ||
        tag === 'TEXTAREA' ||
        tag === 'SELECT';
      return editable;
    };
    const handleKeyDown = (event: globalThis.KeyboardEvent) => {
      if (
        event.defaultPrevented ||
        event.altKey ||
        event.metaKey ||
        event.ctrlKey ||
        isTypingTarget(event.target)
      ) {
        return;
      }
      const key = event.key?.toLowerCase();
      const code = event.code;
      const isArrowRight =
        code === 'ArrowRight' || key === 'arrowright' || event.key === 'ArrowRight';
      const isArrowLeft =
        code === 'ArrowLeft' || key === 'arrowleft' || event.key === 'ArrowLeft';
      if (isArrowRight) {
        handleNavigate('next');
        event.preventDefault();
        return;
      }
      if (isArrowLeft) {
        handleNavigate('previous');
        event.preventDefault();
        return;
      }
      if (key === 'o' && canToggleOriginalAudio) {
        handleOriginalAudioToggle();
        event.preventDefault();
        return;
      }
      if (key === 'f') {
        handleInteractiveFullscreenToggle();
        event.preventDefault();
        return;
      }
      const isArrowUp =
        code === 'ArrowUp' || key === 'arrowup' || event.key === 'ArrowUp';
      if (isArrowUp) {
        adjustTranslationSpeed('faster');
        event.preventDefault();
        return;
      }
      const isArrowDown =
        code === 'ArrowDown' || key === 'arrowdown' || event.key === 'ArrowDown';
      if (isArrowDown) {
        adjustTranslationSpeed('slower');
        event.preventDefault();
        return;
      }
      const isPlusKey =
        key === '+' || key === '=' || code === 'Equal' || code === 'NumpadAdd';
      if (isPlusKey) {
        adjustFontScale('increase');
        event.preventDefault();
        return;
      }
      const isMinusKey =
        key === '-' || key === '_' || code === 'Minus' || code === 'NumpadSubtract';
      if (isMinusKey) {
        adjustFontScale('decrease');
        event.preventDefault();
        return;
      }
      if (!event.shiftKey && (event.code === 'Space' || key === ' ')) {
        handleToggleActiveMedia();
        event.preventDefault();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => {
      window.removeEventListener('keydown', handleKeyDown);
    };
  }, [
    adjustTranslationSpeed,
    adjustFontScale,
    canToggleOriginalAudio,
    handleInteractiveFullscreenToggle,
    handleNavigate,
    handleOriginalAudioToggle,
    handleToggleActiveMedia,
  ]);

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
    const nextAudio = nextChunk.files.find((file) => isAudioFileType(file.type) && file.url);
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
    if (visibleInlineAudioOptions.length === 0) {
      if (inlineAudioSelection) {
        const currentAudio = getMediaItem('audio', inlineAudioSelection);
        if (!currentAudio) {
          setInlineAudioSelection(null);
        }
      }
      return;
    }

    if (inlineAudioSelection) {
      const hasExactMatch = visibleInlineAudioOptions.some((option) => option.url === inlineAudioSelection);
      if (hasExactMatch) {
        return;
      }

      const currentAudio = getMediaItem('audio', inlineAudioSelection);
      const currentBaseId =
        currentAudio ? deriveBaseId(currentAudio) : inlineAudioBaseRef.current ?? deriveBaseIdFromReference(inlineAudioSelection);

      if (currentBaseId) {
        const remapped = visibleInlineAudioOptions.find((option) => {
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
      const fallbackUrl = visibleInlineAudioOptions[0]?.url ?? null;
      if (fallbackUrl) {
        setInlineAudioSelection(fallbackUrl);
        syncInteractiveSelection(fallbackUrl);
      }
      return;
    }

    if (!desiredBaseId) {
      return;
    }

    const preferredOption = visibleInlineAudioOptions.find((option) => {
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
    visibleInlineAudioOptions,
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

  useEffect(() => {
    if (!pendingAutoPlayRef.current) {
      return;
    }
    const controls = inlineAudioControlsRef.current;
    if (!controls) {
      return;
    }
    pendingAutoPlayRef.current = false;
    controls.pause();
    controls.play();
  }, [inlineAudioSelection]);

  useEffect(() => {
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
    selectedItemIds.text,
    textPlaybackPosition,
    textPreview?.url,
    pendingTextScrollRatio,
    getMediaItem,
    deriveBaseId,
    rememberPosition,
  ]);

  useEffect(() => {
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
  }, [selectedItem?.url]);

  useEffect(() => {
    setIsInteractiveFullscreen(false);
    setPendingSelection(null);
    setPendingChunkSelection(null);
    setPendingTextScrollRatio(null);
  }, [normalisedJobId]);

  useEffect(() => {
    onFullscreenChange?.(isInteractiveFullscreen);
  }, [isInteractiveFullscreen, onFullscreenChange]);

  useEffect(() => {
    if (typeof window === 'undefined') {
      return;
    }
    window.localStorage.setItem('player.showOriginalAudio', showOriginalAudio ? 'true' : 'false');
  }, [showOriginalAudio]);

  useEffect(() => {
    if (typeof window === 'undefined') {
      return;
    }
    window.localStorage.setItem(FONT_SCALE_STORAGE_KEY, String(fontScalePercent));
  }, [fontScalePercent]);

  const bookTitle = extractMetadataText(bookMetadata, ['book_title', 'title', 'book_name', 'name']);
  const bookAuthor = extractMetadataText(bookMetadata, ['book_author', 'author', 'writer', 'creator']);
  const sectionLabel = bookTitle ? `Player for ${bookTitle}` : 'Player';
  const loadingMessage = bookTitle ? `Loading generated media for ${bookTitle}…` : 'Loading generated media…';
  const emptyMediaMessage = bookTitle ? `No generated media yet for ${bookTitle}.` : 'No generated media yet.';

  const hasAnyMedia = media.text.length + media.audio.length + media.video.length > 0;
  const headingLabel = bookTitle ?? 'Player';
  const interactiveFontScale = fontScalePercent / 100;
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
  const interactiveFullscreenLabel = isInteractiveFullscreen ? 'Exit fullscreen' : 'Enter fullscreen';
  const sentenceJumpListId = useId();
  const sentenceJumpInputId = useId();
  const sentenceJumpInputFullscreenId = useId();
  const sentenceJumpDisabled = !canJumpToSentence;
  const sentenceJumpDatalist =
    sentenceLookup.suggestions.length > 0 ? (
      <datalist id={sentenceJumpListId}>
        {sentenceLookup.suggestions.map((value) => (
          <option key={value} value={value} />
        ))}
      </datalist>
    ) : null;

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
      showOriginalAudioToggle={canToggleOriginalAudio}
      onToggleOriginalAudio={handleOriginalAudioToggle}
      originalAudioEnabled={effectiveOriginalAudioEnabled}
      disableOriginalAudioToggle={!hasCombinedAudio}
      showTranslationSpeed
      translationSpeed={translationSpeed}
      translationSpeedMin={TRANSLATION_SPEED_MIN}
      translationSpeedMax={TRANSLATION_SPEED_MAX}
      translationSpeedStep={TRANSLATION_SPEED_STEP}
      onTranslationSpeedChange={handleTranslationSpeedChange}
      showSentenceJump={canJumpToSentence}
      sentenceJumpValue={sentenceJumpValue}
      sentenceJumpMin={sentenceLookup.min}
      sentenceJumpMax={sentenceLookup.max}
      sentenceJumpError={sentenceJumpError}
      sentenceJumpDisabled={sentenceJumpDisabled}
      sentenceJumpInputId={sentenceJumpInputId}
      sentenceJumpListId={sentenceJumpListId}
      sentenceJumpPlaceholder={sentenceJumpPlaceholder}
      onSentenceJumpChange={handleSentenceJumpChange}
      onSentenceJumpSubmit={handleSentenceJumpSubmit}
      showFontScale
      fontScalePercent={fontScalePercent}
      fontScaleMin={FONT_SCALE_MIN}
      fontScaleMax={FONT_SCALE_MAX}
      fontScaleStep={FONT_SCALE_STEP}
      onFontScaleChange={handleFontScaleChange}
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
      showOriginalAudioToggle={canToggleOriginalAudio}
      onToggleOriginalAudio={handleOriginalAudioToggle}
      originalAudioEnabled={effectiveOriginalAudioEnabled}
      disableOriginalAudioToggle={!hasCombinedAudio}
      showTranslationSpeed
      translationSpeed={translationSpeed}
      translationSpeedMin={TRANSLATION_SPEED_MIN}
      translationSpeedMax={TRANSLATION_SPEED_MAX}
      translationSpeedStep={TRANSLATION_SPEED_STEP}
      onTranslationSpeedChange={handleTranslationSpeedChange}
      showSentenceJump={canJumpToSentence}
      sentenceJumpValue={sentenceJumpValue}
      sentenceJumpMin={sentenceLookup.min}
      sentenceJumpMax={sentenceLookup.max}
      sentenceJumpError={sentenceJumpError}
      sentenceJumpDisabled={sentenceJumpDisabled}
      sentenceJumpInputId={sentenceJumpInputFullscreenId}
      sentenceJumpListId={sentenceJumpListId}
      sentenceJumpPlaceholder={sentenceJumpPlaceholder}
      onSentenceJumpChange={handleSentenceJumpChange}
      onSentenceJumpSubmit={handleSentenceJumpSubmit}
      showFontScale
      fontScalePercent={fontScalePercent}
      fontScaleMin={FONT_SCALE_MIN}
      fontScaleMax={FONT_SCALE_MAX}
      fontScaleStep={FONT_SCALE_STEP}
      onFontScaleChange={handleFontScaleChange}
    />
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
      {sentenceJumpDatalist}
      {!hasJobId ? (
        <div className="player-panel__empty" role="status">
          <p>No job selected.</p>
        </div>
      ) : (
        <>
          <div className="player-panel__search">
            <MediaSearchPanel currentJobId={jobId} onResultAction={handleSearchSelection} />
          </div>
          <div className="player-panel__tabs-container">
            <header className="player-panel__header">
              <div className="player-panel__tabs-row">{navigationGroup}</div>
            </header>
            <div className="player-panel__panel">
              {!hasAnyMedia && !isLoading ? (
                <p role="status">{emptyMediaMessage}</p>
              ) : !hasTextItems && !hasInteractiveChunks ? (
                <p role="status">No interactive reader media yet.</p>
              ) : (
                <div className="player-panel__stage">
                  {!mediaComplete ? (
                    <div className="player-panel__notice" role="status">
                      Media generation is still finishing. Newly generated files will appear automatically.
                    </div>
                  ) : null}
                  <div className="player-panel__viewer">
                    <div className="player-panel__document">
                      {shouldShowEmptySelectionPlaceholder ? (
                        <div className="player-panel__empty-viewer" role="status">
                          Select a file to preview.
                        </div>
                      ) : shouldShowLoadingPlaceholder ? (
                        <div className="player-panel__document-status" role="status">
                          Loading document…
                        </div>
                      ) : shouldShowStandaloneError ? (
                        <div className="player-panel__document-error" role="alert">
                          {textError}
                        </div>
                      ) : shouldShowInteractiveViewer ? (
                        <>
                          <InteractiveTextViewer
                            ref={textScrollRef}
                            content={interactiveViewerContent}
                            rawContent={interactiveViewerRaw}
                            chunk={resolvedActiveTextChunk}
                            totalSentencesInBook={totalSentencesInBook}
                            activeAudioUrl={inlineAudioSelection}
                            noAudioAvailable={inlineAudioUnavailable}
                            jobId={jobId}
                            onScroll={handleTextScroll}
                            onAudioProgress={handleInlineAudioProgress}
                            getStoredAudioPosition={getInlineAudioPosition}
                            onRegisterInlineAudioControls={handleInlineAudioControlsRegistration}
                            onInlineAudioPlaybackStateChange={handleInlineAudioPlaybackStateChange}
                            onRequestAdvanceChunk={handleInlineAudioEnded}
                            isFullscreen={isInteractiveFullscreen}
                            onRequestExitFullscreen={handleExitInteractiveFullscreen}
                            fullscreenControls={isInteractiveFullscreen ? fullscreenNavigationGroup : null}
                            translationSpeed={translationSpeed}
                            audioTracks={activeAudioTracks}
                            activeTimingTrack={activeTimingTrack}
                            originalAudioEnabled={effectiveOriginalAudioEnabled}
                            fontScale={interactiveFontScale}
                            bookTitle={bookTitle ?? headingLabel}
                            bookCoverUrl={shouldShowCoverImage ? displayCoverUrl : null}
                            bookCoverAltText={coverAltText}
                          />
                          {textLoading && selectedItem ? (
                            <div className="player-panel__document-status" role="status">
                              Loading document…
                            </div>
                          ) : null}
                          {textError ? (
                            <div className="player-panel__document-error" role="alert">
                              {textError}
                            </div>
                          ) : null}
                          {!canRenderInteractiveViewer ? (
                            <div className="player-panel__document-status" role="status">
                              Interactive reader assets are still being prepared.
                            </div>
                          ) : null}
                        </>
                      ) : (
                        <div className="player-panel__document-status" role="status">
                          Interactive reader assets are still being prepared.
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>
        </>
      )}
    </section>
  );
}
