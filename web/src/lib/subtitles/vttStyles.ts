import type { CueVisibility } from './types';

export function injectVttCueStyle(payload: string, backgroundPercent: number, subtitleScale: number): string {
  const clampedBackground = Math.max(0, Math.min(100, Math.round(backgroundPercent / 10) * 10));
  const alpha = clampedBackground / 100;
  const clampedScale = Math.max(0.25, Math.min(4, subtitleScale));
  const scalePercent = Math.round(clampedScale * 100);
  const cueRules = [
    `::cue { font-size: ${scalePercent}% !important; line-height: 1.2 !important; }`,
    clampedBackground === 0
      ? `::cue { background: none !important; background-color: transparent !important; }`
      : `::cue { background: rgba(0, 0, 0, ${alpha}) !important; background-color: rgba(0, 0, 0, ${alpha}) !important; }`,
  ].join('\n');
  const styleBlock = `STYLE\n${cueRules}\n\n`;
  if (!payload) {
    return `WEBVTT\n\n${styleBlock}`;
  }
  if (/^\ufeff?WEBVTT/i.test(payload)) {
    const headerMatch = payload.match(/^\ufeff?WEBVTT[^\n]*\n(?:\n|\r\n)/i);
    if (headerMatch && headerMatch.index === 0) {
      const headerLength = headerMatch[0].length;
      return `${payload.slice(0, headerLength)}${styleBlock}${payload.slice(headerLength)}`;
    }
  }
  return `WEBVTT\n\n${styleBlock}${payload}`;
}

export function filterCueTextByVisibility(rawText: string, visibility: CueVisibility): string {
  if (!rawText) {
    return rawText;
  }
  const lines = rawText.split(/\r?\n/);
  const filtered: string[] = [];

  for (const line of lines) {
    const classMatch = line.match(/<c\.([^>]+)>/i);
    if (classMatch) {
      const classes = classMatch[1]
        .split(/\s+/)
        .map((value) => value.trim())
        .filter(Boolean);
      if (classes.some((value) => value === 'original') && !visibility.original) {
        continue;
      }
      if (classes.some((value) => value === 'transliteration') && !visibility.transliteration) {
        continue;
      }
      if (classes.some((value) => value === 'translation') && !visibility.translation) {
        continue;
      }
    }
    filtered.push(line);
  }

  if (filtered.length === lines.length) {
    return rawText;
  }
  return filtered.join('\n');
}
