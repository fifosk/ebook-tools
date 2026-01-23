/**
 * Utility functions for Youtube Player components
 * Pure functions with no side effects - easy to test and reuse
 */

/**
 * Replace the file extension in a URL while preserving query params and hash
 * @example replaceUrlExtension("video.mp4?id=123#t=10", ".webm") // "video.webm?id=123#t=10"
 */
export function replaceUrlExtension(value: string, suffix: string): string | null {
  const trimmed = value.trim();
  if (!trimmed) {
    return null;
  }
  const [pathPart, hashPart] = trimmed.split('#', 2);
  const [pathOnly, queryPart] = pathPart.split('?', 2);
  if (!pathOnly || !/\.[^/.]+$/.test(pathOnly)) {
    return null;
  }
  let result = pathOnly.replace(/\.[^/.]+$/, suffix);
  if (queryPart) {
    result += `?${queryPart}`;
  }
  if (hashPart) {
    result += `#${hashPart}`;
  }
  return result;
}

/**
 * Read a nested value from an object using a path array
 * @example readNestedValue({a: {b: {c: 42}}}, ['a', 'b', 'c']) // 42
 */
export function readNestedValue(source: unknown, path: string[]): unknown {
  let current: unknown = source;
  for (const key of path) {
    if (!current || typeof current !== 'object') {
      return null;
    }
    current = (current as Record<string, unknown>)[key];
  }
  return current;
}

/**
 * Coerce an unknown value to a Record or null
 * Safe type guard for object values
 */
export function coerceRecord(value: unknown): Record<string, unknown> | null {
  if (!value || typeof value !== 'object' || Array.isArray(value)) {
    return null;
  }
  return value as Record<string, unknown>;
}

/**
 * Read a string value from a record, returning null if not found or not a string
 * Also trims and returns null for empty strings
 */
export function readStringValue(
  source: Record<string, unknown> | null | undefined,
  key: string
): string | null {
  if (!source) {
    return null;
  }
  const value = source[key];
  if (typeof value !== 'string') {
    return null;
  }
  const trimmed = value.trim();
  return trimmed ? trimmed : null;
}
