import type { PauseTiming, TrackTimingPayload, WordTiming } from '../api/dtos';

const VALID_TRACK_TYPES: Set<TrackTimingPayload['trackType']> = new Set([
  'translated',
  'original_translated',
  'original'
]);

function toStringOrNull(value: unknown): string | null {
  if (typeof value === 'string') {
    const trimmed = value.trim();
    return trimmed.length > 0 ? trimmed : null;
  }
  return null;
}

function toNumberOrNull(value: unknown): number | null {
  if (typeof value === 'number' && Number.isFinite(value)) {
    return value;
  }
  if (typeof value === 'string') {
    const trimmed = value.trim();
    if (!trimmed) {
      return null;
    }
    const parsed = Number(trimmed);
    return Number.isFinite(parsed) ? parsed : null;
  }
  return null;
}

export function normaliseTrackType(value: unknown): TrackTimingPayload['trackType'] | null {
  const raw = toStringOrNull(value)?.toLowerCase();
  if (!raw) {
    return null;
  }
  if (VALID_TRACK_TYPES.has(raw as TrackTimingPayload['trackType'])) {
    return raw as TrackTimingPayload['trackType'];
  }
  if (raw === 'original-translated' || raw === 'originaltranslated') {
    return 'original_translated';
  }
  if (raw === 'original' || raw === 'orig') {
    return 'original';
  }
  if (raw === 'translation' || raw === 'translated') {
    return 'translated';
  }
  return null;
}

export function normaliseWordLanguage(value: unknown): WordTiming['lang'] | null {
  const raw = toStringOrNull(value)?.toLowerCase();
  if (!raw) {
    return null;
  }
  if (raw === 'orig' || raw === 'original') {
    return 'orig';
  }
  if (raw === 'xlit' || raw === 'translit' || raw === 'transliteration') {
    return 'xlit';
  }
  if (raw === 'trans' || raw === 'translation') {
    return 'trans';
  }
  return null;
}

export function normaliseWordTimings(source: unknown): WordTiming[] {
  if (!Array.isArray(source)) {
    return [];
  }
  const result: WordTiming[] = [];
  source.forEach((entry) => {
    if (!entry || typeof entry !== 'object') {
      return;
    }
    const record = entry as Record<string, unknown>;
    const id = toStringOrNull(record.id);
    const sentenceId = toNumberOrNull(record.sentenceId);
    const tokenIdx = toNumberOrNull(record.tokenIdx);
    const lang = normaliseWordLanguage(record.lang);
    const t0 = toNumberOrNull(record.t0);
    const t1 = toNumberOrNull(record.t1);
    if (!id || sentenceId === null || tokenIdx === null || !lang || t0 === null || t1 === null) {
      return;
    }
    result.push({
      id,
      sentenceId,
      tokenIdx,
      lang,
      text: toStringOrNull(record.text) ?? '',
      t0,
      t1
    });
  });

  result.sort((left, right) => {
    const timeDelta = left.t0 - right.t0;
    if (timeDelta !== 0) {
      return timeDelta;
    }
    const endDelta = left.t1 - right.t1;
    if (endDelta !== 0) {
      return endDelta;
    }
    if (left.sentenceId !== right.sentenceId) {
      return left.sentenceId - right.sentenceId;
    }
    if (left.tokenIdx !== right.tokenIdx) {
      return left.tokenIdx - right.tokenIdx;
    }
    return left.id.localeCompare(right.id);
  });

  return result;
}

export function normalisePauseTimings(source: unknown): PauseTiming[] {
  if (!Array.isArray(source)) {
    return [];
  }
  const result: PauseTiming[] = [];
  source.forEach((entry) => {
    if (!entry || typeof entry !== 'object') {
      return;
    }
    const record = entry as Record<string, unknown>;
    const t0 = toNumberOrNull(record.t0);
    const t1 = toNumberOrNull(record.t1);
    if (t0 === null || t1 === null) {
      return;
    }
    const reasonRaw = toStringOrNull(record.reason);
    const reason =
      reasonRaw === 'silence' || reasonRaw === 'tempo' || reasonRaw === 'gap' ? reasonRaw : undefined;
    result.push({
      t0,
      t1,
      reason
    });
  });
  result.sort((left, right) => {
    const delta = left.t0 - right.t0;
    if (delta !== 0) {
      return delta;
    }
    return left.t1 - right.t1;
  });
  return result;
}

export function normaliseTrackTimingCollection(source: unknown): TrackTimingPayload[] | null {
  if (!source) {
    return null;
  }
  const entries = Array.isArray(source) ? source : [source];
  const payloads: TrackTimingPayload[] = [];
  entries.forEach((entry) => {
    const converted = convertTrackTimingEntry(entry);
    if (converted && converted.length > 0) {
      payloads.push(...converted);
    }
  });
  return payloads.length > 0 ? payloads : null;
}

function convertTrackTimingEntry(entry: unknown): TrackTimingPayload[] | null {
  if (!entry || typeof entry !== 'object') {
    return null;
  }
  const record = entry as Record<string, unknown>;
  const trackType = normaliseTrackType(record.track_type ?? record.trackType);
  if (trackType) {
    const chunkId = toStringOrNull(record.chunk_id ?? record.chunkId) ?? '';
    const words = normaliseWordTimings(record.words);
    const pauses = normalisePauseTimings(record.pauses);
    const trackOffset = toNumberOrNull(record.track_offset ?? record.trackOffset) ?? 0;
    const tempoFactorRaw = toNumberOrNull(record.tempo_factor ?? record.tempoFactor);
    const tempoFactor = tempoFactorRaw && tempoFactorRaw > 0 ? tempoFactorRaw : 1;
    const version = toStringOrNull(record.version) ?? '1';
    return [
      {
        trackType,
        chunkId,
        words,
        pauses,
        trackOffset,
        tempoFactor,
        version
      }
    ];
  }
  return convertLegacyTimingTracks(record);
}

function convertLegacyTimingTracks(record: Record<string, unknown>): TrackTimingPayload[] | null {
  const mixEntries = Array.isArray(record.mix) ? (record.mix as unknown[]) : null;
  const translationEntries = Array.isArray(record.translation)
    ? (record.translation as unknown[])
    : null;
  const originalEntries = Array.isArray(record.original)
    ? (record.original as unknown[])
    : null;
  if (!mixEntries && !translationEntries && !originalEntries) {
    return null;
  }
  const chunkId = toStringOrNull(record.chunk_id ?? record.chunkId) ?? '';
  const trackOffset = toNumberOrNull(record.track_offset ?? record.trackOffset) ?? 0;
  const tempoFactorRaw = toNumberOrNull(record.tempo_factor ?? record.tempoFactor);
  const tempoFactor = tempoFactorRaw && tempoFactorRaw > 0 ? tempoFactorRaw : 1;
  const version = toStringOrNull(record.version) ?? '1';
  const payloads: TrackTimingPayload[] = [];
  if (Array.isArray(translationEntries) && translationEntries.length > 0) {
    const words = buildWordTimingsFromLegacyTokens(
      translationEntries,
      chunkId,
      'trans',
      false,
      true
    );
    if (words.length > 0) {
      payloads.push({
        trackType: 'translated',
        chunkId,
        words,
        pauses: [],
        trackOffset,
        tempoFactor,
        version
      });
    }
  }
  if (Array.isArray(mixEntries) && mixEntries.length > 0) {
    const words = buildWordTimingsFromLegacyTokens(
      mixEntries,
      chunkId,
      'orig',
      true,
      false
    );
    if (words.length > 0) {
      payloads.push({
        trackType: 'original_translated',
        chunkId,
        words,
        pauses: [],
        trackOffset,
        tempoFactor,
        version
      });
    }
  }
  if (Array.isArray(originalEntries) && originalEntries.length > 0) {
    const words = buildWordTimingsFromLegacyTokens(
      originalEntries,
      chunkId,
      'orig',
      false,
      false
    );
    if (words.length > 0) {
      payloads.push({
        trackType: 'original',
        chunkId,
        words,
        pauses: [],
        trackOffset,
        tempoFactor,
        version
      });
    }
  }
  return payloads.length > 0 ? payloads : null;
}

function buildWordTimingsFromLegacyTokens(
  tokens: unknown[],
  chunkId: string,
  defaultLang: WordTiming['lang'],
  laneAware: boolean,
  applyGateOffset: boolean
): WordTiming[] {
  const timings: WordTiming[] = [];
  tokens.forEach((token) => {
    if (!token || typeof token !== 'object') {
      return;
    }
    const record = token as Record<string, unknown>;
    const sentenceId = toNumberOrNull(record.sentenceIdx ?? record.sentenceId);
    const tokenIdx = toNumberOrNull(record.wordIdx ?? record.tokenIdx);
    let start = toNumberOrNull(record.start ?? record.t0);
    let end = toNumberOrNull(record.end ?? record.t1 ?? start);
    if (sentenceId === null || tokenIdx === null || start === null || end === null) {
      return;
    }
    if (applyGateOffset) {
      const gate = toNumberOrNull(record.startGate);
      if (gate !== null && start >= gate - 1e-3) {
        start -= gate;
        end -= gate;
      }
    }
    if (start < 0) {
      end -= start;
      start = 0;
    }
    if (end < start) {
      end = start;
    }
    let lang: WordTiming['lang'] | null = defaultLang;
    if (laneAware) {
      lang = normaliseWordLanguage(record.lane) ?? defaultLang;
    }
    if (!lang) {
      lang = 'trans';
    }
    const id = createLegacyWordTimingId(chunkId, lang, sentenceId, tokenIdx);
    timings.push({
      id,
      sentenceId,
      tokenIdx,
      lang,
      text: toStringOrNull(record.text) ?? '',
      t0: start,
      t1: end
    });
  });
  return timings;
}

function createLegacyWordTimingId(
  chunkId: string,
  lang: WordTiming['lang'],
  sentenceId: number,
  tokenIdx: number
): string {
  const prefix = chunkId || 'chunk';
  return `${prefix}:${lang}:${sentenceId}:${tokenIdx}`;
}

export function attachChunkIdToTimingSource(source: unknown, chunkId: string | null): unknown {
  if (!chunkId || !source || typeof source !== 'object' || Array.isArray(source)) {
    return source;
  }
  const record = source as Record<string, unknown>;
  if ('chunk_id' in record || 'chunkId' in record) {
    return source;
  }
  return { chunk_id: chunkId, ...record };
}
