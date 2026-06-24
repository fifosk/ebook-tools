const SENSITIVE_KEY_MARKERS = [
  'password',
  'secret',
  'token',
  'authorization',
  'authheader',
  'apikey',
  'api_key'
];

function isSensitiveKey(key: string): boolean {
  const normalized = key.replace(/[-_]/g, '').toLowerCase();
  return SENSITIVE_KEY_MARKERS.some((marker) =>
    normalized.includes(marker.replace(/[-_]/g, ''))
  );
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
  return value;
}
