import type { TextPlayerVariantKind } from '../../text-player/TextPlayer';
import type { VoiceInventoryResponse } from '../../api/dtos';
import { resolveLanguageCode } from '../../constants/languageCodes';
import type { AssSubtitleCue, AssSubtitleTrackKind } from '../../lib/subtitles';
import { Accessors, findActiveIndex, findInsertIndex } from '../../lib/timing/timeSearch';

export type TrackKind = AssSubtitleTrackKind;

export type SubtitleTokenSelection = {
  track: TrackKind;
  index: number;
};

export type TrackLineMap = {
  lines: number[][];
  tokenLine: Map<number, number>;
};

export const TRACK_RENDER_ORDER: TrackKind[] = ['original', 'transliteration', 'translation'];

export const EMPTY_LINE_MAP: TrackLineMap = { lines: [], tokenLine: new Map() };

const cueAccessor = Accessors.startEnd;

export function clampScale(value: number | null | undefined): number {
  if (!Number.isFinite(value) || !value) {
    return 1;
  }
  return Math.max(0.25, Math.min(4, value));
}

export function clampOpacity(value: number | null | undefined): number {
  if (!Number.isFinite(value ?? NaN)) {
    return 0.6;
  }
  return Math.max(0, Math.min(1, value ?? 0.6));
}

export function findActiveCueIndex(cues: AssSubtitleCue[], time: number, lastIndex: number): number {
  if (lastIndex >= 0 && lastIndex < cues.length) {
    const last = cues[lastIndex];
    if (time >= last.start && time < last.end) {
      return lastIndex;
    }
  }
  return findActiveIndex(cues, time, cueAccessor);
}

export function findCueInsertIndex(cues: AssSubtitleCue[], time: number): number {
  return findInsertIndex(cues, time, cueAccessor);
}

export function clampOffset(value: number, containerHeight: number): number {
  const maxUp = Math.max(120, Math.min(containerHeight * 0.45, 360));
  return Math.min(0, Math.max(value, -maxUp));
}

export function toVariantKind(track: TrackKind): TextPlayerVariantKind {
  if (track === 'transliteration') {
    return 'translit';
  }
  return track === 'translation' ? 'translation' : 'original';
}

export function resolveDefaultSelection(
  order: TrackKind[],
  tracks: Partial<Record<TrackKind, AssSubtitleCue['tracks'][TrackKind]>>
): SubtitleTokenSelection | null {
  for (const track of ['translation', 'transliteration', 'original'] as TrackKind[]) {
    if (!order.includes(track)) {
      continue;
    }
    const entry = tracks[track];
    if (!entry || entry.tokens.length === 0) {
      continue;
    }
    const currentIndex = entry.currentIndex ?? 0;
    const safeIndex = Math.max(0, Math.min(currentIndex, entry.tokens.length - 1));
    return { track, index: safeIndex };
  }
  return null;
}

export function resolveShadowTarget(
  track: TrackKind,
  index: number,
  translationTokens: string[] | null,
  transliterationTokens: string[] | null
): SubtitleTokenSelection | null {
  if (!translationTokens || !transliterationTokens) {
    return null;
  }
  if (translationTokens.length !== transliterationTokens.length) {
    return null;
  }
  if (track === 'translation' && index < transliterationTokens.length) {
    return { track: 'transliteration', index };
  }
  if (track === 'transliteration' && index < translationTokens.length) {
    return { track: 'translation', index };
  }
  return null;
}

export function moveIndexWithinLine(
  track: TrackKind,
  index: number,
  delta: -1 | 1,
  tokenCount: number,
  lineMaps: Record<TrackKind, TrackLineMap>
): number {
  if (tokenCount <= 1) {
    return 0;
  }
  const map = lineMaps[track] ?? EMPTY_LINE_MAP;
  const lineIndex = map.tokenLine.get(index);
  if (lineIndex === undefined) {
    return (index + delta + tokenCount) % tokenCount;
  }
  const lineTokens = map.lines[lineIndex] ?? [];
  if (lineTokens.length === 0) {
    return (index + delta + tokenCount) % tokenCount;
  }
  const pos = lineTokens.indexOf(index);
  if (pos === -1) {
    return (index + delta + tokenCount) % tokenCount;
  }
  let nextPos = pos + delta;
  if (nextPos < 0) {
    nextPos = lineTokens.length - 1;
  } else if (nextPos >= lineTokens.length) {
    nextPos = 0;
  }
  return lineTokens[nextPos] ?? index;
}

export function buildSubtitleTtsVoiceOptions(
  voiceInventory: VoiceInventoryResponse | null,
  ttsLanguage: string | null | undefined,
  currentVoice: string | null | undefined
): string[] {
  if (!voiceInventory) {
    return [];
  }
  const ttsLang = ttsLanguage ?? '';
  const resolvedCode = resolveLanguageCode(ttsLang) ?? ttsLang;
  const baseLang = resolvedCode.split(/[-_]/)[0]?.toLowerCase() ?? '';
  const result: string[] = [];
  const seen = new Set<string>();
  const append = (voice: string) => {
    const lower = voice.toLowerCase();
    if (seen.has(lower)) {
      return;
    }
    seen.add(lower);
    result.push(voice);
  };
  if (currentVoice) {
    append(currentVoice);
  }
  for (const voice of voiceInventory.piper ?? []) {
    const piperLang = voice.lang.split(/[-_]/)[0]?.toLowerCase() ?? '';
    if (baseLang && piperLang === baseLang) {
      append(voice.name);
    }
  }
  for (const voice of voiceInventory.macos ?? []) {
    const macLang = (voice.lang ?? '').split(/[-_]/)[0]?.toLowerCase() ?? '';
    if (baseLang && macLang === baseLang) {
      append(voice.name);
    }
  }
  for (const entry of voiceInventory.gtts ?? []) {
    const gLang = (entry.code ?? '').split(/[-_]/)[0]?.toLowerCase() ?? '';
    if (baseLang && gLang === baseLang) {
      append(`gTTS-${entry.code}`);
    }
  }
  return result;
}
