export const TWEMOJI_SVG_BASE_URL = 'https://cdn.jsdelivr.net/gh/twitter/twemoji@14.0.2/assets/svg';

export function prefersNativeEmojiFlags(): boolean {
  if (typeof navigator === 'undefined') {
    return true;
  }

  const platform =
    typeof (navigator as unknown as { userAgentData?: { platform?: string } }).userAgentData?.platform === 'string'
      ? (navigator as unknown as { userAgentData: { platform: string } }).userAgentData.platform
      : navigator.platform ?? '';
  const ua = navigator.userAgent ?? '';
  const combined = `${platform} ${ua}`.toLowerCase();

  if (combined.includes('windows') || combined.includes('windows nt') || combined.includes('win32') || combined.includes('win64')) {
    return false;
  }

  return true;
}

export function emojiToTwemojiCodepoint(emoji: string): string | null {
  const trimmed = emoji.trim();
  if (!trimmed) {
    return null;
  }

  const codepoints: string[] = [];
  for (const symbol of Array.from(trimmed)) {
    const cp = symbol.codePointAt(0);
    if (cp === undefined) {
      continue;
    }
    if (cp === 0xfe0f) {
      continue;
    }
    codepoints.push(cp.toString(16));
  }

  return codepoints.length > 0 ? codepoints.join('-') : null;
}

export function twemojiSvgUrlForEmoji(emoji: string): string | null {
  const codepoint = emojiToTwemojiCodepoint(emoji);
  if (!codepoint) {
    return null;
  }
  return `${TWEMOJI_SVG_BASE_URL}/${codepoint}.svg`;
}
