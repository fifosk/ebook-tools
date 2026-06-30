const SENSITIVE_KEY_MARKERS = [
  'apikey',
  'api_key',
  'authkey',
  'auth_key',
  'authheader',
  'authorization',
  'bearer',
  'cookie',
  'credential',
  'csrf',
  'jwt',
  'passkey',
  'pass_key',
  'password',
  'privatekey',
  'private_key',
  'rsskey',
  'rss_key',
  'secret',
  'sessioncookie',
  'sid',
  'token'
];
const PUBLIC_URL_SCHEMES = new Set(['http:', 'https:', 'magnet:']);

function isSensitiveKey(key: string): boolean {
  const normalized = key.replace(/[-_]/g, '').toLowerCase();
  return SENSITIVE_KEY_MARKERS.some((marker) =>
    normalized.includes(marker.replace(/[-_]/g, ''))
  );
}

function stripSensitiveUrlParts(value: string): string {
  const leadingWhitespace = value.match(/^\s*/)?.[0] ?? '';
  const trailingWhitespace = value.match(/\s*$/)?.[0] ?? '';
  const core = value.trim();
  if (!core) {
    return value;
  }
  if (core.toLowerCase().startsWith('magnet:?')) {
    const [query = '', fragment = ''] = core.slice('magnet:?'.length).split('#', 2);
    const publicSearch = new URLSearchParams();
    let removedSearch = false;
    new URLSearchParams(query).forEach((entryValue, key) => {
      if (isSensitiveKey(key)) {
        removedSearch = true;
        return;
      }
      publicSearch.append(key, entryValue);
    });
    if (!removedSearch) {
      return value;
    }
    const nextQuery = publicSearch.toString();
    const nextFragment = fragment ? `#${fragment}` : '';
    return `${leadingWhitespace}magnet:?${nextQuery}${nextFragment}${trailingWhitespace}`;
  }

  let parsed: URL;
  try {
    parsed = new URL(core);
  } catch {
    return value;
  }
  if (!PUBLIC_URL_SCHEMES.has(parsed.protocol)) {
    return value;
  }

  let changed = false;
  if (parsed.username || parsed.password) {
    parsed.username = '';
    parsed.password = '';
    changed = true;
  }

  const publicSearch = new URLSearchParams();
  let removedSearch = false;
  parsed.searchParams.forEach((entryValue, key) => {
    if (isSensitiveKey(key)) {
      removedSearch = true;
      return;
    }
    publicSearch.append(key, entryValue);
  });
  if (removedSearch) {
    const nextSearch = publicSearch.toString();
    parsed.search = nextSearch ? `?${nextSearch}` : '';
    changed = true;
  }

  if (parsed.hash.includes('=')) {
    const fragment = parsed.hash.slice(1);
    const publicFragment = new URLSearchParams();
    let removedFragment = false;
    new URLSearchParams(fragment).forEach((entryValue, key) => {
      if (isSensitiveKey(key)) {
        removedFragment = true;
        return;
      }
      publicFragment.append(key, entryValue);
    });
    if (removedFragment) {
      const nextFragment = publicFragment.toString();
      parsed.hash = nextFragment ? `#${nextFragment}` : '';
      changed = true;
    }
  }

  return changed ? `${leadingWhitespace}${parsed.toString()}${trailingWhitespace}` : value;
}

export function sanitizeTemplateValue(value: unknown): unknown {
  if (Array.isArray(value)) {
    return value.map((entry) => sanitizeTemplateValue(entry));
  }
  if (typeof value === 'object' && value !== null) {
    const sanitized: Record<string, unknown> = {};
    for (const [key, child] of Object.entries(value)) {
      if (isSensitiveKey(key)) {
        continue;
      }
      sanitized[key] = sanitizeTemplateValue(child);
    }
    return sanitized;
  }
  if (typeof value === 'string') {
    return stripSensitiveUrlParts(value);
  }
  return value;
}
