import { synthesizeVoicePreview } from '../api/client';
import { resolveLanguageCode } from './languages';

type TtsRequest = {
  text: string;
  language: string;
  voice?: string | null;
  speed?: number | null;
  playbackRate?: number | null;
};

type CacheEntry = {
  url: string;
  blob: Blob;
  createdAt: number;
  lastUsedAt: number;
};

const MAX_CACHE_ENTRIES = 48;

const ttsCache = new Map<string, CacheEntry>();
const ttsInFlight = new Map<string, Promise<CacheEntry>>();

let sharedAudio: HTMLAudioElement | null = null;

function normalizeText(value: string): string {
  return value.trim().replace(/\s+/g, ' ');
}

function normalizeLanguage(value: string): string {
  const resolved = resolveLanguageCode(value || '');
  return resolved.trim() ? resolved.trim() : 'en';
}

function normalizeVoice(value?: string | null): string {
  return (value ?? '').trim();
}

function normalizeSpeed(value?: number | null): string {
  if (typeof value !== 'number' || !Number.isFinite(value)) {
    return '';
  }
  return String(Math.round(value));
}

function buildKey(request: TtsRequest): string {
  const text = normalizeText(request.text);
  const language = normalizeLanguage(request.language);
  const voice = normalizeVoice(request.voice);
  const speed = normalizeSpeed(request.speed);
  return `${language}::${voice}::${speed}::${text}`;
}

function pruneCache(): void {
  if (ttsCache.size <= MAX_CACHE_ENTRIES) {
    return;
  }
  const entries = Array.from(ttsCache.entries()).sort((left, right) => left[1].lastUsedAt - right[1].lastUsedAt);
  let targetSize = MAX_CACHE_ENTRIES;
  const activeUrl = sharedAudio && !sharedAudio.paused ? sharedAudio.src : null;

  for (const [key, entry] of entries) {
    if (ttsCache.size <= targetSize) {
      break;
    }
    if (activeUrl && entry.url === activeUrl) {
      targetSize = Math.max(0, targetSize - 1);
      continue;
    }
    ttsCache.delete(key);
    try {
      URL.revokeObjectURL(entry.url);
    } catch {
      // Ignore revoke errors.
    }
  }
}

export async function getCachedTtsUrl(request: TtsRequest): Promise<{ url: string; cached: boolean }> {
  const normalizedText = normalizeText(request.text);
  if (!normalizedText) {
    throw new Error('No text to speak.');
  }

  const key = buildKey({ ...request, text: normalizedText });
  const existing = ttsCache.get(key);
  if (existing) {
    existing.lastUsedAt = Date.now();
    return { url: existing.url, cached: true };
  }

  const pending = ttsInFlight.get(key);
  if (pending) {
    const entry = await pending;
    entry.lastUsedAt = Date.now();
    return { url: entry.url, cached: true };
  }

  const promise = (async () => {
    const blob = await synthesizeVoicePreview({
      text: normalizedText,
      language: normalizeLanguage(request.language),
      voice: request.voice ?? undefined,
      speed: request.speed ?? undefined,
    });
    const url = URL.createObjectURL(blob);
    const entry: CacheEntry = {
      url,
      blob,
      createdAt: Date.now(),
      lastUsedAt: Date.now(),
    };
    ttsCache.set(key, entry);
    pruneCache();
    return entry;
  })();

  ttsInFlight.set(key, promise);
  try {
    const entry = await promise;
    return { url: entry.url, cached: false };
  } finally {
    ttsInFlight.delete(key);
  }
}

export async function playAudioUrl(
  url: string,
  options: { playbackRate?: number | null } = {},
): Promise<void> {
  if (typeof window === 'undefined') {
    return;
  }
  if (!sharedAudio) {
    sharedAudio = new Audio();
    sharedAudio.preload = 'auto';
  }
  sharedAudio.pause();
  if (sharedAudio.src !== url) {
    sharedAudio.src = url;
  }
  const playbackRate = options.playbackRate;
  if (typeof playbackRate === 'number' && Number.isFinite(playbackRate) && playbackRate > 0) {
    sharedAudio.playbackRate = Math.max(0.25, Math.min(4, playbackRate));
  } else {
    sharedAudio.playbackRate = 1;
  }
  sharedAudio.currentTime = 0;
  await sharedAudio.play();
}

export async function speakText(request: TtsRequest): Promise<{ url: string; cached: boolean }> {
  const result = await getCachedTtsUrl(request);
  await playAudioUrl(result.url, { playbackRate: request.playbackRate });
  return result;
}
