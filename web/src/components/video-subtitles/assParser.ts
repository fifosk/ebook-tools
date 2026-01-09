export type AssSubtitleTrackKind = 'original' | 'translation' | 'transliteration';

export type AssSubtitleLine = {
  tokens: string[];
  currentIndex: number | null;
};

export type AssSubtitleCue = {
  start: number;
  end: number;
  tracks: Partial<Record<AssSubtitleTrackKind, AssSubtitleLine>>;
};

type ParsedToken = {
  text: string;
  isCurrent: boolean;
};

const DIALOGUE_PREFIX = /^dialogue:/i;
const TAG_PATTERN = /\{[^}]*\}/g;

function parseAssTime(value: string): number | null {
  const trimmed = value.trim();
  if (!trimmed) {
    return null;
  }
  const match = trimmed.match(/^(\d+):(\d{1,2}):(\d{2})(?:[.](\d{1,3}))?$/);
  if (!match) {
    return null;
  }
  const hours = Number.parseInt(match[1] ?? '0', 10);
  const minutes = Number.parseInt(match[2] ?? '0', 10);
  const seconds = Number.parseInt(match[3] ?? '0', 10);
  const fractionRaw = match[4] ?? '0';
  const fraction = Number.parseInt(fractionRaw, 10);
  if (!Number.isFinite(hours) || !Number.isFinite(minutes) || !Number.isFinite(seconds) || !Number.isFinite(fraction)) {
    return null;
  }
  const divisor = fractionRaw.length >= 3 ? 1000 : 100;
  const total = hours * 3600 + minutes * 60 + seconds + fraction / divisor;
  return Number.isFinite(total) ? total : null;
}

function splitDialogueFields(payload: string): string[] | null {
  const fields: string[] = [];
  let buffer = '';
  let separators = 0;
  for (let index = 0; index < payload.length; index += 1) {
    const char = payload[index];
    if (char === ',' && separators < 9) {
      fields.push(buffer);
      buffer = '';
      separators += 1;
    } else {
      buffer += char;
    }
  }
  fields.push(buffer);
  if (fields.length < 10) {
    return null;
  }
  return fields;
}

function decodeAssText(value: string): string {
  return value
    .replace(/\\[Nn]/g, ' ')
    .replace(/\\h/g, ' ')
    .replace(/\\\\/g, '\\');
}

function parseAssToken(raw: string): ParsedToken {
  let isCurrent = false;
  const tagMatches = raw.match(TAG_PATTERN);
  if (tagMatches) {
    for (const tag of tagMatches) {
      if (tag.includes('\\b1')) {
        isCurrent = true;
        break;
      }
    }
  }
  const stripped = raw.replace(TAG_PATTERN, '');
  const decoded = decodeAssText(stripped).trim();
  return { text: decoded, isCurrent };
}

function parseAssLine(value: string): AssSubtitleLine | null {
  const rawTokens = value.split(/\s+/).filter(Boolean);
  if (rawTokens.length === 0) {
    return null;
  }
  const tokens: string[] = [];
  let currentIndex: number | null = null;
  rawTokens.forEach((raw) => {
    const parsed = parseAssToken(raw);
    if (!parsed.text) {
      return;
    }
    const index = tokens.length;
    tokens.push(parsed.text);
    if (parsed.isCurrent) {
      currentIndex = index;
    }
  });
  if (tokens.length === 0) {
    return null;
  }
  return { tokens, currentIndex };
}

function parseCueLines(text: string): AssSubtitleLine[] {
  const normalized = text.replace(/\r/g, '');
  const fragments = normalized.split(/\\N|\n/);
  const lines: AssSubtitleLine[] = [];
  for (const fragment of fragments) {
    const parsed = parseAssLine(fragment);
    if (parsed) {
      lines.push(parsed);
    }
  }
  return lines;
}

function buildTracks(lines: AssSubtitleLine[]): AssSubtitleCue['tracks'] {
  const tracks: AssSubtitleCue['tracks'] = {};
  if (lines.length >= 3) {
    tracks.original = lines[0];
    tracks.translation = lines[1];
    tracks.transliteration = lines[2];
    return tracks;
  }
  if (lines.length === 2) {
    tracks.translation = lines[0];
    tracks.transliteration = lines[1];
    return tracks;
  }
  if (lines.length === 1) {
    tracks.translation = lines[0];
  }
  return tracks;
}

export function parseAssSubtitles(payload: string): AssSubtitleCue[] {
  if (!payload) {
    return [];
  }
  const lines = payload.split(/\r?\n/);
  const cues: AssSubtitleCue[] = [];
  for (const line of lines) {
    const trimmed = line.trim();
    if (!trimmed || !DIALOGUE_PREFIX.test(trimmed)) {
      continue;
    }
    const payloadValue = trimmed.replace(DIALOGUE_PREFIX, '').trim();
    const fields = splitDialogueFields(payloadValue);
    if (!fields) {
      continue;
    }
    const start = parseAssTime(fields[1] ?? '');
    const end = parseAssTime(fields[2] ?? '');
    if (start === null || end === null || end <= start) {
      continue;
    }
    const text = fields[9] ?? '';
    const parsedLines = parseCueLines(text);
    if (parsedLines.length === 0) {
      continue;
    }
    const tracks = buildTracks(parsedLines);
    cues.push({ start, end, tracks });
  }
  return cues.sort((a, b) => a.start - b.start);
}
