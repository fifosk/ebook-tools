export const EMPTY_VTT_DATA_URL = 'data:text/vtt;charset=utf-8,WEBVTT%0A%0A';

export function decodeDataUrl(value: string): string | null {
  const match = value.match(/^data:(.*?)(;base64)?,(.*)$/);
  if (!match) {
    return null;
  }
  const isBase64 = Boolean(match[2]);
  const payload = match[3] ?? '';
  try {
    if (isBase64) {
      return atob(payload);
    }
    return decodeURIComponent(payload);
  } catch {
    return null;
  }
}
