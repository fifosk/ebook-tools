import { MY_LINGUIST_EMPTY_SENTINEL } from './constants';

export function loadStored(
  key: string,
  { allowEmpty = false }: { allowEmpty?: boolean } = {},
): string | null {
  if (typeof window === 'undefined') {
    return null;
  }
  try {
    const raw = window.localStorage.getItem(key);
    if (raw === null) {
      return null;
    }
    if (raw === MY_LINGUIST_EMPTY_SENTINEL) {
      return '';
    }
    if (!raw.trim()) {
      return allowEmpty ? '' : null;
    }
    return raw;
  } catch {
    return null;
  }
}

export function storeValue(
  key: string,
  value: string,
  { allowEmpty = false }: { allowEmpty?: boolean } = {},
): void {
  if (typeof window === 'undefined') {
    return;
  }
  try {
    const trimmed = value.trim();
    const next = allowEmpty && !trimmed ? MY_LINGUIST_EMPTY_SENTINEL : trimmed;
    window.localStorage.setItem(key, next);
  } catch {
    return;
  }
}

export function loadStoredBool(key: string, fallback: boolean): boolean {
  if (typeof window === 'undefined') {
    return fallback;
  }
  try {
    const raw = window.localStorage.getItem(key);
    if (raw === null) {
      return fallback;
    }
    const normalized = raw.trim().toLowerCase();
    if (normalized === 'false' || normalized === '0' || normalized === 'off' || normalized === 'no') {
      return false;
    }
    if (normalized === 'true' || normalized === '1' || normalized === 'on' || normalized === 'yes') {
      return true;
    }
    return fallback;
  } catch {
    return fallback;
  }
}

export function loadStoredNumber(key: string): number | null {
  if (typeof window === 'undefined') {
    return null;
  }
  try {
    const raw = window.localStorage.getItem(key);
    if (!raw) {
      return null;
    }
    const parsed = Number(raw);
    if (!Number.isFinite(parsed) || parsed <= 0) {
      return null;
    }
    return parsed;
  } catch {
    return null;
  }
}

export function storeNumber(key: string, value: number): void {
  if (typeof window === 'undefined') {
    return;
  }
  try {
    if (!Number.isFinite(value) || value <= 0) {
      return;
    }
    window.localStorage.setItem(key, String(Math.round(value)));
  } catch {
    return;
  }
}
