function stripQuery(value: string): string {
  return value.replace(/[?#].*$/, '');
}

function safeDecodeURIComponent(value: string): string {
  try {
    return decodeURIComponent(value);
  } catch {
    return value;
  }
}

function looksLikeFilename(value: string): boolean {
  return /\.[A-Za-z0-9]{1,8}$/.test(value);
}

export function formatMediaDropdownLabel(
  raw: string | null | undefined,
  fallback: string,
): string {
  const trimmed = typeof raw === 'string' ? raw.trim() : '';
  if (!trimmed) {
    return fallback;
  }

  const withoutQuery = stripQuery(trimmed);
  const decoded = safeDecodeURIComponent(withoutQuery);
  const normalised = decoded.replace(/\\/g, '/');
  const leaf = normalised.split('/').filter(Boolean).pop() ?? decoded;
  const leafTrimmed = leaf.trim();

  if (!leafTrimmed) {
    return fallback;
  }

  const separators = [' - ', ' — ', ' – ', ': '];
  for (const separator of separators) {
    const idx = leafTrimmed.lastIndexOf(separator);
    if (idx > 0) {
      const candidate = leafTrimmed.slice(idx + separator.length).trim();
      if (candidate && looksLikeFilename(candidate)) {
        return candidate;
      }
    }
  }

  return leafTrimmed || fallback;
}

