/**
 * Shared metadata formatting utilities used across metadata UI components.
 * Consolidates common functions from jobProgressUtils and bookNarrationUtils.
 */

/**
 * Type guard for plain objects.
 */
export function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

/**
 * Coerce a value to a record type, returning null if not an object.
 */
export function coerceRecord(value: unknown): Record<string, unknown> | null {
  return isRecord(value) ? value : null;
}

/**
 * Normalize a text value by trimming whitespace.
 * Returns null for non-string, empty, or whitespace-only values.
 */
export function normalizeTextValue(value: unknown): string | null {
  if (typeof value !== 'string') {
    return null;
  }
  const trimmed = value.trim();
  return trimmed.length > 0 ? trimmed : null;
}

/**
 * Coerce a value to a number, returning null if not a finite number.
 */
export function coerceNumber(value: unknown): number | null {
  if (typeof value === 'number' && Number.isFinite(value)) {
    return value;
  }
  if (typeof value === 'string') {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : null;
  }
  return null;
}

/**
 * Normalize a list of strings, filtering out empty entries.
 */
export function normalizeStringList(value: unknown): string[] {
  if (!Array.isArray(value)) {
    return [];
  }
  return value
    .map((entry) => {
      if (typeof entry === 'string') {
        return entry.trim();
      }
      if (entry === null || entry === undefined) {
        return '';
      }
      return String(entry).trim();
    })
    .filter((entry) => entry.length > 0);
}

/**
 * Format a list of genres/categories for display.
 * Handles both string (comma-separated) and array formats.
 * Returns null if no valid genres, otherwise returns comma-separated string.
 * Limits to maxItems (default 5) to avoid overly long lists.
 */
export function formatGenreList(value: unknown, maxItems: number = 5): string | null {
  // Handle string format (comma-separated)
  if (typeof value === 'string') {
    const trimmed = value.trim();
    return trimmed.length > 0 ? trimmed : null;
  }
  // Handle array format
  const items = normalizeStringList(value);
  if (items.length === 0) {
    return null;
  }
  const limited = items.slice(0, maxItems);
  return limited.join(', ');
}

/**
 * Format a TV episode code as S01E02 format.
 * Returns null if season or episode is invalid.
 */
export function formatEpisodeCode(season: number | null, episode: number | null): string | null {
  if (!season || !episode) {
    return null;
  }
  if (!Number.isInteger(season) || !Number.isInteger(episode) || season <= 0 || episode <= 0) {
    return null;
  }
  return `S${season.toString().padStart(2, '0')}E${episode.toString().padStart(2, '0')}`;
}

/**
 * Normalize an ISBN candidate by removing non-numeric characters.
 * Returns null if the result is not a valid ISBN-10 or ISBN-13.
 */
export function normalizeIsbnCandidate(value: string | null | undefined): string | null {
  if (!value) {
    return null;
  }
  const cleaned = value.replace(/[^0-9Xx]/g, '').toUpperCase();
  if (cleaned.length === 10 || cleaned.length === 13) {
    return cleaned;
  }
  return null;
}

/**
 * Format a duration in seconds as HH:MM:SS or MM:SS.
 * Returns null if value is not a valid number.
 */
export function formatDuration(seconds: number | null | undefined): string | null {
  if (seconds === null || seconds === undefined || !Number.isFinite(seconds) || seconds < 0) {
    return null;
  }
  const totalSeconds = Math.floor(seconds);
  const hours = Math.floor(totalSeconds / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  const remainingSeconds = totalSeconds % 60;
  const parts = [minutes.toString().padStart(2, '0'), remainingSeconds.toString().padStart(2, '0')];
  if (hours > 0) {
    parts.unshift(hours.toString().padStart(2, '0'));
  }
  return parts.join(':');
}

/**
 * Format a year value for display.
 * Extracts year from full date strings if needed.
 */
export function formatYear(value: unknown): string | null {
  if (typeof value === 'number') {
    if (Number.isInteger(value) && value > 1800 && value < 2200) {
      return value.toString();
    }
    return null;
  }
  if (typeof value === 'string') {
    const trimmed = value.trim();
    // Check if it's a 4-digit year
    if (/^\d{4}$/.test(trimmed)) {
      return trimmed;
    }
    // Try to extract year from date string (YYYY-MM-DD or similar)
    const match = trimmed.match(/^(\d{4})/);
    if (match) {
      return match[1];
    }
    return null;
  }
  return null;
}

/**
 * Get a string field from a record, returning null if missing or invalid.
 */
export function getStringField(
  source: Record<string, unknown> | null | undefined,
  key: string,
): string | null {
  if (!source) {
    return null;
  }
  const value = source[key];
  return typeof value === 'string' && value.trim() ? value.trim() : null;
}

/**
 * Get a number field from a record, returning null if missing or invalid.
 */
export function getNumberField(
  source: Record<string, unknown> | null | undefined,
  key: string,
): number | null {
  if (!source) {
    return null;
  }
  return coerceNumber(source[key]);
}
