export function formatFileSize(size: number | null | undefined): string | null {
  if (typeof size !== 'number' || !Number.isFinite(size) || size <= 0) {
    return null;
  }

  if (size < 1024) {
    return `${size} B`;
  }

  const units = ['KB', 'MB', 'GB'];
  let value = size;
  let unitIndex = -1;

  while (value >= 1024 && unitIndex + 1 < units.length) {
    value /= 1024;
    unitIndex += 1;
  }

  const formatted = value < 10 ? value.toFixed(1) : Math.round(value).toString();
  const unit = units[Math.max(unitIndex, 0)];

  return `${formatted} ${unit}`;
}

export function formatTimestamp(value: string | null | undefined): string | null {
  if (!value) {
    return null;
  }

  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return null;
  }

  return date.toLocaleString();
}

function hasHtmlTags(value: string): boolean {
  return /<[^>]+>/.test(value);
}

export function extractTextFromHtml(raw: string): string {
  if (!raw) {
    return '';
  }

  const trimmed = raw.trim();
  if (!trimmed) {
    return '';
  }

  let textContent = trimmed;

  if (hasHtmlTags(trimmed)) {
    try {
      if (typeof window !== 'undefined' && 'DOMParser' in window) {
        const parser = new DOMParser();
        const doc = parser.parseFromString(trimmed, 'text/html');
        const body = doc.body;
        textContent = body?.innerText ?? body?.textContent ?? trimmed;
      } else {
        textContent = trimmed
          .replace(/<\s*br\s*\/?\s*>/gi, '\n')
          .replace(/<\s*\/p\s*>/gi, '\n\n')
          .replace(/<[^>]+>/g, ' ');
      }
    } catch (error) {
      console.warn('Unable to parse HTML document for preview', error);
      textContent = trimmed.replace(/<[^>]+>/g, ' ');
    }
  }

  return textContent
    .replace(/\u00a0/g, ' ')
    .replace(/\r\n?/g, '\n')
    .replace(/[ \t]+\n/g, '\n')
    .replace(/\n{3,}/g, '\n\n')
    .trim();
}
