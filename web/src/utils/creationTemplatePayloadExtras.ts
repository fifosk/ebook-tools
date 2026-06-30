import { sanitizeTemplateValue } from './creationTemplateSanitizer';

export const HANDOFF_SOURCE_PAYLOAD_FIELD = 'handoff_source';

const RESERVED_TEMPLATE_PAYLOAD_KEYS = new Set([
  'kind',
  'source',
  'version',
  'source_mode',
  'active_section',
  'form_state'
]);

export function normalizeHandoffSource(value: string | null | undefined): string | null {
  const normalized = value?.trim().toLowerCase() ?? '';
  if (!/^[a-z][a-z0-9_-]{0,31}$/.test(normalized)) {
    return null;
  }
  return normalized;
}

export function buildHandoffPayloadExtras(
  handoffSource: string | null | undefined
): Record<string, unknown> | null {
  const normalized = normalizeHandoffSource(handoffSource);
  return normalized ? { [HANDOFF_SOURCE_PAYLOAD_FIELD]: normalized } : null;
}

export function sanitizeCreationTemplatePayloadExtras(
  value: Record<string, unknown> | null | undefined
): Record<string, unknown> {
  if (!value) {
    return {};
  }
  const sanitized = sanitizeTemplateValue(value);
  const record =
    sanitized && typeof sanitized === 'object' && !Array.isArray(sanitized)
      ? sanitized as Record<string, unknown>
      : {};
  const handoffSource = normalizeHandoffSource(
    typeof record[HANDOFF_SOURCE_PAYLOAD_FIELD] === 'string'
      ? record[HANDOFF_SOURCE_PAYLOAD_FIELD]
      : typeof record.handoffSource === 'string'
        ? record.handoffSource
        : null
  );
  const safe: Record<string, unknown> = {};
  for (const [key, entry] of Object.entries(record)) {
    if (
      RESERVED_TEMPLATE_PAYLOAD_KEYS.has(key) ||
      key === HANDOFF_SOURCE_PAYLOAD_FIELD ||
      key === 'handoffSource' ||
      entry === undefined
    ) {
      continue;
    }
    safe[key] = entry;
  }
  if (handoffSource) {
    safe[HANDOFF_SOURCE_PAYLOAD_FIELD] = handoffSource;
  }
  return safe;
}
